---
status: DONE
---
# BUG: Response Grounding - Desincronización LLM ↔ Data Pipeline

## Tipo: A - Desincronización

## Prioridad: 🔴 Critical

## Problema

El LLM genera texto que contradice los datos devueltos por el pipeline:
- `chart_status: success` + texto: "No puedo proporcionar datos"
- Datos válidos en `bank_chart_data` ignorados por el LLM
- El LLM no recibe/lee el contexto de datos del handler

## Evidencia (Producción 2026-02-03)

```
Query: "cartera comercial de invex por entidad federativa"
Chart: ✅ success (Centro: 5.94B, Norte: 2.65B...)
Texto: "No puedo proporcionar el detalle por entidad federativa"
```

## Causa Raíz

El prompt del LLM NO incluye los datos devueltos por el handler. El LLM genera texto "libre" sin contexto de los datos reales.

## Solución Propuesta

### 1. Response Grounding Layer
```python
class ResponseGroundingLayer:
    def ground_response(self, handler_result, llm_prompt):
        if handler_result.chart_status == "success":
            # Inyectar datos en prompt
            grounded_prompt = f"""
            DATOS DISPONIBLES (OBLIGATORIO usar estos):
            {handler_result.data_summary}
            
            INSTRUCCIÓN: Describe ÚNICAMENTE los datos anteriores.
            NO digas "no tengo datos" si hay datos arriba.
            """
            return grounded_prompt
```

### 2. Coherence Validator
```python
def validate_coherence(text: str, chart_data: dict) -> bool:
    """Detecta contradicciones texto ↔ datos"""
    negative_phrases = ["no puedo", "no tengo", "no hay datos", "error técnico"]
    has_negative = any(p in text.lower() for p in negative_phrases)
    has_data = chart_data.get("chart_status") == "success"
    
    if has_negative and has_data:
        raise IncoherentResponseError("Texto contradice datos")
```

## Archivos a Modificar

- `plugins/bank-advisor-private/src/main.py`
- `apps/backend/src/services/saptiva_client.py`
- `apps/backend/src/domain/chat_strategy.py`

## Criterios de Aceptación (DoD)

- [x] Cuando hay datos, el texto DEBE describirlos
- [x] Validador detecta contradicciones y las corrige
- [x] E2E test: query regional → texto coherente con chart
- [x] 20/20 e2e grounding regression tests pasando
- [ ] **Bug no persiste en PROD** (verificar post-deploy)

## Progreso

### 2026-02-06: Lazy LLM Context + Table Injection (commit `f8a0ccec`)

**Problema resuelto:** El LLM generaba valores inventados porque el contexto no incluía datos estructurados ni tablas cuando el usuario las pedía.

**Cambios implementados:**
1. `AnalyticsPayload.to_llm_context(table_mode)` — 3 niveles de densidad (none/excerpt/full)
2. `resolve_table_mode()` — regex con NFD accent stripping para keywords en español
3. `inject_table_if_missing()` — fallback que inyecta tabla si el LLM la omite
4. `table_append_chunk` SSE event — entrega tabla inyectada en tiempo real
5. `user_query` pasado explícitamente a `SystemPromptBuilder.build()`

**Keywords (accent-insensitive, case-insensitive):**
- FULL: tabla, mes a mes, desglose, muestrame los datos, listado, todos los datos
- EXCERPT: datos, valores, detalle, cifras, numeros, muestrame, compara

**Tests:** 55 unit + 20/20 e2e grounding regression

### Reopened: 2026-02-05 (Feedback Triage)

| ID | Fecha | Query | Problema |
|----|-------|-------|----------|
| FDBK-0072 | 2026-02-05 | "cartera comercial de 2025" | Texto dice "Enero 2025: 15,048.23 MDP" pero tabla/grafica muestra 15,047.93. Discrepancia de 0.30 MDP |

### Reopened: 2026-02-10 (Triage automatizado)

| ID | Fecha | Query | Problema |
|----|-------|-------|----------|
| FDBK-0111 | 2026-02-10 | "muéstrame la cartera comercial de invex en 2024" | Grafica y tabla OK, texto confunde meses y cantidades |
| FDBK-0112 | 2026-02-10 | "muestrame la cartera comercial de bbva en 2025" | Grafica y tabla OK, texto cita valores de meses incorrectos |

**Patron persistente:** El LLM sigue citando valores asociados a meses equivocados. La grafica/tabla son correctas pero el texto narrativo usa cantidades de otros meses. Mismo patron que FDBK-0072, FDBK-0093, FDBK-0094.

**Plan v2 (2026-02-10):** Restringir al LLM a describir tendencias + stats pre-computados.

**Plan v3 (2026-02-11):** Benchmark-validated. Routing dinámico Turbo/Legacy + instrucciones adaptivas. Ver `plan.md` y `docs/reports/benchmark_grounding_2026-02-11.md`.

### Reopened: 2026-02-11 (Triage automatizado)

| ID | Fecha | Query | Problema | Stale-chart verdict |
|----|-------|-------|----------|---------------------|
| FDBK-0119 | 2026-02-11 | "cual es la cartera total de INVEX en enero 2024 y en enero 2025" | LLM dice "$38,500M (estimado basado en tendencia)" — fabrica el valor | STALE (falta 2024 en x_range) |
| FDBK-0120 | 2026-02-11 | "que variacion tuvo la cartera de INVEX de enero 2024 respecto a enero 2025" | Calculo +5.74% basado en valor fabricado de FDBK-0119 | STALE |
| FDBK-0121 | 2026-02-11 | "Dame la cartera total de cada banco (lista de 10) para enero 2024 y enero 2025" | Tabla con valores redondeados fabricados ($1,900M, $2,100M para MONEX) | STALE |
| FDBK-0123 | 2026-02-11 | "Muéstrame la cartera comercial CC de enero 2025 para INVEX" | Texto: "$36,410,974,308" pero gráfica muestra valor distinto | — |
| FDBK-0124 | 2026-02-11 | "Muéstrame la cartera comercial CC de INVEX en enero 2025" | Texto vs gráfica desincronizados (mismo patrón que 0123) | — |
| FDBK-0125 | 2026-02-11 | "Muéstrame la cartera total de enero 2025 para INVEX" | Texto: "$38,500,000,000", gráfica con valor correcto distinto | — |
| FDBK-0126 | 2026-02-11 | "cartera comercial de INVEX en enero 2025 vs enero 2024" | Texto con datos incorrectos + COMPARISON_FORMAT (1 trace) | COMPARISON_FORMAT + STALE |

**Patron persistente (3ra ocurrencia, 7 feedbacks):** El LLM Turbo sigue fabricando valores cuando debe citar data points específicos. El fix v3 (routing Turbo→Legacy) está en `develop` pero no desplegado a PROD. Estos feedbacks confirman la urgencia del deploy.

**Sub-patrón nuevo (FDBK-0119→0120):** Valores fabricados se propagan entre turnos vía `fact_extractor.py` → contexto de memoria. El LLM inventó "$38,500M" y el turno siguiente lo reutilizó para calcular variación (+5.74% incorrecto).

### Fix: Multi-Bank Routing in EvolucionBancoHandler (2026-02-11)

**Problema:** Queries multi-banco como "compara la evolución de BBVA e INVEX mes a mes" solo extraían el primer banco. Causaba:
1. Fallback a NL2SQL → bar chart resumen (2 puntos)
2. LLM alucinaba 12 meses de datos que no existían en el chart

**Cambios implementados:**

| Archivo | Cambio |
|---------|--------|
| `evolucion_banco_handler.py` | `_detect_banks()` (multi-banco), `_detect_metric()`, `_handle_multi_bank()` → delega a `EvolutionUseCase` |
| `evolution.py` | `to_response_dict()` en `EvolutionResult` — convierte a formato FSM handler |
| `analytics_data.py` | Warning anti-alucinación para charts resumen (<=4 pts, multi-banco) en `to_llm_context()` |

**Tests:** 26 unit (handler) + 4 anti-alucinación + 44 analytics = 70 tests passing

**E2E GD-7:** Requiere rebuild de `bank-advisor` container para validar con datos reales.

### Deep Investigation (2026-02-10)

**Previous fix (2026-02-06, commit `f8a0ccec`)**: Created `AnalyticsExtractor` (keeps dates paired with values in `DataPoint` objects), `LLMContextBuilder` (generates markdown table with date-value columns), and `to_llm_context()` with 3 density modes. The grounding instruction at `analytics_data.py:370` tells the LLM: "Usa los valores exactos de la tabla anterior en tu análisis. NO incluyas tabla markdown en tu respuesta."

**Gap identified**: The instruction creates a contradiction — the LLM must cite exact values from a 12+ row table but is told NOT to include the table. So it writes free-text from "memory" of the context, and when there are many month-value pairs, it **confuses which value belongs to which month**. The chart and table (injected by post-processor) are correct because they come directly from Plotly traces, but the LLM text is generated independently.

**Code trace**:

| Step | File:Line | What happens | Problem |
|------|-----------|-------------|---------|
| 1 | `analytics_extractor.py:238-240` | Extracts x (dates) + y (values) from Plotly traces correctly | Data is correct |
| 2 | `analytics_data.py:272-279` | Builds markdown table with `Fecha \| BankA \| BankB` columns | Table is correct |
| 3 | `analytics_data.py:294-337` | `_build_summary_stats()` — min/max/último/cambio per bank | Stats are correct |
| 4 | `analytics_data.py:368-371` | Instruction: "Usa valores exactos... NO incluyas tabla markdown" | LLM must cite from memory |
| 5 | `llm_context_builder.py:228-231` | Grounding rule: 'PROHIBIDO decir "no tengo datos"' | Prevents denial, but doesn't prevent month confusion |
| 6 | LLM generates text | Cites Oct value for Dec, Dec value for Oct, etc. | **Month-value association error** |

**Evidence pattern** (persistent across 7+ feedbacks):
- FDBK-0093: "Oct 2024: 15,052.10 MDP" in text but table shows different → text took Dec 2024 value
- FDBK-0094: "Oct 2024" in text shows "Dic 2024" value from chart
- FDBK-0111: "confunde los meses y me da cantidades de un mes que no corresponde"
- FDBK-0112: "los datos que presenta en el texto no coinciden con los meses en grafica y tablas"

**Fix strategy**:
1. **Option A — Post-processor validation**: Add a `validate_month_value_citations()` step after LLM streaming completes. Extract month-value pairs cited in text using regex, compare against `AnalyticsPayload.series[].datos[]`. Flag or correct mismatches.
2. **Option B — Restructured prompt**: Change the instruction from "cite exact values from table" to "reference only the summary stats (min/max/último/cambio) — do NOT cite individual month-value pairs". This reduces the chance of month confusion since the LLM only needs to reference 4 pre-computed stats per bank.
3. **Option C — Hybrid**: Allow the LLM to include the table (remove the "NO incluyas tabla" restriction) and instead instruct it to reference the table rows by position rather than citing values inline.

**Recommended**: Option B (lowest risk, no new code needed). Option A is more robust but requires new post-processing logic.

## Relacionado

- TIPO A: Desincronización
- Feedback negativo: 2026-02-03 (10+ thumbs down) + FDBK-0072 (2026-02-05) + FDBK-0111/0112 (2026-02-10)

## Feedback Vinculado

**16 reporte(s)** de usuarios en produccion.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0003 | `7f5aa3b9` | CARTERA_COMERCIAL de INVEX de 2025 puedes concentrar en u... | el saldo se modifico al presentarlo distribuido por entidad federativa | 2026-01-21 |
| 2 | FDBK-0004 | `7f5aa3b9` | cual es el saldo de la cartera comercial de invex a octub... | El dato que presenta ahora difiere del que primero presento y no es capaz de ... | 2026-01-21 |
| 3 | FDBK-0026 | `cb6c6879` | explícame a detalle que es el IMOR, como se obtiene y dam... | - en la parte de: "en el caso de santander" menciona que el la tasa de morosi... | 2026-02-03 |
| 4 | FDBK-0033 | `cb6c6879` | muestrame la cartera comercial de invex | me dijo que no puede mostrarme el resultado, sin embargo, si me da la tabla y... | 2026-02-03 |
| 5 | FDBK-0072 | `cb6c6879` | ahora muéstrame únicamente la cartera comercial de 2025 | mi única observación aquí es que el valor que menciona en enero 2025 (15,048.... | 2026-02-05 |
| 6 | FDBK-0093 | `cb6c6879` | muestrame una grafica en la que se compare la cartera com... | - en el texto me dice que la cartera de invex fue: "Oct 2024: 15,052.10 MDP" ... | 2026-02-06 |
| 7 | FDBK-0094 | `cb6c6879` | muestrame una grafica en la que se compare la cartera com... | en el texto para santander Oct 2024 me dice una cantidad y en la grafica me p... | 2026-02-06 |
| 8 | FDBK-0111 | `cb6c6879` | muéstrame la cartera comercial de invex en 2024 | despliega los datos correctamente en la grafica y tabla — en el texto confunde los meses y me da cantidades de un mes que no corresponde | 2026-02-10 |
| 9 | FDBK-0112 | `cb6c6879` | muestrame la cartera comercial de bbva en 2025 | los datos de la grafica y tabla están bien — los datos que presenta en el texto no coinciden con los meses en grafica y tablas | 2026-02-10 |
| 10 | FDBK-0119 | `85338a1e` | cual es la cartera total de INVEX en enero 2024 y en enero 2025 | menciona que el valor de enero 2025 es estimado, como si no tuviera el dato | 2026-02-11 |
| 11 | FDBK-0120 | `85338a1e` | que variación tuvo la cartera de INVEX de enero 2024 respecto a enero 2025 | el calculo esta mal pues el valor de enero 2025 no es el correcto | 2026-02-11 |
| 12 | FDBK-0121 | `85338a1e` | Dame la cartera total de cada banco (lista de 10) para enero 2024 y enero 2025 | no tiene información de banco base, datos presentados incorrectos | 2026-02-11 |
| 13 | FDBK-0123 | `85338a1e` | Muéstrame la cartera comercial CC de enero 2025 para INVEX | gráfica no coincide con la información que proporciona en texto | 2026-02-11 |
| 14 | FDBK-0124 | `85338a1e` | Muéstrame la cartera comercial CC de INVEX en enero 2025 | datos en el texto del chat estan mal, gráfica correcta | 2026-02-11 |
| 15 | FDBK-0125 | `85338a1e` | Muéstrame la cartera total de enero 2025 para INVEX | dato del texto esta mal, los de la gráfica son correctos | 2026-02-11 |
| 16 | FDBK-0126 | `85338a1e` | cartera comercial de INVEX en enero 2025 vs enero 2024 | datos del texto son incorrectos, gráfica OK | 2026-02-11 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0003
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `ea9ea471-f54c-4153-801e-95c3f00597af`
- **Message**: `1688173e-0fa3-4c25-aa17-d8bad44dd3e1`
- **Rating**: 👎
- **Query**: "CARTERA_COMERCIAL de INVEX de 2025 puedes concentrar en una tabla el comparativo previo por region? (Cartera Comercial)"
- **Feedback**: "el saldo se modifico al presentarlo distribuido por entidad federativa"
- **Fecha**: 2026-01-21T20:24:48.917Z

### FDBK-0004
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `ea9ea471-f54c-4153-801e-95c3f00597af`
- **Message**: `02cbd8d9-4478-4ca4-81a1-9b45e1ec4230`
- **Rating**: 👎
- **Query**: "cual es el saldo de la cartera comercial de invex a octubre de 2025?"
- **Feedback**: "El dato que presenta ahora difiere del que primero presento y no es capaz de explicar porque se origina la diferencia"
- **Fecha**: 2026-01-21T20:27:36.716Z

### FDBK-0026
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `b96f4170-45e7-4b59-bc3c-5dc4d77c75ca`
- **Message**: `5315c15c-d9d3-4dc6-8a60-ddbe9ef3e980`
- **Rating**: 👎
- **Query**: "explícame a detalle que es el IMOR, como se obtiene y dame un ejemplo que cualquier persona pudiera entender"
- **Feedback**: "- en la parte de: "en el caso de santander" menciona que el la tasa de morosidad fue de 2.32% en el mes de octubre, sin embargo, en los datos de la grafica en el mes de octubre aparece 2.38%
  - me desplego la grafica y tabla de todo todos los datos, checar si en este caso en base al prompt se quiere que despliegue esto"
- **Fecha**: 2026-02-03T18:14:15.568Z

### FDBK-0033
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `6bf39d89-1f72-4814-9a1b-aaf0aa99b278`
- **Message**: `c79ecbb7-44a9-43d7-90b8-44076424f345`
- **Rating**: 👎
- **Query**: "muestrame la cartera comercial de invex"
- **Feedback**: "me dijo que no puede mostrarme el resultado, sin embargo, si me da la tabla y grafica  "
- **Fecha**: 2026-02-03T19:48:46.645Z

### FDBK-0072
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `9ae671a7-3a03-498f-a6c3-c142f665825a`
- **Message**: `15a17c30-ccd3-481c-af0e-7ecab1857e79`
- **Rating**: 👎
- **Query**: "ahora muéstrame únicamente la cartera comercial de 2025"
- **Feedback**: "mi única observación aquí es que el valor que menciona en enero 2025 (15,048.23) no corresponde al de la tabla y gráfico (15,047.93)"
- **Fecha**: 2026-02-05T16:21:33.451Z

### FDBK-0093
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `5652c5bf-e97c-4812-a20a-6d029a7ae9ae`
- **Message**: `87a38f57-fc9b-4971-b9be-f492a08e36ae`
- **Rating**: 👎
- **Query**: "muestrame una grafica en la que se compare la cartera comercial de bbva e invex el ultimo año"
- **Feedback**: "- en el texto me dice que la cartera de invex fue: "Oct 2024: 15,052.10 MDP" pero en los datos de la tabla Oct 2024 muestra otra cantidad
  - la cantidad que dice el texto la toma de diciembre 2024 para invex "
- **Fecha**: 2026-02-06T16:12:14.834Z

### FDBK-0094
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `5652c5bf-e97c-4812-a20a-6d029a7ae9ae`
- **Message**: `d2b467cd-ade0-4f4a-8798-217ce59a7c66`
- **Rating**: 👎
- **Query**: "muestrame una grafica en la que se compare la cartera comercial de bbva y santander el ultimo año"
- **Feedback**: "en el texto para santander Oct 2024 me dice una cantidad y en la grafica me pone la cantidad de Dic 2024"
- **Fecha**: 2026-02-06T16:16:35.992Z

</details>
