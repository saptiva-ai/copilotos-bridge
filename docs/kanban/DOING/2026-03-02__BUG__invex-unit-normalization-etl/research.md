# Research

## Problema

Las gráficas benchmark de INVEX mostraban valores "cerca de 0" comparados con los peers, haciendo que INVEX pareciera insignificante cuando en realidad es un banco de tamaño similar a MONEX/AFIRME.

## Causa Raíz Identificada

Hay dos pipelines ETL que alimentan la misma tabla `bank_fact_kpis_mensual`, y usan unidades diferentes:

| Pipeline | Bancos | Cartera | ICAP | IMOR |
|---|---|---|---|---|
| Legacy CNBV (Excel) | INVEX, BBVA, BANORTE, SANTANDER, HSBC, CITIBANAMEX | miles de pesos | decimal (0.16) | decimal |
| Analisis General (CSV) | MONEX, AFIRME, SCOTIABANK, BAJIO, +12 más | pesos | porcentaje (16.0) | porcentaje |

El merge entre ambos pipelines **falla silenciosamente** porque la columna `fecha` tiene tipos incompatibles (`Date` vs `Datetime`). El `try-except` en `transforms.py:1415` lo atrapa y deja los datos sin unificar → INVEX queda en miles de pesos mientras los peers quedan en pesos, creando una diferencia de ~1000×.

## Datos Crudos Verificados (CSV AG vs BD)

### INVEX Sept 2025

| Columna | CSV AG (crudo) | BD (actual) | Factor |
|---|---|---|---|
| cartera_total | 49,754,432,341 | 49,754,432.341 | ÷1,000 |
| cartera_comercial_total | 15,956,689,215 | 15,956.689 | ÷1,000,000 |
| cartera_vencida | 1,120,013,433 | 1,120,013.433 | ÷1,000 |
| cartera_total_etapa_1 | 47,102,273,556 | 47,102,273.556 | ÷1,000 |
| cartera_total_etapa_2 | 1,532,145,352 | 1,532,145.352 | ÷1,000 |
| cartera_consumo_total | 33,743,568,100 | 0 | N/A |
| cartera_vivienda_total | 54,175,026 | 54,175.026 | ÷1,000 |
| icap_total | 15.7612 | 0.157612 | ÷100 |

### BBVA también afectado (mismo patrón)

| Columna | CSV AG | BD | Factor |
|---|---|---|---|
| cartera_total | 2,016,789,398,854 | 2,016,789,398.854 | ÷1,000 |
| icap_total | 19.9711 | 0.1625 | ÷100 |

### Bancos NO afectados (AG-only, valores correctos)

- AFIRME: cartera_total = 67,937,006,546 (BD) = 67,937,006,546 (CSV) ✓
- MONEX: cartera_total = 54,595,986,019 (BD) ≈ CSV ✓
- SCOTIABANK: cartera_total = 529,339,294,929 (BD) ✓

## Flujo del Bug

```
1. load_cnbv_cartera() → Lee Excel, aplica ×1000 (miles→pesos) → Legacy KPIs
2. load_analisis_general() → Lee CSV 040_TO.csv → AG data (ya en pesos)
3. transform_analisis_general_to_kpis() → Pivotea, normaliza IMOR/IMORA ÷100
4. transform_all() → Merge:
   - Calcula both_banks, legacy_only, ag_only
   - Para both_banks: ag_both.join(legacy_subset) ← FALLA por fecha Date vs Datetime
   - try/except captura el error silenciosamente
   - Resultado: legacy values persisten para both_banks (en miles de pesos)
   - AG-only banks: valores correctos (en pesos)
   → Inconsistencia de unidades en la misma tabla
```

## Bancos Afectados (6 "legacy banks")

Estos bancos existen en AMBAS fuentes (legacy Excel + AG CSV). Cuando el merge falla, quedan con datos legacy (miles de pesos):

1. INVEX (040059/040131)
2. BBVA (040012)
3. BANORTE (040072)
4. SANTANDER (040014)
5. HSBC (040021)
6. CITIBANAMEX (040002)

## Hallazgo Adicional: INVEX Institution Code 040059 → 040131

`enrich_with_instituciones()` remapea INVEX de 040059 a 040131 en los datos CNBV. Pero los archivos ICAP y TDA siguen usando 040059. Sin el remap, el join de ICAP/TDA falla para INVEX.

## Investigación tasa_mn / tasa_me

### Hallazgos

1. **INVEX SÍ existe** en `CorporateLoan_CNBVDB.csv` con código `040059`
2. **Registros recientes tienen Average Rate = 0** (desde ~2017)
3. **El filtro `average_rate > 0`** (loaders_unified.py:624) excluye los registros con tasa 0
4. **Última tasa válida:** diciembre 2016 (tasa_mn ≈ 0.093, tasa_me ≈ 0.056)
5. **Conclusión:** INVEX dejó de reportar tasas de crédito corporativo a la CNBV después de 2016. No es un bug del ETL — es dato faltante en la fuente.

### Evidencia

```
# Últimas tasas no-cero de INVEX en BD:
INVEX|2016-12-01|0.093|0.056
INVEX|2016-11-01|0.091|0.055
INVEX|2016-10-01|0.087|0.054

# Registros recientes en CSV (Jul 2025): Average Rate = 0
Pesos,MiPyMEs,ZACATECAS,32,Moneda nacional,14,Invex,040059,7/31/25,...,0,...
```

## References

- **Tabla afectada:** `bank_fact_kpis_mensual`
- **Fuente AG:** `plugins/bank-advisor-private/data/raw/AnalisisGeneral/sh_datos_csv_40_i/040_TO.csv`
- **Fuente Legacy:** `CNBV_Cartera_Bancos_V2.xlsx`
- **Fuente Tasas:** `CorporateLoan_CNBVDB.csv`
- **AG transform:** `loaders_unified.py:1261` (`transform_analisis_general_to_kpis`)
- **Merge code:** `transforms.py:1330-1416` (step 1.5 AG enrichment)
- **ICAP merge:** `transforms.py:460` (`merge_icap`)
- **Instituciones catalog:** `Instituciones.xlsx`
