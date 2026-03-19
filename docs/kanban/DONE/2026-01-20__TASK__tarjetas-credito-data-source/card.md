---
id: "TASK-2026-01-20__tarjetas-credito-data-source"
title: "Implement Tarjetas de Crédito metrics via Materialized View"
status: "DONE"
phase: "Validate"
priority: "medium"
scope_in:
  - "Migration 052: crear bank_mv_cartera_tdc"
  - "TdcService con get_ranking(), get_evolution()"
  - "Completar mapping en synonyms.yaml y metric_resolver.py"
  - "Agregar refresh al ETL runner (db_writer_3nf.py)"
  - "Tests unitarios para TDC (19 tests)"
scope_out:
  - "Modificar ETL core (transforms.py)"
  - "UI changes"
  - "Nuevas fuentes de datos"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
plan_phase: 5
test_status: "passed"
validation_commands:
  - "psql $DATABASE_URL -c 'SELECT COUNT(*) FROM bank_mv_cartera_tdc;'"
  - "make test T=api TEST_ARGS='-k tdc'"
  - "make pre-deploy.lint"
---

# Summary

- **Objective**: Exponer métricas de tarjetas de crédito desde datos CNBV
- **Origin**: BUG-TARJETAS from BUG-015 user session analysis
- **Result**: ✅ Implementado via Materialized View con 3,940 registros

# Implementation Results

## MV Stats (Production)

| Métrica | Valor |
|---------|-------|
| Registros | 3,940 |
| Bancos | 19 |
| Periodos | 299 |
| Rango | 2000-12 a 2025-10 |

## Sample Data (Oct 2025)

| Banco | Cartera TDC | IMOR |
|-------|-------------|------|
| BBVA | $199,630 M | 6.63% |
| BANAMEX | $160,360 M | 6.31% |
| SANTANDER | $71,979 M | 7.61% |
| INVEX | $31,431 M | 4.97% |

# Files Changed

| Phase | Archivo | Descripción |
|-------|---------|-------------|
| 1 | `migrations/052_create_mv_cartera_tdc.sql` | MV + indices + refresh function |
| 2 | `services/analytics/tdc_service.py` | TdcService (389 líneas) |
| 2 | `services/analytics/__init__.py` | Export TdcService |
| 3 | `config/synonyms.yaml` | 4 métricas TDC |
| 3 | `services/metric_resolver.py` | Keywords TDC |
| 4 | `etl/core/db_writer_3nf.py` | MV refresh list (9 MVs) |
| 5 | `tests/unit/services/test_tdc_service.py` | 19 unit tests |

# Commits

```
125df7a2 feat(bank-advisor): add migration 052 for TDC materialized view
e06b2651 feat(bank-advisor): add TdcService for credit card analytics
418f23c6 feat(bank-advisor): add TDC metrics to synonyms.yaml and metric_resolver
18f90b80 feat(etl): add bank_mv_cartera_tdc to MV refresh list
8ee5eebc test(bank-advisor): add unit tests for TdcService
9a14bf93 fix(migration): use correct table name bank_src_analisis_general
5dbc2a99 fix(migration): normalize institution code format in JOIN
```

# Queries Habilitados

El sistema ahora puede responder:
- "¿Cuál es la cartera de tarjetas de crédito de BBVA?"
- "Dame el IMOR de TDC por banco"
- "Evolución de cartera TDC de INVEX"
- "Ranking de bancos por cartera TDC"

# Updates

- 2026-01-28 18:45 - **COMPLETADO**. Migration aplicada en producción. 3,940 registros.
- 2026-01-28 18:30 - Fixes: tabla correcta (bank_src_analisis_general) y formato institución.
- 2026-01-28 - Plan completado. Opcion B (MV) seleccionada tras auditoria de sistema.
- 2026-01-28 - Research completado. Opcion A descartada (invasiva al ETL core).
- 2026-01-20 - Created from BUG-015 triage. Deferred as data limitation.
