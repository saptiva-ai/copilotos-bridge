# Plan — IMOR Variation Bar Chart

## Status: Draft

## Resumen

Hacer que queries de variacion de IMOR multi-banco entre dos periodos produzcan bar chart horizontal (como cartera comercial), sin romper queries IMOR existentes (single-bank time series, rankings, comparativos).

## Fase 1 — Exclusion condicional en matches() (evolucion_banco_handler.py)

### 1a. Modificar logica de _METRIC_EXCLUSIONS

Actualmente `matches()` rechaza incondicionalmente si el query contiene "imor":

```python
if any(kw in query_lower for kw in self._METRIC_EXCLUSIONS):
    return False
```

Cambiar a exclusion condicional: si el query tiene un patron de comparacion de periodos, permitir que pase:

```python
if any(kw in query_lower for kw in self._METRIC_EXCLUSIONS):
    # Allow ratio metrics through when query has period comparison
    if self._parse_period_comparison(user_query) is None:
        return False
```

**Logica**: Si `_parse_period_comparison()` retorna fechas (ej: "periodo inicial ene 2024 ... actual ene 2025"), el usuario quiere una comparacion delta entre periodos — el unico handler que soporta eso es EvolucionBancoHandler via `_handle_period_delta()`.

### 1b. Agregar IMOR a _METRIC_MAP

```python
_METRIC_MAP = {
    ...existing...,
    # IMOR (ratio metric, allowed via conditional exclusion)
    "imor": "imor",
    "morosidad": "imor",
    "indice de morosidad": "imor",
}
```

### 1c. Verificar no-regresion

Queries que NO deben cambiar:
- "IMOR de INVEX" → no period comparison → excluded → MetricasFinancierasHandler
- "Ranking de IMOR" → no period comparison → excluded → RankingHandler
- "IMOR INVEX vs Sistema" → no period comparison → excluded → ComparativeHandler
- "¿Que es el IMOR?" → no period comparison → excluded → KnowledgeHandler

Queries que SI deben cambiar:
- "Compara el IMOR ... periodo inicial ene 2024 ... periodo actual ene 2025" → period comparison found → allowed → bar chart delta

## Fase 2 — Tests (TDD RED)

### 2a. Tests unitarios nuevos en test_evolucion_handler.py

- `TestMatchesImor`: verificar que matches() rechaza IMOR sin periodo, acepta IMOR con periodo
- `TestDetectMetricImor`: verificar que _detect_metric() resuelve "imor" → "imor"
- `TestHandlePeriodDeltaImor`: verificar que handle() rutea IMOR multi-banco + periodo → execute_delta()

### 2b. Verificar tests existentes

Los 80 tests actuales deben seguir pasando (no regresion).

## Fase 3 — Validacion E2E

```bash
python3.11 tests/e2e/charts/test_variacion_imor_bar_chart.py
```

Target: >= 11/15 validators pasando.

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `handlers/evolucion_banco_handler.py` | Exclusion condicional + _METRIC_MAP |
| `tests/unit/test_evolucion_handler.py` | Tests para IMOR routing |

## Riesgos

1. **Regresion single-bank IMOR**: Mitigado por la condicion `_parse_period_comparison() is None` — solo queries con periodo pasan.
2. **Normalizacion**: `MetricNormalizer` ya maneja IMOR (×100). Sin cambios necesarios.
3. **Colision con otros handlers**: `MetricasFinancierasHandler` tiene prioridad mas baja en el router y es single-bank only. No hay conflicto.
