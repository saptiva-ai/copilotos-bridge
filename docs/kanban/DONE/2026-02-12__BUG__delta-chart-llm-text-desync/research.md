# Research: Delta Chart LLM Text Desync

## Data Flow Trace (completo)

### 1. Plugin: DeltaResult genera datos ricos

```
evolution.py:272 → DeltaResult.to_response_dict()
├── plotly_config: {data: [{type: "bar", orientation: "h", x: [pcts], y: [banks]}]}
├── table_data: {columns: ["Banco","Cartera 2024-01","Cartera 2025-01","Variacion (%)"], rows: [...]}
├── summary: "Variacion de CARTERA_TOTAL entre 2024-01-01 y 2025-01-01 para 10 bancos"
├── bank_names: ["SABADELL","MONEX",...]
└── metadata: {metric_type: "currency"}
```

### 2. Backend: _build_chart_data() extrae parcialmente

```
bank_analytics_client.py:1220-1256 → _build_chart_data()
├── plotly_config ← result["plotly_config"]          ✅
├── table_data ← result.get("table_data")            ✅ (linea 1255)
├── response_text ← result.get("response_text", "")  ✅ (pero DeltaResult NO lo genera)
├── title ← plotly_config["layout"]["title"]          ✅
└── summary ← result.get("summary")                  ❌ NUNCA EXTRAIDO
```

**Hallazgo clave**: `response_text` se extrae pero DeltaResult no lo genera. Este seria el canal natural para inyectar un resumen pre-formateado.

### 3. Backend: BankChartData schema

```python
# schemas/analytics_data.py (BankChartData)
class BankChartData(BaseModel):
    plotly_config: dict
    title: str
    response_text: str          # ← vacío para delta charts
    metadata: dict
    table_data: dict | None     # ← EXISTE en el schema pero no se usa downstream
    chart_status: str
```

**Hallazgo**: `table_data` SÍ llega al schema, pero `system_prompt_builder` nunca lo lee.

### 4. Backend: SystemPromptBuilder ignora table_data

```
system_prompt_builder.py:491 → _build_bank_context()
├── build_analytics_context(bank_chart_data)
│   └── AnalyticsExtractor.extract(bank_chart_data)
│       └── _extract_series(plotly_config)       ← SOLO plotly traces
│           └── Retorna: "INVEX: 22.1%, MONEX: 40.8%..." (sin contexto)
└── NO consulta bank_chart_data.table_data
    NO consulta bank_chart_data.response_text
```

### 5. LLM Context final

```
BASE_CONTEXT:
  "La grafica ya se genero automaticamente.
   NO la describas, NO la expliques."

ANALYTICS_CONTEXT:
  "Datos del chart:
   SABADELL: 49.13
   MONEX: 40.82
   ..."

→ LLM ve numeros pero no sabe:
  - Que representan variaciones % entre dos periodos
  - Que table_data tiene los valores absolutos de ambos periodos
  - Que debe presentarlos en formato tabular
```

## Puntos de Inyeccion Candidatos

### Opcion A: `analytics_extractor.py` (recomendada)

Modificar `_extract_series()` o agregar `_extract_delta_context()`:
- Si `visualization == "bar"` y hay `table_data` → inyectar tabla formateada
- Si hay `summary` → inyectar como preambulo

**Pro**: Centralizado, afecta todos los delta charts
**Con**: Requiere pasar `table_data` desde `BankChartData` al extractor

### Opcion B: `system_prompt_builder.py`

En `_build_bank_context()`, detectar delta charts y construir contexto adicional:
```python
if bank_chart_data.table_data:
    context += format_table_for_llm(bank_chart_data.table_data)
```

**Pro**: Mas directo, no modifica el extractor
**Con**: Logica de formateo fuera del extractor

### Opcion C: `response_text` en DeltaResult (canal existente)

En `evolution.py`, generar `response_text` pre-formateado en DeltaResult:
```python
return {
    ...
    "response_text": self._format_delta_text(sorted_rows, date_a, date_b),
}
```

**Pro**: Usa canal existente que ya fluye al LLM
**Con**: El LLM no "explica" — solo repite texto pre-generado

### Recomendacion

**Opcion A + C combinadas**:
1. Generar `response_text` con resumen breve en DeltaResult (C)
2. Inyectar `table_data` formateado en analytics_extractor (A)
3. El LLM recibe contexto completo y puede responder con naturalidad

## Observaciones Adicionales

- `inject_table_if_missing()` en post-processor ya maneja inyeccion de tablas en el response final — pero opera DESPUES del LLM, no antes
- El `table_data` del delta chart tiene estructura identica al `table_data` que el frontend renderiza — no hay transformacion necesaria
- `response_text` vacío es el disparador: cuando el LLM no tiene texto guia, improvisa
