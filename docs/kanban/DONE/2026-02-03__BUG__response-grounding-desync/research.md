# Research: Response Grounding Desync

## Flujo de Datos Actual

```
User Query
    ↓
Backend (chat_strategy.py)
    ↓
bank_analytics_client.py → MCP call to bank-advisor plugin
    ↓
Plugin returns: {data, plotly_config, metadata, chart_status}
    ↓
_build_chart_data() → BankChartData schema
    ↓
chat_strategy.py adds to context_mgr.add_tool_result()
    ↓
context_manager._summarize_tool_result("bank_analytics", result)
    ↓
NO HANDLER → _default_summary() → truncate to 500 chars  ← BUG HERE
    ↓
LLM receives: "Tool result: {'type': 'bank_chart', 'metric_name': 'IMOR'..."
    ↓
LLM generates text WITHOUT understanding the data
```

## Causa Raíz Identificada

**Archivo**: `apps/backend/src/services/context_manager.py`
**Líneas**: 113-122

```python
def _summarize_tool_result(self, tool_name: str, result: Dict) -> str:
    summaries = {
        "audit_file": self._summarize_audit_result,
        "excel_analyzer": self._summarize_excel_result,
        "deep_research": self._summarize_research_result,
        # NO EXISTE: "bank_analytics": self._summarize_bank_analytics_result
    }
    summarizer = summaries.get(tool_name, self._default_summary)  # ← Fallback
    return summarizer(result)

def _default_summary(self, result: Dict) -> str:
    """Default summarizer for unknown tool types."""
    return f"Tool result: {str(result)[:500]}..."  # ← TRUNCA A 500 CHARS
```

## Impacto

Cuando `bank_analytics` retorna datos válidos:

```python
{
    "chart_status": "success",
    "metric_name": "CARTERA_COMERCIAL",
    "bank_names": ["INVEX"],
    "title": "Cartera Comercial por Región",
    "plotly_config": {
        "data": [
            {"x": ["Centro", "Norte", "Sur"], "y": [5.94e9, 2.65e9, 1.2e9], "name": "INVEX"}
        ],
        "layout": {"title": "Distribución Regional"}
    },
    "time_range": {"start": "2025-10-01", "end": "2025-10-01"}
}
```

El LLM recibe:

```
Tool result: {'type': 'bank_chart', 'metric_name': 'CARTERA_COMERCIAL', 'bank_names': ['INVEX'], 'time_range': {'start': '2025-10-01', 'end': '2025-10-01'}, 'plotly_config': {'data': [{'x': ['Centro', 'Norte', 'Sur'], 'y': [5940000000.0, 2650000...
```

**El LLM no sabe**:
- Que la gráfica fue exitosa
- Qué valores específicos mostrar
- Qué bancos/regiones están incluidos
- Cómo interpretar los números

## Estructura de BankChartData (schema)

```python
# apps/backend/src/schemas/bank_chart.py:112-149
class BankChartData(BaseModel):
    type: str = "bank_chart"
    metric_name: str  # "IMOR", "CARTERA_COMERCIAL", etc.
    bank_names: List[str]  # ["INVEX", "BBVA"]
    time_range: Optional[TimeRange]  # {start, end}
    plotly_config: Dict[str, Any]  # {data: [...traces], layout: {...}}
    data_as_of: str  # "2025-10-01"
    title: Optional[str]  # "IMOR - INVEX vs Sistema"
    chart_status: ChartStatus  # SUCCESS/EMPTY/ERROR/CLARIFICATION
    metadata: Optional[Dict[str, Any]]  # {sql_generated, pipeline, etc.}
```

## Solución Propuesta

Agregar `_summarize_bank_analytics_result()` que extraiga:

1. **Estado del chart**: SUCCESS → "Datos disponibles", ERROR → "Error técnico"
2. **Métrica**: "Métrica: CARTERA_COMERCIAL"
3. **Bancos**: "Bancos: INVEX, BBVA"
4. **Período**: "Período: Oct 2025"
5. **Valores clave**: Extraer de traces (min, max, latest)
6. **Título**: Para contexto semántico

**Output ejemplo**:
```
📊 Datos de Cartera Bancaria:
Estado: ✅ Gráfica generada exitosamente
Métrica: CARTERA_COMERCIAL
Bancos: INVEX
Período: 2025-10-01
Valores por región:
  - Centro: $5,940,000,000
  - Norte: $2,650,000,000
  - Sur: $1,200,000,000

INSTRUCCIÓN: Describe estos datos en tu respuesta. NO digas "no tengo datos".
```

## Archivos a Modificar

1. `apps/backend/src/services/context_manager.py`
   - Agregar `_summarize_bank_analytics_result()`
   - Registrar en dict `summaries`

## Validación

- [ ] Query regional → LLM describe datos del chart
- [ ] `chart_status: success` → texto NO dice "no tengo datos"
- [ ] Valores en texto coherentes con plotly_config
