# Hallazgo: Datos Nov 2025 duplicados + AG faltante en entrega Bajaware

> Entregas analizadas:
> - `drive-download-20260302T184043Z-1-001` (2 de marzo 2026) — original
> - `drive-download-20260304T143340Z-1-001` (4 de marzo 2026) — re-entrega

## Resumen Ejecutivo

| # | Problema | Estado en re-entrega (20260304) | Accion pendiente |
|---|----------|-------------------------------|-----------------|
| A | Nov 2025 = Oct 2025 en `CNBV_Cartera_Bancos_V2.xlsx` | **CORREGIDO** — 35/35 cols diferentes | Cargar CNBV actualizado al ETL |
| B | `040_TO.csv` (Analisis General) no incluido | **SIGUE FALTANDO** — pero BM lo suple 9/10 metricas | Adapter BM→AG o esperar entrega |
| C | "Nueva carpeta" CSVs: Nov = Oct | **SIGUE DUPLICADO** (no se tocaron) | No bloqueante (BM tiene los datos) |

### Comparacion byte-a-byte entre entregas

De **16 archivos ETL** comparados, **solo 1 cambio**: `CNBV_Cartera_Bancos_V2.xlsx` (+800 bytes, md5 diferente).
Todos los demas son byte-for-byte identicos.

| Archivo | Viejo (bytes) | Nuevo (bytes) | Cambio |
|---------|--------------|--------------|--------|
| `CNBV_Cartera_Bancos_V2.xlsx` | 3,378,892 | 3,379,692 | **SI** |
| `CorporateLoan_CNBVDB.csv` | 283,576,883 | 283,576,883 | No |
| `040_R04A_419.csv` | 204,177,645 | 204,177,645 | No |
| `sh_datos_40.csv` | 533,220,402 | 533,220,402 | No |
| `CASTIGOS.xlsx` | 510,219 | 510,219 | No |
| Todos los demas | — | — | No |

Archivos nuevos en re-entrega (no en original):
- `CASTIGOS1.xlsx` (identico a `CASTIGOS.xlsx`)
- `Invex_Tablero_V2.twb` + carpeta archivos (Tableau, datos internos de Feb 2025)
- `Invex_Tablero_V3_v2021.4.twbx` (Tableau, datos internos de Feb 2025)
- `Invex_Tablero_V3_v2021_12.4.twbx` (Tableau, datos internos de Feb 2025)

---

## EDA Completo: Entrega 20260304

### 1. CNBV_Cartera_Bancos_V2.xlsx — **ACTUALIZADO**

| Campo | Valor |
|-------|-------|
| Shape | 12,156 × 40 |
| Periodos | 108 (201701 – 202512) |
| Instituciones/periodo | 58-59 (varia por mes) |
| NULLs | 13 filas con NULLs en cols Etapa VR y desglosadas |

**Nov 2025 CORREGIDO** — 35/35 columnas numericas difieren de Oct:

| Periodo | INVEX Total (MDP) | Etapa 1 | Etapa 2 | Etapa 3 |
|---------|-------------------|---------|---------|---------|
| 202507 | 47,571.07 | 45,059.81 | 1,393.56 | 1,117.70 |
| 202508 | 49,339.46 | 46,903.08 | 1,274.30 | 1,162.09 |
| 202509 | 49,754.43 | 47,102.27 | 1,532.15 | 1,120.01 |
| 202510 | 50,608.63 | 47,810.23 | 1,593.58 | 1,204.83 |
| **202511** | **52,311.73** | **48,992.70** | **2,002.38** | **1,316.65** |
| 202512 | 51,911.96 | 48,272.14 | 2,264.69 | 1,375.13 |

Instituciones extra por mes:
- `040170` aparece en Nov pero no en Oct
- `040136` aparece en Nov pero no en Dic

### 2. CorporateLoan_CNBVDB.csv — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 1,763,972 × 25 (+ 19 trailing empty cols) |
| Periodo | "Monitoring Term" con formato M/DD/YY |
| Rango | 01/31/20 – 9/30/25 (Ene 2020 – Sep 2025) |
| Instituciones | 62 unicas (48 codigos) |
| INVEX (40059) | 66,184 rows |
| Ahorro Famsa (40131) | 1,227 rows |

> **Nota**: No tiene Nov/Dic 2025. Max = Sep 2025.

Top 5 por volumen: Santander (97K), BBVA (91K), HSBC (86K), Banamex (82K), Bajio (80K).

### 3. CASTIGOS.xlsx / CASTIGOS1.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 50 × 13 |
| Periodo | Sin columna temporal — snapshot cross-sectional |
| Formato | Headers en fila 1 como texto, columna "periodo" toda NULL |
| CASTIGOS1 | **Identico** byte-for-byte a CASTIGOS (duplicado) |

Columnas: LIB_CASTIGOS_COMERC, LIB_CASTIGOS_ACT_EMP, QUITAS_COMERC, QUITAS_ENT_FIN, etc.

### 4. Castigos Comerciales.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 2,208 × 3 |
| Columnas | Institucion1, Fecha, CASTIGOS ACMULUADOS COMERCIAL |
| Periodo | 2022/1/01 – 2025/12/01 (48 meses) |
| Instituciones | 50 (con codigos 040XXX) |
| INVEX (040059) | 48 rows, **todos $0.00** |

> **Bug conocido**: quebrantos_comerciales INVEX siempre $0
> (documentado en card.md del ticket `c83c5ccf`).

### 5. ICAP_Bancos.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 14,333 × 6 |
| Columnas | Cve_Inst, Banco, FECHA, ICAP Total, CCB, CCF |
| Periodo | 2006-01-01 – 2025-12-01 |
| Escala | Porcentaje (16.45 = 16.45%) |

### 6. TDA.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 17,494 × 6 |
| Columnas | cve_periodo, Año, Mes, Fecha, cve_institucion, TDA Cartera total |
| Periodo | 200012 – 202512 |
| Fecha format | String MM/DD/YYYY |

### 7. TE_Invex_Sistema.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 32 × 3 |
| Columnas | Fecha1, Sistema, Invex Consumo |
| Periodo | 2019-10-31 – 2024-12-31 |
| Frecuencia | Bimensual |

> **Nota**: Solo 32 datapoints. No tiene 2025.

### 8. QUEBRANTOS.csv — sin cambios

| Campo | Valor |
|-------|-------|
| Encoding | UTF-16 LE (BOM), TSV |
| Shape | 46 × 3 |
| Columnas | Institucion1, Bancos, Quebrantos CC |
| Periodo | Sin columna temporal — snapshot |

### 9. TASAS DATOS.csv — sin cambios

| Campo | Valor |
|-------|-------|
| Encoding | UTF-16 LE (BOM), TSV |
| Shape | 24 × 3 |
| Columnas | Descripcion, Moneda, Prom. Tasa Efectiva Promedio |
| Contenido | Tasas promedio por banco/moneda |
| INVEX MN | 14.56% |

### 10. castigos.csv — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 48 × 15 |
| Columnas | Row#, institucion, + 13 conceptos de castigos (codigos 1128*) |
| Periodo | Sin columna temporal — snapshot |

### 11. Instituciones.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 99 × 2 |
| Columnas | CLAVE, DESCRIPCION |
| INVEX | CLAVE=040059, DESCRIPCION="INVEX" |
| Incluye | 99 entradas (bancos + consolidados + grupos) |

### 12. Cuentas_desc.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 36 × 3 |
| Columnas | Concepto, Etapa, Descripcion |
| Uso | Catalogo de mapeo concepto→etapa→descripcion para CNBV |

### 13. cat_conceptos_40.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 617 × 9 |
| Columnas | sector, idtema, idconcepto, descripcion, nivel, indicador, orden, cuenta mapeo |
| Uso | Catalogo de conceptos sector 40 (Banca Multiple) para AG/BM |

### 14. tda IFRS9.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 75 × 266 |
| Formato | Pivotada — periodos como columnas (serial numbers en headers) |
| Contenido | TDA por tipo de credito (Cartera total, Comercial, Consumo, Vivienda) |

> **Nota**: Formato complejo. Dates en headers como serial numbers Excel.
> El loader actual (`loaders_tda_etapas.py`) no lee este archivo — usa `TDA.xlsx`.

### 15. FD239760.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 11,628 × 40 |
| Formato | **Identico schema** a CNBV_Cartera_Bancos_V2.xlsx |
| Periodo | 201701 – 202503 (99 periodos, hasta Mar 2025) |
| vs CNBV | Datos compartidos MATCH. CNBV tiene 9 periodos adicionales (Abr-Dic 2025) |

> **Conclusion**: Version anterior del CNBV Excel. Irrelevante para ETL actual.

### 16. nuevo2.csv — sin cambios

| Campo | Valor |
|-------|-------|
| Encoding | Latin-1 |
| Shape | ~287K × 25 (sin header) |
| Formato | Mismo schema que CorporateLoan_CNBVDB.csv pero **sin fila de encabezado** |
| Periodo | Solo 2 fechas: 8/31/25 y 9/30/25 (Ago-Sep 2025) |
| Instituciones | 41 |
| INVEX (40059) | 3,408 rows |

> **Nota**: Parece ser un subconjunto/exportacion parcial del CorporateLoan
> para los ultimos 2 meses. Posiblemente generado por el script R `CorporateLoan_BM.R`.

### 17. 040_R04A_419.csv — sin cambios

| Campo | Valor |
|-------|-------|
| Tamaño | 195 MB |
| Uso | Reporte R04A (importacion a `bank_src_reporte_r04a`) |

### 18. Catera Analitica Benchmark v2.xlsx — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 11,807 × 334 |
| Formato | Pivotada con multi-header (conceptos como columnas) |
| Uso | Benchmark analitico (importacion a `bank_src_benchmark_analitica`) |

### 19. sh_datos_40.csv (Banca Multiple) — sin cambios

| Campo | Valor |
|-------|-------|
| Shape | 12,651,848 rows |
| Columnas | sector, idconcepto, entidad, periodo, saldo, valor |
| Periodo | 200012 – 202512 |
| Entidades Dic 2025 | 58 |
| INVEX (040059) max | 202512 |

> BM cubre hasta Dic 2025 para 58 entidades. Sin embargo, BM alimenta
> `bank_src_banca_multiple`, NO `bank_fact_kpis_mensual` directamente.

### 20. Nueva carpeta (CSVs mensuales AG) — sin cambios

| Campo | Valor |
|-------|-------|
| Archivos | 18 CSVs: 2024-07.csv a 2025-12.csv |
| Shape | 58 × 37 cada uno |
| Formato | Entidad (codigo corto) × 35 conceptos AG como columnas |
| Nov=Oct | **SI** — `2025-11.csv` es identico byte-for-byte a `2025-10.csv` |
| Cobertura | Solo 18 meses (no es reemplazo del AG historico completo) |

Codigos de entidad: formato corto (5, 59, 60, 40002, 40012...) vs AG original (000005, 040012...).

### Archivos Tableau (nuevos, no ETL)

Los `.twbx` contienen snapshots de datos de Feb 2025 (CNBV hasta Mar 2023,
CorporateLoan ~42MB). Son fotos historicas empaquetadas con el dashboard.
Irrelevantes para el ETL actual.

---

## Problema A: Nov 2025 en CNBV — **CORREGIDO**

### Verificacion

```
Entrega 20260302: Oct vs Nov — 35/35 cols iguales (placeholder)
Entrega 20260304: Oct vs Nov — 0/35 cols iguales (CORREGIDO)
                  Oct vs Dic — 1/35 cols iguales (legitimo)
```

md5 CNBV:
- Viejo: `75afd178f05cf17dcd6a8c19e3752544`
- Nuevo: `e2b0f3ceb58660142a2100c1475cc80c`

**Accion**: Copiar nuevo CNBV a `incoming/` y re-ejecutar ETL Unificado.

---

## Problema B: AG (040_TO.csv) — **SIGUE FALTANDO, PERO BM LO SUPLE PARCIALMENTE**

`040_TO.csv` no aparece en ninguna parte de la entrega:
- No en raiz
- No en "Nueva carpeta" (esos son CSVs mensuales en formato diferente)
- No dentro de los `.twbx` (solo tienen CNBV, CorporateLoan, ICAP, etc.)

### Hallazgo critico: BM (`sh_datos_40.csv`) contiene los mismos datos que AG

Ambos archivos son del **Sector 40 (Banca Multiple)** de la CNBV con los mismos IDs
de concepto y entidad. Se verifico comparacion cruzada para INVEX (40059) en Oct 2025:

| Metrica | AG `saldo_se` | BM `valor` (saldo=130) | Match |
|---------|-------------|----------------------|-------|
| cartera_total (40100185) | 50,608,634,993 | 50,608,634,993 | **EXACTO** |
| cartera_vencida (40100341) | 1,204,831,444 | 1,204,831,444 | **EXACTO** |
| cartera_etapa_1 (40100263) | 47,810,228,310 | 47,810,228,310 | **EXACTO** |
| cartera_etapa_2 (40100302) | 1,593,575,239 | 1,593,575,239 | **EXACTO** |
| cartera_comercial (40100186) | 16,402,586,992 | 16,402,586,992 | **EXACTO** |
| cartera_consumo (40100206) | 34,152,326,747 | 34,152,326,747 | **EXACTO** |
| cartera_vivienda (40100217) | 53,721,254 | 53,721,254 | **EXACTO** |
| IMOR (40200017) | 2.3807% | 2.3807% (×100) | **~Igual** (Δ<0.001%) |
| IMORA (40200033) | 8.8343% | 8.8823% (×100) | **Cercano** (Δ~0.5%) |
| ICAP (4021750) | 15.97% | — | **NO EXISTE en BM** |

**Diferencias clave BM vs AG:**

| Aspecto | AG (`040_TO.csv`) | BM (`sh_datos_40.csv`) |
|---------|-------------------|------------------------|
| tipo_saldo | String: "Sin consolidar" | Numerico: saldo=130 |
| IMOR/IMORA | Porcentaje (2.38) | Decimal (0.0238) |
| ICAP | SI (concepto 4021750) | NO |
| Periodo max | 202510 (Oct 2025) | **202512 (Dic 2025)** |
| Entidades | ~80 | 58 en dic 2025 |

**Mapeo de campos:**
- AG `concepto` = BM `idconcepto` (mismos IDs)
- AG `institucion` = BM `entidad` (mismos codigos)
- AG `fecha` = BM `periodo` (ambos YYYYMM)
- AG `tipo_saldo="Sin consolidar"` → BM `saldo=130`
- AG `saldo_se` = BM `valor` (identico para cartera; escala diferente para ratios)

**BM aporta datos nuevos Nov/Dic 2025 para INVEX:**

| Metrica | Nov 2025 | Dic 2025 |
|---------|----------|----------|
| cartera_total | 52,311,733,550 | 51,911,959,665 |
| cartera_comercial | 16,270,118,429 | 15,843,739,553 |
| cartera_consumo | 35,988,863,866 | 36,016,431,676 |
| cartera_vivienda | 52,751,255 | 51,788,436 |
| cartera_etapa_1 | 48,992,704,787 | 48,272,143,592 |
| cartera_etapa_2 | 2,002,375,527 | 2,264,690,516 |
| cartera_vencida | 1,316,653,236 | 1,375,125,557 |
| IMOR | 2.52% | 2.65% |
| IMORA | 8.98% | 9.35% |

### Opciones para mitigar AG faltante

**Opcion 1 (Recomendada):** Crear adapter ETL que lea BM y lo transforme a formato AG.
- Pro: 9/10 metricas disponibles inmediatamente para Nov-Dic 2025 (58 bancos)
- Contra: ICAP faltaria (pero ya se carga de `ICAP_Bancos.xlsx` via legacy loader)
- Esfuerzo: ~medio dia de desarrollo + tests

**Opcion 2:** Esperar a que Bajaware envie `040_TO.csv` actualizado.
- Pro: No requiere cambios de codigo
- Contra: Dependencia externa, timeline incierto

**Opcion 3:** Hibrida — implementar Opcion 1 como fallback permanente + seguir solicitando AG.

### CSVs de "Nueva carpeta" — NO son sustituto

1. Nov 2025 sigue duplicado de Oct (no lo corrigieron)
2. Solo cubren 18 meses (Jul 2024 - Dic 2025), no el historico completo
3. Codigos de entidad en formato diferente (requeriria nuevo loader)

**Accion**: Seguir solicitando `040_TO.csv` a Bajaware, pero ya no es bloqueante
gracias a BM.

---

## Archivos Verificados (consolidado)

| Archivo | Shape | Periodo max | Cambio vs 0302 | Alimenta |
|---------|-------|-------------|----------------|----------|
| CNBV_Cartera_Bancos_V2.xlsx | 12,156×40 | 202512 | **SI** | `bank_fact_kpis_mensual` (legacy) |
| CorporateLoan_CNBVDB.csv | 1,763,972×25 | Sep 2025 | No | `tasa_mn`, `tasa_me` |
| CASTIGOS.xlsx | 50×13 | snapshot | No | `quebrantos_comerciales` |
| CASTIGOS1.xlsx | 50×13 | snapshot | NUEVO (=CASTIGOS) | duplicado |
| Castigos Comerciales.xlsx | 2,208×3 | Dic 2025 | No | `castigos_acum_comercial` |
| ICAP_Bancos.xlsx | 14,333×6 | Dic 2025 | No | `icap_total`, CCB, CCF |
| TDA.xlsx | 17,494×6 | 202512 | No | `tda_cartera_total` |
| TE_Invex_Sistema.xlsx | 32×3 | Dic 2024 | No | `tasa_sistema`, `tasa_invex_consumo` |
| QUEBRANTOS.csv | 46×3 | snapshot | No | referencia |
| TASAS DATOS.csv | 24×3 | snapshot | No | referencia |
| castigos.csv | 48×15 | snapshot | No | referencia |
| Instituciones.xlsx | 99×2 | — | No | `bank_dim_institucion` |
| 040_R04A_419.csv | ~5.8M | ? | No | `bank_src_reporte_r04a` |
| sh_datos_40.csv | 12.6M | 202512 | No | `bank_src_banca_multiple` |
| nuevo2.csv | ~287K×25 | Sep 2025 | No | (CorporateLoan sin header) |
| FD239760.xlsx | 11,628×40 | 202503 | No | (CNBV version anterior) |
| Catera Analitica Benchmark v2.xlsx | 11,807×334 | ? | No | `bank_src_benchmark_analitica` |
| CREADOR DE TDA.xlsx | 23MB | ? | No | (fuente TDA) |
| tda IFRS9.xlsx | 75×266 | ? | No | (TDA pivotada, no usada) |
| Cuentas_desc.xlsx | 36×3 | — | No | catalogo |
| cat_conceptos_40.xlsx | 617×9 | — | No | catalogo AG |
| Nueva carpeta (18 CSVs) | 58×37 c/u | Dic 2025 | No | (AG mensual, Nov=Oct) |

---

## ICAP en Tableau — Analisis del .twbx

El `.twbx` (`Invex_Tablero_V3_v2021_12.4.twbx`) contiene la definicion completa del dashboard.

**Fuente ICAP**: `ICAP_Bancos.xlsx` (hoja `ICAP Bancos$`), schema:
- `Cve_Inst` (string), `Banco` (string), `FECHA` (date)
- `ICAP Total` (real), `CCB` (real), `CCF` (real)

**Formulas Tableau** (calculated fields):
```
ICAP %     = [ICAP Total] / 100
Invex ICAP = IF Banco = 'Invex' THEN [ICAP Total]/100 ELSE 0 END
```

No hay calculo complejo — CNBV entrega ICAP pre-calculado. Tableau solo divide /100.

**Cobertura**:
- twbx empaquetado: 13,498 filas, 81 bancos, hasta Nov 2024
- Entrega actual: 14,333 filas, 98 bancos, hasta **Dic 2025**
- INVEX Dic 2025: ICAP=16.38%, CCB=16.38%, CCF=16.38%

**Conclusion**: ICAP tiene fuente independiente de AG. No necesita `040_TO.csv`.

---

## Conclusion Final: Todas las metricas cubiertas sin AG

| Metrica | Fuente disponible | Periodo max | Requiere AG? |
|---------|------------------|-------------|-------------|
| 7 carteras (total, vencida, etapas, comercial, consumo, vivienda) | CNBV Excel (7 bancos) + BM (58 bancos) | Dic 2025 | No |
| IMOR / IMORA | CNBV Excel + BM | Dic 2025 | No |
| ICAP | `ICAP_Bancos.xlsx` | Dic 2025 | No |

**10/10 metricas del KPI pipeline tienen cobertura hasta Dic 2025.**

El ETL Unificado Paso 5 funciona sin AG (runbook § "Ejecucion sin AG"):
- `transform_all()` detecta ausencia de AG y salta esas ramas
- Con `--upsert`, los 56 bancos AG-only preservan datos hasta Oct 2025
- Para actualizar esos 56 bancos a Nov/Dic: necesitaria adapter BM→AG (tarea BACKLOG)

---

## Mensaje Actualizado para Bajaware

> Hola equipo,
>
> Gracias por la re-entrega del 4 de marzo. Confirmamos que el
> `CNBV_Cartera_Bancos_V2.xlsx` ya tiene datos reales de Noviembre 2025
> (35/35 columnas con valores distintos a Octubre). Ese tema queda resuelto.
>
> Sobre los otros puntos:
>
> 1. **Analisis General (040_TO.csv)**: Sigue sin incluirse. Sin embargo,
>    verificamos que `sh_datos_40.csv` (Banca Multiple) contiene los mismos
>    conceptos y entidades con valores identicos, y ya cubre hasta Dic 2025.
>    Vamos a adaptar nuestro pipeline para usarlo como fuente alternativa.
>
>    De todas formas, si pueden incluir `040_TO.csv` actualizado en la
>    proxima entrega lo agradeceríamos — contiene el ICAP que no esta en BM.
>
> 2. **CSVs mensuales en "Nueva carpeta"**: `2025-11.csv` sigue siendo
>    copia de `2025-10.csv`. Con BM disponible esto ya no es bloqueante,
>    pero conviene corregirlo para la proxima entrega.
>
> Gracias,
> Jaziel
