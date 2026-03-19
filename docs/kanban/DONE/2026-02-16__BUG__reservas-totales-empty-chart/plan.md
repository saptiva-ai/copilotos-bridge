# Plan — Reservas Totales Empty Chart

## Status: Draft

## Resumen

Agregar "reservas" al routing del `EvolucionBancoHandler` y crear un path de **promedio multi-banco** que computa `AVG(metric)` entre dos fechas, en vez de solo delta (variación %).

## Fase 1 — Routing: handler intercepta "reservas" (evolucion_banco_handler.py)

### 1a. Agregar keywords de activación

En `EVOLUTION_KEYWORDS` agregar "reservas" como keyword que activa el handler:

```python
EVOLUTION_KEYWORDS = {
    ...existing...
    # Reserves
    "reservas": None,
    "provisiones": None,
}
```

**Riesgo de regresión**: "reservas" no colisiona con ningún otro handler (verificado: no está en FINANCIAL_KEYWORDS, ni en otros handlers). El `peer_average_handler` usa "promedio" pero con "contra/vs" que lo diferencia.

### 1b. Agregar métricas a _METRIC_MAP

```python
_METRIC_MAP = {
    ...existing...
    # Reservas
    "reservas totales": "reservas_etapa_todas",
    "reservas": "reservas_etapa_todas",
    "provisiones": "reservas_etapa_todas",
    "reservas preventivas": "reservas_etapa_todas",
    "estimaciones preventivas": "reservas_etapa_todas",
}
```

Esto hace que `_detect_metric()` resuelva "reservas totales" → `reservas_etapa_todas` (longest match first, ya implementado).

### 1c. Verificar que _METRIC_EXCLUSIONS no bloquea

`_METRIC_EXCLUSIONS` = `{imor, morosidad, mora, icor, cobertura, icap, ...}`. "Reservas" NO está en la exclusion list → OK.

## Fase 2 — Average path: nuevo método en EvolutionUseCase

### Problema

El prompt dice "periodo inicial enero 2023 ... periodo actual enero 2024" → `_parse_period_comparison()` matchea → rutea a `execute_delta()` que calcula **variación %** entre 2 puntos.

Pero el usuario pidió **"promedio para los meses seleccionados"** → necesita `AVG(metric)` de TODOS los meses en el rango.

### 2a. Detectar keyword "promedio" en _handle_multi_bank()

En `_handle_multi_bank()`, antes de llamar `_handle_period_delta()`:

```python
async def _handle_multi_bank(self, session, user_query, banks, start_date, end_date, metric):
    periods = self._parse_period_comparison(user_query)

    # NEW: "promedio" + period range → average path
    query_lower = user_query.lower()
    wants_average = "promedio" in query_lower or "average" in query_lower

    if periods and wants_average:
        return await self._handle_period_average(
            session, banks, metric, periods[0], periods[1],
            user_query=user_query,
        )

    if periods:
        return await self._handle_period_delta(...)  # existing

    # ...rest unchanged
```

### 2b. Nuevo método _handle_period_average()

```python
async def _handle_period_average(
    self, session, banks, metric, date_a, date_b, user_query="",
) -> dict[str, Any]:
    """Compute AVG(metric) per bank between two dates. Returns horizontal bar chart."""
    use_case = get_evolution_use_case()
    result = await use_case.execute_average(session, banks, metric, date_a, date_b)
    highlight = self._detect_highlight_bank(user_query, banks)
    return result.to_response_dict(highlight_bank=highlight)
```

### 2c. Nuevo método execute_average() en EvolutionUseCase

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/evolution.py`

```python
async def execute_average(
    self, session, banks: list[str], metric: str, date_a: str, date_b: str,
) -> AverageResult:
    """
    Query ALL months between date_a and date_b, compute AVG(metric) per bank.
    Returns AverageResult with horizontal bar chart data.
    """
    # SQL: SELECT banco_norm, AVG(abs({metric})) as avg_val
    #      FROM bank_fact_kpis_mensual
    #      WHERE fecha BETWEEN date_a AND date_b
    #        AND banco_norm IN (banks)
    #      GROUP BY banco_norm
```

### 2d. AverageResult dataclass

Similar a `DeltaResult` pero con un solo valor por banco (promedio), no dos (inicio/fin).

```python
@dataclass
class AverageResult:
    banks: list[str]
    values: list[float]        # AVG(metric) per bank
    metric: str
    date_a: str
    date_b: str

    def to_response_dict(self, highlight_bank=None) -> dict:
        # Horizontal bar chart: y=banks, x=values
        # highlight_bank gets red (#E45756), rest grey (#999999)
        # table_data: [banco, avg_value] per row
```

## Fase 3 — Test y validación

```bash
# Unit tests para _detect_metric() con reservas
python3.11 -m pytest plugins/bank-advisor-private/tests/unit/test_evolucion_handler.py -k reservas

# E2E test
python3.11 tests/e2e/charts/test_reservas_totales_bar_chart.py
```

Target: ≥11/13 validadores pasando.

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `handlers/evolucion_banco_handler.py` | Keywords + _METRIC_MAP + _handle_period_average() |
| `application/use_cases/evolution.py` | execute_average() + AverageResult |
| `tests/unit/test_evolucion_handler.py` | Tests para reservas routing + average |

## Riesgos

1. **Colisión "promedio" con peer-average**: El `peer_average` handler matchea "promedio de INVEX contra bancos" pero requiere "contra/vs" pattern. El nuevo path solo se activa cuando `_parse_period_comparison()` ya matcheó + "promedio" está presente. Bajo riesgo.
2. **Valores negativos de reservas**: `reservas_etapa_todas` se almacena negativo. `execute_average()` debe usar `abs()` para mostrar valores positivos en chart.
3. **Regresión cartera**: Agregar keywords no afecta _METRIC_MAP existing entries (longest match first).
