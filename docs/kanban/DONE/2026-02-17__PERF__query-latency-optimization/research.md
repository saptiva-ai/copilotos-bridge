# Research — Query Latency Optimization

## Fecha: 2026-02-17

## Metodología

Script `tests/e2e/charts/perf_trace_query.py` mide timestamps reales de cada SSE event
desde el cliente. Se ejecutaron 2 prompts × 2 runs (cold cache + warm cache).

## Resultados reales

### Run 1 (cold cache — sin queries previas)

| Fase | RANKING (snapshot) | TREND (peer_average) |
|------|-------------------:|---------------------:|
| **1. MCP blocking** (setup→meta) | **14,929ms (14.9s)** | **9,397ms (9.4s)** |
| 2. meta→chart | 0.2ms | 0.6ms |
| 3. chart→first LLM chunk | 4,336ms (4.3s) | 7,441ms (7.4s) |
| 4. LLM generation (all chunks) | 35ms | 20ms |
| **TOTAL** | **19,300ms (19.3s)** | **16,859ms (16.9s)** |

### Run 2 (warm cache — misma query repetida)

| Fase | RANKING (snapshot) | TREND (peer_average) |
|------|-------------------:|---------------------:|
| **1. MCP blocking** (setup→meta) | **8,574ms (8.6s)** | **8,453ms (8.5s)** |
| 2. meta→chart | 0.2ms | 0.6ms |
| 3. chart→first LLM chunk | 4,600ms (4.6s) | 7,440ms (7.5s) |
| 4. LLM generation (all chunks) | 40ms | 17ms |
| **TOTAL** | **13,214ms (13.2s)** | **15,930ms (15.9s)** |

## Hallazgos clave

### 1. MCP blocking es 50-80% del tiempo total

La fase `BankAdvisorPreCheckService.check_and_invoke()` bloquea TODO antes de
que el streaming pueda comenzar. Incluye:
- QueryRouter classification (regex + optional semantic scoring)
- Context enrichment (last_metric, last_banks, memory)
- MCP HTTP call to bank-advisor plugin (JSON-RPC POST /rpc)
- SQL query execution in bank-advisor
- Chart data formatting (DataFrame → Plotly config)

**Cold: 9.4-14.9s | Warm: 8.5-8.6s**

El cache reduce RANKING de 14.9→8.6s (6.3s savings), pero TREND apenas mejora
(9.4→8.5s). Esto sugiere que el cache cubre clasificación pero NO resultados MCP.

### 2. LLM generation es instantánea — el wait es el cuello de botella

Los chunks LLM llegan en BURST (<50ms para todos). No hay streaming real
token-by-token. La latencia del LLM es:
- **Connect + thinking time**: 4.3-7.5s (espera hasta primer token)
- **Generation**: <50ms (todos los chunks llegan juntos)

Esto indica que el backend **buferea los SSE events** en vez de flushearlos
individualmente. Los chunks se acumulan hasta que el asyncio event loop los
despacha en batch.

### 3. Chart y meta llegan simultáneamente

```
14929.0ms  meta
14929.1ms  chunk (133 chars — pre-chart text)
14929.2ms  bank_chart (2431B)
```

Los 3 events se emiten en <0.3ms — confirma que `chat_stream_producer.py`
emite chart inmediatamente después de meta, sin latencia adicional.

### 4. No hay streaming real desde Saptiva

Los chunks del LLM (50 chars cada uno) llegan TODOS en el mismo momento:
```
19265.4ms  chunk  chars=50
19265.4ms  chunk  chars=50
19265.5ms  chunk  chars=50
19265.5ms  chunk  chars=50
19265.5ms  chunk  chars=50
```

Esto sugiere que Saptiva responde con el texto completo y el backend lo
trocea artificialmente en chunks de 50 chars. NO es streaming real.

### 5. Corrección del diagnóstico (2026-02-18)

El burst de chunks no prueba por sí solo que Saptiva no streamee. En el backend,
el flujo con `bank_chart_data` usaba explícitamente `chat_completion()` (no
streaming) dentro de `chat_stream_producer.py` (`_handle_rag_context_path`), y
luego troceaba localmente la respuesta con `ChunkEmitter`.

Implicación: parte de la latencia percibida (chart → primer chunk) era una
decisión del pipeline backend, no necesariamente del proveedor LLM.

## Distribución del tiempo (promedio)

```
|████████████████████████|░░░░░░░░░░░|░░|
0s       MCP blocking      LLM wait   Gen
         ~10s (60%)         ~6s (35%)  <0.1s (1%)
```

## Oportunidades de optimización

### P0 — Cache de resultados MCP en Redis (ahorro: 5-12s)

Actualmente solo se cachea la clasificación del QueryRouter, NO los resultados
del MCP tool. Para queries idénticas de onboarding (same prompt), la SQL se
ejecuta cada vez.

**Implementación**: Cache key = `mcp:result:{tool}:{hash(params)}`, TTL=300s.
Primera consulta: ~10s. Segunda consulta: <100ms.

### P0 — Investigar buffering de SSE (ahorro: percepción -5s)

Los chunks LLM llegan en batch, no streaming real. Si Saptiva realmente
devuelve streaming, el problema está en el backend (asyncio buffering,
httpx streaming config, o SSE flush interval).

Si Saptiva NO hace streaming (devuelve todo junto), no hay nada que hacer
del lado backend — la percepción de "typing" es falsa.

### P1 — Reducir LLM wait time (ahorro: 2-4s)

El gap entre chart y primer chunk LLM es 4-7s. Esto puede deberse a:
- System prompt demasiado largo (tools list completa)
- LLM model cold start en Saptiva
- Input token count alto por chart metadata en prompt

**Investigar**: Tamaño del system prompt actual. Reducir tools list para
queries determinísticas que ya tienen chart.

### P1.5 — Streaming real en path RAG (ahorro: TTFB perceptual 1-4s)

Para queries con chart/RAG, priorizar `chat_completion_stream()` y usar fallback
a `chat_completion()` solo si el stream no entrega chunks.

Esto reduce el tiempo al primer chunk sin perder resiliencia.

### P2 — Paralelizar MCP + LLM setup (ahorro: 2-3s)

Actualmente MCP bloquea → luego LLM empieza. Si el system prompt se puede
construir en paralelo con parte de la MCP call, se solaparían 2-3s.

## Archivos relevantes para instrumentación

| Archivo | Líneas | Qué medir |
|---------|--------|-----------|
| `streaming_handler.py` | 147-152 | Tiempo total de `check_and_invoke()` |
| `bank_advisor_precheck.py` | 360-376 | Breakdown: classification vs MCP call |
| `bank_analytics_client.py` | 649-762 | Tiempo de `query_bank_analytics()` |
| `chat_stream_producer.py` | 112-129 | Tiempo de chart emission |
| `saptiva_client.py` | 403-419 | Tiempo hasta primer token LLM |
| `stream_response_finalizer.py` | 194-202 | Ya tiene `latency_ms` calculation |

## Run 3: ICAP Snapshot (query compleja — 284 chars, 10 bancos, periodo específico)

### Cold cache

| Fase | Tiempo |
|------|-------:|
| **1. MCP blocking** (0 → meta) | **8,975ms (9.0s)** |
| 2. meta → chart | 0.0ms |
| 3. chart → first LLM chunk | 3,869ms (3.9s) |
| 4. LLM generation (all chunks) | 25ms |
| **TOTAL** | **12,869ms (12.9s)** |

### Warm cache

| Fase | Tiempo |
|------|-------:|
| **1. MCP blocking** (0 → meta) | **8,354ms (8.4s)** |
| 2. meta → chart | 0.0ms |
| 3. chart → first LLM chunk | 5,578ms (5.6s) |
| 4. LLM generation (all chunks) | 13ms |
| **TOTAL** | **13,945ms (13.9s)** |

**Cache effect: mínimo** — solo 0.6s ahorro en MCP (9.0→8.4s).
LLM variabilidad alta: 3.9s vs 5.6s entre runs (no determinístico).

## Hallazgo adicional: NO hay streaming real del LLM

Todos los chunks LLM llegan en un burst de <30ms:
```
12844.4ms  chunk  chars=50
12844.5ms  chunk  chars=50   ← 0.0ms delta
12844.5ms  chunk  chars=50   ← 0.0ms delta
12844.5ms  chunk  chars=50   ← 0.0ms delta
12858.7ms  chunk  chars=50   ← 14ms delta (buffer flush)
```

Esto confirma que Saptiva devuelve el texto COMPLETO y el backend lo trocea
en chunks de 50 chars artificialmente. No hay token-by-token streaming.

## Resumen consolidado (3 tipos de query)

| Query | MCP block | LLM wait | LLM gen | Total |
|-------|----------:|---------:|--------:|------:|
| RANKING quebrantos (cold) | 14.9s | 4.3s | <0.1s | 19.3s |
| TREND tasa_mn (cold) | 9.4s | 7.4s | <0.1s | 16.9s |
| ICAP snapshot (cold) | 9.0s | 3.9s | <0.1s | 12.9s |
| **Promedio** | **11.1s** | **5.2s** | **<0.1s** | **16.4s** |

Distribución: **MCP blocking 68%** | **LLM wait 32%** | **LLM gen ~0%**

## Siguiente paso

Instrumentar `bank_advisor_precheck.py` con `time.perf_counter()` en cada
sub-fase para obtener el breakdown real del MCP blocking:
- QueryRouter classification (regex + semantic scoring)
- Context enrichment
- HTTP POST to bank-advisor /rpc
- Bank-advisor SQL execution
- Chart formatting

## Update 2026-02-18

- Implementado: streaming-first para path RAG con fallback seguro a no-streaming.
- Implementado: fast-path determinístico en `should_run_advisor` para queries
  claramente bancarias/no bancarias (evita scorer semántico cuando no aporta).
- Implementado: reuse de HTTP client + tools cache stale-while-revalidate.
- Implementado: `clarification fast-path` en `ChatStreamProducer` (sin roundtrip LLM).

## Re-medición final 2026-02-18 (post optimización)

| Query | Cold total | Warm total |
|-------|-----------:|-----------:|
| RANKING quebrantos | 0.46s | 0.40s |
| TREND tasa_mn | 6.44s | 6.14s |
| ICAP snapshot | 0.34s | 0.34s |
| **Promedio** | **2.41s** | **2.29s** |

Observación: el objetivo de latencia `<15s` se cumple ampliamente. El cuello
restante relevante es LLM generation en escenarios con chart exitoso (~6.1-6.4s).
