# Research: Tableau Gap Analysis

**Fecha:** 2026-02-12

---

## 1. EDA: Columnas 35-39 del CNBV XLSX

Script: `scripts/data/eda_xlsx_cols_35_39.py`

### Headers descubiertos

| Col | Header XLSX | Cobertura |
|-----|-------------|-----------|
| 34 | Reservas Etapa todas | 100% (12,096/12,097) |
| 35 | Res Actividad Empresarial o Comercial Etapa todas | 99.9% |
| 36 | Res Entidades Financieras Etapa todas | 99.9% |
| 37 | Res Entidades Gubernamentales Etapa todas | 99.9% |
| 38 | Res Creditos de Consumo Etapa todas | 100% |
| 39 | Res Creditos a la Vivienda Etapa todas | 99.9% |

### Valores de muestra INVEX (201701)

```
{34: -657.946616, 35: -349.540418, 36: -14.394543, 37: 0, 38: -284.801786, 39: -0.149469}
```

### Observaciones

1. **Signo negativo**: Reservas en XLSX son negativas (convencion contable). Para ICOR y PE se necesita negar.
2. **INVEX tiene 0 gubernamental**: `col 37 = 0` en todas las muestras. Consistente con perfil fiduciario/inversion de INVEX.
3. **Reservas segmentadas disponibles**: Cols 35-39 permiten calcular Reservas SG (Sin Gobierno) para ICOR exacto y PE SG.
4. **Formula ICOR Tableau**: `Reservas_SG / Cartera_Vencida` donde `Reservas_SG = Reservas_Todas - Res_Consumo - Res_Gubernamentales`.

---

## 2. Cobertura BD post-Fase 1 (INVEX, 300 filas)

| Columna | Cobertura | Status |
|---------|-----------|--------|
| cartera_total | 300 (100%) | OK |
| cartera_comercial_total | 300 (100%) | OK |
| cartera_consumo_total | 300 (100%) | OK |
| cartera_vivienda_total | 262 (87%) | OK |
| cartera_vencida | 299 (99.7%) | OK |
| imor | 299 (99.7%) | OK |
| imora | 263 (87.7%) | OK |
| empresarial_total | 107 (35.7%) | Backfilled Fase 1 |
| entidades_financieras_total | 107 (35.7%) | Backfilled Fase 1 |
| entidades_gubernamentales_total | 27 (9%) | INVEX=0 en la mayoria |
| cartera_comercial_sin_gob | 107 (35.7%) | Backfilled Fase 1 |
| reservas_etapa_todas | 107 (35.7%) | Backfilled Fase 1 |
| ct_etapa_1 | 107 (35.7%) | Backfilled Fase 1 |
| ct_etapa_2 | 47 (15.7%) | Muchos meses E2=0 para INVEX |
| ct_etapa_3 | 107 (35.7%) | Backfilled Fase 1 |
| pe_total | 107 (35.7%) | Backfilled Fase 1 |
| icor | 106 (35.3%) | Backfilled Fase 1 |
| icap_total | 238 (79.3%) | ETL original |
| quebrantos_comerciales | 106 (35.3%) | Pendiente Fase 2 |
| tda_cartera_total | 46 (15.3%) | Pendiente Fase 3 |
| tasa_mn | 53 (17.7%) | Pendiente Fase 4 |
| tasa_me | 53 (17.7%) | Pendiente Fase 4 |
| tasa_sistema | 18 (6%) | Pendiente Fase 4 |

### Techo del 35.7%

El XLSX cubre Ene 2017 - Nov 2025 (107 meses). La BD tiene 300 filas para INVEX (desde ~2000). Las 193 filas pre-2017 no tienen fuente conocida. Los dashboards Tableau tambien usan datos desde 2017, asi que la cobertura es 100% dentro del rango relevante.

---

## 3. Cross-check INVEX Ene 2024

| Campo | Valor BD | Unidad |
|-------|----------|--------|
| cartera_total | 36,410,974,308 | pesos |
| empresarial_total | 13,415,742,253 | pesos |
| entidades_financieras_total | 1,454,866,360 | pesos |
| entidades_gubernamentales_total | 0 | pesos |
| cartera_comercial_sin_gob | 14,870,608,613 | pesos |
| reservas_etapa_todas | -1,683,594,868 | pesos (negativo) |
| ct_etapa_1 | 0.9628 | ratio (96.3%) |
| ct_etapa_2 | 0.0158 | ratio (1.6%) |
| ct_etapa_3 | 0.0213 | ratio (2.1%) |
| pe_total | 0.0462 | ratio (4.6%) |
| icor | 2.1701 | ratio (217%) |

### Verificaciones de integridad

- `emp + efin = cc_sin_gob`: 13,415,742,253 + 1,454,866,360 = 14,870,608,613 MATCH
- `e1 + e2 + e3 ~ 1.0`: 0.9628 + 0.0158 + 0.0213 = 0.9999 (VR = 0.0001)
- `pe = -reservas / ct`: 1,683,594,868 / 36,410,974,308 = 0.0462 MATCH
- `icor = |reservas| / cv`: 1,683,594,868 / 775,807,250 = 2.1701 MATCH

---

## 4. Fuentes de datos pendientes (archivos disponibles)

| Archivo | Ubicacion | Columnas target |
|---------|-----------|----------------|
| CASTIGOS.xlsx | `drive-download-20260212T024209Z-1-001/` | quebrantos_comerciales, castigos_acum |
| Castigos Comerciales.xlsx | idem | quitas_comer, lib_castigos_comerc |
| TDA.xlsx | idem | tda_cartera_total, tda_por_segmento |
| CorporateLoan_CNBVDB.csv | idem (confirmado) | tasa_mn, tasa_me |
| TE_Invex_Sistema.xlsx | `tableau_extract/Data/INVEX ANALITICS/` | tasa_sistema, tasa_invex_consumo |
| ICAP_Bancos.xlsx | idem | icap_total (ya 79% cargado) |

---

## 5. EDA: TDA.xlsx (Fase 3)

### Estructura

| Col | Header | Tipo |
|-----|--------|------|
| 0 | cve_periodo | int (YYYYMM) |
| 1 | Año | str |
| 2 | Mes | str |
| 3 | Fecha | str (MM/DD/YYYY) |
| 4 | cve_institucion | str (CNBV code, e.g. "040059") |
| 5 | TDA Cartera total | float (porcentaje, e.g. 4.09 = 4.09%) |

### Cobertura

- **Filas**: 17,494
- **Instituciones**: 145 (todas usan códigos CNBV)
- **Periodo**: Dic 2000 — Dic 2025 (301 meses)
- **Densidad**: ~97% completa (17,494 / 145×301 = 39.8% — muchas instituciones no existían en 2000)

### Muestra INVEX 202401

- XLSX: `tda_cartera_total = 4.094268` (4.09%)
- BD: `tda_cartera_total = 0.0000` (cero — ETL cargó zeros, NO datos reales)

### Hallazgo: TDA existente en BD son todos CEROS para INVEX

INVEX tiene 46 filas con TDA = 0.000000 y 254 filas con TDA = NULL.
Los 46 ceros **no son datos válidos** — el ETL original cargó zeros.
BBVA sí tiene valores reales (ej: 202410 = 1.67%).

### Implicación para el backfill

- **NO usar COALESCE**: los ceros existentes deben sobreescribirse
- Usar `WHERE tda_cartera_total IS NULL OR tda_cartera_total = 0`
- TDA.xlsx cubre 301 meses vs 300 en BD → cobertura prácticamente total para INVEX

---

## 6. Anomalía IMORA: Root Cause Analysis (Fase 4.5)

### Síntoma

INVEX IMORA salta de **8.83%** (Oct 2025) a **2.25%** (Nov 2025) — caída de 6.6 puntos porcentuales.

### Datos observados

```
periodo_id | imora_pct | castigos_acum | imor_pct | cc_total_mdp | cv_mdp
202508     |    8.4457 |          0.00 |   2.3553 |    16,204.19 | 1,162.09
202509     |    8.5100 |          0.00 |   2.2511 |    15,956.69 | 1,120.01
202510     |    8.8343 |          0.00 |   2.3807 |    16,402.59 | 1,204.83
202511     |    2.2464 |          0.00 |     NULL |    16,402.59 |     NULL
```

**Oct y Nov 2025 tienen datos de cartera idénticos** (16,402.59 MDP) — Nov es copia de Oct en el CNBV XLSX (datos no publicados aún).

### Causa raíz: Mezcla de dos fuentes con fórmulas distintas

**Fuente 1 — ETL (concepto CNBV 40200033):**
- Pobló `imora` para meses 200312-202510 (264 meses para INVEX)
- Fórmula oficial CNBV: incluye componentes que nuestra reconstrucción no captura
- Valores: 4.68% (Ene 2024) → 8.83% (Oct 2025) — tendencia creciente

**Fuente 2 — backfill_castigos.py (fórmula Tableau):**
- Fórmula: `(CC_E3_SG + Castigos_Acum_Comercial) / (CC_E1_SG + CC_E2_SG + CC_E3_SG)`
- Para INVEX: castigos_acum = 0, así que IMORA ≈ CC_E3 / CC_total_sin_VR
- Valor calculado: ~2.25% para Oct y Nov 2025

### Evidencia definitiva

```
-- BBVA y BANORTE: IMORA hasta Oct 2025 (ETL), NO Nov 2025
-- INVEX llega a Nov 2025 solo porque el backfill escribió donde era NULL

banco_norm | imora_pct | periodo_id
BANORTE    |    3.0646 |     202510   -- ETL (último mes procesado)
BBVA       |    4.4027 |     202510   -- ETL (último mes procesado)
INVEX      |    8.8343 |     202510   -- ETL preservado por COALESCE
INVEX      |    2.2464 |     202511   -- Backfill (único mes con IMORA NULL)
```

### Código que causó la mezcla

`scripts/data/backfill_castigos.py` líneas 403-411:

```python
cur.execute("""
    UPDATE bank_fact_kpis_mensual
    SET quebrantos_comerciales = COALESCE(quebrantos_comerciales, %(q)s),
        castigos_acum_comercial = COALESCE(castigos_acum_comercial, %(a)s),
        imora = COALESCE(imora, %(imora)s)     -- PRESERVA valor ETL existente
    WHERE banco_norm = %(banco)s AND periodo_id = %(periodo)s
      AND (quebrantos_comerciales IS NULL
           OR castigos_acum_comercial IS NULL
           OR imora IS NULL)
""")
```

`COALESCE(imora, nuevo_valor)` retorna el existente cuando no es NULL:
- Oct 2025: `imora` ya existía (ETL = 8.83%) → COALESCE lo preservó
- Nov 2025: `imora` era NULL → COALESCE escribió el valor backfill (2.25%)

### Decisión

**Archivos Tableau = source of truth.** Cambiar COALESCE → SET directo y re-ejecutar.

---

## 7. Fórmulas Tableau (extraídas del TWB)

Fuente: `tableau_extract/Invex_Tablero_V3.twb` (XML, 3.5 MB)

### Métricas principales

| Métrica | Fórmula Tableau | Notas |
|---------|----------------|-------|
| **IMORA** | `(CC_E3_SG + CASTIGOS_ACUM_COMERCIAL) / (CC_E1_SG + CC_E2_SG + CC_E3_SG)` | SG = Sin Gobierno = Empresarial + Ent.Financieras |
| **Quebrantos CC** | `LIB_CASTIGOS_COMERC + QUITAS_COMER` | De CASTIGOS.xlsx |
| **Castigos Acumulados** | `RUNNING_SUM(SUM(LIB_CASTIGOS_COMERC))` | Table calculation (running sum por filas) |
| **Cartera Vencida** | `CC_E3_SG + Vivienda_E3` | Excluye consumo y gobierno |
| **ICOR** | `Reservas_SG / Cartera_Vencida` | Reservas SG = Reservas - Consumo - Gobierno |
| **PE Total** | `Reservas_Etapa_Todas × -1 / Cartera_Total` | — |
| **PE Total SG** | `(Reservas - Res_Gub - Res_Consumo) × -1 / Cartera_Total` | — |
| **TDA** | `Non_Performing_Portfolio / Total_Portfolio` | De TE_Invex_Sistema.xlsx |
| **Reservas SG** | `(Reservas × -1) - (Res_Consumo × -1 + Res_Gub × -1)` | — |
| **CT_Etapa_X** | `(Comercial_EX + Consumo_EX + Vivienda_EX) / Cartera_Total` | Comercial INCLUYE gobierno |

### Campos filtrados por banco

```
IMORA_Invex = IF DESCRIPCION = 'INVEX' THEN IMORA ELSE NULL END
Quebrantos_Invex = IF institucion = '040059' THEN Quebrantos_CC ELSE 0 END
Invex_Cartera_Comercial = IF DESCRIPCION = 'INVEX' THEN CC_Total ELSE 0 END
ICOR_Invex = IF DESCRIPCION = 'INVEX' THEN ICOR ELSE 0 END
```

### Etapas (definiciones SG vs con Gobierno)

| Nombre TWB | Incluye Gobierno | Uso |
|------------|-----------------|-----|
| Comercial Etapa X **SG** | No | IMORA, Cartera Vencida |
| Comercial Etapa X (sin sufijo) | Sí | CT_Etapa ratios |
| Cartera Comercial **SG** | No | Dashboard CC_sg |
| Cartera Comercial Total | Sí | Dashboard CC |

### Data Sources en el TWB

| Datasource | Archivos | Conexión |
|---|---|---|
| `Sheet1+ (Varias conexiones)` | CNBV_Cartera_Bancos_V2.xlsx + Instituciones.xlsx + CASTIGOS.xlsx + Castigos Comerciales.xlsx | JOIN por CLAVE/institucion |
| `CorporateLoan_CNBVDB.csv+` | CorporateLoan_CNBVDB.csv | Directa |
| `TDA` | TDA.xlsx + Instituciones.xlsx | JOIN por cve_institucion |
| `ICAP Bancos` | ICAP_Bancos.xlsx | Directa |
| `TE_Invex_Sistema` | TE_Invex_Sistema.xlsx | Directa |

---

## 8. Discrepancias de Fórmulas: ETL vs Tableau

### IMORA

| Componente | ETL (concepto 40200033) | Tableau (TWB) | Backfill actual |
|---|---|---|---|
| Numerador | Fórmula CNBV oficial (opaca) | CC_E3_SG + Castigos_Acum | CC_E3_SG + Castigos_Acum |
| Denominador | Fórmula CNBV oficial | CC_E1_SG + CC_E2_SG + CC_E3_SG | CC_E1_SG + CC_E2_SG + CC_E3_SG |
| Incluye gobierno? | Desconocido | **Excluye** (SG) | **Excluye** (SG) |
| Incluye VR? | Desconocido | **Excluye** | **Excluye** |
| Rango de valores | ~4-9% (INVEX 2024-2025) | ~2-3% (INVEX 2024-2025) | Coincide con Tableau |

**Conclusión**: Backfill implementa correctamente la fórmula Tableau. Los valores ETL usan una fórmula diferente (concepto CNBV oficial).

### Cartera Vencida

| | ETL | Tableau |
|---|---|---|
| Definición | Concepto CNBV genérico | CC_E3_SG + Vivienda_E3 |
| Incluye consumo | Sí (probablemente) | **No** |
| Incluye gobierno | Sí (probablemente) | **No** |

**Impacto**: La `cartera_vencida` de BD puede diferir de Tableau. Necesita investigación adicional.

### ICOR

| | Backfill actual (Fase 1) | Tableau |
|---|---|---|
| Numerador | `ABS(reservas_etapa_todas)` | `Reservas_SG` (excluye consumo + gobierno) |
| Denominador | `cartera_vencida` (ETL) | `CC_E3_SG + Vivienda_E3` |

**Impacto**: ICOR actual usa reservas totales y CV del ETL. Tableau usa reservas SG y su propia CV. Discrepancia significativa.

---

## 9. EDA: Archivos Crudos Nuevos (Fase 4.5)

### Inventario completo del drive

| Archivo | Tamaño | Rows | Cols | Periodos | Instituciones | Notas |
|---------|--------|------|------|----------|---------------|-------|
| CNBV_Cartera_Bancos_V2.xlsx | 3.4 MB | 12,097 | 36 | 201701-202511 | 48 | Base principal |
| CASTIGOS.xlsx | 450 KB | 2,142 | ~12 | 202201-202511 | 46 | Castigos por tipo |
| Castigos Comerciales.xlsx | 56 KB | 2,208 | 3 | 202201-202511 | ~46 | Acumulados |
| TDA.xlsx | 649 KB | 17,494 | 6 | 200012-202512 | 145 | Solo TDA Total (v2 perdió segmentos) |
| ICAP_Bancos.xlsx | 480 KB | 14,275 | 6 | 202201-202511 | ~77 | ICAP + CCB + CCF |
| CorporateLoan_CNBVDB.csv | 270 MB | 1.67M | 25 | 201606-202511 | 48 | Granular |
| **CREADOR DE TDA.xlsx** | **23 MB** | **37,165** | **78** | **200012-202511** | **135** | **Breakdown completo E1/E2/E3/VR** |
| **Catera Analitica Benchmark v2.xlsx** | **49 MB** | **~11,764** | **334** | **201701-202512** | **137** | **Pivot: 37 concept codes** |
| **040_R04A_419.csv** | **64 MB** | — | — | 202512 | — | **CNBV R04A raw** |
| **nuevo2.csv** | **42 MB** | **287,050** | **25** | Aug-Nov 2025 | ~48 | CorporateLoan reciente |
| QUEBRANTOS.csv | 2.3 KB | 46 | 3 | Snapshot | 46 | Resumen single period |
| TASAS DATOS.csv | 1.9 KB | 24 | 3 | Snapshot | 12 | Peer comparison |
| TE_Invex_Sistema.xlsx | 9 KB | 18 | 3 | 201910-202208 | 1 | Solo en extract viejo |
| Instituciones.xlsx | 11 KB | ~77 | 2 | — | 77 | Lookup CLAVE→DESCRIPCION |

### CREADOR DE TDA.xlsx — La fuente más rica

- **Sheet "BD TDA"**: 37,161 rows × 78 columns
- Breakdown: E1/E2/E3/VR/TOT para cada segmento de crédito
- Segmentos: Cartera de Crédito, Comerciales, Empresarial, Ent.Financieras, Ent.Gubernamentales, Consumo (Tarjeta, Personales, Nómina, Automotriz, Arrendamiento, Otros), Vivienda, ABCD
- **25 años de historia** (Dic 2000 — Nov 2025), 135 instituciones
- Potencialmente reemplaza CNBV_Cartera_Bancos_V2.xlsx como fuente principal

### ICAP_Bancos.xlsx — Datos complementarios

- 14,275 rows, 77 bancos, Ene 2022 — Nov 2025
- Columnas: `Cve_Inst`, `Banco`, `FECHA`, `ICAP Total`, `CCB`, `CCF`
- CCB = Capital Contable Básico, CCF = Capital Complementario/Fundamental
- Backfill potencial: ampliar cobertura ICAP + nuevas métricas CCB/CCF

### Scripts R — Pipelines de preparación

- **Castigos_BM.R**: Lee `040_R04A_419.csv`, filtra periodo 202512, pivota concepto×institución, /1M (MDP). 13 concept codes de castigos.
- **CorporateLoan_BM.R**: Combina 2 CSVs, limpia columnas, calcula Etapa1 = Cartera_vigente, Etapa3 = Cartera_vencida. Genera `nuevo2.csv`.

---

## 10. Comparativa: Archivos Viejos (Aug 2024) vs Nuevos (Feb 2025)

| Archivo | Viejo (rows) | Nuevo (rows) | Viejo (periodos) | Nuevo (periodos) | Delta |
|---------|-------------|-------------|-------------------|-------------------|-------|
| CASTIGOS.xlsx | 1,362 | 2,142 | 202201-202406 | 202201-202511 | +780 rows, +17 meses |
| CNBV_Cartera_Bancos_V2.xlsx | 11,108 | 12,097 | 201701-202406 | 201701-202511 | +989 rows, +17 meses |
| Castigos Comerciales.xlsx | 1,380 | 2,208 | — | — | +828 rows |
| ICAP_Bancos.xlsx | 13,148 | 14,274 | — | — | +1,126 rows |
| TDA.xlsx | 16,674 | 17,494 | 200012-202406 | 200012-202512 | +820 rows, +13 meses |
| CorporateLoan_CNBVDB.csv | 82 MB | 270 MB | — | — | 3× más grande |

### Cambios estructurales

| Archivo | Cambio |
|---------|--------|
| **TDA.xlsx** | **Breaking**: Viejo = 18 cols (TDA por segmento). Nuevo = 6 cols (solo TDA Total). Usar `CREADOR DE TDA.xlsx` para granularidad |
| ICAP_Bancos.xlsx | Nuevo agrega sheet `Hoja1` (lookup 77 bancos) |
| Demás | Extensión pura, headers idénticos |

### Archivos exclusivos

| Solo en ROOT (nuevo) | Solo en EXTRACT (viejo) |
|---|---|
| CREADOR DE TDA.xlsx (23 MB) | TE_Invex_Sistema.xlsx (9 KB) |
| Catera Analitica Benchmark v2.xlsx (49 MB) | |
| 040_R04A_419.csv (64 MB) | |
| nuevo2.csv (42 MB) | |
| QUEBRANTOS.csv, TASAS DATOS.csv | |
| Castigos_BM.R, CorporateLoan_BM.R | |

---

## 11. Fase 5: Fix IMORA + ICAP Backfill (DONE)

### Fix IMORA — COALESCE → OVERWRITE

**Cambio** en `backfill_castigos.py` líneas 403-407:
```python
# ANTES (preserva ETL)
SET imora = COALESCE(imora, %(imora)s)

# DESPUÉS (Tableau prevalece)
SET imora = COALESCE(%(imora)s, imora)
```

**Resultado**: 1,855 filas afectadas. INVEX Oct 2025: 8.83% → 2.25% (consistente con Nov).

También se refactorizó `main()` para que `--dry-run` no requiera `DATABASE_URL`.

### ICAP Backfill — `scripts/data/backfill_icap.py`

**Fuente**: ICAP_Bancos.xlsx (14,275 rows, 77 bancos, Jun 2006 — Nov 2025)

**Columnas escritas**:
- `icap_total`: OVERWRITE (XLSX prevalece sobre ETL)
- `icap_ccb`: **NUEVA** (ALTER TABLE) — Capital Contable Básico
- `icap_ccf`: **NUEVA** (ALTER TABLE) — Capital Complementario/Fundamental

**Nota formato**: ICAP en BD se almacena como porcentaje directo (15.2 = 15.2%), no como ratio. El XLSX usa el mismo formato → sin conversión.

**Resultado**: 3,893 filas afectadas, 52 bancos. INVEX extendido a 202511.

**Verificación INVEX últimos meses**:
```
202509: ICAP=15.76%, CCB=15.76%, CCF=15.76%
202510: ICAP=15.97%, CCB=15.97%, CCF=15.97%
202511: ICAP=15.74%, CCB=15.74%, CCF=15.74%
```

**Cambios en código**:
- `kpi.py`: +2 columnas (`icap_ccb`, `icap_ccf`)
- `analytics_service.py`: +2 entradas en SAFE_METRIC_COLUMNS
- Tests: 185 passed, 0 failed

---

## 12. Recomendaciones — Próximos Pasos

### Fase 6: Alineación ICOR con Tableau (prioridad MEDIA)

1. Recalcular `icor` con fórmula Tableau: `Reservas_SG / (CC_E3_SG + Vivienda_E3)`
2. Requiere reservas segmentadas (cols 35-39 CNBV XLSX ya disponibles)
3. Requiere recalcular `cartera_vencida` con definición Tableau

### Fase 7: Reservas segmentadas + PE SG (prioridad MEDIA)

1. Agregar columnas: `res_empresarial`, `res_consumo`, `res_vivienda`, `res_gubernamental`
2. Calcular `reservas_sg = reservas_todas - res_consumo - res_gubernamental`
3. Calcular `pe_sg = reservas_sg * -1 / cartera_total`
4. Desbloquea 3 worksheets SIN HANDLER (Reservas SG)

### Fase 8: Ampliación de cobertura (prioridad BAJA)

1. CREADOR DE TDA.xlsx como fuente alternativa (25 años vs 9 años, 78 cols)
2. 040_R04A_419.csv para castigos detallados por concepto CNBV
3. nuevo2.csv para CorporateLoan reciente (Aug-Nov 2025)
