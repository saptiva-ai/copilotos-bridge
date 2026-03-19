# Plan: Fix LLM Month-Value Confusion (Iteración 3 — Benchmark-Validated)

## Problema

El LLM cita valores correctos pero **los asocia a meses equivocados** en el texto narrativo. La gráfica y tabla son correctas (vienen de Plotly traces), pero el texto generado por el LLM confunde qué valor corresponde a qué mes.

**Evidencia** (9 feedbacks):
- FDBK-0093: "Oct 2024: 15,052.10 MDP" en texto pero tabla muestra otra cantidad → tomó valor de Dic
- FDBK-0111: "confunde los meses y me da cantidades de un mes que no corresponde"
- FDBK-0112: "los datos del texto no coinciden con los meses en gráfica y tablas"

## Root Cause (validado por benchmark)

**Benchmark v1** (1 banco, 12 meses): Turbo+pipe-table = **100%** accuracy.
**Benchmark v2** (2 bancos, 24 meses, system prompt producción): Turbo+pipe-table = **92.3%**, Legacy+markdown-kv = **93.9%**.

El bug **NO es de formato ni modelo** — es de **complejidad de contexto**:
- Queries simples (lookup, tendencia single-bank) → Turbo funciona perfecto
- Queries con datos densos (multi-banco, evolución, comparaciones) → **cross-bank swaps en transición de párrafo**
- La degradación v1→v2 fue de -7.7% para Turbo y -6.1% para Legacy con markdown-kv

**La instrucción actual** obliga al LLM a citar 12+ pares mes-valor de memoria. En queries complejas, confunde la asociación.

## Estrategia: Routing dinámico Turbo/Legacy + instrucciones adaptivas

En vez de degradar la UX con un solo enfoque, usamos **el modelo correcto para la complejidad de la query**:

| Tipo de query | Modelo | Instrucción | Latencia | Accuracy esperada |
|---------------|--------|-------------|----------|-------------------|
| Simple (lookup, tendencia) | **Turbo** | Solo tendencias + stats pre-computados | ~4s | 92-100% |
| Compleja (evolución, comparación, meses detallados) | **Legacy** | Cita valores exactos (es preciso) | ~12s | 94% |

**Beneficio UX**: El usuario no espera 12s por "¿cuál es la cartera de invex?". Solo cuando pide datos densos se activa Legacy, y la espera se justifica porque los datos son correctos.

---

## Fase 1: Señales de complejidad (data_complexity_signals)

Ya existen las señales en el código — solo hay que centralizarlas:

### 1a. `resolve_data_model()` — función nueva en `system_prompt_builder.py`

```python
def resolve_data_model(
    bank_chart_data: Optional[Dict[str, Any]],
    user_query: str,
    current_model: str,
) -> str:
    """
    Decide si escalar a Legacy basado en complejidad de datos.

    Señales de complejidad (cualquiera activa Legacy):
    - Multi-banco: >1 trace en plotly_config.data
    - Tabla densa: table_mode == "full" AND num_points > 6
    - Keywords de evolución/comparación en user_query

    Solo escala FROM Turbo TO Legacy. Si el usuario ya seleccionó
    Legacy u otro modelo, no lo cambia.
    """
```

### 1b. Señales de complejidad

| Señal | Fuente | Umbral |
|-------|--------|--------|
| Multi-banco | `len(plotly_config["data"]) > 1` | >1 trace |
| Datos densos | `table_mode == "full"` AND `num_points > 6` | >6 puntos + keyword "tabla" |
| Keywords evolución | regex: `evolucion\|mes a mes\|meses\|trimestre\|comparar?\|compara\|vs\b\|diferencia` | cualquiera |

### 1c. Punto de inyección

**Archivo**: `streaming_handler.py:419` — justo ANTES de `SystemPromptBuilder.build()`:

```python
# NUEVO: Model routing basado en data complexity
if bank_chart_data:
    routed_model = resolve_data_model(
        bank_chart_data=bank_chart_data,
        user_query=context.message,
        current_model=context.model,
    )
    if routed_model != context.model:
        logger.info(
            "model_routing.escalated",
            from_model=context.model,
            to_model=routed_model,
            reason="data_complexity",
        )
        context.model = routed_model

# EXISTENTE: SystemPromptBuilder.build(model=context.model, ...)
```

---

## Fase 2: Instrucciones adaptivas por modelo (analytics_data.py)

**Archivo**: `apps/backend/src/schemas/analytics_data.py`

### 2a. `to_llm_context()` acepta parámetro `model`

El `table_mode` ya se pasa como parámetro. Agregar `model: str = "Saptiva Turbo"` para adaptar instrucciones:

**Para Turbo** (model default — protección contra citas individuales):
```python
instruction = (
    "REGLAS PARA TU RESPUESTA:\n"
    "1. Describe la TENDENCIA general (crecimiento, caída, estabilidad) "
    "usando los estadísticos pre-computados de arriba.\n"
    "2. Puedes citar: último valor, mínimo, máximo y cambio del período.\n"
    "3. NO cites valores individuales de meses específicos — "
    "la tabla y gráfica adjuntas muestran ese detalle al usuario.\n"
    "4. NO incluyas tabla markdown — el sistema la agregará automáticamente.\n"
    "5. Si mencionas un valor, SIEMPRE inclúyelo con su fecha exacta "
    "tal como aparece en los estadísticos."
)
```

**Para Legacy** (modelo preciso — puede citar libremente):
```python
instruction = (
    "Usa los valores exactos de la tabla anterior en tu análisis. "
    "Cita los datos con su mes y año correspondiente de la tabla. "
    "NO incluyas tabla markdown — el sistema la agregará automáticamente. "
    "No redondees ni recalcules."
)
```

### 2b. Propagación del `model` por el pipeline

`build_analytics_context()` en `llm_context_builder.py` → `to_llm_context(table_mode, model)` en `analytics_data.py`.

Flujo: `streaming_handler` → `SystemPromptBuilder.build(model)` → `_build_bank_context(bank_chart_data, user_query)` → `build_analytics_context(model=model)` → `to_llm_context(table_mode, model)`.

---

## Fase 3: Feature flag + config

**Archivo**: `apps/backend/src/core/config.py`

```python
# Model routing for data queries
data_model_routing_enabled: bool = Field(
    default=False,
    description="Auto-escalate to Legacy for complex data queries",
)
data_model_escalation_target: str = Field(
    default="Saptiva Legacy",
    description="Model to use for complex data queries",
)
```

**Activación**: env var `DATA_MODEL_ROUTING_ENABLED=true`. OFF by default para deploy seguro.

---

## Fase 4: Post-procesador guardrail (safety net)

**Archivo**: `apps/backend/src/services/streaming/response_postprocessor.py`

Cuando el LLM es Turbo Y cita ≥3 pares mes-valor individuales (ignoró la instrucción), agregar disclaimer:

```python
@staticmethod
def detect_month_value_citations(
    response: str,
    bank_chart_data: Optional[Dict[str, Any]],
) -> Tuple[str, Optional[str]]:
    """Detecta citas mes-valor y agrega disclaimer si ≥3."""
```

Regex: `(enero|febrero|...|diciembre)\s*(de\s*)?(20\d{2})[\s:,]+[\d,.]+\s*(MDP|%|mdp)`

Si ≥3 citas: `"> Nota: Los valores exactos por mes están disponibles en la tabla y gráfica adjuntas."`

---

## Fase 5: Tests

### 5a. Unit tests — model routing (`test_data_model_routing.py`)

```python
def test_single_bank_stays_turbo():
    """Single bank, few points → no escalation."""

def test_multi_bank_escalates_to_legacy():
    """2+ traces in plotly_config → Legacy."""

def test_evolution_keywords_escalate():
    """'evolución mes a mes' → Legacy."""

def test_already_legacy_not_changed():
    """User selected Legacy → no re-routing."""

def test_feature_flag_disabled_no_routing():
    """Flag off → always current model."""
```

### 5b. Unit tests — instrucciones adaptivas (`test_analytics_data.py`)

```python
def test_turbo_instruction_prohibits_individual_citations():
    context = payload.to_llm_context(table_mode="full", model="Saptiva Turbo")
    assert "NO cites valores individuales" in context

def test_legacy_instruction_allows_exact_values():
    context = payload.to_llm_context(table_mode="full", model="Saptiva Legacy")
    assert "valores exactos" in context
    assert "NO cites valores individuales" not in context
```

### 5c. Unit tests — guardrail post-procesador

```python
def test_detect_citations_with_many_month_values():
def test_no_detection_with_summary_stats_only():
```

### 5d. Regression E2E

Re-ejecutar los 20 tests de grounding + benchmark v2 para validar.

---

## Fase 6: Validación E2E contra PROD

1. **Feature flag OFF**: deploy, verificar que comportamiento es idéntico al actual
2. **Feature flag ON**: activar routing
3. Probar queries:
   - "cartera comercial de invex" → Turbo (~4s), texto sin citas individuales
   - "evolución de la cartera de invex en 2024 mes a mes" → Legacy (~12s), citas exactas correctas
   - "compara cartera invex vs bbva" → Legacy, sin cross-bank swaps
4. Verificar logs: `model_routing.escalated` aparece solo para queries complejas

---

## Archivos a modificar

| # | Archivo | Cambio |
|---|---------|--------|
| 1 | `apps/backend/src/services/streaming/system_prompt_builder.py` | Nueva función `resolve_data_model()` |
| 2 | `apps/backend/src/routers/chat/handlers/streaming_handler.py` | Inyectar routing antes de `SystemPromptBuilder.build()` |
| 3 | `apps/backend/src/schemas/analytics_data.py` | `to_llm_context(model=)` con instrucciones adaptivas |
| 4 | `apps/backend/src/services/llm_context_builder.py` | Propagar `model` a `build_analytics_context()` |
| 5 | `apps/backend/src/core/config.py` | Feature flag `data_model_routing_enabled` |
| 6 | `apps/backend/src/services/streaming/response_postprocessor.py` | Guardrail `detect_month_value_citations()` |
| 7 | `apps/backend/tests/unit/test_data_model_routing.py` | Tests routing (NUEVO) |
| 8 | `apps/backend/tests/unit/test_analytics_extractor.py` | Tests instrucciones adaptivas |
| 9 | `apps/backend/tests/unit/test_response_postprocessor.py` | Tests guardrail |

## Progreso de ejecución (2026-02-11)

| Fase | Estado | Commit | Tests |
|------|--------|--------|-------|
| 1. Routing dinámico | DONE | `27f12191` | 20 unit |
| 2. Instrucciones adaptivas | DONE | `27f12191` | 8 unit |
| 3. Feature flag | DONE | `27f12191` | — |
| 4. Guardrail post-procesador | DONE | `16df986e` | 11 unit |
| 5a-c. Unit tests | DONE | incluidos arriba | 39 total |
| 5d. Regression E2E | PENDIENTE | — | — |
| 6. Validación PROD | PENDIENTE | — | — |

## Riesgo

- **Bajo**: Feature flag OFF por default — deploy sin cambio de comportamiento
- **Medio**: Legacy tiene 3x la latencia de Turbo — pero solo para queries complejas donde la latencia se justifica por precisión
- **Mitigation**: El routing es conservador (solo escala de Turbo→Legacy, nunca degrada). Si Legacy no responde, el fallback ya existe en el streaming pipeline

## Evidencia de benchmark

| Escenario | Turbo | Legacy | Veredicto |
|-----------|-------|--------|-----------|
| Single-bank, 12 meses | **100%** / 3.9s | 100% / 8.5s | Turbo sobra |
| Multi-bank, 24 meses | **92.3%** / 4.4s | 84-**93.9%** / 12.6s | Legacy para multi-bank |
| Cross-bank swaps | **0** swaps (pipe-table) | 1-4 swaps | Turbo más seguro + instrucción restrictiva |

**Conclusión**: Turbo+instrucción restrictiva para simple (rápido, seguro), Legacy+instrucción permisiva para complejo (lento, preciso). Mejor UX que usar Legacy para todo.
