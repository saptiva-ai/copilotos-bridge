# Plan: Fix Delta Chart LLM Text Desync (TDD)

## Enfoque TDD

Tests PRIMERO, implementacion DESPUES. Cada fase tiene su test rojo → verde → refactor.

---

## Phase 1: DeltaResult genera `response_text` (plugin)

### Test Rojo 1.1: `test_delta_result_has_response_text`

```python
# plugins/bank-advisor-private/tests/unit/test_delta_response_text.py

class TestDeltaResultResponseText:
    """DeltaResult.to_response_dict() must include response_text."""

    def test_response_text_present(self):
        result = DeltaResult(
            metric="cartera_total",
            date_a="2024-01-01",
            date_b="2025-01-01",
            rows=[
                DeltaRow("INVEX", 100.0, 122.0, 22.0),
                DeltaRow("BBVA", 500.0, 485.0, -3.0),
            ],
        )
        d = result.to_response_dict()
        assert "response_text" in d
        assert d["response_text"]  # not empty

    def test_response_text_mentions_metric(self):
        result = DeltaResult(metric="cartera_total", ...)
        d = result.to_response_dict()
        assert "cartera" in d["response_text"].lower()

    def test_response_text_mentions_periods(self):
        result = DeltaResult(date_a="2024-01-01", date_b="2025-01-01", ...)
        d = result.to_response_dict()
        assert "2024" in d["response_text"]
        assert "2025" in d["response_text"]

    def test_response_text_mentions_all_banks(self):
        rows = [DeltaRow("INVEX", 100, 122, 22), DeltaRow("BBVA", 500, 485, -3)]
        result = DeltaResult(rows=rows, ...)
        d = result.to_response_dict()
        assert "INVEX" in d["response_text"]
        assert "BBVA" in d["response_text"]
```

### Implementacion 1.1

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/evolution.py`
**Metodo**: `DeltaResult.to_response_dict()`

Agregar `response_text` al dict de retorno:

```python
def _build_response_text(self) -> str:
    """Build LLM-ready text summary of delta comparison."""
    lines = [
        f"Comparacion de {self.metric.upper().replace('_', ' ')} "
        f"entre {self.date_a} y {self.date_b}:\n"
    ]
    for r in sorted(self.rows, key=lambda r: r.pct_change, reverse=True):
        sign = "+" if r.pct_change >= 0 else ""
        lines.append(
            f"- {r.bank}: {r.value_a:,.1f} → {r.value_b:,.1f} MDP "
            f"({sign}{r.pct_change:.1f}%)"
        )
    return "\n".join(lines)
```

Y en `to_response_dict()`:
```python
return {
    ...
    "response_text": self._build_response_text(),
}
```

---

## Phase 2: `analytics_extractor` inyecta `table_data` al contexto (backend)

### Test Rojo 2.1: `test_extractor_includes_table_data`

```python
# apps/backend/tests/unit/test_analytics_extractor_delta.py

class TestAnalyticsExtractorDelta:
    """Extractor must include table_data in LLM context for delta charts."""

    def test_delta_chart_context_has_table(self):
        chart_data = BankChartData(
            plotly_config={
                "data": [{"type": "bar", "orientation": "h",
                          "x": [22.0, -3.0], "y": ["INVEX", "BBVA"]}],
                "layout": {"title": "Variacion %..."},
            },
            table_data={
                "columns": ["Banco", "Ene 2024", "Ene 2025", "Variacion (%)"],
                "rows": [["INVEX", 100.0, 122.0, 22.0], ["BBVA", 500.0, 485.0, -3.0]],
            },
            ...
        )
        context = AnalyticsExtractor.extract(chart_data)
        assert "INVEX" in context
        assert "122" in context or "122.0" in context
        assert "Variacion" in context or "variacion" in context

    def test_non_delta_chart_no_table_injection(self):
        """Line charts without table_data should not break."""
        chart_data = BankChartData(
            plotly_config={
                "data": [{"type": "scatter", "x": [...], "y": [...]}],
                "layout": {},
            },
            table_data=None,
            ...
        )
        context = AnalyticsExtractor.extract(chart_data)
        assert context  # still works without table_data
```

### Implementacion 2.1

**Archivo**: `apps/backend/src/services/analytics_extractor.py`

Agregar metodo `_format_table_context()`:

```python
@staticmethod
def _format_table_context(table_data: dict) -> str:
    """Format table_data as markdown table for LLM context."""
    if not table_data or "columns" not in table_data or "rows" not in table_data:
        return ""
    cols = table_data["columns"]
    rows = table_data["rows"]
    header = " | ".join(str(c) for c in cols)
    sep = " | ".join("---" for _ in cols)
    body = "\n".join(
        " | ".join(str(v) for v in row) for row in rows
    )
    return f"\n{header}\n{sep}\n{body}\n"
```

Modificar `extract()` para incluir table_data si existe:

```python
@classmethod
def extract(cls, chart_data: BankChartData) -> str:
    series_context = cls._extract_series(chart_data.plotly_config)
    table_context = ""
    if chart_data.table_data:
        table_context = cls._format_table_context(chart_data.table_data)
    return series_context + table_context
```

---

## Phase 3: LLM context builder agrega instruccion delta (backend)

### Test Rojo 3.1: `test_delta_context_instruction`

```python
# apps/backend/tests/unit/test_llm_context_builder_delta.py

class TestDeltaContextInstruction:
    """LLM context must include delta-specific instruction."""

    def test_delta_chart_has_comparison_instruction(self):
        context = build_llm_context(
            bank_chart_data=BankChartData(
                plotly_config={"data": [{"type": "bar", "orientation": "h", ...}]},
                table_data={"columns": [...], "rows": [...]},
                response_text="Comparacion de CARTERA_TOTAL...",
                ...
            )
        )
        # Must tell LLM this is a comparison and data is complete
        assert "comparacion" in context.lower() or "variacion" in context.lower()
        assert "tabla" in context.lower() or "datos" in context.lower()

    def test_non_delta_no_comparison_instruction(self):
        context = build_llm_context(
            bank_chart_data=BankChartData(
                plotly_config={"data": [{"type": "scatter", ...}]},
                table_data=None,
                ...
            )
        )
        assert "comparacion" not in context.lower()
```

### Implementacion 3.1

**Archivo**: `apps/backend/src/services/llm_context_builder.py`

Agregar contexto condicional para delta charts:

```python
DELTA_CONTEXT = (
    "La grafica muestra una COMPARACION de variacion porcentual entre dos periodos. "
    "Los datos en la tabla a continuacion son los valores exactos — usalos para responder. "
    "NO digas que no tienes datos. Los datos YA estan calculados y son correctos."
)
```

En `build_from_raw()`, detectar delta chart:

```python
if (chart_data.table_data
    and chart_data.plotly_config.get("data", [{}])[0].get("orientation") == "h"):
    context_parts.append(DELTA_CONTEXT)
```

---

## Archivos a Modificar (resumen)

| # | Fase | Archivo | Cambio |
|---|------|---------|--------|
| 1 | Ph1 | `plugins/.../use_cases/evolution.py` | `_build_response_text()` en DeltaResult |
| 2 | Ph2 | `apps/backend/src/services/analytics_extractor.py` | `_format_table_context()` + inyeccion |
| 3 | Ph3 | `apps/backend/src/services/llm_context_builder.py` | `DELTA_CONTEXT` instruccion condicional |

## Tests a Crear

| # | Fase | Archivo test | Checks |
|---|------|-------------|--------|
| 1 | Ph1 | `plugins/.../tests/unit/test_delta_response_text.py` | response_text presente, con metrica, periodos, bancos |
| 2 | Ph2 | `apps/backend/tests/unit/test_analytics_extractor_delta.py` | table_data en contexto, no rompe line charts |
| 3 | Ph3 | `apps/backend/tests/unit/test_llm_context_builder_delta.py` | instruccion delta presente, ausente en non-delta |

## Criterio de Exito

1. **Unit tests**: Los 3 archivos de tests pasan
2. **E2E**: Re-ejecutar `test_variacion_cartera_comercial_bar_chart.py` — texto NO dice "no tengo datos"
3. **Regresion**: Line charts existentes no se rompen (no inyectan tabla donde no hay)
4. **PROD**: Misma query produce chart + texto coherente
