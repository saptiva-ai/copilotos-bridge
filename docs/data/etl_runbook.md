# Runbook: Actualización Mensual de Datos

> Guía operativa para agregar nuevos meses de datos al sistema BankAdvisor.
> Para gotchas de datos y problemas conocidos, ver [`source_mapping.md` § Gotchas](source_mapping.md#gotchas-conocidos).

## Contenido

- [Prerequisitos](#prerequisitos)
- [Flujo Completo](#flujo-completo-5-min-setup--30-min-ejecución)
- [Comandos Individuales](#comandos-individuales)
- [Ejecución Programática](#ejecución-programática-python)
- [Refresh Manual Paso a Paso](#refresh-manual-paso-a-paso-sin-orquestador) ← cuando el orquestador falla
- [Post-carga: verificación multi-banco](#post-carga-verificación-de-completitud-multi-banco)
- [Ejecución sin AG (evita OOM)](#ejecución-sin-analisisgeneral-evita-oom)
- [Troubleshooting](#troubleshooting)
  - [Índice rápido de problemas operativos](#índice-rápido-de-problemas-operativos)
- [Referencia Rápida](#referencia-rápida)

### Índice rápido de problemas operativos

| Problema | Solución rápida |
|----------|----------------|
| "File not found" en loader | Verificar nombres en `current/`, crear symlink → [§ Troubleshooting](#file-not-found-en-algún-loader) |
| Año nuevo sin particiones | Crear particiones SQL → [§ Particiones](#particiones-faltantes-para-años-nuevos) |
| MV no se actualiza | Refresh manual sin CONCURRENTLY → [§ MVs](#materialized-views-no-se-actualizan) |
| ETL muere con exit 137 | Omitir AG o más RAM → [§ OOM](#error-de-memoria-oom--exit-137) |
| Bancos dual-source con escala rota | Fix SQL con factores o restaurar desde AG → [§ Escala rota](#bancos-dual-source-con-escala-rota-cartera--icap) |
| `cartera_comercial_sin_gob` en MDP para dual-source | ×1M (no hay concepto AG) → [§ Escala rota](#bancos-dual-source-con-escala-rota-cartera--icap) |
| Spike ~2× en Ene 2023 INVEX | Legacy+AG se sumaron → [`source_mapping.md` § Spike](source_mapping.md#spike-enero-2023-patrón-de-duplicación-legacyag) |
| `periodo_id` es NULL | Fix SQL → [§ Post-ETL](#post-etl-verificar-periodo_id) |
| Datos correctos en BD pero invisibles en frontend | Verificar `periodo_id` + flush Redis + restart backend |
| Quebrantos comerciales bajos o faltantes | Usar `CASTIGOS.xlsx` (flujos), NO `Castigos Comerciales.xlsx` (acumulados) → [source_mapping § Castigos](source_mapping.md#8-castigos-dos-fuentes-dos-semánticas-corregido-2026-03-04) |
| ICAP/ICOR solo para INVEX en multi-banco | Gap de ICAP_Bancos.xlsx para el mes cargado → [§ Post-carga multi-banco](#post-carga-verificación-de-completitud-multi-banco) |
| 5 bancos sin cartera en comparación | Gap de AG para el mes cargado → [§ Post-carga multi-banco](#post-carga-verificación-de-completitud-multi-banco) |
| Tasas divergen de PPT del cliente | CSV de backfill apunta a entrega anterior → [source_mapping § CSV version gap](source_mapping.md#10-csv-version-gap-tasas-dic-2025--corregido-2026-03-04) |
| Gotchas de datos (INVEX, escala, tasas) | Ver [`source_mapping.md` § Gotchas](source_mapping.md#gotchas-conocidos) |

---

## Prerequisitos

- Acceso a Google Drive de Bajaware (carpeta compartida)
- Variable `DATABASE_URL` configurada apuntando a PostgreSQL en GCP
- Python 3.11 con dependencias del ETL instaladas
- Directorio `plugins/bank-advisor-private/data/raw/` disponible

## Flujo Completo (5 min setup + ~30 min ejecución)

### 1. Descargar nueva entrega de Google Drive

Bajaware comparte una carpeta en Google Drive con los archivos actualizados.
Descargar el ZIP y extraer en `incoming/`:

```bash
cd plugins/bank-advisor-private/data/raw/incoming/
unzip ~/Downloads/drive-download-20260318T*.zip -d drive-download-20260318T000000Z-001
```

Archivos esperados en la entrega:
- `AG_040_TO.csv` (Análisis General, ~747 MB)
- `BM_SH_DATOS_40.csv` (Banca Múltiple, ~527 MB)
- `040_R04A_*.csv` (Reportes R04A)
- `040_R12A_*.csv` (Reportes R12A)
- `Total_Base_Historica_Comercial.csv` + variantes marginales
- `Hipotecarios_Marginales.csv`
- `BE_BM_*.xlsx` (workbook métricas)
- `CNBV_Cartera_Bancos_V2.xlsx`
- `Catera Analitica Benchmark v2.xlsx`
- `CREADOR DE TDA.xlsx`
- Complementarios: `CASTIGOS.xlsx`, `ICAP_Bancos.xlsx`, `TDA.xlsx`, `TE_*.xlsx`

### 2. Verificar frescura actual

```bash
make etl-freshness
```

### 3. Ejecutar refresh (full reload)

```bash
# Auto-detecta incoming más reciente, full reload
make etl-refresh

# O especificar directorio y periodo objetivo
make etl-refresh INCOMING=drive-download-20260318T000000Z-001 PERIODO=202601
```

### 4. Refresh incremental (solo periodos nuevos)

```bash
# Solo cargar datos desde noviembre 2025 en adelante
make etl-refresh INCOMING=drive-download-20260318T000000Z-001 PERIODO=202601 MIN_PERIODO=202511
```

Esto hace `DELETE + INSERT` en lugar de `TRUNCATE + INSERT`, preservando datos existentes.

### 5. Dry run

```bash
make etl-refresh DRY=1 INCOMING=drive-download-20260318T000000Z-001
```

### 6. Verificar resultado

```bash
make etl-freshness

psql $DATABASE_URL -c "SELECT * FROM etl_runs ORDER BY started_at DESC LIMIT 5"
```

## Comandos Individuales

```bash
# Solo CSVs grandes (analisis_general, banca_multiple, etc.)
make etl-refresh --skip-unified --skip-mvs

# Solo ETL unificado (KPIs, métricas, segmentos del workbook)
make etl-refresh --skip-big-sources --skip-mvs

# Solo refresh de materialized views
make etl-refresh --skip-big-sources --skip-unified
```

## Ejecución Programática (Python)

```python
from pathlib import Path
from etl.core.refresh_orchestrator import RefreshOrchestrator

orch = RefreshOrchestrator(
    data_root=Path("plugins/bank-advisor-private/data/raw"),
    db_url="postgresql://bankadvisor:password@host:5432/bankadvisor",
)

# Full refresh
result = orch.run(
    incoming_name="drive-download-20260318T000000Z-001",
    target_periodo="202601",
)

# Incremental (solo desde noviembre 2025)
result = orch.run(
    incoming_name="drive-download-20260318T000000Z-001",
    target_periodo="202601",
    min_periodo="202511",
)

print(result.summary())
```

## Refresh Manual Paso a Paso (sin orquestador)

Cuando la entrega no incluye todos los archivos esperados o el orquestador falla:

```bash
export DATABASE_URL='postgresql://bankadvisor:PASSWORD@HOST:5432/bankadvisor'
cd /path/to/octavios-chat-bajaware_invex

VENV=plugins/bank-advisor-private/.venv/bin/python3.11
```

### Paso 1: Copiar entrega

```bash
cp -r "/mnt/c/Users/.../Downloads/drive-download-FECHA" \
  plugins/bank-advisor-private/data/raw/incoming/drive-download-FECHA
```

### Paso 2: Promote (actualizar symlinks)

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
from etl.core.data_promotion import promote_incoming_drop
from pathlib import Path
raw = Path('plugins/bank-advisor-private/data/raw')
result = promote_incoming_drop(
    incoming_dir=raw / 'incoming/drive-download-FECHA',
    current_dir=raw / 'current',
    fallback_dir=raw,
    force=True,
)
for item in result.items:
    print(f'  {item.action:8s} {item.dest_rel} <- {item.source}')
"
```

### Paso 3: Symlinks manuales (si nombres difieren)

```bash
# BM loader espera BM_SH_DATOS_40.csv
ln -sf ../incoming/drive-download-FECHA/sh_datos_40.csv \
  plugins/bank-advisor-private/data/raw/current/BM_SH_DATOS_40.csv
```

### Paso 4: Cargar sources incrementales

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
from pathlib import Path
from sqlalchemy import create_engine
from etl.core.loaders.loaders_banca_multiple import load_banca_multiple
engine = create_engine('$DATABASE_URL')
print(load_banca_multiple(Path('plugins/bank-advisor-private/data/raw/current'), engine, min_periodo='YYYYMM'))
"

PYTHONPATH=plugins/bank-advisor-private $VENV -c "
from pathlib import Path
from sqlalchemy import create_engine
from etl.core.loaders.loaders_reportes_reg import load_reportes_regulatorios
engine = create_engine('$DATABASE_URL')
print(load_reportes_regulatorios(Path('plugins/bank-advisor-private/data/raw/current'), engine, min_periodo='YYYYMM'))
"
```

### Paso 5: ETL Unificado (KPIs)

> Si AG no está disponible o causa OOM, ver § "Ejecución sin AnalisisGeneral".

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
import polars as pl
from pathlib import Path
from etl.core.loaders_unified import (
    get_data_paths, load_cnbv_cartera, load_instituciones,
    load_castigos, load_castigos_comerciales, load_icap,
    load_tda, load_te_invex, load_corporate_loan
)
from etl.core.transforms import transform_all
from etl.core.db_writer_3nf import save_to_normalized_schema

paths = get_data_paths(Path('plugins/bank-advisor-private/data/raw/current'))
sources = {
    'cnbv': load_cnbv_cartera(paths),
    'instituciones': load_instituciones(paths),
    'castigos': load_castigos(paths),
    'castigos_comerciales': load_castigos_comerciales(paths),
    'icap': load_icap(paths),
    'tda': load_tda(paths),
    'te': load_te_invex(paths),
    'corporate_rates': load_corporate_loan(paths),
}
result = transform_all(sources)
save_to_normalized_schema(result, '$DATABASE_URL', use_upsert=True)
"
```

### Paso 6: IMOR Comercial

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
import sys
sys.argv = ['',
    '--xlsx', 'plugins/bank-advisor-private/data/raw/current/CNBV_Cartera_Bancos_V2.xlsx',
    '--castigos', 'plugins/bank-advisor-private/data/raw/current/Castigos Comerciales.xlsx',
    '--db-url', '$DATABASE_URL'
]
from etl.core.loaders.loaders_imor_comercial import main
main()
"
```

### Paso 7: Refresh MVs

```sql
SELECT * FROM bank_mv_refresh_all();

-- Si falla con "concurrently":
REFRESH MATERIALIZED VIEW bank_mv_cartera_por_estado;
```

### Paso 8: Validar

```sql
SELECT banco_norm, fecha::date,
       ROUND(cartera_total::numeric/1e6) as cartera_MM,
       ROUND(icap_total::numeric,4) as icap,
       ROUND(imor::numeric,4) as imor,
       ROUND(imor_comercial::numeric,4) as imor_com
FROM bank_fact_kpis_mensual
WHERE fecha = (SELECT MAX(fecha) FROM bank_fact_kpis_mensual)
  AND cartera_total > 0
ORDER BY banco_norm;
```

### Post-ETL: Verificar periodo_id

> **Crítico**: Si ejecutaste el ETL manual (fuera de `db_writer_3nf.py`), `periodo_id` puede quedar NULL.
> Datos con `periodo_id = NULL` son **invisibles** para el frontend.
> Ver [`source_mapping.md` § periodo_id](source_mapping.md#4-periodo_id-y-pipeline-legacy) para detalles.

```sql
-- Verificar
SELECT COUNT(*) FROM bank_fact_kpis_mensual WHERE periodo_id IS NULL;

-- Fix
UPDATE bank_fact_kpis_mensual
SET periodo_id = EXTRACT(YEAR FROM fecha)::int * 100 + EXTRACT(MONTH FROM fecha)::int
WHERE periodo_id IS NULL;
```

### Post-carga: verificación de completitud multi-banco

> **Lección aprendida (2026-03-04)**: Un gap de datos en Dic 2025 causó 7 thumbs-down del cliente.
> 5 de 7 bugs eran NULLs en columnas clave para los 10 bancos peer.
> Ver [`source_mapping.md` § Gaps Dic 2025](source_mapping.md#9-gaps-de-datos-dic-2025-corregido-2026-03-04).

Después de cada carga de un nuevo mes, ejecutar esta verificación sobre los **10 bancos peer**:

```sql
-- Detectar bancos con NULLs en columnas clave para el mes cargado
-- Reemplazar '2025-12-01' con la fecha del mes recién cargado
SELECT banco_norm,
  CASE WHEN icap_total     IS NULL THEN 'NULL' ELSE 'OK' END AS icap,
  CASE WHEN icor            IS NULL THEN 'NULL' ELSE 'OK' END AS icor,
  CASE WHEN cartera_total   IS NULL OR cartera_total = 0   THEN 'NULL' ELSE 'OK' END AS cartera,
  CASE WHEN cartera_comercial_sin_gob IS NULL THEN 'NULL' ELSE 'OK' END AS sin_gob,
  CASE WHEN tasa_mn         IS NULL THEN 'NULL' ELSE 'OK' END AS tasa_mn,
  CASE WHEN tasa_me         IS NULL THEN 'NULL' ELSE 'OK' END AS tasa_me
FROM bank_fact_kpis_mensual
WHERE fecha = '2025-12-01'
  AND banco_norm IN (
    'INVEX','AFIRME','BANCO BASE','BANCREA','BANSI',
    'MIFEL','MONEX','MULTIVA','SABADELL','VE POR MAS'
  )
ORDER BY banco_norm;
```

**Checklist** (todos deben ser "OK" para los 10 bancos, excepto notas):

| # | Verificación | Query esperado | Nota |
|---|-------------|----------------|------|
| 1 | ICAP para 10 bancos | 10 filas con `icap = OK` | Fuente: `ICAP_Bancos.xlsx` |
| 2 | ICOR para 10 bancos | 10 filas con `icor = OK` | Calculado: `reservas / cartera_vencida` |
| 3 | Cartera para 10 bancos | 10 filas con `cartera = OK` | Fuente: CNBV o AG |
| 4 | sin_gob para 10 bancos | 10 filas con `sin_gob = OK` | Fuente: `sh_datos_40.csv` (concepto 40100200) |
| 5 | Tasas para 10 bancos | 10 con `tasa_mn = OK` | `tasa_me`: BANSI = NULL desde Jun 2022 (gap genuino) |

**Si hay NULLs**, aplicar fixes quirúrgicos según la fuente correspondiente
(ver [source_mapping § Gaps Dic 2025](source_mapping.md#9-gaps-de-datos-dic-2025-corregido-2026-03-04)).

**Verificar cobertura de 10 bancos en MVs** (post `bank_mv_refresh_all()`):

```sql
SELECT COUNT(DISTINCT banco_norm) AS bancos_con_datos
FROM bank_mv_comparativa_bancos
WHERE periodo_id = 202512;  -- Reemplazar con YYYYMM del mes cargado
-- Esperado: 10
```

---

## Ejecución sin AnalisisGeneral (evita OOM)

El ETL Unificado puede ser matado por OOM (exit 137) al cargar AG (122K records) +
CorporateLoan (219MB) + concat de esquemas heterogéneos.

**Solución**: Omitir AG en el dict `sources`. La función `transform_all()` detecta
automáticamente que AG no está y salta esas ramas.

**Impacto**:
- Se pierden los 56 bancos AG-only (AFIRME, BAJIO, CIBANCO, etc.)
- Con `--upsert`, esos 56 bancos se preservan del load anterior
- `market_share` no se recalcula (depende de AG)
- Solo se actualizan los ~7 bancos del CNBV Excel

---

## Troubleshooting

> Para gotchas de datos (escala, códigos INVEX, tasa, periodo_id), ver
> [`source_mapping.md` § Gotchas](source_mapping.md#gotchas-conocidos).

### "File not found" en algún loader

Los archivos pueden tener nombres diferentes entre entregas. Los loaders buscan
por glob (`*R04A*.csv`), pero si el nombre cambió demasiado, puede fallar.

```bash
ls -la plugins/bank-advisor-private/data/raw/current/
```

| Loader espera | Variante recibida | Solución |
|---------------|-------------------|----------|
| `BM_SH_DATOS_40.csv` | `sh_datos_40.csv` | Symlink manual |
| `040_R04A_417_10.csv` | `040_R04A_419.csv` | Glob `*R04A*.csv` lo detecta |
| `AG_040_TO.csv` | `040_TO.csv` | Glob `*040_TO*.csv` lo detecta |

### Particiones faltantes para años nuevos

Las tablas particionadas necesitan particiones por año. Para 2026:

```sql
CREATE TABLE bank_src_analisis_general_2026
    PARTITION OF bank_src_analisis_general
    FOR VALUES FROM ('202600') TO ('202700');

CREATE TABLE bank_src_banca_multiple_2026
    PARTITION OF bank_src_banca_multiple
    FOR VALUES FROM ('202600') TO ('202700');

CREATE TABLE bank_src_reporte_r04a_2026
    PARTITION OF bank_src_reporte_r04a
    FOR VALUES FROM ('202600') TO ('202700');

CREATE TABLE bank_src_reporte_r12a_2026
    PARTITION OF bank_src_reporte_r12a
    FOR VALUES FROM ('202600') TO ('202700');
```

### Materialized views no se actualizan

```sql
-- Refresh manual individual
REFRESH MATERIALIZED VIEW bank_mv_ranking_cartera_mensual;
REFRESH MATERIALIZED VIEW bank_mv_evolucion_cartera_banco;

-- Si falla con "cannot refresh concurrently" (MV sin unique index):
REFRESH MATERIALIZED VIEW bank_mv_cartera_por_estado;
```

### Error de memoria (OOM / exit 137)

1. **Omitir AG** (ver § arriba) — reduce ~40% del uso de RAM
2. Reducir `chunk_size` en loaders de sources grandes (default 1M, reducir a 100K)
3. Ejecutar en una máquina con más RAM

### Bancos dual-source con escala rota (cartera + ICAP)

**Síntoma**: Los 6 bancos dual-source + SISTEMA muestran cartera ~1000× menor e ICAP
como decimal (0.15 en vez de 15). Ocurre en dos escenarios:
1. Meses sin cobertura AG (ej. Nov/Dic cuando AG max = Oct)
2. ETL legacy ejecutado con `--upsert` sobreescribe datos correctos de AG

**Detección** (ver [`source_mapping.md` § Escala](source_mapping.md#factores-de-corrección-para-meses-legacy-only)):
```sql
-- Cartera: buscar valores sospechosamente bajos
SELECT banco_norm, COUNT(*)
FROM bank_fact_kpis_mensual
WHERE banco_norm IN ('INVEX','BBVA','BANORTE','SANTANDER','HSBC','CITIBANAMEX','SISTEMA')
  AND cartera_total > 0
  AND cartera_total < CASE
    WHEN banco_norm = 'SISTEMA' THEN 100e9
    WHEN banco_norm = 'INVEX' THEN 500e6
    ELSE 10e9 END
GROUP BY banco_norm;

-- ICAP: buscar valores en escala decimal
SELECT banco_norm, COUNT(*)
FROM bank_fact_kpis_mensual
WHERE icap_total > 0 AND icap_total < 1
GROUP BY banco_norm;
```

**Fix manual SQL** (factores en [`source_mapping.md`](source_mapping.md#factores-de-corrección-para-meses-legacy-only)):
```sql
-- Cartera (×1000 monetarias, ×1M comercial + sin_gob)
UPDATE bank_fact_kpis_mensual
SET cartera_total = cartera_total * 1000,
    cartera_vencida = cartera_vencida * 1000,
    cartera_total_etapa_1 = cartera_total_etapa_1 * 1000,
    cartera_total_etapa_2 = cartera_total_etapa_2 * 1000,
    cartera_consumo_total = cartera_consumo_total * 1000,
    cartera_vivienda_total = cartera_vivienda_total * 1000,
    cartera_comercial_total = cartera_comercial_total * 1000000,
    cartera_comercial_sin_gob = cartera_comercial_sin_gob * 1000000
WHERE banco_norm IN ('BBVA','BANORTE','SANTANDER','HSBC','CITIBANAMEX')
  AND cartera_total > 0 AND cartera_total < 10e9;

-- ICAP (×100 decimal → porcentaje)
UPDATE bank_fact_kpis_mensual
SET icap_total = icap_total * 100
WHERE icap_total > 0 AND icap_total < 1;

-- Método preferido: restaurar desde AG source (ver source_mapping.md § Factores)
-- Ejemplo: restaurar cartera_comercial_total para INVEX
UPDATE bank_fact_kpis_mensual k
SET cartera_comercial_total = ag.importe
FROM bank_src_analisis_general ag
WHERE k.banco_norm = 'INVEX'
  AND ag.institucion = '040059' AND ag.concepto = 40100186
  AND ag.periodo = TO_CHAR(k.fecha, 'YYYYMM');
```

**Historial de fixes DB**:
- 2026-03-03 (sesión 1): ICAP ×100 — 717 filas (6 bancos + SISTEMA)
- 2026-03-03 (sesión 1): Cartera ×1000 — 307 filas (SISTEMA 28, 5 bancos 231, INVEX 48)
- 2026-03-03 (sesión 2): INVEX cartera_vencida — 63 filas (×1000 pre-2022 + fix Oct-Dec 2022 + spike Ene 2023)
- 2026-03-03 (sesión 2): INVEX cartera_total_etapa_3 — 107 filas (SET = cartera_vencida)
- 2026-03-03 (sesión 2): INVEX cartera_comercial_total pre-2022 — 253 filas (restaurado desde AG concepto 40100186)
- 2026-03-03 (sesión 2): INVEX cartera_vivienda_total pre-2022 — 215 filas (restaurado desde AG concepto 40100217)
- 2026-03-03 (sesión 2): INVEX spike Ene 2023 — 5 columnas corregidas (patrón 2× legacy+AG)
- 2026-03-03 (sesión 2): cartera_comercial_sin_gob ×1M — 647 filas (INVEX 108 + 5 bancos 539)
- 2026-03-03 (sesión 2): INVEX cartera_total 2017-2021 zeros — 60 filas restauradas desde AG concepto 40100185
- 2026-03-04: quebrantos_comerciales — 1652 filas cargadas desde `CASTIGOS.xlsx` (LIB_CASTIGOS_COMERC). Bancos nuevos: MONEX, MIFEL, AFIRME, BANCO BASE + meses faltantes para 42 bancos más. Ver [source_mapping.md § Castigos](source_mapping.md#8-castigos-dos-fuentes-dos-semánticas-corregido-2026-03-04)
- 2026-03-04: ICAP Dic 2025 — 9 bancos peer actualizados desde `ICAP_Bancos.xlsx`. Ver [source_mapping.md § Gaps Dic 2025](source_mapping.md#9-gaps-de-datos-dic-2025-corregido-2026-03-04)
- 2026-03-04: ICOR Dic 2025 — 9 bancos peer calculados (reservas/cartera_vencida) desde CNBV
- 2026-03-04: Cartera Dic 2025 — 5 bancos AG-only (BANCREA, BANSI, MULTIVA, SABADELL, VPM) desde `CNBV_Cartera_Bancos_V2.xlsx` (MDP×1e6)
- 2026-03-04: sin_gob/eg Dic 2025 — 5 bancos desde `sh_datos_40.csv` (concepto 40100200, saldo=130)
- 2026-03-04: Tasas Dic 2025 — 5 UPDATEs quirúrgicos corrigiendo CSV version gap (Feb 12 → Mar 2). Ver [source_mapping.md § CSV version gap](source_mapping.md#10-csv-version-gap-tasas-dic-2025--corregido-2026-03-04)
- 2026-03-04: INVEX institucion_id NULL → 31 — 301 filas (FK faltante de quirúrgico anterior)

**Prevención**: Cuando AG se actualice, el upsert sobreescribirá con valores correctos.
No ejecutar ETL legacy con `--upsert` sin AG posterior.

---

## Referencia Rápida

| Qué quieres hacer | Comando |
|-------------------|---------|
| Ver estado actual | `make etl-freshness` |
| Refresh completo (orquestador) | `make etl-refresh INCOMING=<dir> PERIODO=<YYYYMM>` |
| Refresh incremental | `make etl-refresh INCOMING=<dir> PERIODO=<YYYYMM> MIN_PERIODO=<YYYYMM>` |
| Dry run | `make etl-refresh DRY=1` |
| Solo CSVs grandes | `make etl-refresh --skip-unified --skip-mvs` |
| Solo workbook | `make etl-refresh --skip-big-sources --skip-mvs` |
| Solo refresh MVs | `make etl-refresh --skip-big-sources --skip-unified` |
| Manual sin AG (evita OOM) | Ver § "Refresh Manual Paso a Paso" |
| Solo IMOR Comercial | Ver § "Refresh Manual" paso 6 |
| Validar KPIs de un mes | `psql $DB -c "SELECT ... WHERE fecha = '2025-12-01'"` |
| Verificar periodo_id | `SELECT COUNT(*) FROM bank_fact_kpis_mensual WHERE periodo_id IS NULL` |
| Verificar escala ICAP | `SELECT banco_norm, COUNT(*) FROM bank_fact_kpis_mensual WHERE icap_total > 0 AND icap_total < 1 GROUP BY banco_norm` |
| Verificar escala cartera | Ver query de detección en § "Bancos dual-source con escala rota" |
| Verificar escala sin_gob | `SELECT banco_norm, COUNT(*) FROM bank_fact_kpis_mensual WHERE cartera_comercial_sin_gob > 0 AND cartera_comercial_sin_gob < 1e6 GROUP BY banco_norm` |
| Verificar etapa_3 = vencida | `SELECT COUNT(*) FROM bank_fact_kpis_mensual WHERE cartera_total_etapa_3 != cartera_vencida AND cartera_vencida > 0` |
