# Research

## Preguntas

1. Por que `HALL-001` sigue detectando entidades fabricadas si hay guardrails de truth-gating?
2. El fallo `GND-002` (ROE sin chart) es bug de producto o expectativa de test?
3. Que parte del harness esta generando falsos positivos/falsos negativos?

## Hallazgos iniciales

1. `ResponsePostProcessor.validate_truth_gating()` ejecuta validacion, pero en flujo normal solo registra violaciones; no fuerza correccion de salida.
2. En la suite `test_hallucination_detection.py` el detector de entidades (`detect_entity_fabrication`) es lexical y no usa contexto estructurado del chart; puede marcar casos ambiguos.
3. `test_bug_2026_02_03_regional_queries_routing.py` permite pass con `detected_type == "unknown"` para queries regionales, reduciendo poder de regresion.
4. `apps/backend/tests/integration/test_sql_grounding.py` se cuelga durante setup de Mongo (`connect_to_mongo`) y ademas su contenido actual no valida SQL real (asserts placeholders).

## Hipotesis de causa raiz prioritaria

1. El contexto LLM para casos de chart exitoso no expresa de forma operacional las dimensiones permitidas/no permitidas (temporal vs regional/entidad/sector), dejando espacio a inferencia creativa.
2. El guardrail post-respuesta existe pero esta en modo observabilidad (log-only), no en modo correccion.
3. La cobertura E2E no esta alineada en severidad: algunos suites exigen exactitud fuerte y otros aceptan estados ambiguos.

## Evidencia de comandos

- `python3 tests/e2e/regression/test_response_grounding_desync.py` -> 19/20
- `python3 tests/e2e/regression/test_hallucination_detection.py` -> 3/4
- `python3 tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py` -> 8/8 con casos `unknown`
- `cd apps/backend && TEST_MODE=true timeout 180 .venv/bin/pytest tests/integration/test_sql_grounding.py --no-cov -q` -> exit 124

## Referencias internas

- `apps/backend/src/services/streaming/response_postprocessor.py`
- `apps/backend/src/services/truth_gating_service.py`
- `apps/backend/src/services/llm_context_builder.py`
- `tests/e2e/regression/test_hallucination_detection.py`
- `tests/e2e/regression/test_response_grounding_desync.py`

## Falsos positivos / falsos negativos de clarificacion

### FP-01 (clarificacion no necesaria): query completa termina en aclaracion generica

- Caso observado: `"ROE de INVEX en 2025"` puede terminar en fallback generico con `missing_fields=["metric"]` aun cuando la metrica viene explicita.
- Evidencia:
  - `apps/backend/src/services/tool_execution_service.py` (fallback global a `_build_generic_bank_clarification` cuando respuesta no llega con `data`/`clarification`).
  - `apps/backend/src/config/banking_keywords.py` (`DEFAULT_METRIC_OPTIONS` sin ROE/ROA, lo que ademas degrada la UX del fallback).
- Impacto:
  - Clarificacion engañosa (pide metrica cuando la metrica ya esta).
  - Usuario responde a un problema distinto al real (error tecnico / datos no disponibles).

### FP-02 (payload degradado): bancos en contexto como lista de caracteres

- Caso observado: `context.banks` llega en algunos flujos como string y se consume como iterable de chars.
- Evidencia:
  - `plugins/bank-advisor-private/src/bankadvisor/specs.py` en `get_previous_banks()` recorre `context["banks"]` asumiendo lista.
  - `apps/backend/src/services/tool_execution_service.py` tomaba `clar_ctx["banks"]` sin normalizar.
- Impacto:
  - Clarificacion muestra entidades corruptas (`["I","N","V","E","X",...]`) y rompe inferencia en siguientes turnos.

### FN-01 (test harness): se acepta exito con señal debil

- Caso observado: suite de routing regional acepta `unknown` como pass en consultas que deberian ser regionales.
- Evidencia:
  - `tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py` lineas de aceptacion para `detected_type == "unknown"`.
- Impacto:
  - Regresiones reales de routing pueden quedar ocultas.

### FN-02 (cobertura inestable): test de integracion colgado

- Caso observado: `test_sql_grounding.py` timeout durante setup (Mongo), sin assert de grounding fuerte.
- Evidencia:
  - `cd apps/backend && TEST_MODE=true timeout 180 .venv/bin/pytest tests/integration/test_sql_grounding.py --no-cov -q` -> exit 124.
- Impacto:
  - No detecta regresiones cuando mas importa (join parser->sql->respuesta).

## Mejora aplicada (TDD corto, backend)

1. Normalizacion de `context.banks` / `context.available_banks` en clarificaciones para evitar listas de caracteres.
2. Fallback generico ahora detecta metrica explicita y ajusta `missing_fields` semanticamente:
   - sin metrica -> pide metrica
   - con metrica y sin banco -> pide banco
   - con metrica y banco -> no marca faltantes (trata como fallo de ejecucion)

Archivos:
- `apps/backend/src/services/tool_execution_service.py`
- `apps/backend/tests/unit/test_tool_execution_service.py`

## Mejora aplicada (TDD corto, plugin + harness)

1. `SessionContext.get_previous_banks()` ahora normaliza bancos desde formatos mixtos:
   - string unico (`"INVEX"`)
   - string CSV (`"INVEX, BBVA"`)
   - listas/tuplas
   - listas de dicts tipo opcion (`{"id": "INVEX"}`, `{"value": "BBVA"}`)
2. Se agregaron tests unitarios dedicados para ese flujo.
3. Se endurecio el criterio del test regional:
   - consultas regionales ya no pasan con `detected_type="unknown"` (ahora fallan como inconclusas).

Archivos:
- `plugins/bank-advisor-private/src/bankadvisor/specs.py`
- `plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_session_context.py`
- `tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py`

## Hallazgos adicionales (continuacion)

### FN-03 (wiring incompleto): backend envia `enriched_context` pero no se usa en estrategia de clarificacion

- Caso observado:
  - `ToolExecutionService` construye `session_context.enriched_context`.
  - `QueryOrchestrator.apply_clarification_strategy()` llamaba `determine_strategy(spec)` sin `PluginContext`.
- Impacto:
  - Se pierden señales semánticas (follow-up/similarity) y puede dispararse HARD_ASK cuando no corresponde.
- Fix:
  - `process_analytics_query(..., clarification_context=...)` ahora recibe y propaga `session_context["enriched_context"]`.
  - `QueryOrchestrator.apply_clarification_strategy(..., plugin_context=...)` parsea `PluginContext.from_dict(...)` y lo pasa a `determine_strategy`.

### FP/FN-04 (heuristica agresiva): cualquier query corta heredaba banco

- Caso observado:
  - En `ClarificationService._should_infer_from_context()`, la regla `len(query.split()) <= 5` inferia banco aunque no hubiera señales de follow-up.
  - Ejemplo: `"icap actual"` heredaba banco anterior y evitaba aclaracion necesaria.
- Impacto:
  - Falso negativo de clarificacion (responde con banco heredado cuando debio pedir banco).
- Fix:
  - La inferencia por query corta ahora exige cues de seguimiento (`y`, `ahora`, `compar`, `agrega`, `ese/esa`, etc.).

### Estabilidad de tests (hang)

- Caso observado:
  - `test_uses_memory_context_fallback` y corrida amplia de `TestInvokeBankAnalytics` se colgaban por dependencias externas no mockeadas y enriquecimiento semántico en unit flow.
- Fix:
  - Backend: enriquecimiento semántico con timeout y fallback baseline; ademas se omite scoring semántico cuando solo hay `memory_context` sin turns recientes.
- Tests: `test_handles_redis_cache_error_on_get` ahora mockea `query_bank_analytics` (evita llamada real).

### FP-05 (harness): `Entity Fabrication` marcaba estados validos como alucinacion

- Caso observado:
  - `test_hallucination_detection.py` marcaba `critical` solo por detectar >=2 nombres de estados en el texto.
  - En consultas regionales (`estado/entidad federativa/región`) eso genera falsos positivos.
- Fix:
  - `detect_entity_fabrication()` ahora recibe `user_query` + `has_chart_data` y baja a `info` cuando los estados son coherentes con una consulta regional.
  - `run_hallucination_checks()` y `assess_response_quality()` propagan ese contexto.
