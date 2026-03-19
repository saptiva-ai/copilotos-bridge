# Research: ETL CorporateLoan INVEX tasa_mn/tasa_me

## 1. El loader funciona correctamente

`load_corporate_loan()` en `loaders_unified.py:567-681` produce datos INVEX correctos:
- 113 filas con `institucion = "040059"`, tasa_mn ~0.13, tasa_me ~0.08
- 48 filas con `institucion = "040131"` (Banco Ahorro Famsa, revocado 2020)
- Filtro `average_rate > 0 AND < 100` + `MIN_RATE_SAMPLES = 5` funcionan bien

## 2. El bug está en el merge, no en el load

### Bug Chain (3 pasos)

**Paso 1: `enrich_with_instituciones()` remap (transforms.py:177-182)**
```python
pl.when(pl.col("banco").str.to_uppercase().str.contains("INVEX"))
.then(pl.lit("040131"))  # ← INVEX queda con código de Ahorro Famsa
.otherwise(pl.col("institucion"))
```
INVEX cambia de `040059` (correcto) a `040131` (código de Banco Ahorro Famsa).

**Paso 2: `merge_corporate_rates()` join contamination (transforms.py:611-615)**
```python
merged = full_data.join(corp_subset, on=["fecha_month", "institucion"], how="left")
```
- cnbv_prepared INVEX: `institucion = "040131"`
- corporate_rates: tiene 48 filas de Ahorro Famsa con `institucion = "040131"`
- **Match INCORRECTO**: INVEX recibe tasas de Ahorro Famsa (~39% MN) en vez de las suyas (~13% MN)
- Para meses post-2020 (Famsa revocado): INVEX recibe NULL → se convierte en NaN

**Paso 3: `merge_corporate_rates_final()` coalesce preference (transforms.py:696-709)**
```python
pl.coalesce([pl.col("tasa_mn"), pl.col("tasa_mn_corp")]).alias("tasa_mn_new")
```
- Coalesce prefiere el valor existente (contaminado con Famsa o NaN)
- En Polars, `NaN ≠ NULL` — coalesce NO cae al fallback cuando el valor es NaN
- Resultado: INVEX siempre queda con datos incorrectos o NaN

### Evidencia diagnóstica

| Paso | INVEX tasa_mn non-null | Valores | ¿Correcto? |
|------|----------------------|---------|------------|
| load_corporate_loan | 113/113 | ~0.13 | ✓ |
| merge_corporate_rates | 41/108 | ~0.39 | ✗ (Ahorro Famsa) |
| aggregate_monthly_kpis | 108/108 | NaN + Famsa | ✗ |
| merge_corporate_rates_final | 108/108 | NaN | ✗ |

## 3. Comparación con ICAP/TDA (que SÍ fueron arreglados)

`merge_icap()` y `merge_tda()` (transforms.py:479, 528) tienen el fix de remap:
```python
# FIX 2026-03-02: Remap INVEX ICAP institution code 040059 → 040131
icap_df = icap_df.with_columns([
    pl.when(pl.col("institucion") == "040059")
    .then(pl.lit("040131"))
    .otherwise(pl.col("institucion"))
    .alias("institucion")
])
```
**Pero `merge_corporate_rates()` NO tiene este fix.** Se quedó sin corregir en el BUG-2026-03-02.

Diferencia clave: ICAP_Bancos.xlsx y TDA.xlsx NO tienen entradas para Ahorro Famsa (040131),
así que el remap es seguro. CorporateLoan SÍ tiene 48 filas de Ahorro Famsa, por lo que
solo remap NO es suficiente — también hay que filtrar los datos de Famsa.

## 4. Contradicción en el codebase

- `bank_mappings.py:43`: `"INVEX": "040059"` ← correcto, fuente de verdad
- `bank_mappings.py:87`: `"BANCO AHORRO FAMSA": "040131"` ← 040131 es Famsa, no INVEX
- `bank_mappings.py:218-219`: Comentario dice "040059->040131 was wrong"
- `enrich_with_instituciones()`: Sigue haciendo 040059→040131 ← contradicción

## 5. Fix approach

Agregar remap + filtro de Ahorro Famsa en `merge_corporate_rates()`:
1. Filtrar `institucion != "040131"` (eliminar Ahorro Famsa del corp_rates)
2. Remap `040059 → 040131` (INVEX matchea con cnbv_prepared)

Consistente con patrón de ICAP/TDA pero con filtro adicional por la colisión de códigos.

## 6. Documentación incorrecta a corregir

`docs/data/etl_runbook.md:450-456` dice:
> "INVEX dejó de reportar tasas después de diciembre 2016"

**FALSO.** El CSV tiene 13,543 registros válidos de INVEX hasta Dic 2025.
MN: 10,986 registros, ME: 2,189 registros.
