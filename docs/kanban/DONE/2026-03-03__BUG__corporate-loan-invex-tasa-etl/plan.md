# Plan: Fix CorporateLoan INVEX tasa merge + docs update

## Phase 1 — Fix merge_corporate_rates() en transforms.py

**Archivo:** `plugins/bank-advisor-private/etl/core/transforms.py`
**Función:** `merge_corporate_rates()` (línea 590)

Después de `corp_subset = corp_rates_df.select(...)` (línea 608), agregar:

```python
# FIX 2026-03-03: Remap INVEX corporate loan institution code 040059 → 040131
# enrich_with_instituciones() remaps INVEX to 040131 in full_data,
# but CorporateLoan uses the original code 040059. Without this fix,
# INVEX gets contaminated with Banco Ahorro Famsa (040131, revoked 2020) data.
# Filter out Ahorro Famsa entries first to avoid duplication after remap.
corp_subset = corp_subset.filter(pl.col("institucion") != "040131")
corp_subset = corp_subset.with_columns([
    pl.when(pl.col("institucion") == "040059")
    .then(pl.lit("040131"))
    .otherwise(pl.col("institucion"))
    .alias("institucion")
])
```

**Razón:** Consistente con el fix de `merge_icap()` (línea 479) y `merge_tda()` (línea 528),
pero con filtro adicional porque CorporateLoan tiene datos de Ahorro Famsa que ICAP/TDA no tienen.

## Phase 2 — Corregir documentación

### 2a. etl_runbook.md (líneas 450-456)

Reemplazar la sección incorrecta:
```
### tasa_mn / tasa_me = 0 para INVEX
**No es un bug del ETL**. INVEX dejó de reportar tasas...
```

Con la sección corregida:
```
### tasa_mn / tasa_me = 0 para INVEX (CORREGIDO 2026-03-03)
**Era un bug del merge en el ETL.** El CSV CorporateLoan_CNBVDB.csv tiene 13,543
registros válidos de INVEX (Jun 2016 – Dic 2025, MN ~13%, ME ~8%).
El bug era que `merge_corporate_rates()` joineaba con el código de institución
remapeado (040131 = Ahorro Famsa), produciendo valores incorrectos.
Fix: remap 040059→040131 + filtro Ahorro Famsa en merge_corporate_rates().
```

### 2b. source_mapping.md — Gotchas

Agregar nuevo gotcha sobre la colisión de código 040059/040131 en CorporateLoan.

## Phase 3 — Validación

### 3a. Script diagnóstico (sin re-ejecutar ETL completo)

```python
# Verificar que merge_corporate_rates produce valores correctos para INVEX
cnbv_with_tasa = merge_corporate_rates(cnbv_prepared, corp_rates)
invex = cnbv_with_tasa.filter(pl.col("banco_norm") == "INVEX").collect()
assert invex["tasa_mn"].drop_nulls().len() > 100  # should have ~108 months
assert invex["tasa_mn"].mean() < 0.25  # ~13%, not ~39% (Ahorro Famsa)
```

### 3b. Re-ejecutar ETL (opcional, verificar que no se pierde el data patch)

Si se re-ejecuta el ETL (`etl_unified --upsert`), los valores de tasa deben quedar
correctos para INVEX directamente del pipeline, sin necesidad de SQL manual.
