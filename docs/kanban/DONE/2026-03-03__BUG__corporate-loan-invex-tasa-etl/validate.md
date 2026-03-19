# Validation: CorporateLoan INVEX tasa ETL fix

## 1. Diagnóstico pre-fix

| Métrica | Valor | Esperado | Status |
|---------|-------|----------|--------|
| INVEX tasa_mn source (loader) | 113 rows, ~0.13 | ✓ loader OK | ✓ |
| INVEX tasa_mn after merge_corporate_rates | 41/108, ~0.39 | >100, ~0.13 | ✗ (Ahorro Famsa) |
| INVEX tasa_mn after final merge | NaN | ~0.13 | ✗ |

## 2. Diagnóstico post-fix

| Métrica | Valor | Esperado | Status |
|---------|-------|----------|--------|
| INVEX tasa_mn after merge_corporate_rates | 106/108, mean 0.161 | >100, ~0.13-0.20 | ✓ |
| INVEX tasa_mn range | 0.1248 – 0.2007 | 0.08 – 0.20 | ✓ |
| INVEX tasa_me range | 0.0528 – 0.1017 | 0.05 – 0.10 | ✓ |
| INVEX last 3 months (Dic/Nov/Oct 2025) | 0.175, 0.176, 0.180 | ~0.13-0.18 | ✓ |

## 3. Regresión peers (post-fix)

| Banco | Rows | tasa_mn non-null | Mean | Status |
|-------|------|-----------------|------|--------|
| INVEX | 108 | 106 | 0.1610 | ✓ FIXED |
| BBVA | 271 | 108 | 0.1281 | ✓ sin cambio |
| SANTANDER | 108 | 107 | 0.1341 | ✓ sin cambio |
| BANORTE | 108 | 107 | 0.1263 | ✓ sin cambio |
| HSBC | 108 | 105 | 0.1168 | ✓ sin cambio |
| CITIBANAMEX | 196 | 108 | 0.1188 | ✓ sin cambio |

## 4. Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `plugins/bank-advisor-private/etl/core/transforms.py` | Fix merge_corporate_rates(): filtro Ahorro Famsa + remap INVEX |
| `docs/data/etl_runbook.md` | Corregida sección incorrecta sobre tasa INVEX |
| `docs/data/source_mapping.md` | Actualizado gotcha código institución INVEX |
| `docs/kanban/DOING/2026-03-03__BUG__*/` | Task docs (card, research, plan, validate) |

## 5. Data patch en DB (115 UPDATEs)

Aplicado antes del fix ETL como medida temporal. Valores tomados del CSV crudo
con promedio ponderado por Total Portfolio. Validado contra peers:

| Banco (Dic 2025) | tasa_mn | tasa_me |
|----------|---------|---------|
| HSBC | 17.16% | 5.83% |
| SANTANDER | 15.51% | 7.89% |
| BBVA | 14.93% | 7.26% |
| CITIBANAMEX | 14.13% | 6.36% |
| BANORTE | 13.92% | 6.78% |
| **INVEX** | **12.86%** | **8.26%** |

## 6. Nota sobre NaN vs NULL

48/108 meses de INVEX KPIs son non-NaN después de `aggregate_monthly_kpis()`.
Esto es esperado: `WEIGHTED_AVG_COLUMNS` incluye `tasa_mn`/`tasa_me`, y meses
sin portfolio weight producen NaN. Afecta a todos los bancos, no es específico de INVEX.
