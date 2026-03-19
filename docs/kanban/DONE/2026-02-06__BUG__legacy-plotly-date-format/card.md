# BUG: Legacy PlotlyGenerator produce fechas "Jan 2025" y doble-escala ICAP

## Status: REVIEW

## Descripcion

Queries como "Explícame la evolución del ICAP de Santander de enero a octubre 2025" pasan por el path legacy (`PlotlyGenerator` + `sql_result_transformer`) en vez del path nuevo (`ChartFormatter`). Esto produce:

1. Fechas como "Jan 2025" en vez de "2025-01-01" (ISO)
2. Valores ICAP de ~1779 en vez de ~17.79% (x100 duplicado)
3. `visualization: None` en vez de `line_chart`

## Deteccion

Test: `tests/e2e/regression/test_bug_regression_suite.py` — MONTH-001 falla:
```
Trace 'SANTANDER' x values don't look like dates: Jan 2025
```

## Root Cause

`query_orchestrator.py:445`:
```python
if data.get("type") == "data" and "values" in data:
    plotly_config = PlotlyGenerator.generate(...)  # Legacy path
```

Cuando `get_filtered_data()` devuelve data con key `"values"`, el `PlotlyGenerator` legacy sobreescribe el `plotly_config` ya generado por `ChartFormatter`. El legacy path usa `strftime("%b %Y")` y aplica `apply_ratio_conversion` que multiplica x100 otra vez.

## Fix Aplicado (2026-02-06)

Commit: `11b44e45`

| Archivo | Cambio |
|---------|--------|
| `sql_result_transformer.py` | `_format_month_label()` → ISO dates (YYYY-MM-DD) |
| `plotly_generator.py` | `_convert_hu3_to_legacy()` → ISO dates |
| `main.py` | `NO_SCALE_METRICS` guard en `apply_ratio_conversion` |
| `query_orchestrator.py` | `"plotly_config" not in data` previene overwrite |

## Validacion

- 27/27 bug regression suite pass (antes 26/27)
- MONTH-001: 3/3 pass
- DECIMAL-001: 3/3 pass (sin regresiones)

## Archivos Involucrados

- `plugins/bank-advisor-private/src/bankadvisor/services/query_orchestrator.py:445` (routing)
- `plugins/bank-advisor-private/src/bankadvisor/services/plotly_generator.py` (legacy formatter)
- `plugins/bank-advisor-private/src/bankadvisor/services/sql_result_transformer.py:184` (strftime "%b %Y")
- `plugins/bank-advisor-private/src/bankadvisor/services/chart_formatter.py` (new formatter — correct)
- `plugins/bank-advisor-private/src/main.py:1044` (ratio conversion)

## Prioridad

Media — 1 test case falla, afecta queries con "Explícame la evolución de..."
