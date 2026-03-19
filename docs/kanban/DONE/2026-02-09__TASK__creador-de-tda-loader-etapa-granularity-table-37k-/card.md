---
status: REVIEW
---
# TASK: CREADOR DE TDA loader: Etapa granularity table (37K rows × 78 cols)

**Prioridad:** P1
**Fecha:** 2026-02-09
**Status:** BACKLOG

---

## Resumen

## Problem

`CREADOR DE TDA.xlsx` (23MB) contains the full Etapa 1/2/3/VR breakdown per credit sub-type for 135 institutions × 300 periods (200012-202511). This is the **source data** behind the Tableau "Benchmark" dashboard — it powers all Etapa composition charts, Cartera Vencida ratios, IMORA calculations.

Currently NO table exists in prod for this granularity level. The existing `bank_fact_kpis_mensual.tda_cartera_total` only stores the final TDA percentage (Etapa3/Total), losing all sub-segment detail.

## Research

### File structure
- **Sheet "BD TDA"**: 37,160 data rows × 78 columns
- **Columns**: `ID`, `cve_periodo`, `cve_institucion`, then 75 metric columns:
  - 15 credit sub-types × 4 Etapas (ET1, ET2, ET3, VR) + 15 TOT columns
  - Credit types: Comerciales (Empresarial, Ent. Financieras, Gubernamentales), Consumo (Tarjeta, Personales, Nomina, Automotriz, Bienes Muebles, Arrendamiento, Otros), Vivienda, ABCD
- **Sheet "TDA"**: 37,162 rows — pivot summary (Etapa3 + TOT + TDA ratio). Redundant with TDA.xlsx.

### Tableau business logic extracted
These formulas from `Invex_Tablero_V3.twb` use BD TDA data:
- `Cartera Vencida = Comercial_ET3_SG + Vivienda_ET3`
- `IMORA = (Comercial_ET3_SG + Castigos) / (ET1_SG + ET2_SG + ET3_SG)`
- `CT_Etapa1 = (Comercial_ET1 + Consumo_ET1 + Vivienda_ET1) / Cartera_Total`
- `PE Total = Reservas × (-1) / Cartera_Total`

### Prod comparison
- `bank_fact_kpis_mensual` has `cartera_total_etapa_1/2/3` but only for AGGREGATE total (not per credit type)
- No per-segment Etapa breakdown exists anywhere in prod

## Plan

### Option A: Wide table (mirror source structure)
```sql
CREATE TABLE bank_src_tda_etapas (
    cve_periodo INTEGER NOT NULL,
    cve_institucion VARCHAR(10) NOT NULL,
    -- 75 numeric columns matching BD TDA headers
    -- e.g. comerciales_et1, empresarial_et1, ...
    fecha_carga TIMESTAMP DEFAULT NOW()
);
```
Pro: simple 1:1 mapping. Con: 75 columns is wide.

### Option B: Long/unpivoted table (like benchmark)
```sql
CREATE TABLE bank_src_tda_etapas (
    cve_institucion VARCHAR(10) NOT NULL,
    cve_periodo INTEGER NOT NULL,
    tipo_credito VARCHAR(50) NOT NULL,    -- 'Comerciales', 'Consumo', etc.
    subtipo VARCHAR(80) NOT NULL,          -- 'Empresarial', 'Tarjeta', etc.
    etapa VARCHAR(5) NOT NULL,             -- 'ET1', 'ET2', 'ET3', 'VR', 'TOT'
    importe NUMERIC(20,6),
    fecha_carga TIMESTAMP DEFAULT NOW()
);
```
Pro: normalized, easy to query. Con: more rows (~560K), unpivot logic needed.

**Recommendation: Option B** — normalized long format. Matches the benchmark loader pattern already established. Enables flexible SQL queries like `WHERE tipo_credito = 'Comerciales' AND etapa = 'ET3'`.

### Implementation steps
1. Migration `055_create_tda_etapas.sql`
2. Loader `etl/core/loaders/loaders_tda_etapas.py` — read BD TDA sheet, unpivot 75 cols to long format
3. Add to `data_promotion.py` specs
4. Wire into `etl_unified.py` load_all_sources
5. Dry-run validation

## Testing

```bash
# Dry-run
cd plugins/bank-advisor-private
.venv/bin/python3 -c "
from etl.core.loaders.loaders_tda_etapas import load_tda_etapas
from pathlib import Path
result = load_tda_etapas(Path('data/raw/incoming/...'), engine=None, dry_run=True)
print(result)
"
# Expect: ~560K rows (37,160 × 15 sub-types)
```

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
