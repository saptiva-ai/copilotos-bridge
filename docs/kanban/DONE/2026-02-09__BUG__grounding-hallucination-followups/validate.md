# Validation

## Baseline (antes del fix)

- `python3 tests/e2e/regression/test_response_grounding_desync.py` -> 19/20
- `python3 tests/e2e/regression/test_hallucination_detection.py` -> 3/4
- `python3 tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py` -> 8/8 (con `unknown` en regionales)
- `cd apps/backend && TEST_MODE=true timeout 180 .venv/bin/pytest tests/integration/test_sql_grounding.py --no-cov -q` -> 124 (timeout)

## Comandos de validacion objetivo

- `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_analytics_extractor.py --no-cov -q`
- `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/services/streaming/test_response_postprocessor.py --no-cov -q`
- `python3 tests/e2e/regression/test_response_grounding_desync.py`
- `python3 tests/e2e/regression/test_hallucination_detection.py`
- `python3 tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py`

## Evidencia a registrar

- Resumen pass/fail por suite
- Casos exactos fallidos
- Cambios de comportamiento observables en respuestas del LLM

## Estado

- [~] Parcial

## Ejecucion reciente (2026-02-09)

- `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_tool_execution_service.py -k "BuildGenericBankClarification or normalizes_clarification_context_banks_string" --no-cov -q` -> **5 passed**
- Nota: la corrida completa de `tests/unit/test_tool_execution_service.py` quedo bloqueada en entorno local; se mantiene validacion focalizada para los cambios del fallback/clarificacion.
- `cd plugins/bank-advisor-private && .venv/bin/pytest src/bankadvisor/tests/unit/test_session_context.py -q` -> **4 passed**
- `python3 tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py` -> **bloqueado en sandbox** (sin acceso a `localhost:8002`, `Operation not permitted`)

## Ejecucion reciente (2026-02-09, continuacion)

- `cd apps/backend && .venv/bin/pytest --no-cov -q tests/unit/services/intent/test_context_enricher.py tests/unit/test_tool_execution_service.py::TestInvokeBankAnalytics` -> **26 passed**
- `cd plugins/bank-advisor-private && .venv/bin/pytest tests/unit/test_contextual_clarification.py tests/unit/test_clarification_service.py -q` -> **64 passed**
- `cd plugins/bank-advisor-private && .venv/bin/pytest src/bankadvisor/tests/unit/test_query_spec_parser_financial_metrics.py src/bankadvisor/tests/unit/test_session_context.py -q` -> **6 passed**
- `python3 tests/e2e/regression/test_bug_2026_02_03_response_grounding_desync.py` -> **8/8 passed**
- `python3 tests/e2e/regression/test_2026_02_08_bug_fecha_valor_tabular_desync.py` -> **3/3 passed**
- `python3 tests/e2e/regression/test_bug_2026_02_05_chart_year_mismatch_e2e.py` -> **3/3 passed**
- `python3 tests/e2e/regression/test_bug_regression_suite.py` -> **27/27 passed** (incluye `MONTH-001` del ticket legacy-plotly-date-format)
- `python3 tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py` -> **8/8 passed** (tras ajuste de detector para evitar `unknown` falso negativo)
- `python3 tests/e2e/regression/test_hallucination_detection.py` -> **4/4 passed** (sin hallucinations detectadas tras ajuste de entity-fabrication checker contextual)

## Resultado consolidado

- Cobertura objetivo de issues revisados: **verde** en unit + regresion E2E focal.
- Riesgo residual:
  - Persisten warnings de entorno (`PytestCacheWarning` por permisos de `.pytest_cache`).
  - Validacion de sintaxis via `py_compile` no se pudo usar por permisos de escritura en `__pycache__` (sin impacto funcional en pruebas ejecutadas).
