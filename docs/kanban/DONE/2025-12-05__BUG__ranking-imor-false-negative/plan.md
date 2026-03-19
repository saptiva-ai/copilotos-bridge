# Plan: BUG-014 Fix

## Phase 1: Detect ranking and extract banks from traces

**Location:** `streaming_handler.py` lines 1751-1779

```python
# BUG-014: Detect ranking intent and extract banks from traces
intent_type = (
    get_val(bank_chart_data, "intent")
    or get_val(metadata, "intent")
    or ""
)
is_ranking = intent_type == "ranking"

# Handle ranking intent - bank_names is empty but data contains all banks
if not bank_names_list:
    # Check if we have trace data (actual banks in chart)
    plotly_cfg = get_val(bank_chart_data, "plotly_config", {})
    traces = plotly_cfg.get("data", []) if plotly_cfg else []
    if traces:
        # Extract bank names from plotly traces
        trace_names = [
            t.get("name", "") for t in traces if t.get("name")
        ]
        if trace_names:
            bank_names_list = trace_names
            bank_names = ", ".join(bank_names_list)
            is_ranking = True
        else:
            bank_names = "todos los bancos del sistema"
            is_ranking = True
    else:
        bank_names = "todos los bancos del sistema"
else:
    bank_names = ", ".join(bank_names_list)
```

## Phase 2: Add ranking-specific LLM context

**Location:** `streaming_handler.py` lines 1850-1861

```python
# BUG-014: Add ranking-specific context
if is_ranking:
    bank_context += f"""

**TIPO DE CONSULTA: RANKING**
El usuario pidió un ranking/clasificación de bancos por {metric_name}.
El gráfico muestra TODOS los bancos ordenados por la métrica solicitada.
En tu respuesta:
- Menciona quién lidera el ranking y quién está al final
- Destaca la posición de bancos relevantes (INVEX, BBVA, Banorte, etc.)
- Compara los valores extremos (mejor vs peor)
- Proporciona contexto sobre qué significa estar alto/bajo en este ranking"""
```

## Testing

### Unit Tests
**File:** `apps/backend/tests/unit/test_ranking_context_extraction.py`

Tests the core logic for:
- Extracting bank names from plotly traces when `bank_names_list` is empty
- Detecting ranking intent from metadata
- Fallback to "todos los bancos del sistema" when no traces

Run: `python -m pytest apps/backend/tests/unit/test_ranking_context_extraction.py -v`

### E2E Tests
**File:** `tests/e2e/test_ranking_false_negative.py`

Validates against regression:
- Chart returns data for multiple banks
- LLM response does NOT contain false negative phrases ("No encuentro información")
- LLM acknowledges ranking data with positive indicators

Run: `python tests/e2e/test_ranking_false_negative.py`

## Verification

1. Deploy to production
2. Test query: "¿Cuál es el ranking de bancos por IMOR?"
3. Verify LLM acknowledges data and provides ranking analysis
