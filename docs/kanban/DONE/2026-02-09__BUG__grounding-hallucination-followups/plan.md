# Plan

## Objetivo

Eliminar respuestas con desglose inventado y estabilizar la validacion de regresion para grounding/contexto.

## Scope

### In

- Guardrail de contexto para dimensiones disponibles (temporal/banco/regional/entidad/sector)
- Endurecimiento de tests unitarios y E2E relacionados
- Correccion de manejo de violaciones criticas de truth-gating en salida final
- Diagnostico y hardening del test de integracion colgado

### Out

- Cambios de frontend
- Rediseño completo del pipeline de tools

## Fases (TDD)

### Phase 1 - Context Guardrail (Red -> Green)

- [ ] Agregar tests unitarios que fallen cuando el contexto no explicita limites de desglose.
- [ ] Implementar en `LLMContextBuilder` seccion de dimensiones disponibles/no disponibles.
- [ ] Verificar unit tests del extractor/context builder.

Archivos candidatos:
- `apps/backend/tests/unit/test_analytics_extractor.py`
- `apps/backend/src/services/llm_context_builder.py`

### Phase 2 - Truth Gating Enforcement (Red -> Green)

- [ ] Agregar tests de postprocessor para violaciones criticas de breakdown.
- [ ] Aplicar correccion de salida cuando haya violaciones criticas.
- [ ] Validar no regresion con tests de `response_postprocessor`.

Archivos candidatos:
- `apps/backend/tests/unit/services/streaming/test_response_postprocessor.py`
- `apps/backend/src/services/streaming/response_postprocessor.py`

### Phase 3 - Regression Harness Hardening

- [ ] Endurecer `regional_queries_routing` para no aceptar `unknown` en casos regionales.
- [ ] Ajustar o aislar `test_sql_grounding.py` para evitar hangs (skip condicional/fixtures robustos).
- [ ] Re-correr E2E clave.

Archivos candidatos:
- `tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py`
- `apps/backend/tests/integration/test_sql_grounding.py`
- `apps/backend/tests/integration/conftest.py`

## Validation Commands

- `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_analytics_extractor.py --no-cov -q`
- `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/services/streaming/test_response_postprocessor.py --no-cov -q`
- `python3 tests/e2e/regression/test_response_grounding_desync.py`
- `python3 tests/e2e/regression/test_hallucination_detection.py`

## Success Criteria

- `GND-002` sin falla por ausencia de chart en replay
- `HALL-001` sin fabricacion de entidades detectada
- Suite de routing regional no acepta `unknown` como exito en queries regionales
- Test SQL grounding deja de bloquear pipeline local
