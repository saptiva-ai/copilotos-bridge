# Plan de Corrección: Discrepancia TASA PROMEDIO MN/ME

## Decisión: Adoptar el método de Tableau

**Fuente de verdad**: Tableau. Nuestro sistema debe producir los mismos valores.

**Target inmediato**: Coincidir con los valores de las capturas de pantalla. Si post-fix no se logra coincidencia exacta con algún valor, se documenta como hipótesis plausible (data refresh diferente en capturas vs CSV del repo).

**Razón**: El tablero Tableau es la referencia oficial de Invex. Aunque el método estadístico de nuestro backfill es más correcto (excluir del denominador registros sin tasa), la prioridad es **coincidir con Tableau** para que el usuario no vea discrepancias.

**Alternativa descartada**: Mantener nuestro método y documentar la diferencia → rechazada porque los usuarios no leerán la documentación y seguirán reportando el bug.

## Fase 1: Fix en Backfill Script

### Archivo: `scripts/data/backfill_tasas.py`

**Cambio en `read_corporate_loan()` (líneas 160-190):**

**Antes:**
```python
# Filter valid rows
valid = (
    df["date"].notna()
    & df["Total Portfolio"].notna()
    & (df["Total Portfolio"] > 0)
    & df["Average Rate"].notna()
    & (df["Average Rate"] > 0)  # ← EXCLUYE filas con tasa=0
    & df["currency"].notna()
    & df["banco"].notna()
)
df = df[valid].copy()

# Weighted average
df["weighted_rate"] = df["Average Rate"] * df["Total Portfolio"]
grouped = df.groupby(["banco", "periodo", "currency"]).agg(
    sum_wr=("weighted_rate", "sum"),
    sum_port=("Total Portfolio", "sum"),
)
grouped["tasa"] = grouped["sum_wr"] / grouped["sum_port"] / 100.0
```

**Después (método Tableau):**
```python
# Filter valid rows (keep rate=0 rows for denominator)
valid = (
    df["date"].notna()
    & df["Total Portfolio"].notna()
    & (df["Total Portfolio"] > 0)  # portfolio must be positive
    & df["Average Rate"].notna()   # rate must be non-null
    # NOTE: Average Rate = 0 rows are KEPT (Tableau compatibility)
    & df["currency"].notna()
    & df["banco"].notna()
)
df = df[valid].copy()

# Weighted average (Tableau method):
# - Numerator: only rows with rate > 0
# - Denominator: ALL rows with portfolio > 0
df["weighted_rate"] = df["Average Rate"].where(df["Average Rate"] > 0, 0) * df["Total Portfolio"]

grouped = df.groupby(["banco", "periodo", "currency"]).agg(
    sum_wr=("weighted_rate", "sum"),        # SUM(rate*portfolio) for rate>0
    sum_port=("Total Portfolio", "sum"),     # SUM(portfolio) for ALL rows
)
grouped["tasa"] = grouped["sum_wr"] / grouped["sum_port"] / 100.0
```

**Efecto**: El denominador ahora incluye portfolio de filas con tasa=0, igualando el comportamiento de Tableau.

## Fase 2: Fix NULL→0 en Serie Temporal — COMPLETADA ✅

### Diagnóstico
**El bug estaba en el dato de origen, no en el pipeline**.

Cadena del bug:
1. `backfill_tasas.py` computaba `SUM(0*port)/SUM(port) = 0.0` cuando ALL rates=0
2. DB almacenaba `0.0` (float real, no NULL)
3. `evolution.py:1313` filtra con `metric_col.isnot(None)` → `0.0` pasa
4. `visualization_service:251` pasa `0.0` a Plotly como data point → línea cae a 0%

### Fix aplicado
En `backfill_tasas.py`: cuando `sum_wr == 0` (todas las tasas son 0), producir `NaN` → `None` en el resultado. Tableau semántica: `SUM(NULL) = NULL`.

### Pipeline verificado (NO requiere cambios)
- `_build_timeline_chart()` preserva `None` correctamente (test confirma `[100, None, 300]`)
- `evolution.py` filtra `IS NOT NULL` → NULLs crean gaps naturales en Plotly
- `_build_comparison_chart()` convierte `None→0` para barras (aceptable: barra en 0 vs ausente)

### Puntos de NULL→0 en otros contextos (bugs separados, fuera de scope)
- `chart_formatter.py:1092` — `.fillna(0)` en stacked bar pivot
- `region_service.py:230-235,261` — `COALESCE(...,0)` + `.fillna(0)`
- `analytics_service.py:2343-2348` — `COALESCE(...,0)` en SQL regional

Estos NO afectan tasa MN/ME (son para cartera regional/IFRS).

## Fase 3: Tests de Regresión

### Test 1: Snapshot de valores Enero 2025
```python
# tests/unit/test_backfill_tasas_tableau_parity.py

EXPECTED_JAN_2025 = {
    # (banco, currency): expected_rate_as_ratio
    ("BANCREA", "mn"): 0.135266,
    ("BANCREA", "me"): 0.029481,
    ("VE POR MAS", "mn"): 0.134341,
    ("BANCO BASE", "mn"): 0.131707,
    ("BANCO BASE", "me"): 0.074674,
    ("MONEX", "mn"): 0.126951,
    ("MONEX", "me"): 0.071170,
    ("INVEX", "me"): 0.090477,
    ("SABADELL", "mn"): 0.130253,
    ("SABADELL", "me"): 0.073642,
}
```

### Test 2: Propiedad de que tasa=0 afecta denominador
```python
def test_zero_rate_rows_affect_denominator():
    """Filas con tasa=0 deben inflar el denominador (método Tableau)."""
    # Crear dataframe con 1 fila tasa=10%, portfolio=100
    # y 1 fila tasa=0, portfolio=100
    # Resultado esperado: 10*100 / (100+100) / 100 = 0.05 (5%)
    # NO: 10*100 / 100 / 100 = 0.10 (10%)
```

### Test 3: Serie temporal sin NULL→0
```python
def test_missing_months_are_null_not_zero():
    """Meses sin dato deben ser NULL, no 0."""
    # Verificar que la serie temporal para un banco con meses faltantes
    # devuelve None/null para esos meses
```

## Fase 4: Re-ejecutar Backfill en PROD

```bash
# Via SSH tunnel
ssh -L 18000:localhost:8000 ${PROD_USER}@${PROD_HOST} -N -f

# Dry run primero
DATABASE_URL='...' python3.11 scripts/data/backfill_tasas.py --dry-run

# Ejecutar
DATABASE_URL='...' python3.11 scripts/data/backfill_tasas.py

# Verificar
psql $DATABASE_URL -c "
  SELECT banco_norm, tasa_mn*100, tasa_me*100
  FROM bank_fact_kpis_mensual
  WHERE periodo_id = 202501
    AND banco_norm IN ('BANCREA','INVEX','BANCO BASE','MONEX','SABADELL','VE POR MAS')
  ORDER BY banco_norm;
"
```

## Fase 5: Refrescar MVs y Verificar E2E

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_comparativa_bancos;
REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_resumen_sistema;
```

Actualizar valores de referencia en tests E2E:
- `tests/e2e/charts/test_tasa_mn_dual_prompts.py`: TABLEAU_BANKS_MN
- `tests/e2e/charts/test_tasa_me_dual_prompts.py`: TABLEAU_BANKS_ME

## Estimación de Impacto

| Métrica | Antes | Después |
|---------|-------|---------|
| Bancos afectados MN | 5 de 14 | 0 |
| Bancos afectados ME | 5 de 14 | 0 |
| Max diff MN | 0.18pp | 0pp |
| Max diff ME | 4.85pp | 0pp |
| BANCREA ME | 7.80% (nuestro) vs 2.95% (Tableau) | 2.95% = Tableau |
