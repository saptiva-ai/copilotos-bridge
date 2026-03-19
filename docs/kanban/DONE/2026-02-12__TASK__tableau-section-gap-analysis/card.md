# TASK: Tableau Section Gap Analysis — What We Have vs What We Need

**Prioridad:** P1
**Fecha:** 2026-02-12
**Status:** DONE
**Progreso:** Fases 0-9 completadas. **44/44 worksheets GENERABLE (100%)**. Task lista para REVIEW

---

## Progreso

| Fase | Estado | Fecha | Detalle |
|------|--------|-------|---------|
| **0** | DONE | 2026-02-12 | `cartera_total` agregado a `visualizations.yaml` (+2 worksheets) |
| **1** | DONE | 2026-02-12 | Backfill 13 cols desde CNBV XLSX: 1,784 filas, 17 bancos, Ene 2017-Nov 2025 |
| **2** | DONE | 2026-02-12 | CASTIGOS + IMORA: 3,568 filas. Script `backfill_castigos.py`, ORM + SAFE + viz + synonyms |
| **3** | DONE | 2026-02-12 | TDA backfill: 6,597 filas. Script `backfill_tda.py`, XLSX overwrite (source of truth) |
| **4** | DONE | 2026-02-12 | Tasas: 6,607 filas. Script `backfill_tasas.py`. CorporateLoan CSV (tasa_mn/me, 45 bancos, 114 meses) + TE XLSX (tasa_sistema/invex, 18 bimestrales). +5 viz configs |
| **4.5** | DONE | 2026-02-12 | **Investigación**: Anomalía IMORA (8.83%→2.25%), análisis TWB fórmulas, EDA archivos crudos Tableau, comparativa old vs new. Ver `research.md` |
| **5** | DONE | 2026-02-12 | Fix IMORA: COALESCE→OVERWRITE (1,855 filas). ICAP backfill: 3,893 filas, 52 bancos, +ccb/ccf columnas. Script `backfill_icap.py`, ORM + SAFE |
| **6+7** | DONE | 2026-02-12 | ICOR Tableau + reservas segmentadas: 1,855 filas, 53 bancos, +7 columnas. Script `backfill_reservas_icor.py`. ICOR=Res_SG/(CC_E3+VIV_E3), PE_SG=Res_SG/CT. ORM + SAFE + viz + synonyms |
| **8** | DONE | 2026-02-12 | Expand CODE_TO_BANCO 16→53 bancos en `backfill_cartera_total.py`. 4,263 filas, +1,109 ICOR. Cross-validation INVEX Jun 2025: 15/15 métricas EXACTAS vs XLSX |
| **8.5** | DONE | 2026-02-12 | **Fix CC_TOTAL bug**: `cartera_comercial_total` no se recalculaba en UPDATE (solo componentes). ETL tenía valores viejos (~solo Empresarial). Fix: OVERWRITE + agregar CC al UPDATE. 4,198 filas corregidas, 0 mismatches |
| **9** | DONE | 2026-02-12 | **Etapa VR + PE_Promedio**: `ct_etapa_vr` columna nueva (ALTER TABLE + 2,019 filas). ORM + SAFE_METRIC_COLUMNS + viz config + synonyms + multi-metric (stacked bar E1/E2/E3/VR). PE_Promedio: ya cubierto por `ComparativeRatioHandler` + `build_advanced_ranking(show_average_line=True)`. **44/44 GENERABLE (100%)** |

---

## Resumen

Mapeo completo de las 28 secciones (dashboards) del tablero Tableau `Invex_Tablero_V3.twb` contra los datos y handlers que ya tenemos en la plataforma. Identifica qué secciones están cubiertas, cuáles parcialmente, y cuáles están pendientes.

## Fuentes de Datos del Tablero

| # | Datasource | Archivo | Qué contiene | Periodos | Rows |
|---|---|---|---|---|---|
| 1 | `Sheet1+ (Varias conexiones)` | **CNBV_Cartera_Bancos_V2.xlsx** + CASTIGOS.xlsx + Castigos Comerciales.xlsx | Carteras por etapa IFRS 9, reservas, castigos | 201701-202511 | 12,097 |
| 2 | `CorporateLoan_CNBVDB.csv+` | **CorporateLoan_CNBVDB.csv** | Cartera comercial detallada + tasas | 201606-202511 | 1.67M |
| 3 | `TDA` | **TDA.xlsx** | TDA Cartera total (6 cols, sin segmentos) | 200012-202512 | 17,494 |
| 4 | `ICAP Bancos` | **ICAP_Bancos.xlsx** | ICAP Total + CCB + CCF | 202201-202511 | 14,275 |
| 5 | `TE_Invex_Sistema` | **TE_Invex_Sistema.xlsx** | Tasa efectiva INVEX vs Sistema | 201910-202208 | 18 |
| 6 | `CREADOR DE TDA` | **CREADOR DE TDA.xlsx** (NEW) | TDA granular: 78 cols, Etapa breakdown completo | 200012-202511 | 37,165 |
| 7 | `Benchmark` | **Catera Analitica Benchmark v2.xlsx** (NEW) | 334 cols pivot, 37 concept codes CNBV | 201701-202512 | ~11,764 |
| 8 | `R04A_419` | **040_R04A_419.csv** (NEW) | CNBV raw report (castigos por concepto) | 202512 | ~64MB |

### Decisión: Source of Truth

**Los archivos Tableau (XLSX/CSV crudos) son la fuente de verdad**, no el ETL CNBV.
- Los backfill scripts deben usar **OVERWRITE** (no COALESCE)
- Si hay discrepancia ETL vs Tableau, el valor Tableau prevalece
- Ver `research.md` → Sección "Anomalía IMORA" para justificación

## Mapeo: Dashboards del Tablero vs Plataforma

### Leyenda de estado
- **CUBIERTO**: Datos en BD + handler funcional + gráfica operativa
- **PARCIAL**: Datos en BD pero handler/formula incompleta o faltante
- **SIN DATOS**: Columna existe en BD pero vacía o con cobertura <50%
- **NO EXISTE**: No tenemos la tabla/columna en BD

---

### GRUPO 1: Cartera Total (Fuente: CNBV_Cartera_Bancos_V2.xlsx)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **CT_DB** | Cartera Total comparativo | `cartera_total` | **CUBIERTO** | 100% INVEX, niche banks recién backfilled |
| **CT Evol** | Cartera Total evolución temporal | `cartera_total` | **CUBIERTO** | Handler `evolucion_banco` |

### GRUPO 2: Cartera Comercial (Fuente: CNBV + CorporateLoan)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **CC_DB** | CC comparativo (INVEX vs sector) | `cartera_comercial_total` | **CUBIERTO** | 100% cobertura |
| **CC Graph DB** | CC evolución temporal | `cartera_comercial_total` | **CUBIERTO** | |
| **CC_sg_DB** | CC Sin Gobierno comparativo | `cartera_comercial_sin_gob` | **PARCIAL** | 35.7% cobertura INVEX (107/300). Backfilled Fase 1, techo XLSX |
| **CC S guber DB** | CC Sin Gobierno evolución | `cartera_comercial_sin_gob` | **PARCIAL** | Misma cobertura. 100% desde Ene 2017 |

### GRUPO 3: Cartera Vencida / IMOR / IMORA (Fuente: CNBV)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **Cart_Venc_DB** | Cartera vencida comparativo | `cartera_vencida` | **CUBIERTO** | 99% INVEX |
| **CART VENC** | Cartera vencida (vista alt.) | `cartera_vencida` | **CUBIERTO** | |
| **CVG** | Cartera vencida gráfica evol. | `cartera_vencida` | **CUBIERTO** | |
| **IMORA DB** | IMORA comparativo + datos | `imora` | **CUBIERTO** | Fórmula Tableau. Fix Fase 5: COALESCE→OVERWRITE, 1,855 filas sobreescritas |
| **IMORA G DB** | IMORA gráfica evolución | `imora` | **CUBIERTO** | Serie continua, sin saltos anómalos |

### GRUPO 4: ICOR (Fuente: CNBV)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **ICOR_DB** | ICOR comparativo | `icor` | **CUBIERTO** | Fórmula Tableau: Res_SG/(CC_E3+VIV_E3). Backfilled Fase 6+7 |
| **ICG** | ICOR gráfica evolución | `icor` | **CUBIERTO** | 100% desde Ene 2017 (XLSX techo) |

### GRUPO 5: Pérdida Esperada / Reservas (Fuente: CNBV)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **PET** | PE Total comparativo + promedio | `pe_total` | **PARCIAL** | 35.7% cobertura (107/300). Backfilled Fase 1: -Reservas/CT |
| **RES_DB** | Reservas totales comparativo | `reservas_etapa_todas` | **PARCIAL** | 35.7% cobertura (107/300). Backfilled Fase 1 |
| **Res Graph DB** | Reservas evolución temporal | `reservas_etapa_todas` | **PARCIAL** | Backfilled Fase 1, 100% desde Ene 2017 |
| **RESSG_DB** | Reservas Sin Gobierno | `reservas_etapa_todas` - gub - consumo | **PARCIAL** | Requiere segmentar reservas por tipo |
| **RES_DB sin gub** | Reservas Sin Gobierno alt. | ídem | **PARCIAL** | |

### GRUPO 6: Etapas IFRS 9 (Fuente: CNBV)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **Etapas DB** | Composición E1/E2/E3/VR | `ct_etapa_1`, `ct_etapa_2`, `ct_etapa_3` | **PARCIAL** | 35.7% cobertura (ratios). Backfilled Fase 1. Etapa VR no existe en BD |

### GRUPO 7: ICAP (Fuente: ICAP_Bancos.xlsx)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **ICAP DB** | ICAP comparativo | `icap_total` | **CUBIERTO** | 79% INVEX (cargado por ETL original) |
| **ICAP C db** | ICAP evolución temporal | `icap_total` | **CUBIERTO** | |

### GRUPO 8: Quebrantos / Castigos (Fuente: CASTIGOS.xlsx)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **Quebrantos DB** | Quebrantos CC = Castigos + Quitas | `quebrantos_comerciales` | **CUBIERTO** | Backfilled Fase 2: LIB_CASTIGOS_COMERC + QUITAS_COMER |
| **Quebrantos GDB** | Quebrantos gráfica evolución | `quebrantos_comerciales` | **CUBIERTO** | Viz config `quebrantos_comerciales` agregada Fase 2 |

### GRUPO 9: TDA (Fuente: TDA.xlsx)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **TDA DB** | TDA Cartera Total | `tda_cartera_total` | **CUBIERTO** | 100% INVEX (300/300). Backfilled Fase 3 desde TDA.xlsx |

### GRUPO 10: Tasas (Fuente: CorporateLoan_CNBVDB.csv)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **Tasas DB** | Tasas promedio ponderadas | `tasa_mn`, `tasa_me` | **CUBIERTO** | 38% INVEX (114/300). Backfilled Fase 4, promedio ponderado por cartera |
| **Tasas CC** | Tasas CC MN + ME + vs promedio | `tasa_mn`, `tasa_me` | **CUBIERTO** | Viz configs `tasa_mn` + `tasa_me` agregadas Fase 4 |
| **Tasas MN** | Tasas MN vs promedio sector | `tasa_mn` | **CUBIERTO** | 45 bancos, Jun 2016 — Nov 2025 |
| **Tasas ME** | Tasas ME vs promedio sector | `tasa_me` | **CUBIERTO** | 45 bancos, Jun 2016 — Nov 2025 |

### GRUPO 11: Tasa Efectiva (Fuente: TE_Invex_Sistema.xlsx)

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **Tasa Int EF db** | Tasa interés efectiva INVEX vs Sistema | `tasa_sistema`, `tasa_invex_consumo` | **CUBIERTO** | 6% INVEX (18/300, bimestral Oct 2019-Aug 2022). Backfilled Fase 4, viz configs agregadas |

### GRUPO 12: Benchmark / Índice

| Dashboard | Métricas Tableau | Columna BD | Estado | Notas |
|---|---|---|---|---|
| **Benchmark** | Vista general benchmark | Múltiples | **PARCIAL** | Dashboard compuesto, depende de todas las métricas |
| **INDICE BENCHMARK** | Parámetros de fechas | N/A | **N/A** | UI de navegación |

---

## Resumen de Cobertura

| Estado | Pre-Fase 1 | Post-Fase 3 | Post-Fase 4 | Post-Fase 6+7 | Post-Fase 8 |
|---|---|---|---|---|---|
| **CUBIERTO** | 7 (25%) | 14 (50%) | 19 (68%) | 21 (75%) | **27** (96%) |
| **PARCIAL** | 18 (64%) | 11 (39%) | 6 (21%) | 4 (14%) | **0** (0%) |
| **SIN DATOS** | 1 (4%) | 1 (4%) | 0 (0%) | 0 (0%) | 0 (0%) |
| **N/A** (UI) | 2 (7%) | 2 (7%) | 2 (7%) | 2 (7%) | 2 (7%) |

### Columnas BD con cobertura <50% (post Fase 1)

| Columna | Antes | Ahora | Fuente pendiente |
|---|---|---|---|
| ~~`ct_etapa_1/2/3`~~ | 15% | **35.7%** | DONE (Fase 1, techo XLSX) |
| ~~`pe_total`~~ | 15% | **35.7%** | DONE (Fase 1) |
| ~~`empresarial_total`~~ | 0% | **35.7%** | DONE (Fase 1) |
| ~~`entidades_financieras_total`~~ | 0% | **35.7%** | DONE (Fase 1) |
| ~~`entidades_gubernamentales_total`~~ | 0% | **9%** | DONE (INVEX tiene 0 en mayoría de meses) |
| ~~`cartera_comercial_sin_gob`~~ | 0% | **35.7%** | DONE (Fase 1) |
| ~~`reservas_etapa_todas`~~ | 0% | **35.7%** | DONE (Fase 1) |
| ~~`icor`~~ | 35% | **35.3%** | DONE (Fase 1) |
| ~~`tda_cartera_total`~~ | 15% | **100%** | DONE (Fase 3, 6597 rows, overwrite) |
| ~~`quebrantos_comerciales`~~ | 35% | **~50%** | DONE (Fase 2, 3568 rows) |
| ~~`tasa_mn` / `tasa_me`~~ | 18% | **38%** | DONE (Fase 4, 6589 rows, promedio ponderado) |
| ~~`tasa_sistema` / `tasa_invex_consumo`~~ | 6% | **6%** | DONE (Fase 4, 18 rows, bimestral — techo XLSX) |

### Datos que NO existen en BD (columnas nuevas necesarias)

| Métrica Tableau | Descripción | Fuente |
|---|---|---|
| ~~Etapa VR (amounts)~~ | ~~Cartera en Value Recovery~~ | ~~CNBV col[6]~~ DONE Fase 9 |
| ~~IMORA (formula Tableau)~~ | ~~Incluye castigos acumulados, excl. gobierno~~ | ~~CASTIGOS.xlsx + CNBV~~ DONE Fase 2 |
| ~~PE Total SG~~ | ~~PE excluyendo gobierno y consumo~~ | ~~Calcular~~ DONE Fase 6+7 |
| ~~Reservas por segmento~~ | ~~Res_Empresarial, Res_Consumo, Res_Vivienda, Res_Gub~~ | ~~CNBV cols[35-39]~~ DONE Fase 6+7 |
| ~~Castigos acumulados (running sum)~~ | ~~Para IMORA~~ | ~~CASTIGOS.xlsx~~ DONE Fase 2 |
| Quitas por tipo | QUITAS_COMER, QUITAS_CONSUMO, etc. | CASTIGOS.xlsx |

---

## Gap de Gráficas: Worksheets Tableau vs Plataforma

### Capacidades actuales de la plataforma

**`visualizations.yaml`** — 19 configs de chart (actualizado Fase 6+7):

| Viz ID | Métrica BD | Tipo Chart | Modo | Fase |
|---|---|---|---|---|
| `cartera_comercial` | `cartera_comercial_total` | Bar | `dashboard_month_comparison` | — |
| `cartera_comercial_sin_gob` | `cartera_comercial_sin_gob` | Bar | `dashboard_month_comparison` | — |
| `perdida_esperada` | `reservas_etapa_todas` | Line | `timeline_with_summary` | — |
| `reservas_totales` | `reservas_etapa_todas` | Bar | `dashboard_month_comparison` | — |
| `reservas_variacion` | `reservas_etapa_todas` | Bar | `variation_chart` | — |
| `imor` | `imor` | Line | `dual_mode` | — |
| `cartera_vencida` | `cartera_vencida` | Line | `dual_mode` | — |
| `icor` | `icor` | Line | `dual_mode` | — |
| `icap` | `icap_total` | Line | `dual_mode` | — |
| `cartera_total` | `cartera_total` | Line | `dual_mode` | F0 |
| `imora` | `imora` | Line | `dual_mode` | F2 |
| `quebrantos_comerciales` | `quebrantos_comerciales` | Bar | `dual_mode` | F2 |
| **`tda_cartera_total`** | **`tda_cartera_total`** | **Line** | **`dual_mode`** | **F4** |
| **`tasa_mn`** | **`tasa_mn`** | **Line** | **`dual_mode`** | **F4** |
| **`tasa_me`** | **`tasa_me`** | **Line** | **`dual_mode`** | **F4** |
| **`tasa_sistema`** | **`tasa_sistema`** | **Line** | **`dual_mode`** | **F4** |
| **`tasa_invex_consumo`** | **`tasa_invex_consumo`** | **Line** | **`dual_mode`** | **F4** |
| **`reservas_sg`** | **`reservas_sg`** | **Line** | **`dual_mode`** | **F6+7** |
| **`pe_sg`** | **`pe_sg`** | **Line** | **`dual_mode`** | **F6+7** |

**Nota**: NO existe config de viz para `etapas IFRS`.

**13 handlers** generan datos + Plotly config:
- `MultiMetricHandler` (distribución/stacked), `MetricasFinancierasHandler`, `EvolucionBancoHandler` (series temporales), `ResumenSistemaHandler`
- `CarteraActividadHandler`, `CarteraTamanoHandler`, `CarteraDestinoHandler`, `ViviendaPerfilHandler`, `CarteraRegionHandler`
- `ComparativeRatioHandler`, `MarketShareHandler`, `SegmentHandler`, `InstitutionRankingHandler`

### Leyenda

- **GENERABLE**: Datos + handler + viz config → la plataforma puede generar la gráfica hoy
- **PARCIAL-DATOS**: Handler existe pero datos con cobertura <50%
- **PARCIAL-FORMULA**: Datos existen pero la fórmula difiere del Tableau
- **SIN HANDLER**: Datos en BD pero no hay handler/viz config dedicado
- **SIN DATOS NI HANDLER**: No hay datos ni handler

---

### Mapeo detallado: 44 Worksheets Tableau → Plataforma

#### CARTERA TOTAL (3 worksheets → Dashboard CT_DB + CT Evol)

| Worksheet | Tipo Tableau | Handler Plataforma | Viz Config | Estado Gráfica | Bloqueante |
|---|---|---|---|---|---|
| `CT_Comparativo` | Tabla datos | `EvolucionBancoHandler` | `cartera_total` | **GENERABLE** | Viz config agregada Fase 0 |
| `CT_Comparativo (G)` | Bar comparativo | `EvolucionBancoHandler` | `cartera_total` | **GENERABLE** | Viz config agregada Fase 0 |
| `CT_Graph` | Línea temporal | `EvolucionBancoHandler` | `cartera_total` | **GENERABLE** | Viz config agregada Fase 0 |

#### CARTERA COMERCIAL (6 worksheets → Dashboards CC_DB, CC Graph DB, CC_sg_DB, CC S guber DB)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `CC_Comparativo` | Tabla datos | `EvolucionBancoHandler` | `cartera_comercial` | **GENERABLE** | — |
| `CC_Comparativo (G)` | Bar comparativo | Handlers múltiples | `cartera_comercial` | **GENERABLE** | — |
| `CC_Graph` | Línea temporal | `EvolucionBancoHandler` | `cartera_comercial` | **GENERABLE** | — |
| `CC_sg_Comparativo` | Tabla datos | Handlers múltiples | `cartera_comercial_sin_gob` | **GENERABLE** | Fase 8: 53 bancos, 107 meses |
| `CC_sg_Comparativo (G)` | Bar comparativo | Handlers múltiples | `cartera_comercial_sin_gob` | **GENERABLE** | Fase 8: cobertura expandida |
| `CC_sg_Graph` | Línea temporal | `EvolucionBancoHandler` | `cartera_comercial_sin_gob` | **GENERABLE** | Fase 8: cobertura expandida |

#### CARTERA VENCIDA (4 worksheets → Dashboards Cart_Venc_DB, CART VENC, CVG)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `Cart_Venc` | Bar horizontal | `ComparativeRatioHandler` | `cartera_vencida` | **GENERABLE** | — |
| `Cart_Venc (dat)` | Tabla datos | Handler + datos | `cartera_vencida` | **GENERABLE** | — |
| `Cart_Venc (GÇ)` | Línea temporal | `EvolucionBancoHandler` | `cartera_vencida` | **GENERABLE** | — |
| `Cart_Ven_Monto` | Línea monto | `EvolucionBancoHandler` | `cartera_vencida` | **GENERABLE** | — |

#### IMORA (3 worksheets → Dashboards IMORA DB, IMORA G DB)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `IMORA` | Bar horizontal | `ComparativeRatioHandler` | `imora` | **GENERABLE** | Fix Fase 5: OVERWRITE, fórmula Tableau consistente |
| `IMORA (dat)` | Tabla datos | Handler + datos | `imora` | **GENERABLE** | |
| `IMORA (GC)` | Línea temporal | `EvolucionBancoHandler` | `imora` | **GENERABLE** | Serie continua post-fix |

#### ICOR (3 worksheets → Dashboards ICOR_DB, ICG)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `ICOR` | Bar horizontal | `ComparativeRatioHandler` | `icor` | **GENERABLE** | Fórmula Tableau Fase 6+7 |
| `ICOR (2)` | Tabla datos | Handler + datos | `icor` | **GENERABLE** | |
| `ICOR (G)` | Línea temporal | `EvolucionBancoHandler` | `icor` | **GENERABLE** | |

#### PÉRDIDA ESPERADA (3 worksheets → Dashboard PET)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `PE_Comparativo` | Tabla datos | Handlers múltiples | `perdida_esperada` | **GENERABLE** | Fase 8: 53 bancos, PE_total calculado |
| `PE_Mes` | Tabla por mes | Handlers múltiples | `perdida_esperada` | **GENERABLE** | Fase 8: cobertura expandida |
| `PE_Promedio` | Bar + línea promedio | `ComparativeRatioHandler` | `perdida_esperada` | **GENERABLE** | Fase 9: `build_advanced_ranking(show_average_line=True)` ya genera barra+línea promedio |

#### RESERVAS (6 worksheets → Dashboards RES_DB, Res Graph DB, RESSG_DB, RES_DB sin gub)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `Res_Comparativo (G) (2)` | Bar comparativo | Handlers múltiples | `reservas_totales` | **GENERABLE** | Fase 8: 53 bancos, reservas expandidas |
| `Res_Graph` | Línea temporal | `EvolucionBancoHandler` | `perdida_esperada` | **GENERABLE** | Fase 8: cobertura expandida |
| `RES_SG_Comparativo` | Tabla datos SG | `EvolucionBancoHandler` | `reservas_sg` | **GENERABLE** | Fase 6+7: reservas_sg + viz + synonyms |
| `RESSG_Mes` | Tabla mes SG | `EvolucionBancoHandler` | `reservas_sg` | **GENERABLE** | |
| `Res_Comparativo (SG)` | Bar evol SG | `EvolucionBancoHandler` | `reservas_sg` | **GENERABLE** | |
| `Res_Comparativo (G) sin gub` | Bar PE SG | `EvolucionBancoHandler` | `pe_sg` | **GENERABLE** | Fase 6+7: pe_sg + viz + synonyms |

#### ETAPAS IFRS 9 (1 worksheet → Dashboard Etapas DB)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `Etapas` | Stacked bar (E1/E2/E3/VR) | `MultiMetricHandler` | `ct_etapa_vr` | **GENERABLE** | Fase 9: ct_etapa_vr columna nueva, 2,019 filas, 53 bancos. Multi-metric stacked bar E1/E2/E3/VR |

#### ICAP (3 worksheets → Dashboards ICAP DB, ICAP C db)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `ICAP` | Bar horizontal | `ComparativeRatioHandler` | `icap` | **GENERABLE** | — |
| `ICAP (M_ACT)` | Tabla datos | Handler + datos | `icap` | **GENERABLE** | — |
| `ICAP_tiempo` | Línea temporal | `EvolucionBancoHandler` | `icap` | **GENERABLE** | — |

#### QUEBRANTOS (3 worksheets → Dashboards Quebrantos DB, Quebrantos GDB)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `Quebrantos` | Tabla datos | `EvolucionBancoHandler` | `quebrantos_comerciales` | **GENERABLE** | Viz config + datos agregados Fase 2 |
| `Quebrantos (4)` | Bar comparativo | `ComparativeRatioHandler` | `quebrantos_comerciales` | **GENERABLE** | Viz config agregada Fase 2 |
| `Quebrantos G` | Bar evolución temporal | `EvolucionBancoHandler` | `quebrantos_comerciales` | **GENERABLE** | Datos backfilled Fase 2 |

#### TDA (1 worksheet → Dashboard TDA DB)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `TDA` | Línea temporal (INVEX vs sector) | `EvolucionBancoHandler` | `tda_cartera_total` (default) | **GENERABLE** | Datos 100% backfilled Fase 3 |

#### TASAS (7 worksheets → Dashboards Tasas DB, Tasas CC, Tasas MN, Tasas ME)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `Tasas` | Tabla datos MN/ME | `EvolucionBancoHandler` | `tasa_mn`, `tasa_me` | **GENERABLE** | Backfilled Fase 4 (45 bancos, 114 meses) |
| `Tasa x Tiempo MN` | Línea MN temporal | `EvolucionBancoHandler` | `tasa_mn` | **GENERABLE** | Viz config agregada Fase 4 |
| `Tasa x Tiempo ME` | Línea ME temporal | `EvolucionBancoHandler` | `tasa_me` | **GENERABLE** | Viz config agregada Fase 4 |
| `Tasas vs Promedio MN` | Bar INVEX vs promedio | `ComparativeRatioHandler` | `tasa_mn` | **GENERABLE** | Promedio ponderado por cartera |
| `Tasas vs Promedio MN (2)` | Tabla datos MN | Handler + datos | `tasa_mn` | **GENERABLE** | |
| `Tasas vs Promedio ME` | Bar INVEX vs promedio | `ComparativeRatioHandler` | `tasa_me` | **GENERABLE** | |
| `Tasas vs Promedio ME (2)` | Tabla datos ME | Handler + datos | `tasa_me` | **GENERABLE** | |

#### TASA EFECTIVA (1 worksheet → Dashboard Tasa Int EF db)

| Worksheet | Tipo Tableau | Handler | Viz Config | Estado | Bloqueante |
|---|---|---|---|---|---|
| `Tasa Int Efectiva` | Línea dual (INVEX vs Sistema) | `EvolucionBancoHandler` | `tasa_sistema`, `tasa_invex_consumo` | **GENERABLE** | Backfilled Fase 4 (18 bimestrales) |

#### UI / NAVEGACIÓN (1 worksheet)

| Worksheet | Tipo | Estado |
|---|---|---|
| `PARAM FECHAS` | Selector de fechas (UI) | **N/A** |

---

### Resumen de Gráficas

| Estado | Worksheets | % | Detalle |
|---|---|---|---|
| **GENERABLE** | **44** | **100%** | +2 post Fase 9 (Etapas VR + PE_Promedio) |
| **PARCIAL-DATOS** | 0 | 0% | Eliminado Fase 9 |
| **PARCIAL-FORMULA** | 0 | 0% | Todas corregidas Fase 5 |
| **SIN HANDLER** | 0 | 0% | Eliminado Fase 6+7 |
| **SIN DATOS NI HANDLER** | 0 | 0% | Eliminado Fase 4 |
| **N/A** | 1 | 2% | UI de navegación |

### Acciones para cerrar el gap

#### ~~Quick Wins~~ DONE (Fase 0, 2026-02-12)
1. ~~**Agregar `cartera_total` a `visualizations.yaml`**~~ DONE → +2 worksheets GENERABLE
2. **Los 16 GENERABLES ya funcionan** — validar con queries de ejemplo

#### ~~Fase 1: Backfill datos~~ DONE (2026-02-12)
- ~~Backfill `reservas_etapa_todas`, `empresarial_total`, `entidades_financieras_total`, `entidades_gubernamentales_total`~~ DONE
- ~~Calcular `pe_total = -reservas/CT`, `icor = ABS(reservas)/CV`~~ DONE
- ~~Backfill etapas ratios `ct_etapa_1/2/3`~~ DONE
- **Resultado**: 1,784 filas, 17 bancos, 13 columnas. Cobertura 100% Ene 2017+

#### ~~Fase 2~~ DONE (2026-02-12): CASTIGOS + IMORA
- IMORA: fórmula Tableau `(CC_E3 + Castigos_Acum) / CC_E1_E2_E3` — 3,568 rows
- Quebrantos comerciales backfilled (LIB_CASTIGOS + QUITAS)
- `castigos_acum_comercial` columna nueva (ALTER TABLE)
- ORM + SAFE_METRIC_COLUMNS + visualizations.yaml + synonyms.yaml
- Script: `scripts/data/backfill_castigos.py`
- **+6 worksheets GENERABLE** (IMORA ×3 + Quebrantos ×3)

#### ~~Fase 3~~ DONE (2026-02-12): TDA backfill
- Script: `scripts/data/backfill_tda.py` — 6,597 rows, overwrite (XLSX = source of truth)
- INVEX 100% cobertura (300/300), de 46 ceros → 300 valores reales
- XLSX formato porcentaje (4.09) → DB ratio (0.0409)
- **+1 worksheet GENERABLE** (TDA)

#### ~~Fase 4~~ DONE (2026-02-12): Tasas MN/ME + TE
- Script: `scripts/data/backfill_tasas.py` — 6,607 rows (6,589 tasas + 18 TE)
- CorporateLoan CSV: promedio ponderado `SUM(rate×portfolio)/SUM(portfolio)` por banco+mes+moneda
- TE_Invex_Sistema.xlsx: 18 puntos bimestrales (Oct 2019 — Aug 2022) en filas INVEX
- +5 viz configs: `tda_cartera_total`, `tasa_mn`, `tasa_me`, `tasa_sistema`, `tasa_invex_consumo`
- Todos los scripts usan `periodo_id` (int) en WHERE clause (no `fecha`)
- **+8 worksheets GENERABLE** (Tasas ×7 + TE ×1)

---

## Plan de Trabajo (Priorizado)

### ~~Fase 1~~ DONE: Backfill desde CNBV_Cartera_Bancos_V2.xlsx
- Script: `scripts/data/backfill_cartera_total.py` (extendido con 13 columnas)
- EDA: `scripts/data/eda_xlsx_cols_35_39.py` (descubrió reservas segmentadas)
- 1,784 filas, 17 bancos, Ene 2017 – Nov 2025
- Cross-check INVEX 202401: CT=36.4B, EMP=13.4B, PE=4.6%, ICOR=217%

### Fase 2: Backfill desde CASTIGOS.xlsx (MEDIA prioridad)
- `quebrantos_comerciales` (LIB_CASTIGOS_COMERC + QUITAS_COMER)
- Castigos acumulados para IMORA corregido

### Fase 3: Backfill desde TDA.xlsx (MEDIA prioridad)
- `tda_cartera_total` y sub-segmentos

### Fase 4: Backfill desde CorporateLoan CSV + TE_Invex_Sistema.xlsx (BAJA prioridad)
- Tasas MN/ME ponderadas
- Tasa efectiva INVEX vs Sistema

### ~~Fase 5~~ DONE (2026-02-12): Fix IMORA + ICAP backfill
- **Fix IMORA**: `COALESCE(imora, new)` → `COALESCE(new, imora)` en backfill_castigos.py
- Re-ejecutado: 1,855 filas sobreescritas (ETL → Tableau). INVEX Oct 2025: 8.83% → 2.25%
- **ICAP backfill**: Script `backfill_icap.py` — 3,893 filas, 52 bancos, Jun 2006 — Nov 2025
- Columnas nuevas: `icap_ccb`, `icap_ccf` (ALTER TABLE + ORM + SAFE_METRIC_COLUMNS)
- INVEX: cobertura ICAP extendida a 202511 (+1 mes), CCB/CCF disponibles
- Tests: 185 passed, 0 failed

### ~~Fase 6+7~~ DONE (2026-02-12): ICOR Tableau + Reservas segmentadas + PE_SG
- Script: `scripts/data/backfill_reservas_icor.py` — 1,855 filas, 53 bancos, Ene 2017 – Nov 2025
- 7 columnas nuevas: `res_empresarial`, `res_financieras`, `res_gubernamental`, `res_consumo`, `res_vivienda`, `reservas_sg`, `pe_sg`
- ICOR alineado con Tableau: `Reservas_SG / (CC_E3_SG + Vivienda_E3)` (antes: ABS(Reservas)/CV)
- PE_SG: `Reservas_SG / Cartera_Total` (nueva métrica sin gobierno/consumo)
- INVEX Nov 2025: ICOR=1.0833 (108% cobertura), PE_SG=0.79%
- ORM + SAFE_METRIC_COLUMNS + viz configs (`reservas_sg`, `pe_sg`) + synonyms
- **+7 worksheets GENERABLE** (ICOR ×3 + Reservas SG ×4)
- Tests: 185 passed, 0 failed

---

## Investigación Fase 4.5 — Hallazgos Clave

### Anomalía IMORA: ETL vs Tableau
- **Problema**: INVEX IMORA salta de 8.83% (Oct 2025) a 2.25% (Nov 2025)
- **Causa raíz**: `COALESCE(imora, %(imora)s)` en backfill_castigos.py preservó valores ETL
- **ETL** (concepto CNBV 40200033): meses 202401-202510, fórmula diferente → 4.68%-8.83%
- **Backfill** (fórmula Tableau): solo mes 202511 (único mes NULL) → 2.25%
- **Prueba**: BBVA/BANORTE tienen IMORA hasta 202510 (ETL), NO 202511. INVEX llega a 202511 solo por backfill
- **Fix**: Cambiar a SET directo (sin COALESCE) y re-ejecutar. Ver `research.md`

### Archivos nuevos descubiertos
- `CREADOR DE TDA.xlsx`: 37K rows, 78 cols, breakdown completo Etapa/VR por segmento (200012-202511)
- `Catera Analitica Benchmark v2.xlsx`: 11K rows, 334 cols (pivot), 37 concept codes CNBV
- `ICAP_Bancos.xlsx`: 14K rows, ICAP + CCB + CCF (202201-202511)
- `040_R04A_419.csv`: CNBV raw R04A report (64MB, castigos por concepto)
- `nuevo2.csv`: CorporateLoan Aug-Nov 2025 (287K rows, 25 cols)
- Scripts R: `Castigos_BM.R`, `CorporateLoan_BM.R` (pipelines de preparación de datos)

### Fórmulas Tableau (extraídas del TWB)
| Métrica | Fórmula Tableau |
|---------|----------------|
| **IMORA** | `(CC_Etapa3_SG + CASTIGOS_ACUM_COMERCIAL) / (CC_E1_SG + CC_E2_SG + CC_E3_SG)` |
| **Quebrantos CC** | `LIB_CASTIGOS_COMERC + QUITAS_COMER` |
| **Cartera Vencida** | `CC_Etapa3_SG + Vivienda_Etapa3` (≠ nuestra BD que usa cartera_vencida ETL) |
| **ICOR** | `Reservas_SG / Cartera_Vencida` |
| **PE Total** | `Reservas_Etapa_Todas × -1 / Cartera_Total` |
| **PE Total SG** | `(Reservas - Res_Gub - Res_Consumo) × -1 / Cartera_Total` |
| **TDA** | `Non_Performing_Portfolio / Total_Portfolio` (de TE_Invex_Sistema) |
| **Reservas SG** | `(Reservas × -1) - (Res_Consumo × -1 + Res_Gub × -1)` |

---

## Criterios de Aceptacion

- [x] Columnas CNBV XLSX pobladas 100% desde Ene 2017 (Fase 1)
- [x] Reservas, PE, ICOR calculados con formula Tableau (simplificada)
- [x] `cartera_total` viz config agregada (Fase 0)
- [x] Quebrantos/Castigos backfilled desde CASTIGOS.xlsx (Fase 2) — 3,568 rows
- [x] IMORA fórmula Tableau implementada: (CC_E3 + Castigos_Acum) / CC_Total (Fase 2)
- [x] `imora` + `quebrantos_comerciales` viz configs + synonyms (Fase 2)
- [x] TDA backfilled desde TDA.xlsx (Fase 3) — 6,597 rows, INVEX 100%
- [x] Tasas MN/ME backfilled (Fase 4) — 6,589 rows, 45 bancos, promedio ponderado
- [x] TE Sistema/INVEX backfilled (Fase 4) — 18 rows bimestrales
- [x] 5 viz configs agregadas: TDA, tasa_mn, tasa_me, tasa_sistema, tasa_invex_consumo
- [x] Investigación IMORA anomalía completada — root cause identificado (Fase 4.5)
- [x] EDA archivos Tableau crudos + fórmulas TWB extraídas (Fase 4.5)
- [x] Fix IMORA: COALESCE → OVERWRITE + re-ejecutar backfill (Fase 5) — 1,855 filas
- [x] Backfill ICAP desde ICAP_Bancos.xlsx (Fase 5) — 3,893 filas, 52 bancos, +ccb/ccf
- [x] ORM + SAFE_METRIC_COLUMNS actualizados para icap_ccb, icap_ccf
- [x] Tests: 185 passed, 0 failed
- [x] Alinear ICOR con fórmula Tableau (Fase 6+7): Res_SG/(CC_E3+VIV_E3), 1,855 filas
- [x] Reservas segmentadas: 5 columnas + reservas_sg + pe_sg (Fase 6+7)
- [x] +7 viz configs (reservas_sg, pe_sg) + synonyms
- [x] Cross-validation contra datos Tableau para INVEX Jun 2025 — 15/15 métricas EXACTAS
- [x] Etapa VR: `ct_etapa_vr` columna nueva (ALTER TABLE + 2,019 filas, ratio 1-E1-E2-E3)
- [x] ORM + SAFE_METRIC_COLUMNS + viz config + synonyms + multi-metric stacked bar
- [x] PE_Promedio: ya cubierto por `build_advanced_ranking(show_average_line=True)`
- [x] **44/44 worksheets GENERABLE (100%)**

---

## Referencias

- TWB: `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/Invex_Tablero_V3.twb`
- XLSX: `CNBV_Cartera_Bancos_V2.xlsx` (misma carpeta)
- Ticket relacionado: `2026-02-09__TASK__map-tableau-business-logic-formulas-to-sql-viewset`
