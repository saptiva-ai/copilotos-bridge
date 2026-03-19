---
id: "INCIDENT-2026-03-03__etl-broke-dual-source-scale"
title: "ETL run rompió escala de bancos dual-source + introdujo ceros y spikes"
status: "DONE"
severity: "Alta — afecta gráficas de producción para 7 bancos + SISTEMA"
detected: "2026-03-02"
resolved: "2026-03-03"
duration_impact: "~24 horas con datos incorrectos en producción"
artifacts:
  card: card.md
---

# Incidente: ETL run rompió escala de datos para bancos dual-source

## Timeline

| Fecha | Evento |
|-------|--------|
| ~2026-03-01 | **Datos correctos** en producción. Gráficas de INVEX, BBVA, etc. mostraban valores coherentes. |
| 2026-03-02 | **ETL ejecutado** para incorporar nueva entrega de Bajaware (drive-download-20260302). Incluye datos hasta Dic 2025. |
| 2026-03-02 | **Datos rotos post-ETL**. Cartera de bancos dual-source aparece ~1000× menor. ICAP en decimal. Ceros en periodos históricos. |
| 2026-03-02 14:00 | Bug identificado. Card BUG-invex-unit-normalization creada. |
| 2026-03-02 21:31 | Primera ronda de fixes: ETL code fix + upsert BD (5,238 rows). |
| 2026-03-03 (sesión 1) | Fixes BD directos: ICAP ×100 (717 filas), cartera ×1000 (307 filas). |
| 2026-03-03 (sesión 2) | Fixes BD profundos: INVEX multi-columna (~640 filas), spike Ene 2023, zeros 2017-2021, cartera_comercial_sin_gob para 6 bancos (647 filas). |
| 2026-03-03 | **Resuelto**. Redis flusheado en ambos servers. Datos verificados. |

## Root Cause

El ETL Unificado tiene **dos pipelines que escriben a la misma tabla** (`bank_fact_kpis_mensual`):

1. **Legacy** (`CNBV_Cartera_Bancos_V2.xlsx`): datos en MDP (millones de pesos), ICAP en decimal
2. **Análisis General** (`040_TO.csv`): datos en pesos, ICAP en porcentaje

**Orden esperado**: Legacy → AG upsert (AG sobreescribe legacy para los 6 bancos en común).

**Lo que pasó**: El ETL corrió Legacy con `--upsert`, y:
- Para meses cubiertos por AG: AG sobreescribió correctamente
- Para meses SIN cobertura AG (Dic 2025, meses recientes): quedaron con valores legacy en escala incorrecta
- Para algunos meses: ambos pipelines sumaron valores (patrón 2× en Ene 2023)
- `merge_icap()` se aplicó DESPUÉS del merge legacy↔AG, reintroduciendo ICAP en decimal para bancos dual-source
- Columnas derivadas (`cartera_comercial_sin_gob`) nunca fueron corregidas por AG (no hay concepto AG)

## Impacto

### Bancos afectados
| Banco | Tipo | Afectado |
|-------|------|----------|
| INVEX | Dual-source | Más afectado — cartera, ICAP, sin_gob, zeros históricos |
| BBVA | Dual-source | Cartera, ICAP, sin_gob |
| BANORTE | Dual-source | Cartera, ICAP, sin_gob |
| SANTANDER | Dual-source | Cartera, ICAP, sin_gob |
| HSBC | Dual-source | Cartera, ICAP, sin_gob |
| CITIBANAMEX | Dual-source | Cartera, ICAP, sin_gob |
| SISTEMA | Agregado | ICAP, cartera (calculado de dual-source) |
| AFIRME, MONEX, etc. | AG-only | **No afectados** |

### Métricas afectadas
| Métrica | Síntoma | Escala del error |
|---------|---------|-----------------|
| cartera_total | ~1000× menor | 50M vs 50B |
| cartera_comercial_total | ~1M× menor | 15K vs 15B |
| cartera_comercial_sin_gob | ~1M× menor | 15K vs 15B |
| cartera_vencida | ~1000× menor | 115K vs 115M |
| cartera_vivienda_total | ~1000× menor (parcial) | 39K vs 39M |
| icap_total | decimal vs porcentaje | 0.15 vs 15 |
| cartera_total_etapa_3 | ~1000× menor (siempre) | cartera_vencida/1000 |
| cartera_total 2017-2021 INVEX | ceros | 0 vs 19-24B |

### Gráficas de producción afectadas
- Benchmark INVEX vs peers (cartera, ICAP, sin_gob)
- Promedios de sistema (incluyen dual-source con escala incorrecta)
- Series temporales con spikes en Ene 2023 y ceros en 2017-2021

## Correcciones aplicadas (DB directas)

### Sesión 1 (2026-03-03)
| Fix | Filas | Método |
|-----|-------|--------|
| ICAP ×100 (6 bancos + SISTEMA) | 717 | `SET icap_total = icap_total * 100 WHERE icap_total < 1` |
| Cartera ×1000 (7 entidades) | 307 | Umbrales por banco (SISTEMA < 100B, big banks < 10B, INVEX < 500M) |

### Sesión 2 (2026-03-03)
| Fix | Filas | Método |
|-----|-------|--------|
| INVEX cartera_total 2017-2021 (zeros) | 60 | Restaurado desde AG concepto 40100185 |
| INVEX cartera_total Ene 2023 (spike) | 1 | Restaurado desde AG (era 55.97B, correcto 29.47B) |
| INVEX cartera_vencida pre-2022 ×1000 | 59 | Factor ×1000 |
| INVEX cartera_vencida Oct-Dec 2022 | 3 | Restaurado desde AG concepto 40100341 |
| INVEX cartera_vencida Ene 2023 (spike 2×) | 1 | Restaurado desde AG (457M → 228M) |
| INVEX cartera_total_etapa_3 | 107 | SET = cartera_vencida (AG mapea a vencida, no etapa_3) |
| INVEX cartera_total_etapa_1 Ene 2023 | 1 | Restaurado desde AG concepto 40100263 |
| INVEX cartera_comercial_total pre-2022 | 253 | Restaurado desde AG concepto 40100186 |
| INVEX cartera_vivienda_total pre-2022 | 215 | Restaurado desde AG concepto 40100217 |
| INVEX comercial + vivienda Ene 2023 (2×) | 2 | Restaurado desde AG |
| cartera_comercial_sin_gob ×1M (6 bancos) | 647 | Factor ×1M (no hay concepto AG para esta columna) |
| INVEX sin_gob Ene 2023 spike | 1 | ÷2 (patrón duplicación) |

**Total: ~2,374 filas corregidas en DB**

## Pendientes (no corregidos)

| Issue | Razón | Riesgo |
|-------|-------|--------|
| `etapa_1` pre-2022 INVEX | Datos pre-IFRS9, no hay equivalente real | Bajo (etapa_1 no se grafica individualmente) |
| `cartera_comercial_total` 2022-2023 legacy vs AG (~25% diff) | Diferencia de definición, no de escala | Medio (afecta ~50% de meses 2022-2023) |
| Jul 2025 = Jun 2025 INVEX | Posible dato duplicado de origen | Bajo |
| Nov 2025 = Oct 2025 | Dato duplicado por Bajaware | Bajo (conocido) |
| **Código ETL sin fix definitivo** | `merge_icap()` no normaliza ×100, legacy no aplica ×1M suficiente | **Alto — próximo ETL re-run reintroducirá el problema** |

## Acciones preventivas requeridas

1. **Fix código `merge_icap()`**: Multiplicar ×100 al cargar desde ICAP_Bancos.xlsx
2. **Fix código `load_cnbv_cartera()`**: Aplicar ×1,000,000 en vez de ×1,000 para cartera
3. **Fix código `transforms.py`**: `cartera_total_etapa_3` debe igualarse a `cartera_vencida` post-merge
4. **Fix código `cartera_comercial_sin_gob`**: Recalcular después de que comercial_total esté en escala correcta
5. **Agregar validación post-ETL**: Query automático que detecte valores en escala legacy (cartera < umbral, ICAP < 1)
6. **Nunca ejecutar Legacy solo sin AG después** — documentado en `etl_runbook.md`

## Documentación actualizada

- `docs/data/source_mapping.md` — Nuevas secciones: spike Ene 2023, etapa_3, sin_gob, tabla de conceptos AG
- `docs/data/etl_runbook.md` — Historial de fixes, queries de detección, método de restauración AG
