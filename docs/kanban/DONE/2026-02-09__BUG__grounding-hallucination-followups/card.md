---
id: BUG-2026-02-09__grounding-hallucination-followups
title: "Follow-up de Grounding y Alucinaciones (ROE, regional, test harness)"
status: REVIEW
phase: Validate
priority: critical
scope_in:
  - Validar regresiones de grounding/chart-year/legacy-date-format con backend real
  - Corregir alucinaciones de desglose regional/entidad en respuesta final
  - Corregir caso ROE sin chart en suite de grounding
  - Endurecer harness/tests que hoy pasan con senal debil o se cuelgan
scope_out:
  - Cambios de UI
  - Nuevas metricas o nuevas features de negocio
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - python3 tests/e2e/regression/test_response_grounding_desync.py
  - python3 tests/e2e/regression/test_hallucination_detection.py
  - python3 tests/e2e/regression/test_bug_2026_02_05_chart_year_mismatch_e2e.py
  - python3 tests/e2e/regression/test_bug_regression_suite.py
  - cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/services/test_truth_gating_hallucination.py tests/unit/services/test_hallucination_detection_integration.py --no-cov -q
pr_files: []
test_status: "unit+e2e local green (hallucination_detection 4/4, response_grounding 8/8, routing_regional 8/8)"
reported_by: "regression-sweep"
reported_at: "2026-02-09"
---

# Resumen

**Objetivo**: cerrar gaps detectados en el barrido de regresion de grounding para evitar analisis financieros con desgloses no soportados y casos de enrutamiento ambiguo.

**Hallazgos principales del barrido (2026-02-09)**:

1. `response_grounding_desync` paso en feedback historico, pero quedo 1 falla nueva en replay extendido:
   - `tests/e2e/regression/test_response_grounding_desync.py` -> **19/20 pass**
   - Falla: `GND-002` (`"ROE de INVEX en 2025"`) con `Expected chart but none returned`.
2. `hallucination_detection` sigue detectando fabricacion de entidades en escenario fsaavedra:
   - `tests/e2e/regression/test_hallucination_detection.py` -> **3/4 pass**
   - `HALL-001` fallo por menciones de estados/regiones no confiables.
3. `regional_queries_routing` pasa 8/8, pero con criterio debil:
   - Hay casos regionales marcados como pass con `Detected type: unknown`.
4. `test_sql_grounding.py` se cuelga en setup de infraestructura (Mongo), no aporta validacion real:
   - timeout repetido y test con asserts triviales.

## Matriz de validacion ejecutada

- `tests/e2e/regression/test_bug_2026_02_03_response_grounding_desync.py` -> 8/8 pass
- `tests/e2e/regression/test_bug_2026_02_05_chart_year_mismatch_e2e.py` -> 3/3 pass
- `tests/e2e/regression/test_bug_2026_02_05_chart_year_mismatch.py` -> 24/24 pass
- `tests/e2e/regression/test_bug_regression_suite.py` -> 27/27 pass
- `tests/e2e/regression/test_bug_2026_01_30_month_decimal_scope.py` -> 9/9 pass
- `tests/e2e/regression/test_bug_2026_01_30_icap_decimal.py` -> 3/3 pass
- `tests/e2e/regression/test_bug_2026_01_30_query_scope.py` -> 3/3 pass
- `tests/e2e/regression/test_2026_02_08_bug_fecha_valor_tabular_desync.py` -> 3/3 pass
- `tests/e2e/regression/test_feedback_replay_2026_02_05.py` -> 10/10 pass
- `tests/e2e/regression/test_feedback_replay_2026_02_06.py` -> 13/13 pass
- `tests/e2e/regression/test_response_grounding_desync.py` -> **19/20 pass (1 fail)**
- `tests/e2e/regression/test_hallucination_detection.py` -> **3/4 pass (1 fail)**
- `apps/backend/tests/integration/test_sql_grounding.py` -> **hang/timeout (exit 124)**

## Riesgo

- Riesgo de presentar desgloses geograficos inventados en consultas tabulares o de seguimiento.
- Riesgo de falsa sensacion de cobertura por tests que pasan con `unknown`.
- Riesgo operativo por pipeline de pruebas inestable (test colgado en integracion).

## Criterios de aceptacion (DoD local previo a deploy)

- [ ] `test_response_grounding_desync.py` en 20/20
- [ ] `test_hallucination_detection.py` en 4/4 sin fabricacion de entidades
- [ ] `test_bug_2026_02_03_regional_queries_routing.py` sin aceptar `unknown` para queries regionales
- [ ] `apps/backend/tests/integration/test_sql_grounding.py` deja de colgarse (skip controlado o setup robusto)
- [ ] Unit tests nuevos/actualizados en verde con TDD (red->green->refactor)

## Relacionado

- `docs/kanban/DOING/2026-02-03__BUG__response-grounding-desync/card.md`
- `docs/kanban/DOING/2026-02-05__BUG__chart-year-mismatch/card.md`
- `docs/kanban/DOING/2026-02-06__BUG__legacy-plotly-date-format/card.md`
- `docs/kanban/DONE/2026-01-30__BUG__wrong-month-data-mapping/card.md`
- `docs/kanban/DONE/2026-01-27__TASK__hallucination-detection/card.md`
