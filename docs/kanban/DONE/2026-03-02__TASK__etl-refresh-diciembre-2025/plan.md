# Plan: ETL Refresh Diciembre 2025

> Actualización a periodo 202512 con la entrega `drive-download-20260302T184043Z-1-001`

## Estado actual de la BD (pre-refresh)

| Tabla | Max periodo | Gap |
|-------|-------------|-----|
| `bank_src_banca_multiple` | 202510 | 2 meses |
| `bank_src_reporte_r04a` | 202510 | 2 meses |
| `bank_fact_kpis_mensual` | 2025-11 | Nov incompleto + Dic faltante |
| Nov 2025 KPIs | imor: 34%, mktshare: 0%, tda: 48% | Huecos severos |

## Fase 1: Promover archivos a `incoming/` y actualizar `current/`

### 1.1 Copiar entrega
```bash
cp -r "/mnt/c/Users/Jaziel Flores/Downloads/drive-download-20260302T184043Z-1-001" \
  plugins/bank-advisor-private/data/raw/incoming/drive-download-20260302T184043Z-1-001
```

### 1.2 Ejecutar promote vía orquestador (actualiza symlinks en `current/`)
El orquestador maneja la promoción automáticamente. Los archivos que `data_promotion.py` detecta:
- `CNBV_Cartera_Bancos_V2.xlsx` ✅ (required)
- `Instituciones.xlsx` ✅ (required)
- `CASTIGOS.xlsx` ✅ (required)
- `ICAP_Bancos.xlsx` ✅ (required)
- `TDA.xlsx` ✅ (required)
- `CorporateLoan_CNBVDB.csv` ✅ (required)
- `Castigos Comerciales.xlsx` ✅ (optional)
- `TE_Invex_Sistema.xlsx` ✅ (optional, NUEVO en esta entrega)
- `CREADOR DE TDA.xlsx` ✅ (optional)
- `BE_BM_*.xlsx` ❌ NO incluido (optional)
- `AnalisisGeneral/` ❌ NO incluido (optional, usará fallback a estático)

### 1.3 Symlink manual para banca_multiple
**CRÍTICO**: El loader `loaders_banca_multiple.py:74` busca `BM_SH_DATOS_40.csv` pero el archivo se llama `sh_datos_40.csv`. Necesitamos crear un symlink adicional:
```bash
ln -sf ../incoming/drive-download-20260302T184043Z-1-001/sh_datos_40.csv \
  plugins/bank-advisor-private/data/raw/current/BM_SH_DATOS_40.csv
```

### 1.4 Symlink para R04A (ya existe en specs de promotion)
El R04A se encuentra vía glob `*R04A*.csv` y ya tiene manejo. Verificar que el symlink apunte al archivo nuevo:
```bash
ln -sf ../incoming/drive-download-20260302T184043Z-1-001/040_R04A_419.csv \
  plugins/bank-advisor-private/data/raw/current/040_R04A_419.csv
```

## Fase 2: Cargar sources particionadas (incremental: ≥ 202511)

### 2.1 Banca Múltiple → `bank_src_banca_multiple`
- Fuente: `sh_datos_40.csv` (533 MB, hasta 202512)
- Modo: incremental `MIN_PERIODO=202511` (DELETE + INSERT solo periodos nuevos)
- Rows estimados: ~500K (2 meses × ~250K/mes)
- Tiempo estimado: ~2-3 min

### 2.2 Reporte R04A → `bank_src_reporte_r04a`
- Fuente: `040_R04A_419.csv` (204 MB, hasta 202512)
- Modo: incremental `MIN_PERIODO=202511`
- R12A: no incluido en entrega, se omite (loader es tolerante)

### 2.3 Loaders que se omiten (sin archivo nuevo)
- `analisis_general` → sin `040_TO.csv` → fallback a estático (max 202510)
- `cartera_comercial` → sin archivos nuevos → se omite
- `cartera_vivienda` → sin archivos nuevos → se omite
- `benchmark` → sin cambios → se omite
- `tda_etapas` → sin cambios → se omite

**Decisión**: Usar `--skip-big-sources` y ejecutar los 2 loaders manualmente con incremental, para evitar truncar tablas que no cambiaron.

## Fase 3: ETL Unificado (KPIs + métricas)

### 3.1 Fuentes que alimentan `bank_fact_kpis_mensual`
| Fuente | Columnas que aporta | Status |
|--------|---------------------|--------|
| `CNBV_Cartera_Bancos_V2.xlsx` | cartera_total, cartera_vencida, etapas, → imor calculado | ✅ Actualizado |
| `ICAP_Bancos.xlsx` | icap_total, icap_ccb, icap_ccf | ✅ Actualizado |
| `CASTIGOS.xlsx` | quebrantos_comerciales | ✅ Actualizado |
| `CorporateLoan_CNBVDB.csv` | tasa_mn, tasa_me | ✅ Actualizado |
| `TDA.xlsx` | tda_cartera_total | Sin cambios (mismo tamaño) |
| `TE_Invex_Sistema.xlsx` | tasa_sistema, tasa_invex_consumo | ✅ NUEVO en entrega |
| `Castigos Comerciales.xlsx` | castigos_acum_comercial | Sin cambios |
| `AnalisisGeneral/040_TO.csv` | imor, imora, market_share (multi-banco) | ❌ Max 202510 |

### 3.2 Impacto esperado en huecos de Nov 2025
| Métrica | Antes | Después (esperado) |
|---------|-------|---------------------|
| `icap_total` | 49/58 | ~49/58 (mejora con nuevos datos ICAP) |
| `imor` | 20/58 | ~20-36/58 (solo bancos en CNBV_Cartera, AG sigue en 202510) |
| `market_share` | 0/58 | 0/58 → **SIGUE VACÍO** (depende de AG con todos los bancos) |
| `tda` | 28/58 | ~28-37/58 (TDA.xlsx sin cambios) |
| `tasa_mn` | 38/58 | ~38-39/58 (CorporateLoan actualizado) |

### 3.3 Limitación conocida: `market_share` y `imora` multi-banco
`market_share_pct` se calcula en `calculate_market_share()` como `cartera_banco / cartera_SISTEMA`. Requiere que SISTEMA tenga `cartera_total` para el periodo. Si CNBV_Cartera tiene dato de SISTEMA para Nov/Dic, el market_share se calculará para bancos que tengan cartera.

`imora` (incluyendo castigos) viene de AnalisisGeneral que está en max 202510.

### 3.4 Tablas que NO se actualizan
- `bank_fact_metricas_financieras` — sin `BE_BM_*.xlsx`
- `bank_fact_cartera_segmentada` — sin `BE_BM_*.xlsx`

### 3.5 Comando de ejecución
```bash
# ETL Unificado: procesa workbook + complementarios → KPIs
export DATABASE_URL='<url>'
PYTHONPATH=plugins/bank-advisor-private python3.11 -m etl.core.etl_unified \
  --data-root plugins/bank-advisor-private/data/raw/current
```

## Fase 4: IMOR Comercial (loader dedicado)

Ejecutar `loaders_imor_comercial.py` para actualizar `imor_comercial` y `cvc_cc` con los nuevos datos de CNBV_Cartera + Castigos Comerciales:

```bash
PYTHONPATH=plugins/bank-advisor-private python3.11 -m etl.core.loaders.loaders_imor_comercial \
  --xlsx plugins/bank-advisor-private/data/raw/current/CNBV_Cartera_Bancos_V2.xlsx \
  --castigos "plugins/bank-advisor-private/data/raw/current/Castigos Comerciales.xlsx" \
  --db-url "$DATABASE_URL"
```

## Fase 5: Refresh MVs

```bash
# Vía orquestador (solo MVs)
make etl-refresh --skip-big-sources --skip-unified

# O directamente en SQL
psql $DATABASE_URL -c "SELECT * FROM bank_mv_refresh_all();"
```

MVs afectadas:
- `bank_mv_comparativa_bancos` → depende de KPIs
- `bank_mv_resumen_sistema` → depende de KPIs
- `bank_mv_ranking_cartera_mensual` → depende de KPIs

## Fase 6: Validación

### 6.1 Freshness check
```bash
make etl-freshness
```

### 6.2 Queries de validación manual
```sql
-- ¿Dic 2025 existe en KPIs?
SELECT banco_norm, fecha, cartera_total, icap_total, imor, market_share_pct
FROM bank_fact_kpis_mensual
WHERE fecha = '2025-12-01' AND banco_norm IN ('INVEX', 'SISTEMA', 'BBVA')
ORDER BY banco_norm;

-- ¿Nov 2025 mejoró?
SELECT
    COUNT(*) as total,
    COUNT(icap_total) as with_icap,
    COUNT(imor) as with_imor,
    COUNT(market_share_pct) as with_mktshare
FROM bank_fact_kpis_mensual WHERE fecha = '2025-11-01';

-- ¿Sources actualizadas?
SELECT MAX(periodo) FROM bank_src_banca_multiple;  -- esperado: 202512
SELECT MAX(periodo) FROM bank_src_reporte_r04a;    -- esperado: 202512
```

## Secuencia de ejecución completa

```bash
# 0. Setup
export DATABASE_URL='postgresql://bankadvisor:...@${PROD_DB_HOST}:5432/bankadvisor'
cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex

# 1. Copiar entrega a incoming
cp -r "/mnt/c/Users/Jaziel Flores/Downloads/drive-download-20260302T184043Z-1-001" \
  plugins/bank-advisor-private/data/raw/incoming/drive-download-20260302T184043Z-1-001

# 2. Promote (actualiza symlinks en current/)
PYTHONPATH=plugins/bank-advisor-private python3.11 -c "
from etl.core.data_promotion import promote_incoming_drop, find_latest_incoming_dir
from pathlib import Path
raw = Path('plugins/bank-advisor-private/data/raw')
result = promote_incoming_drop(
    incoming_dir=raw / 'incoming/drive-download-20260302T184043Z-1-001',
    current_dir=raw / 'current',
    fallback_dir=raw,
    force=True,
)
for item in result.items:
    print(f'  {item.action:8s} {item.dest_rel} <- {item.source}')
if result.missing_required:
    print(f'MISSING REQUIRED: {[m.dest_rel for m in result.missing_required]}')
"

# 3. Symlink manual para banca_multiple (loader espera BM_SH_DATOS_40.csv)
ln -sf ../incoming/drive-download-20260302T184043Z-1-001/sh_datos_40.csv \
  plugins/bank-advisor-private/data/raw/current/BM_SH_DATOS_40.csv

# 4. Cargar banca_multiple incremental (solo >=202511)
PYTHONPATH=plugins/bank-advisor-private python3.11 -c "
from pathlib import Path
from sqlalchemy import create_engine
from etl.core.loaders.loaders_banca_multiple import load_banca_multiple
engine = create_engine('$DATABASE_URL')
result = load_banca_multiple(
    data_root=Path('plugins/bank-advisor-private/data/raw/current'),
    engine=engine,
    min_periodo='202511',
)
print(result)
"

# 5. Cargar R04A incremental (solo >=202511)
PYTHONPATH=plugins/bank-advisor-private python3.11 -c "
from pathlib import Path
from sqlalchemy import create_engine
from etl.core.loaders.loaders_reportes_reg import load_reportes_regulatorios
engine = create_engine('$DATABASE_URL')
result = load_reportes_regulatorios(
    data_root=Path('plugins/bank-advisor-private/data/raw/current'),
    engine=engine,
    min_periodo='202511',
)
print(result)
"

# 6. ETL Unificado (KPIs)
PYTHONPATH=plugins/bank-advisor-private python3.11 -m etl.core.etl_unified \
  --data-root plugins/bank-advisor-private/data/raw/current \
  --db-url "$DATABASE_URL"

# 7. IMOR Comercial
PYTHONPATH=plugins/bank-advisor-private python3.11 -m etl.core.loaders.loaders_imor_comercial \
  --xlsx plugins/bank-advisor-private/data/raw/current/CNBV_Cartera_Bancos_V2.xlsx \
  --castigos "plugins/bank-advisor-private/data/raw/current/Castigos Comerciales.xlsx" \
  --db-url "$DATABASE_URL"

# 8. Refresh MVs
psql "$DATABASE_URL" -c "SELECT * FROM bank_mv_refresh_all();"

# 9. Validar
make etl-freshness
```

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| `market_share` sigue NULL Nov/Dic | Medio | Depende de 040_TO.csv (AG). Pedir a Bajaware en próxima entrega |
| ETL Unificado hace TRUNCATE+INSERT en KPIs | Alto | Toda la tabla se reescribe; si falla a media carga, se pierde data. Hacer backup antes |
| Loader banca_multiple no encuentra `BM_SH_DATOS_40.csv` | Alto | Symlink manual en paso 3 |
| Particiones 2026 no existen | Bajo | Datos solo llegan a 202512, no necesarias aún |

## Backup pre-ejecución (recomendado)
```sql
CREATE TABLE bank_fact_kpis_mensual_backup_20260302 AS
SELECT * FROM bank_fact_kpis_mensual;
```
