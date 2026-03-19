# Research: Fecha-Valor Tabular Desync

## Questions

- Donde se rompe el contrato fecha-valor en el flujo Plugin -> Backend -> LLM -> Frontend?
- El error nace en el chart, en el contexto para LLM, o en ambos?
- Que practicas externas reducen alucinacion en respuestas tabulares con contexto multi-turn?

## Findings

1. Backend table context usa alineacion por posicion, no por fecha.
- Archivo: `apps/backend/src/schemas/analytics_data.py`
- Funcion: `_build_markdown_table`
- Riesgo: con series de longitudes distintas, una fila de mes puede mostrar el valor de otro mes.

2. Plugin timeline puede crear trazas con `x` global y `y` parcial por banco.
- Archivo: `plugins/bank-advisor-private/src/bankadvisor/services/visualization_service.py`
- Funcion: `_build_timeline_chart`
- Riesgo: si un banco no tiene dato en un mes, `y` puede quedar desplazado respecto a `x`.

3. Extractor backend cae a fecha actual si no parsea fecha.
- Archivo: `apps/backend/src/services/analytics_extractor.py`
- Funcion: `_parse_date`
- Riesgo: contaminacion temporal silenciosa en payload/contexto.

4. El fallback de tabla reutiliza el mismo constructor tabular.
- Archivo: `apps/backend/src/services/streaming/response_postprocessor.py`
- Funcion: `inject_table_if_missing`
- Riesgo: el mismo defecto puede aparecer en inyeccion post-procesada.

5. Gaps de pruebas.
- Hay cobertura fuerte para casos alineados, pero faltan casos con meses faltantes por banco.
- Se requiere regression dedicada para prevenir reintroduccion.

## TDD Evidence (Red -> Green)

### Red (fallaba antes del fix)

- Tabla backend:
  - fila `Feb 2025` mostraba valor de `Mar 2025` para banco con hueco mensual.
- Timeline plugin:
  - traza `SANTANDER` quedaba `y=[100, 300]` para `x=[Ene, Feb, Mar]` (corrimiento).
- Extractor:
  - `\"2025-01\"` y `\"Jan 2025\"` no parseaban y caian en fecha actual.

### Green (despues del fix)

- Tabla backend alinea por fecha y respeta huecos con `—`.
- Timeline plugin rellena faltantes con `None` y mantiene `len(x)==len(y)` por traza.
- Extractor parsea formatos mensuales y rechaza fecha invalida sin inventar `today()`.

## References

### Internas
- `apps/backend/src/schemas/analytics_data.py`
- `apps/backend/src/services/analytics_extractor.py`
- `plugins/bank-advisor-private/src/bankadvisor/services/visualization_service.py`
- `apps/backend/src/services/streaming/response_postprocessor.py`
- `tests/e2e/regression/test_response_grounding_desync.py`

### Externas (mitigacion de alucinacion y grounding)
- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks: https://arxiv.org/abs/2005.11401
- Lost in the Middle: How Language Models Use Long Contexts: https://arxiv.org/abs/2307.03172
- Chain-of-Verification Reduces Hallucination in Large Language Models: https://aclanthology.org/2024.findings-acl.212/
- SelfCheckGPT: https://aclanthology.org/2023.emnlp-main.557/
- ToTTo: A Controlled Table-To-Text Generation Dataset: https://aclanthology.org/2020.emnlp-main.89/
- OpenAI Structured Outputs (schema-constrained responses): https://platform.openai.com/docs/guides/structured-outputs
