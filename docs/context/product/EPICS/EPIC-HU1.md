# EPIC-HU1: Query Multi-Banco

> **Status**: ✅ DONE
> **Priority**: P0
> **Close Date**: 29 Dec 2025

---

## Agent Execution Context

> **CRITICAL**: This section provides everything a sub-agent needs to execute.

### Target Files

| Action | Path | Description |
|--------|------|-------------|
| ✅ CREATE | `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | QuerySpec builder agent |
| ✅ CREATE | `plugins/bank-advisor-private/src/agents/sql_agent.py` | SQL execution agent |
| ✅ CREATE | `plugins/bank-advisor-private/src/models/query_spec.py` | QuerySpec JSON Schema |
| ✅ CREATE | `plugins/bank-advisor-private/src/validators/sql_validator.py` | SQL guardrails (3 layers) |
| ✅ CREATE | `plugins/bank-advisor-private/src/services/query_budget.py` | Resource limits enforcement |
| ✅ MODIFY | `plugins/bank-advisor-private/src/router/orchestrator.py` | Router integration |
| ✅ CREATE | `plugins/bank-advisor-private/tests/unit/test_queryspec_builder.py` | Unit tests (45 tests) |
| ✅ CREATE | `plugins/bank-advisor-private/tests/integration/test_sql_agent.py` | Integration tests (12 tests) |

### Integration Points

```
Usuario: "Dame IMOR de INVEX en diciembre 2024"
            │
            ▼
    ┌───────────────┐
    │    Router     │ Intent: SQL_QUERY
    └───────┬───────┘
            │
            ▼
    ┌───────────────────┐
    │ QuerySpec Builder │ → Consulta Ontology_Terms (Weaviate)
    │                   │ → Genera QuerySpec JSON
    │                   │ → Valida con JSON Schema
    └───────┬───────────┘
            │
            ▼ QuerySpec: {bank: "INVEX", metric: "IMOR", period: "2024-12"}
            │
    ┌───────────────┐
    │   SQL Agent   │ → Valida QuerySpec
    │               │ → Genera SQL SELECT
    │               │ → Aplica guardrails (3 capas)
    │               │ → Ejecuta en PostgreSQL
    └───────┬───────┘
            │
            ▼ Resultado: {value: 2.34, date: "2024-12-31", source: "v_cnbv_metrics_monthly"}
            │
    ┌───────────────┐
    │   Response    │ → Texto NL + dato + trazabilidad + SQL
    └───────────────┘
```

### Example Input/Output

**Input** (what the feature receives):
```json
{
  "user_query": "Dame el IMOR de INVEX en diciembre 2024",
  "session_id": "sess_123",
  "user_id": "user_456"
}
```

**QuerySpec Output** (intermediate):
```json
{
  "query_id": "q_789",
  "intent": "SQL_QUERY",
  "banks": ["INVEX"],
  "metrics": ["IMOR"],
  "period": {
    "start": "2024-12-01",
    "end": "2024-12-31",
    "granularity": "monthly"
  },
  "aggregation": null,
  "filters": {},
  "confidence": 0.95,
  "ambiguity_flags": []
}
```

**Final Output** (to user):
```json
{
  "response_text": "El IMOR de INVEX en diciembre 2024 fue 2.34%.",
  "data": {
    "bank": "INVEX",
    "metric": "IMOR",
    "value": 2.34,
    "unit": "%",
    "date_cutoff": "2024-12-31"
  },
  "source_refs": ["table:v_cnbv_metrics_monthly", "source:CNBV"],
  "sql_executed": "SELECT imor FROM v_cnbv_metrics_monthly WHERE bank_code = 'INVEX' AND period = '2024-12-31'",
  "execution_time_ms": 1523
}
```

### Validation Commands

```bash
# Preflight: ensure stack is up
make dev

# Run unit tests
cd plugins/bank-advisor-private
pytest tests/unit/test_queryspec_builder.py -v

# Run integration tests (requires PostgreSQL)
pytest tests/integration/test_sql_agent.py -v

# Run PoC validation (100% pass rate)
python scripts/queryspec_poc.py

# Health check
curl http://localhost:8002/health

# Test query end-to-end
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Dame IMOR de INVEX en diciembre 2024"}'
```

---

## General Description

### Objective

Permitir a analistas consultar métricas financieras de cualquier banco mexicano usando lenguaje natural, con datos precisos, trazables y validados contra CNBV.

### Solution enables

- Consultas en lenguaje natural (no SQL manual)
- Acceso a datos de 14 bancos mexicanos
- Trazabilidad completa: dato → SQL → tabla → fuente
- Validación automática de precisión (±0.01% vs CNBV)
- Latencia < 3 segundos para 95% de queries

### Problems solved

| Current Problem | Impact | Solution |
|-----------------|--------|----------|
| Consultas SQL manuales requieren conocimiento técnico | Analistas dependen de ingenieros de datos | NL2SQL con QuerySpec Builder |
| Datos fragmentados en múltiples fuentes | Horas buscando información correcta | Vista consolidada `v_cnbv_metrics_monthly` |
| Sin trazabilidad de origen de datos | Dudas sobre precisión en reportes | Campo `source_refs` en cada respuesta |
| Riesgo de SQL injection | Vulnerabilidad de seguridad | Guardrails de 3 capas + whitelist estricta |

### Expected benefits

- **Para el usuario**: Consultas en segundos, no horas
- **Para el negocio**: Reducción de dependencia en equipos de data (ahorro ~USD 1,600/mes según BRD)
- **Para el sistema**: Pipeline NL2SQL validado y reutilizable para HU2, HU3

### Success metrics

| Metric | Baseline | Target | Actual | How to measure |
|--------|----------|--------|--------|----------------|
| Latencia p50 | N/A | < 3s | ~1.5s | CloudWatch / logs |
| Latencia p95 | N/A | < 5s | ~2.8s | CloudWatch / logs |
| Precisión vs CNBV | N/A | 99.99% | 100% | Validación manual vs fuente oficial |
| Bancos disponibles | 0 | 10+ | 14 | `SELECT DISTINCT bank_code FROM v_cnbv_metrics_monthly` |
| QuerySpec pass rate | N/A | 100% | 100% | PoC validation script |

---

## Strategic Alignment

### Why this epic? (BRD Alignment)

**BRD use case**: UC-3 - Consulta a cálculos/datos

> "Pregunta en chat → respuesta en lenguaje natural + mención de dato específico + trazabilidad de dónde obtuvo el dato"
> — BRD.md, Sección 4: Casos de Uso

**Direct connection**:
- Esta épica implementa **el core del producto** - convertir lenguaje natural en datos precisos
- Es **prerequisito** para todas las demás épicas (HU2-HU5)
- Contribuye al **WAU (North Star Metric)** como funcionalidad base que usuarios usarán diariamente
- Se alinea con el principio de diseño #1: **"Precisión regulatoria por encima de creatividad (no alucinar)"**

**BRD Success Metrics Contribution**:

| BRD Metric | How HU1 Contributes |
|------------|---------------------|
| WAU (North Star) | Enables baseline functionality for weekly queries |
| TTI (Time-To-Insight) | Reduces from ~1 month to < 5 seconds |
| ARR per client | Demonstrates core value proposition for USD 30k contracts |

### How does it integrate? (Architecture Alignment)

**Components involved**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     EPIC-HU1 Architecture                        │
├──────────────┬─────────────────┬──────────────────┬─────────────┤
│   Router     │  QuerySpec      │   SQL Agent      │ PostgreSQL  │
│ (Existing)   │   Builder       │    (New)         │  (Existing) │
│              │    (New)        │                  │             │
├──────────────┼─────────────────┼──────────────────┼─────────────┤
│ Classifies   │ 1. Queries      │ 1. Validates     │ Stores      │
│ intent as    │    Weaviate     │    QuerySpec     │ 14 bancos   │
│ SQL_QUERY    │    for entities │ 2. Generates SQL │ monthly KPIs│
│              │ 2. Builds JSON  │ 3. Applies       │             │
│              │ 3. Validates    │    guardrails    │             │
│              │    schema       │ 4. Executes      │             │
│              │                 │ 5. Returns data  │             │
└──────────────┴─────────────────┴──────────────────┴─────────────┘
```

**Integration with existing architecture**:

| Existing Component | Integration Point | HU1 Responsibility |
|-------------------|-------------------|-------------------|
| Router/Orchestrator | Intent classification | Receives SQL_QUERY intent, routes to QuerySpec Builder |
| Weaviate (Ontology_Terms) | Grounding | QuerySpec Builder queries for canonical entity names |
| PostgreSQL (v_cnbv_metrics_monthly) | Data source | SQL Agent executes validated queries |
| AuditTrailService | Logging | Logs QuerySpec + SQL + results for compliance |

**Technical dependencies**:

| Component | Status | Required for | Blocker? |
|-----------|--------|--------------|----------|
| Intent Router | ✅ DONE | Intent classification | No |
| Ontology_Terms (Weaviate) | ✅ DONE | Entity grounding | No |
| PostgreSQL + Vista | ✅ DONE | Data retrieval | No |
| JSON Schema (QuerySpec) | ✅ DONE | Validation | No |
| SQL Guardrails (3 layers) | ✅ DONE | Security | No |

**No blockers** - All dependencies completed.

---

## Deliverables List

| # | Deliverable | File Path | Completion Criteria |
|---|-------------|-----------|---------------------|
| E1 | QuerySpec JSON Schema | `plugins/bank-advisor-private/src/models/query_spec.py` | ✅ Schema validates 100% of test cases |
| E2 | QuerySpec Builder Agent | `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | ✅ Generates valid QuerySpec from NL |
| E3 | SQL Agent | `plugins/bank-advisor-private/src/agents/sql_agent.py` | ✅ Executes SQL with guardrails |
| E4 | SQL Validator (3 layers) | `plugins/bank-advisor-private/src/validators/sql_validator.py` | ✅ Blocks all non-SELECT, validates whitelist |
| E5 | Query Budget Service | `plugins/bank-advisor-private/src/services/query_budget.py` | ✅ Enforces max rows, timeout, joins |
| E6 | Unit Tests | `plugins/bank-advisor-private/tests/unit/` | ✅ 45 unit tests passing |
| E7 | Integration Tests | `plugins/bank-advisor-private/tests/integration/` | ✅ 12 integration tests passing |
| E8 | PoC Validation Script | `plugins/bank-advisor-private/scripts/queryspec_poc.py` | ✅ 100% pass rate on 20 test queries |

---

## Acceptance Criteria

### Functional

- [x] **CA-01**: System accepts queries in natural language (Spanish)
- [x] **CA-02**: System supports 10+ bancos mexicanos (actual: 14)
- [x] **CA-03**: System returns data matching CNBV (±0.01% tolerance)
- [x] **CA-04**: Every response includes `date_cutoff` field
- [x] **CA-05**: Every response includes `source_refs` field
- [x] **CA-06**: System traces each result to SQL executed
- [x] **CA-07**: QuerySpec validates against JSON Schema
- [x] **CA-08**: System rejects queries with confidence < 0.7 (abstention mode)

### Non-Functional

- [x] **CA-09**: Latencia p50 < 3 segundos (actual: ~1.5s)
- [x] **CA-10**: Latencia p95 < 5 segundos (actual: ~2.8s)
- [x] **CA-11**: SQL guardrails block non-SELECT statements (100% block rate)
- [x] **CA-12**: Query budget enforced: max 5000 rows, 30s timeout, 2 joins
- [x] **CA-13**: All queries logged to AuditTrailService for compliance
- [x] **CA-14**: Zero SQL injection vulnerabilities (whitelist + parameterization)

---

## Implementation Phases

### Phase 1: QuerySpec Foundation (COMPLETED)

**Deliverables**: E1, E2

**Files created/modified**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/src/models/query_spec.py` | CREATE | JSON Schema definition |
| `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | CREATE | NL → QuerySpec transformation |
| `plugins/bank-advisor-private/tests/unit/test_queryspec_builder.py` | CREATE | Validation tests |

**Status**: ✅ Completed 27 Dec 2025 (commit `364be292`)

---

### Phase 2: SQL Execution & Guardrails (COMPLETED)

**Deliverables**: E3, E4, E5

**Files created/modified**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/src/agents/sql_agent.py` | CREATE | SQL generation and execution |
| `plugins/bank-advisor-private/src/validators/sql_validator.py` | CREATE | 3-layer validation |
| `plugins/bank-advisor-private/src/services/query_budget.py` | CREATE | Resource limits |
| `plugins/bank-advisor-private/tests/integration/test_sql_agent.py` | CREATE | E2E tests |

**Status**: ✅ Completed 28 Dec 2025 (commit `5f8c03cb`)

---

### Phase 3: PoC Validation & Testing (COMPLETED)

**Deliverables**: E6, E7, E8

**Files created/modified**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/scripts/queryspec_poc.py` | CREATE | Validation script |
| `plugins/bank-advisor-private/tests/unit/` | CREATE | 45 unit tests |
| `plugins/bank-advisor-private/tests/integration/` | CREATE | 12 integration tests |

**Status**: ✅ Completed 29 Dec 2025 (commit `0ed25aee`)

**Result**: 100% pass rate on 20 test queries

---

## Definition of Done

| Criterion | Verification Command | Pass Condition | Status |
|-----------|---------------------|----------------|--------|
| Unit tests | `pytest tests/unit/ -v` | 45/45 passing | ✅ PASS |
| Integration tests | `pytest tests/integration/ -v` | 12/12 passing | ✅ PASS |
| PoC validation | `python scripts/queryspec_poc.py` | 100% accuracy | ✅ PASS |
| Lint | `ruff check src/` | 0 errors | ✅ PASS |
| Type check | `mypy src/` | 0 errors | ✅ PASS |
| Security | SQL injection tests | 100% blocked | ✅ PASS |
| Performance | Latency benchmark | p95 < 5s | ✅ PASS (2.8s) |
| Data accuracy | Manual CNBV validation | ±0.01% | ✅ PASS |

**Overall Status**: ✅ ALL CRITERIA MET - EPIC COMPLETE

---

## Risks and Mitigation

| Risk | Prob | Impact | Status | Mitigation |
|------|------|--------|--------|------------|
| QuerySpec fantasía (invalid entities) | Alta | Alta | ✅ Mitigated | Grounding with Ontology_Terms + JSON Schema validation |
| SQL injection | Media | Crítica | ✅ Mitigated | 3-layer guardrails + whitelist + parameterization |
| Performance degradation | Media | Media | ✅ Monitored | Query budget enforced (max 5000 rows, 30s timeout) |
| Data staleness | Baja | Media | ⚠️ Monitored | Monthly ETL from CNBV (manual for v1.2) |
| Grounding failures | Media | Alta | ✅ Mitigated | Abstention mode when confidence < 0.7 |

---

## References

| Document | Relevant Section |
|----------|------------------|
| [BRD.md](../BRD.md) | Section 4: Use Cases (UC-3) |
| [BRD.md](../BRD.md) | Section 6: Success Metrics (TTI, WAU) |
| [PRD.md](../product/PRD.md) | HU1: Query Multi-Banco |
| [architecture/AGENTS.md](../architecture/AGENTS.md) | QuerySpec Builder + SQL Agent contracts |
| [architecture/DATA.md](../architecture/DATA.md) | QuerySpec schema + Ontology_Terms |
| [architecture/SECURITY.md](../architecture/SECURITY.md) | SQL guardrails implementation |
| [GAPS.md](../PRD-old/GAPS.md) | P0-1: QuerySpec PoC Validation (RESOLVED) |
| [GAPS.md](../PRD-old/GAPS.md) | P0-2: SQL Guardrails (RESOLVED) |

---

## Notes

- This epic is the **foundation** for all other epics (HU2-HU5)
- QuerySpec Builder reuses Ontology_Terms from HU4 for grounding
- SQL Agent provides the data layer for HU2 (multi-bank comparisons)
- PoC validation demonstrates **100% accuracy** - no hallucinations
- All 14 bancos in PostgreSQL confirmed available: INVEX, BBVA, Santander, Banorte, HSBC, Scotiabank, Inbursa, Afirme, Banregio, BanBajío, Ve por Más, Banco Azteca, Banca Mifel, BanCoppel

**Next Epic**: [EPIC-HU2: Comparación Multi-Banco](EPIC-HU2.md) (requires Chart Builder - P1-2)
