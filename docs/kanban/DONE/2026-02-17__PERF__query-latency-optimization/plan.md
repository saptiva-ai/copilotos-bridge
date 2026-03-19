# Plan — Query Latency Optimization

## Baseline (research.md)

| Query type | MCP block | LLM wait | Total |
|-----------|----------:|--------:|------:|
| RANKING quebrantos (cold) | 14.9s | 4.3s | 19.3s |
| TREND tasa_mn (cold) | 9.4s | 7.4s | 16.9s |
| ICAP snapshot (cold) | 9.0s | 3.9s | 12.9s |
| **Promedio** | **11.1s** | **5.2s** | **16.4s** |

Distribución: MCP blocking 68% | LLM wait 32% | LLM gen ~0%

---

## Phase 0 — Quick Wins (backend-only, no plugin changes)

### 0.1 Remove redundant catalog check (~50ms saved)

**File**: `apps/backend/src/services/tool_execution_service.py`

`handle_catalog_query()` is called TWICE:
- Line ~428: Fast path (before classification) — correct
- Line ~782: After classification (redundant) — DEAD CODE

If a query is catalog, it returns at line 429. The second call at 782 ALWAYS returns None.

**Action**: Delete lines 777-789 (second catalog check block).

### 0.2 Improve cache key generation (cache hit rate: <1% → ~40%)

**File**: `apps/backend/src/services/tool_execution_service.py`

Current cache key: `mcp:tool:bank_analytics:{message[:100]}:{params_hash}`

Problems:
- `message[:100]` truncates — different queries can collide
- No normalization — "IMOR de INVEX" ≠ "imor de invex"
- Acronym variants miss cache — "pdm" vs "participación de mercado"

**Action**: Replace with normalized full-message hash:
```python
normalized = _normalize_acronyms(combined_message.lower().strip())
msg_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
cache_key = f"mcp:tool:bank_analytics:{msg_hash}:{params_hash}"
```

### 0.3 Increase bank_analytics cache TTL (300s → 900s)

**File**: `apps/backend/src/services/tool_execution_service.py`

Banking regulatory data (CNBV) updates monthly. 5-minute TTL is unnecessarily aggressive.
Increase to 15 minutes for bank_analytics results.

**Action**: Change `TOOL_CACHE_TTL[TOOL_NAME_BANK_ANALYTICS]` from 300 to 900.

### 0.4 Add [PERF] timing instrumentation

**Files**:
- `apps/backend/src/services/tool_execution_service.py` — `invoke_bank_analytics()` total + sub-phases
- `apps/backend/src/services/streaming/bank_advisor_precheck.py` — `check_and_invoke()` breakdown

Add `time.perf_counter()` at key pipeline points:
1. `t0`: Entry to `check_and_invoke()`
2. `t1`: After `load_recent_messages()`
3. `t2`: After `should_run_advisor()`
4. `t3`: After `invoke_bank_analytics()` returns
5. Inside `invoke_bank_analytics()`:
   - `ta`: Entry
   - `tb`: After catalog fast path
   - `tc`: After classification (`is_bank_query`)
   - `td`: After cache check
   - `te`: After `query_bank_analytics()` (MCP HTTP call)

Log with `[PERF]` prefix for easy grep in production.

### 0.5 RAG streaming-first with safe fallback (ahorro TTFB: 1-4s)

**File**: `apps/backend/src/services/streaming/chat_stream_producer.py`

Actualmente el path con chart/RAG hacía `chat_completion()` (no-streaming) y
troceaba texto localmente. Cambiar a:

1. Intentar `chat_completion_stream()` primero
2. Si no llegan chunks o falla, fallback a `chat_completion()`

Esto reduce tiempo al primer chunk sin sacrificar estabilidad.

### 0.6 Deterministic precheck fast-path (ahorro: 0.5-3s)

**File**: `apps/backend/src/services/streaming/bank_advisor_precheck.py`

Antes de ejecutar scoring semántico costoso:

1. Si query tiene señales bancarias de alta confianza → `should_run=True`
2. Si query es claramente no bancaria → `should_run=False`
3. Solo casos ambiguos pasan al scorer semántico completo

### 0.7 Prompt overhead trim en chart path (ahorro: ~100-400ms p95)

**Files**:
- `apps/backend/src/routers/chat/handlers/streaming_handler.py`
- `apps/backend/src/services/streaming/bank_advisor_precheck.py`

1. Evitar fetch de `list_bank_advisor_tools()` cuando ya existe `bank_chart_data`
   (query ya resuelta por Bank Advisor; tools discoverability agrega latencia sin valor).
2. Gate con flag `BANK_TOOLS_PROMPT_ENABLED` para benchmark A/B.
3. Normalizar acrónimos antes del hash de routing cache (`routing:should_run:v2:*`)
   para subir hit-rate entre variantes ("ICPA" vs "ICAP").

### 0.8 Reusar HTTP client hacia bank-advisor RPC (ahorro: ~50-250ms por llamada caliente)

**File**: `apps/backend/src/services/bank_analytics_client.py`

1. Reemplazar creación de `httpx.AsyncClient` por llamada en hot-path:
   - `list_bank_advisor_tools()`
   - `call_bank_advisor_tool()`
   - `query_bank_analytics()`
2. Reusar un client por event loop (keep-alive activo) para reducir handshake/connection setup.
3. Mantener compatibilidad con tests que mockean `httpx.AsyncClient` (bypass de reuse en modo mock).

### 0.9 Tools list cache con TTL + stale-while-revalidate (ahorro: ~50-300ms p95 en prompt build)

**File**: `apps/backend/src/services/bank_analytics_client.py`

1. Agregar TTL configurable para `list_bank_advisor_tools` (`BANK_ADVISOR_TOOLS_CACHE_TTL_SECONDS`, default 600s).
2. Si cache está stale y `refresh=False`, devolver cache inmediato y disparar refresh en background.
3. Mantener path síncrono sólo para cold start/refresh explícito.

### 0.10 Clarification fast-path sin LLM (ahorro: ~1.0-2.2s en respuestas de aclaración)

**File**: `apps/backend/src/services/streaming/chat_stream_producer.py`

1. Si `bank_chart_data.type == "clarification"`, omitir llamada a `chat_completion_stream()`.
2. Reusar mensaje de aclaración (`response_text`/`message`) como respuesta final directa.
3. Mantener emisión de `bank_clarification` (ya enviada por `ChartFlowHandler`) y chunks de texto para persistencia/historial.

---

## Phase 1 — Plugin SQL optimization (future, requires plugin changes)

- Profile slow SQL queries in bank-advisor plugin
- Add database indexes for common query patterns
- Optimize DataFrame → Plotly serialization

## Phase 2 — LLM pipeline optimization (future)

- Reduce system prompt size for deterministic queries
- Investigate Saptiva streaming configuration
- Consider response templates for common patterns

---

## Validation

```bash
# Unit tests
python3.11 -m pytest apps/backend/tests/ -x -q

# E2E regression
python3.11 tests/e2e/charts/test_tasa_me_dual_prompts.py
python3.11 tests/e2e/charts/test_tasa_mn_dual_prompts.py
python3.11 tests/e2e/charts/test_quebrantos_cc_yearly_bar_chart.py

# Perf trace (manual)
python3.11 tests/e2e/charts/perf_trace_query.py
```

## Risk Assessment

- **Phase 0.1** (remove redundant call): Zero risk — dead code removal
- **Phase 0.2** (cache key): Low risk — better normalization increases hits, doesn't break misses
- **Phase 0.3** (TTL increase): Low risk — worst case is 15min stale data (acceptable for monthly data)
- **Phase 0.4** (instrumentation): Zero risk — logging only, no behavior change
- **Phase 0.5** (RAG streaming-first): Low risk — fallback mantiene comportamiento previo
- **Phase 0.6** (deterministic precheck): Low risk — casos ambiguos conservan scorer semántico
- **Phase 0.7** (prompt/cache trim): Low risk — sólo omite trabajo redundante y versiona cache key
- **Phase 0.8** (HTTP client reuse): Low risk — cambia transporte HTTP, no lógica de negocio
- **Phase 0.9** (tools stale-while-revalidate): Low risk — prioriza latencia usando cache existente
- **Phase 0.10** (clarification fast-path): Low risk — evita roundtrip LLM sólo cuando ya existe aclaración estructurada

## Update 2026-02-18

- Aplicado 0.5: streaming-first en RAG con fallback a no-streaming.
- Aplicado 0.6: fast-path determinístico en precheck.
- Aplicado 0.7: skip de bank-tools markdown en chart path + cache key normalizada v2.
- Aplicado 0.8: reusable HTTP client para RPC de bank-advisor en hot-path.
- Aplicado 0.9: cache TTL + stale-while-revalidate para `list_bank_advisor_tools`.
- Aplicado 0.10: clarification fast-path en `ChatStreamProducer` (sin LLM cuando ya hay `bank_clarification`).
