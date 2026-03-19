# Plan

## Objective
- Alinear el calculo de IMOR comercial (CVC/CC) con la fuente de verdad de Tableau/Bajaware, eliminando la dependencia del E3 derivado impreciso.

## Scope
### In
- Agregar columna `imor_comercial` a `bank_fact_kpis_mensual` (ex monthly_kpis)
- Actualizar definicion de `bank_mv_evolucion_cartera_banco` (031) para incluir `imor_comercial` + variaciones YoY/MoM
- Cargar datos de E3 real desde `CNBV_Cartera_Bancos_V2.xlsx` para periodos historicos
- Hacer refresh de todas las VMs via `bank_mv_refresh_all()`
- Ajustar `_execute_delta_hip()` para leer de la VM en lugar de calcular on-the-fly
- TDD: tests primero, implementacion despues

### Out
- Cambios en handlers o routing (ya funcional)
- Cambios en MetricNormalizer (`hip_imor_comercial` ya registrado)
- Soporte de periodos > Jun 2024 sin nueva fuente de Bajaware

## Hallazgos de la Investigacion de VMs

### Inventario de VMs relevantes

| VM | Tiene IMOR? | Fuente | Refresh |
|----|-------------|--------|---------|
| `bank_mv_evolucion_cartera_banco` (031) | `imor` (general) | `bank_fact_kpis_mensual` | `bank_mv_refresh_evolucion()` (CONCURRENT) |
| `bank_mv_ranking_cartera_mensual` (030) | `imor`, `icor`, `icap_total` | `bank_fact_kpis_mensual` | `bank_mv_refresh_ranking()` (CONCURRENT) |
| `bank_mv_cartera_por_actividad` (047) | `imor_calculado` | `bank_fact_cartera_comercial` | `refresh_bank_analytics_mvs()` |
| `bank_mv_cartera_por_tamano` (047) | `imor_calculado` | `bank_fact_cartera_comercial` | `refresh_bank_analytics_mvs()` |
| `bank_mv_cartera_por_estado` (048) | `imor_calculado` | `bank_fact_cartera_comercial` | `refresh_bank_analytics_mvs()` |
| `bank_mv_metricas_financieras` (049) | `imor`, `icor` | `bank_fact_metricas_financieras` | Manual |

### Decision: `bank_fact_kpis_mensual` + `bank_mv_evolucion_cartera_banco`

**Razon**: `bank_fact_kpis_mensual` ya tiene `imor` (IMOR general), `icor`, `icap_total` como columnas de ratio.
Agregar `imor_comercial` sigue el patron existente. La MV de evolucion (031) ya tiene
variaciones YoY/MoM para `imor` — agregar las mismas para `imor_comercial` es natural.

### Reto: Cobertura temporal

| Fuente | Cobertura |
|--------|-----------|
| `bank_fact_kpis_mensual` | 2024-09 → presente |
| `CNBV_Cartera_Bancos_V2.xlsx` | 2017-01 → 2024-06 |
| Gap | 2024-07 a 2024-08 (2 meses) |

Estrategia: Para periodos historicos (pre 2024-09) que no estan en `bank_fact_kpis_mensual`,
insertar filas con al menos `institucion_id`, `periodo_id`, `imor_comercial` desde el xlsx.
Para periodos 2024-09+, calcular `imor_comercial` durante el ETL (si `saldo_etapa3` se
carga en futuras entregas) o dejarlo NULL hasta tener fuente.

## Phases

### Phase 0 - TDD: Tests de precision (RED) ✅ DONE
- [x] 8 tests unitarios: formula, MetricNormalizer, ORM column check
- [x] E2E test 15/15 passed

### Phase 1 - Migracion 058 ✅ DONE
- [x] ALTER TABLE + 3 MVs recreadas (evolucion, ranking, comparativa)
- [x] FK population: 3,016 rows updated

### Phase 2 - Loader xlsx ✅ DONE
- [x] `loaders_imor_comercial.py`: xlsx → `bank_fact_kpis_mensual.imor_comercial`
- [x] 2,916 updated + 512 inserted en PROD DB
- [x] Cobertura: 2017-01 a 2024-06

### Phase 3 - Refresh MVs ✅ DONE
- [x] Todas las MVs refreshed
- [x] MV tiene `imor_comercial` para periodos historicos

### Phase 4 - Enfoque hibrido MV+fallback ✅ DONE
- [x] `_execute_delta_hip()` reescrito con `_read_mv_imor()` + `_read_fact_imor()`
- [x] Merge per-period: MV gana, fallback llena gaps
- [x] Log de audit: `sources={'BANCO': 'mv/fb'}` por periodo
- [x] E2E 15/15 passed con valores hibridos

### Phase 5 - Centralizacion completa ✅ DONE

xlsx actualizado encontrado en `drive-download-20260209T193355Z-1-001/CNBV_Cartera_Bancos_V2.xlsx`:
- Cobertura: 201701 → **202511** (107 periodos, 135 bancos)
- 12,097 filas, 8,350 con imor_comercial no-null

Ejecucion:
- [x] Loader: 3,987 updated + 114 inserted, 0 errores
- [x] Refresh MVs: evolucion, ranking, comparativa, analytics
- [x] Verify: INVEX 202401=2.3454%, 202501=2.3633% (ambos del MV)
- [x] E2E 15/15 passed con `sources={'BANCO': 'mv/mv'}` para los 10 bancos
- [ ] (Opcional) Eliminar `_read_fact_imor()` fallback de `evolution.py` — ya no se activa pero
  se mantiene como safety net para futuros periodos sin xlsx

## Validation Commands
- `python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/domain/test_imor_comercial_computation.py`
- `python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/etl/test_loader_etapa3.py`
- `python3.11 tests/e2e/charts/test_variacion_cvc_cc_bar_chart.py`
- `python3.11 -m pytest -q plugins/bank-advisor-private/tests/ -k "imor_comercial"`

## Success Criteria
- [x] IMOR comercial coincide con xlsx (tolerancia < 0.05pp) para periodos cubiertos por xlsx (2017-01 a 2024-06).
- [x] `bank_fact_kpis_mensual` tiene columna `imor_comercial` poblada para periodos 2017-01 a 2024-06.
- [x] `bank_mv_evolucion_cartera_banco` incluye `imor_comercial` + variaciones YoY/MoM tras refresh.
- [x] `_execute_delta_hip()` lee del MV para periodos con xlsx, fallback para periodos sin xlsx.
- [x] E2E test pasa 15/15.
- [x] Centralizado al 100%: xlsx actualizado (hasta Nov 2025) cargado, MV usa `mv/mv` para todos los bancos.
- [ ] **PENDIENTE**: Deploy de codigo Python a PROD (enfoque hibrido en `evolution.py`).
