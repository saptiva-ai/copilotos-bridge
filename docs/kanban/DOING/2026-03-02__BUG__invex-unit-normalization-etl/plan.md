# Plan

## Objective

Corregir la inconsistencia de unidades en `bank_fact_kpis_mensual` para que INVEX (y los demás legacy banks) sean comparables con los peers AG-only. Normalizar el pipeline AG para que use las mismas unidades que el legacy.

## Scope

### In

- Normalizar unidades AG: cartera pesos→miles de pesos (÷1000), ICAP %→decimal (÷100)
- Fix fecha type mismatch en merge legacy↔AG
- Remap INVEX ICAP/TDA institution code 040059→040131
- Re-run ETL con `--upsert` para corregir datos históricos
- Validación BD post-fix

### Out

- tasa_mn/tasa_me para INVEX (dato faltante en fuente, no es bug)
- Cambios en frontend/analytics_service
- Blank pages PDF / LLM interpretation (tareas separadas)

## Estrategia

En lugar de multiplicar valores INVEX-specific, la solución es **normalizar el pipeline AG completo** para que produzca las mismas unidades que el legacy:

- AG cartera: pesos → ÷1000 → miles de pesos (como legacy)
- AG ICAP: porcentaje (16.0) → ÷100 → decimal (0.16) (como legacy)
- AG IMOR/IMORA: porcentaje (2.5) → ÷100 → decimal (0.025) (ya existía para IMOR/IMORA, se extiende a ICAP)

Y **arreglar el merge** para que no falle silenciosamente por fecha type mismatch.

## Phases

### Phase 1 — Normalización AG + Fix merge (IMPLEMENTADO)

- [x] `loaders_unified.py`: Dividir cartera cols ÷1000 en `transform_analisis_general_to_kpis()`
- [x] `loaders_unified.py`: Dividir ICAP ÷100 (añadir a la lista de normalize_exprs existente)
- [x] `transforms.py`: Cast fecha antes del join legacy↔AG
- [x] `transforms.py`: Remap INVEX ICAP code 040059→040131 en `merge_icap()`
- [x] `transforms.py`: Remap INVEX TDA code 040059→040131 en `merge_tda()`
- [x] `transforms_pipeline.py`: Mismo fix de fecha para la versión pipeline

#### Phase 1 Files

- `plugins/bank-advisor-private/etl/core/loaders_unified.py` (líneas 1319-1340)
- `plugins/bank-advisor-private/etl/core/transforms.py` (líneas 476-486, 525-534, 1369-1377)
- `plugins/bank-advisor-private/etl/core/transforms_pipeline.py`

### Phase 2 — Re-run ETL + Validación (PENDIENTE)

- [ ] Re-run ETL: `cd plugins/bank-advisor-private && .venv/bin/python3.11 -m etl.etl_unified --upsert`
- [ ] Spot check BD: comparar INVEX vs AFIRME/MONEX (cartera_total, icap_total, imor)
- [ ] Verificar IMOR derivado: `cartera_vencida / cartera_total × 100` ≈ `imor × 100`
- [ ] Verificar ICAP: INVEX icap_total entre 10-25 (no 0.1-0.2)
- [ ] Verificar que bancos AG-only (AFIRME, MONEX, etc.) no cambiaron
- [ ] Ejecutar tests E2E snapshot (si existen para dic 2025)

#### Phase 2 Files

- N/A (solo ejecución y validación)

## Validation Commands

```bash
# Re-run ETL (PROD via SSH tunnel)
cd plugins/bank-advisor-private
.venv/bin/python3.11 -m etl.etl_unified --upsert

# Spot check: INVEX vs peers deben estar en la misma escala
psql -c "
SELECT banco_norm, cartera_total, icap_total, imor
FROM bank_fact_kpis_mensual
WHERE banco_norm IN ('INVEX', 'AFIRME', 'MONEX')
  AND fecha = '2025-09-01'
ORDER BY banco_norm;
"

# Verificar IMOR derivado para INVEX
psql -c "
SELECT banco_norm, cartera_vencida, cartera_total,
       ROUND(cartera_vencida::numeric / NULLIF(cartera_total, 0) * 100, 2) as imor_calc,
       ROUND(imor::numeric * 100, 2) as imor_stored
FROM bank_fact_kpis_mensual
WHERE banco_norm = 'INVEX' AND fecha = '2025-09-01';
"

# E2E tests
TEST_BACKEND_URL=http://localhost:18000 python3.11 tests/e2e/charts/test_icap_dic2025_snapshot.py
TEST_BACKEND_URL=http://localhost:18000 python3.11 tests/e2e/charts/test_cartera_dic2025_snapshot.py
```

## Success Criteria

1. INVEX cartera_total ≈ 49,754,432 (miles de pesos) — comparable con MONEX ~54,595,986
2. INVEX icap_total ≈ 0.1576 (decimal) — comparable con AFIRME ~0.1139
3. Ratio INVEX/MONEX cartera_total ≈ 0.91 (no 0.0009 como antes)
4. IMOR derivado (cartera_vencida/cartera_total) ≈ imor almacenado
5. Bancos AG-only (AFIRME, MONEX, SCOTIABANK) sin cambios en valores
6. 6 legacy banks (INVEX, BBVA, BANORTE, SANTANDER, HSBC, CITIBANAMEX) con valores coherentes
