# Research — IMOR Variation Scatter Instead of Bar

## Status: Complete

## Hallazgos clave

### 1. IMOR es columna valida en MonthlyKPI
- Columna `imor` en `bank_fact_kpis_mensual` (MonthlyKPI model)
- `execute_delta()` valida dinamicamente via `_get_kpi_columns()` (no whitelist)
- `getattr(MonthlyKPI, metric_lower)` resuelve correctamente

### 2. MetricNormalizer ya maneja IMOR
- IMOR almacenado como decimal: 0.02 = 2%
- `DECIMAL_DISPLAY_METRICS = {FinancialMetric.IMOR}` → multiplicador ×100
- `MetricNormalizer.normalize("imor", 0.02)` → 2.0
- Variacion usa % de cambio: (2.5 - 2.0) / 2.0 × 100 = 25%

### 3. `_parse_period_comparison()` en BaseHandler
- 3 patrones regex: labeled ("periodo inicial...actual"), directo ("ene 2024 vs ene 2025"), year-only
- Soporte de acentos via NFD normalization
- Retorna `(date_a, date_b)` como "YYYY-MM-DD" o None

### 4. Bloqueo en matches()
```python
_METRIC_EXCLUSIONS = {"imor", "morosidad", "mora", "icor", "cobertura", "icap", ...}

def matches(self, user_query, entities=None, spec=None):
    query_lower = user_query.lower()
    if any(kw in query_lower for kw in self._METRIC_EXCLUSIONS):
        return False  # <-- BLOQUEO INCONDICIONAL
    return any(keyword in query_lower for keyword in EVOLUTION_KEYWORDS.keys())
```

### 5. No se necesitan cambios en execute_delta()
- Columna "imor" pasa validacion automaticamente
- Normalizador convierte decimales a porcentajes
- Formula de variacion funciona con cualquier valor numerico

## Conclusion
Solo se necesitan 2 cambios en `evolucion_banco_handler.py`:
1. Hacer la exclusion condicional (permitir si hay period comparison)
2. Agregar "imor" a `_METRIC_MAP`
