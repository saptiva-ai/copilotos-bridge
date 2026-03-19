---
id: "BUG-2026-03-03__quebrantos-comerciales-invex-zero"
title: "INVEX quebrantos_comerciales siempre $0 — institution code mismatch + date format bug"
status: "DOING"
severity: "Alta — datos financieros incorrectos para INVEX y potencialmente para otros bancos"
detected: "2026-03-03"
resolved: "Code fix aplicado, pendiente --upsert en PROD"
artifacts:
  card: card.md
---

# Bug: INVEX quebrantos_comerciales siempre $0

## Resumen

INVEX muestra `quebrantos_comerciales = 0` para TODOS los periodos en `bank_fact_kpis_mensual`.
El valor correcto para T1 2024 es **115.857 MDP (~116 MDP)**. Esto también afecta el TOTAL/PROMEDIO
del sistema, que muestra 1,267 MDP en vez de 1,383 MDP (diferencia = 116 = INVEX faltante).

## Root Cause

**Dos bugs independientes en el pipeline ETL de CASTIGOS.xlsx:**

### Bug A: Institution Code Mismatch (INVEX-específico)

En `transforms.py:174-182`, un fix previo (2025-12-05) reescribe el código de institución de INVEX
para compatibilidad con el JOIN de ICAP:

```python
# enrich_with_instituciones() — transforms.py:177-182
df = df.with_columns([
    pl.when(pl.col("banco").str.to_uppercase().str.contains("INVEX"))
    .then(pl.lit("040131"))       # ← Reescrito para ICAP
    .otherwise(pl.col("institucion"))
    .alias("institucion")
])
```

Esto se ejecuta ANTES de `enrich_with_castigos()`, causando:

```
cartera INVEX.institucion = "040131"  (reescrito)
castigos INVEX.institucion = "040059" (original CNBV)
→ LEFT JOIN: NO MATCH → NULL → fill_null(0) → quebrantos = 0
```

**Contexto**: `040059` = INVEX en catálogo CNBV. `040131` = Banco Ahorro Famsa (adquirido por INVEX).
El fix original asumió que ICAP usa 040131, pero no consideró que CASTIGOS.xlsx usa 040059.

### Bug B: Date Format Parsing (afecta TODOS los bancos)

`CASTIGOS.xlsx` usa formato `MM/DD/YYYY`, pero `load_castigos()` parsea como `DD/MM/YYYY`:

```python
# loaders_unified.py:386-391
df = df.with_columns([
    pl.coalesce([
        pl.col("fecha").str.to_date("%d/%m/%Y", strict=False),  # ← INCORRECTO
        pl.col("fecha").str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False),
    ]).alias("fecha")
])
```

**Efecto**: `02/01/2024` (Feb 1) → `2024-01-02` (Jan 2). Todos los 2,190 rows parsean a mes=1 (enero).
Los bancos con datos en enero se salvan por coincidencia (`01/01/2024` parsea igual en ambos formatos).

**Evidencia** (columnas AÑO/MES del Excel confirman formato MM/DD):

| AÑO  | MES | FECHA        | lib_castigos_comerc |
|------|-----|-------------|---------------------|
| 2024 | 01  | 01/01/2024  | 0                   |
| 2024 | 02  | 02/01/2024  | 115.857323          |
| 2024 | 10  | 2024-01-10  | 0                   |

MES=02 + FECHA=02/01/2024 → febrero, no día 2 de enero.

## Impacto en Datos

### INVEX (Bug A — datos completamente perdidos)

| Periodo | Valor real (MDP) | Valor en DB | Error |
|---------|-----------------|-------------|-------|
| May 2022 | 120.247 | 0 | -120.247 |
| Feb 2024 | 115.857 | 0 | -115.857 |
| Apr 2025 | 106.259 | 0 | -106.259 |

### TOTAL/PROMEDIO (consecuencia de Bug A)

| Periodo | Valor esperado | Valor actual | Diferencia |
|---------|---------------|-------------|------------|
| T1 2024 | 1,383 MDP | 1,267.62 MDP | -115.857 (= INVEX) |

### Otros bancos (Bug B — datos en mes incorrecto)

Bancos con quebrantos en meses != enero tienen el dato asignado al mes equivocado.
Por coincidencia, la mayoría reportan en enero (dato anual), así que el impacto práctico
es menor para T1 queries. Sin embargo, queries mensuales o de otros trimestres serían incorrectos.

## Correcciones

### Fix 1: Date format — `loaders_unified.py:load_castigos()`

```python
# ANTES (incorrecto):
pl.col("fecha").str.to_date("%d/%m/%Y", strict=False)

# DESPUÉS (correcto):
pl.col("fecha").str.to_date("%m/%d/%Y", strict=False)
```

### Fix 2: Institution code mapping — `transforms.py:enrich_with_castigos()`

Aplicar el mismo mapeo de institución al dataframe de castigos antes del JOIN:

```python
# Mapear códigos de institución para compatibilidad con cartera
# (INVEX: 040059 en CASTIGOS → 040131 en cartera preparada)
castigos_df = castigos_df.with_columns([
    pl.col("institucion").replace({"040059": "040131"}).alias("institucion")
])
```

### Fix 3: Re-run ETL con --upsert

```bash
cd plugins/bank-advisor-private
.venv/bin/python3.11 -m etl.etl_unified --upsert
```

## Validación Post-Fix

```sql
-- INVEX debe tener ~116 MDP en feb 2024
SELECT banco_norm, fecha, quebrantos_comerciales
FROM bank_fact_kpis_mensual
WHERE banco_norm = 'INVEX'
  AND quebrantos_comerciales > 0;

-- TOTAL T1 2024 debe ser ~1,383 MDP
SELECT SUM(quebrantos_comerciales) as total
FROM bank_fact_kpis_mensual
WHERE fecha = '2024-02-01'  -- Feb 2024 (dato anual de INVEX)
  AND quebrantos_comerciales > 0;
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `plugins/bank-advisor-private/etl/core/loaders_unified.py` | Fix date format en `load_castigos()` |
| `plugins/bank-advisor-private/etl/core/transforms.py` | Fix institution code mapping en `enrich_with_castigos()` |

## Relación con Tasks Previos

- `TASK-2026-02-09-1802__loader-quebrantos` (DONE) — cerrado como "redundante", pero el bug de datos persistía
- Fix 2025-12-05 en `enrich_with_instituciones()` — introdujo Bug A al reescribir el código de INVEX

## Lecciones

1. **Los fixes de JOINs tienen efectos cascada**: Reescribir `institucion` para un JOIN (ICAP) rompe otros JOINs downstream (castigos).
2. **Verificar formato de fecha con columnas auxiliares**: AÑO/MES en el Excel confirman el formato correcto; no asumir DD/MM vs MM/DD.
3. **Los datos anuales en meses "raros" son los más vulnerables**: Si INVEX reportara en enero como la mayoría, el Bug B habría enmascarado el Bug A.
