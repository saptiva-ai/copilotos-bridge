# Validate: ETL Refresh Diciembre 2025

## Resultado Final

| Tabla | Antes | Despues | Delta |
|-------|-------|---------|-------|
| `bank_fact_kpis_mensual` | 11,882 rows / max 2025-11 | 11,913 rows / max **2025-12** | +31 rows |
| `bank_src_banca_multiple` | max 202510 | max **202512** | +147,684 rows |
| `bank_src_reporte_r04a` | max 202510 | max **202512** | +184,871 rows |

## INVEX Dic 2025

| Metrica | Valor |
|---------|-------|
| cartera_total | $51,912 MDP |
| icap_total | 16.38% |
| imor | 2.65% |
| tda_cartera_total | 2.43% |
| tasa_mn | 0.00% (sin datos CorporateLoan para INVEX) |

## Dic 2025 Bancos Completos (post-IMOR Comercial fix)

| Banco | Cartera (MDP) | ICAP | IMOR | IMOR Com | CVC | Tasa MN |
|-------|--------------|------|------|----------|-----|---------|
| BANORTE | 1,232 | 20.06% | 1.41% | 1.62% | 1.58% | 13.92% |
| BBVA | 2,089 | 20.15% | 1.63% | 1.06% | 0.90% | 14.93% |
| CITIBANAMEX | 456 | 20.82% | 2.16% | 1.74% | 1.70% | 14.13% |
| HSBC | 479 | 19.38% | 3.05% | 3.22% | 3.17% | 17.16% |
| INVEX | 52 | 16.38% | 2.65% | 2.29% | 2.29% | 0.00% |
| SANTANDER | 985 | 18.49% | 2.03% | 1.59% | 1.35% | 15.51% |

## Cobertura Dic 2025

- 38 bancos con `imor_comercial` (post-fix del loader)
- 6 bancos con datos completos (CNBV + IMOR Comercial)
- 32 bancos con solo `imor_comercial` + `cvc_cc`

## Nov 2025 Coverage (post-refresh)

| Metrica | Bancos con dato |
|---------|-----------------|
| cartera_total | 45/58 |
| icap_total | 49/58 |
| imor | 26/58 |
| tda | 33/58 |
| tasa_mn | 38/58 |
| imor_comercial | 39/58 |

## Bugs Corregidos

1. **ICAP/TDA INVEX** (`transforms.py`): Institution code mismatch `040059` vs `040131`. ICAP_Bancos.xlsx y TDA.xlsx usan codigo viejo `040059`, pero `enrich_with_instituciones()` remapea INVEX a `040131`. Fix: remap en `merge_icap()` y `merge_tda()`.

2. **Polars is_in type error** (`loaders_banca_multiple.py`, `loaders_reportes_reg.py`): Polars inferia `valor` como Float64 pero el codigo intentaba `is_in(["n.d.", ...])` con strings. Fix: check dtype antes de limpiar.

3. **R04A column name mismatch** (`loaders_reportes_reg.py`): `_detect_report_schema()` renombraba `institucion`->`clave_institucion` pero la tabla DB usa `institucion`. Fix: skip schema mapping, hacer `_transform_reporte()` flexible.

4. **Missing unique index** (`bank_fact_kpis_mensual`): UPSERT requiere `UNIQUE INDEX` en `(banco_norm, fecha)`. Fix: `CREATE UNIQUE INDEX uq_kpis_banco_fecha`.

5. **IMOR Comercial loader** (`loaders_imor_comercial.py`): usaba `UPDATE WHERE institucion_id AND periodo_id` pero el ETL Unificado deja esos FKs como NULL. Fix: cambiar a `ON CONFLICT (banco_norm, fecha) DO UPDATE SET`. Resultado: 4,137 updates, 0 errores (antes 3,350 + 755 errores).

## Limitaciones Conocidas

- `market_share_pct` vacio en Nov/Dic 2025: depende de AnalisisGeneral (`040_TO.csv`) que solo llega a 202510
- SISTEMA no tiene fila en Dic 2025: CNBV_Cartera no incluye dato agregado de SISTEMA para ese mes
- `tasa_mn` de INVEX = 0.00%: CorporateLoan no tiene datos de tasas para INVEX

## Archivos Modificados

- `plugins/bank-advisor-private/etl/core/transforms.py` (fix ICAP/TDA INVEX code mapping)
- `plugins/bank-advisor-private/etl/core/loaders/loaders_banca_multiple.py` (fix Polars type)
- `plugins/bank-advisor-private/etl/core/loaders/loaders_reportes_reg.py` (fix column names + Polars type)
- `plugins/bank-advisor-private/etl/core/loaders/loaders_imor_comercial.py` (fix upsert to use ON CONFLICT)
- `docs/data/etl_runbook.md` (add manual refresh guide, troubleshooting)
- `docs/data/source_mapping.md` (add gotchas, IMOR comercial mapping)
- `docs/data/schema.md` (update cobertura temporal, unique index note)
