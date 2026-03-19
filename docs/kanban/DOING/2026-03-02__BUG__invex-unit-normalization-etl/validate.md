# Validation

## Pre-fix State (2026-03-02)

### DB Values Sept 2025 — INVEX vs Peers

| Banco | cartera_total | icap_total | imor |
|---|---|---|---|
| INVEX | 49,754,432 | 0.1576 | 0.0225 |
| AFIRME | 67,937,006,546 | 11.3899 | 0.0399 |
| MONEX | 54,595,986,019 | 19.0469 | 0.0147 |

**Problema visible:** INVEX cartera ~1000× menor, ICAP ~100× menor que peers.
Causa: merge legacy↔AG fallaba silenciosamente por fecha type mismatch (Date vs Datetime).

## Fix Intento 1 — Normalización AG (REVERTIDO)

Se intentó normalizar AG: cartera ÷1000, ICAP ÷100. Esto fue INCORRECTO porque la
convención de la BD es pesos (cartera) y porcentaje (ICAP). La normalización rompió
los 18 bancos AG al dejarlos en escala diferente a los otros 25 bancos.

**Revertido**: se eliminó ÷1000 de cartera y ÷100 de ICAP. Solo IMOR/IMORA ÷100
se mantiene (era pre-existente y correcto).

## Fix Correcto — Fecha cast + INVEX code remap

- `transforms.py`: Cast `fecha` Date→Datetime antes del join legacy↔AG
- `transforms.py`: Remap INVEX 040059→040131 en `merge_icap()` y `merge_tda()`
- `transforms_pipeline.py`: Mismo fix de fecha
- `loaders_unified.py`: Solo IMOR/IMORA ÷100 (sin tocar cartera ni ICAP)

## Post-fix Validation (BD — 2026-03-02 22:06)

5,238 rows re-upserted (18 bancos × ~290 meses). Valores restaurados a pesos.

### Checklist

- [x] Upsert completado sin errores (5,238 rows)
- [x] INVEX cartera_total = 49,754,432,341 pesos ✓
- [x] INVEX icap_total = 15.76 (porcentaje) ✓
- [x] AFIRME cartera_total = 67,937,006,546 pesos ✓
- [x] MONEX cartera_total = 54,595,986,019 pesos ✓
- [x] 39 bancos en pesos (>1B), 6 bancos pequeños genuinos (<1B) ✓
- [x] 0 bancos con mezcla de escalas ✓
- [x] IMOR derivado = cartera_vencida/cartera_total coincide con imor almacenado ✓
- [ ] E2E tests (pendiente)

### BD Spot Check Sept 2025

| Banco | Cartera (pesos) | ICAP (%) | IMOR (decimal) |
|---|---|---|---|
| INVEX | 49,754,432,341 | 15.76 | 0.0225 |
| AFIRME | 67,937,006,546 | 15.27 | 0.0399 |
| MONEX | 54,595,986,019 | 19.12 | 0.0147 |
| BANCREA | 42,218,625,556 | 10.91 | 0.0433 |
| SABADELL | 101,304,317,693 | 14.70 | 0.0178 |

Todos en la misma escala: pesos para cartera, porcentaje para ICAP, decimal para IMOR.

### Ratios de verificación

- AFIRME/INVEX cartera: 1.37 ✓ (antes del fix: 1365×)
- MONEX/INVEX cartera: 1.10 ✓
- BBVA/BANORTE cartera: 1.73 ✓

## Fix Nov/Dic 2025 — Escala Legacy en Meses sin AG

AG CSV solo cubre hasta Oct 2025. Los 6 bancos dual-source (INVEX, BBVA, BANORTE,
SANTANDER, HSBC, CITIBANAMEX) quedaron con valores en escala legacy (MDP) para
Nov y Dic 2025.

### Fix aplicado (SQL UPDATE manual)

**Ronda 1** (4 bancos × 2 meses = 8 rows): INVEX, CITIBANAMEX, SANTANDER, HSBC
**Ronda 2** (2 bancos × 2 meses = 4 rows): BBVA, BANORTE (no detectados inicialmente
porque su cartera ÷1000 seguía siendo >1B)

Factores aplicados:
- `cartera_total, cartera_vencida, etapa_1, etapa_2, consumo, vivienda` × 1,000
- `cartera_comercial_total` × 1,000,000
- `icap_total` × 100

### Validación post-fix Nov/Dic

- [x] 0 bancos con ratio Oct/Nov > 5 (scan completo) ✓
- [x] 0 bancos con ratio Nov/Dic > 5 ✓
- [x] BBVA cartera_comercial_total Dic = ~1.18T (consistente con Oct ~1.19T) ✓
- [x] BANORTE cartera_comercial_total Dic = ~538B (consistente con Oct ~537B) ✓

### Incidente: ETL legacy ejecutado sin AG (2026-03-03)

Se ejecutó `transform_all()` sin AG para cargar Dic 2025. Esto sobreescribió los valores
correctos (de AG) con valores legacy ×1000 menores para los 7 bancos. Restauración:
1. Re-run AG upsert (5,238 rows) → restauró Oct y anteriores
2. Re-aplicar SQL UPDATE manual Nov/Dic (12 rows) → restauró Nov/Dic

**Lección**: NUNCA ejecutar ETL legacy sin AG upsert después. Ver `etl_runbook.md`.

### Prevención futura

- Cuando la próxima entrega de AG cubra Nov/Dic, el upsert sobreescribirá estos valores
  automáticamente con los de AG (que ya vienen en pesos)
- El fix manual solo es necesario mientras AG no cubra esos meses
- Solicitar a Bajaware: AG `040_TO.csv` actualizado + corrección de Nov en Excel

### Hallazgos adicionales (2026-03-03)

- **Nov 2025 = Oct 2025** en `CNBV_Cartera_Bancos_V2.xlsx`: datos de origen duplicados
  por Bajaware (136 instituciones, todas las columnas). No es bug del ETL.
- **Dic 2025: solo 6 bancos en BD**: AG no incluido en entrega → peers AG-only sin Dic →
  `AVG(solo INVEX) = INVEX` en gráficas de promedio.
- **`cartera_consumo_total` = 0 en legacy**: pipeline Legacy no calcula esta métrica.
  Solo AG la produce. Sin fix posible hasta nueva entrega de AG.

## Estado Actual de Métricas

| Metrica | Estado | Notas |
|---|---|---|
| cartera_total | Fixeado | Pesos, AG upsert + SQL manual Nov/Dic |
| cartera_comercial_total | Fixeado | Pesos, AG upsert + SQL manual Nov/Dic |
| cartera_vencida | Fixeado | Pesos, AG upsert + SQL manual Nov/Dic |
| cartera_etapa_1/2 | Fixeado | Pesos, AG upsert + SQL manual Nov/Dic |
| cartera_consumo_total | Parcial | 0 en Nov/Dic (legacy no calcula, solo AG) |
| cartera_vivienda_total | Fixeado | Pesos, AG upsert + SQL manual Nov/Dic |
| icap_total | Fixeado | Porcentaje, AG upsert + SQL manual Nov/Dic |
| imor / imora | Fixeado | Decimal (÷100 pre-existente, sin cambio) |
| tasa_mn / tasa_me | No es bug | INVEX no reporta tasas desde dic 2016 |
