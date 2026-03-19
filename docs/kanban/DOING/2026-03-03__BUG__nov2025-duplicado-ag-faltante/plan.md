# Plan: Carga de datos entrega 20260304

> Objetivo: Cargar todos los datos disponibles de la re-entrega sin perder datos
> existentes de bancos AG-only (56 bancos con datos hasta Oct 2025).

## Estado: EJECUTADO (2026-03-04)

> **NOTA**: Fases 0-5 se ejecutaron como planeado. Fase 5 revelo problema de escala
> (legacy ETL produce valores ~1000x menores en MDP vs pesos del DB). Se cambio a
> approach quirurgico: UPDATE directo con datos BM (`sh_datos_40.csv`), que ya esta
> en escala pesos correcta. Ver card.md para resultados de validacion.

## Contexto

- Entrega: `drive-download-20260304T143340Z-1-001` (en Windows Downloads)
- Problema A (CNBV Nov=Oct): CORREGIDO en re-entrega
- Problema B (AG faltante): MITIGADO — BM suple 9/10 metricas, ICAP independiente
- **RIESGO**: El orquestador usa `use_upsert=False` (TRUNCATE+INSERT), lo cual
  borraria datos de 56 bancos AG-only. Debemos usar modo manual con `use_upsert=True`.

## Pre-requisitos

- [ ] Tunnel SSH a PROD activo: `ssh -L 18000:localhost:8000 $PROD_USER@$PROD_HOST -N -f`
- [ ] `DATABASE_URL` exportado y accesible
- [ ] Venv disponible: `plugins/bank-advisor-private/.venv/bin/python3.11`

---

## Fase 0: Snapshot de seguridad (antes de tocar nada)

Guardar estado actual de las tablas criticas para rollback si algo falla.

```bash
VENV=plugins/bank-advisor-private/.venv/bin/python3.11

# 0.1 Snapshot de bank_fact_kpis_mensual (tabla principal)
psql $DATABASE_URL -c "
  CREATE TABLE bank_fact_kpis_mensual_bak_20260304
  AS SELECT * FROM bank_fact_kpis_mensual;
"

# 0.2 Contar filas para referencia
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT banco_norm) AS bancos,
    MIN(fecha) AS min_fecha,
    MAX(fecha) AS max_fecha
  FROM bank_fact_kpis_mensual;
"

# 0.3 Snapshot de KPIs INVEX actuales (para comparar después)
psql $DATABASE_URL -c "
  SELECT banco_norm, fecha::date,
         ROUND(cartera_total::numeric/1e6) as cartera_MM,
         ROUND(icap_total::numeric,4) as icap,
         ROUND(imor::numeric,4) as imor
  FROM bank_fact_kpis_mensual
  WHERE banco_norm = 'INVEX'
    AND fecha >= '2025-07-01'
  ORDER BY fecha;
" > /tmp/invex_kpis_before.txt
cat /tmp/invex_kpis_before.txt
```

**Criterio de éxito**: Tabla de backup creada. Si la carga falla:
```sql
-- ROLLBACK completo
TRUNCATE bank_fact_kpis_mensual;
INSERT INTO bank_fact_kpis_mensual SELECT * FROM bank_fact_kpis_mensual_bak_20260304;
```

---

## Fase 1: Copiar entrega a incoming

```bash
# 1.1 Copiar desde Windows a incoming
cp -r "/mnt/c/Users/Jaziel Flores/Downloads/drive-download-20260304T143340Z-1-001" \
  plugins/bank-advisor-private/data/raw/incoming/drive-download-20260304T143340Z-1-001

# 1.2 Verificar contenido
ls -lh plugins/bank-advisor-private/data/raw/incoming/drive-download-20260304T143340Z-1-001/ | head -25
```

**Criterio de éxito**: Directorio creado con ~20 archivos, CNBV Excel ~3.3MB.

---

## Fase 2: Dry-run de promote (no toca filesystem)

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
from etl.core.data_promotion import promote_incoming_drop
from pathlib import Path

raw = Path('plugins/bank-advisor-private/data/raw')
result = promote_incoming_drop(
    incoming_dir=raw / 'incoming/drive-download-20260304T143340Z-1-001',
    current_dir=raw / 'current',
    fallback_dir=raw,
    dry_run=True,
)

print('=== DRY RUN: Promote Plan ===')
for item in result.items:
    tag = 'REQUIRED' if item.required else 'optional'
    print(f'  {item.action:8s} [{tag:8s}] {item.dest_rel}')
    if item.source:
        print(f'           <- {item.source}')
    if item.note:
        print(f'           NOTE: {item.note}')

missing = result.missing_required
if missing:
    print(f'\n⚠ MISSING REQUIRED: {[m.dest_rel for m in missing]}')
else:
    print(f'\n✓ Todos los archivos requeridos encontrados')
"
```

**Criterio de éxito**: 0 missing required. CNBV Excel apunta a la nueva entrega.

**Verificar que CNBV_Cartera_Bancos_V2.xlsx apuntara al nuevo** (no al viejo de 20260302).

---

## Fase 3: Promote real (actualizar symlinks)

```bash
# 3.1 Promote
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
from etl.core.data_promotion import promote_incoming_drop
from pathlib import Path

raw = Path('plugins/bank-advisor-private/data/raw')
result = promote_incoming_drop(
    incoming_dir=raw / 'incoming/drive-download-20260304T143340Z-1-001',
    current_dir=raw / 'current',
    fallback_dir=raw,
    force=True,
)

for item in result.items:
    print(f'  {item.action:8s} {item.dest_rel} <- {item.source}')
"

# 3.2 Symlink manual: BM (el promote no lo hace automaticamente)
ln -sf ../incoming/drive-download-20260304T143340Z-1-001/sh_datos_40.csv \
  plugins/bank-advisor-private/data/raw/current/BM_SH_DATOS_40.csv

# 3.3 Verificar symlinks actualizados
ls -la plugins/bank-advisor-private/data/raw/current/CNBV_Cartera_Bancos_V2.xlsx
ls -la plugins/bank-advisor-private/data/raw/current/BM_SH_DATOS_40.csv
ls -la plugins/bank-advisor-private/data/raw/current/ICAP_Bancos.xlsx
```

**Criterio de éxito**: Symlinks apuntan a `20260304`, no a `20260302`.

---

## Fase 4: Dry-run del ETL Unificado

Ejecutar la carga en modo dry_run para verificar que los loaders leen correctamente
sin escribir a la BD.

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
import polars as pl
from pathlib import Path
from etl.core.loaders_unified import (
    get_data_paths, load_cnbv_cartera, load_instituciones,
    load_castigos, load_castigos_comerciales, load_icap,
    load_tda, load_te_invex, load_corporate_loan
)

paths = get_data_paths(Path('plugins/bank-advisor-private/data/raw/current'))

# Cargar cada fuente y validar shapes
sources = {}
for name, loader in [
    ('cnbv', load_cnbv_cartera),
    ('instituciones', load_instituciones),
    ('castigos', load_castigos),
    ('castigos_comerciales', load_castigos_comerciales),
    ('icap', load_icap),
    ('tda', load_tda),
    ('te', load_te_invex),
    ('corporate_rates', load_corporate_loan),
]:
    try:
        df = loader(paths)
        if hasattr(df, 'collect'):
            df = df.collect()
        sources[name] = df
        print(f'✓ {name:25s} shape={df.shape}')
    except Exception as e:
        print(f'✗ {name:25s} ERROR: {e}')

# Validar CNBV: Nov 2025 debe ser diferente de Oct
cnbv = sources.get('cnbv')
if cnbv is not None:
    print(f'\nCNBV periodos max: {cnbv.select(pl.col(\"periodo\").max()).item() if \"periodo\" in cnbv.columns else \"N/A\"}')

# Validar ICAP: debe llegar a Dic 2025
icap = sources.get('icap')
if icap is not None and 'FECHA' in icap.columns:
    print(f'ICAP fecha max: {icap[\"FECHA\"].max()}')
"
```

**Criterio de éxito**: Todos los loaders `✓`, CNBV con periodo max 202512, ICAP con fecha max 2025-12-01.

---

## Fase 5: Transform dry-run (verificar KPIs sin escribir)

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

# Inspeccionar monthly_kpis
kpis = result.get('monthly_kpis')
if kpis is not None:
    if hasattr(kpis, 'collect'):
        kpis = kpis.collect()
    print(f'monthly_kpis shape: {kpis.shape}')
    print(f'bancos: {sorted(kpis[\"banco_norm\"].unique().to_list())}')
    print(f'fecha min: {kpis[\"fecha\"].min()}, max: {kpis[\"fecha\"].max()}')

    # INVEX Nov/Dic 2025
    invex = kpis.filter(
        (pl.col('banco_norm') == 'INVEX') &
        (pl.col('fecha') >= pl.date(2025, 10, 1))
    ).sort('fecha')
    print(f'\n=== INVEX Oct-Dic 2025 (pre-escritura) ===')
    for r in invex.iter_rows(named=True):
        ct = r.get('cartera_total', 0) or 0
        icap = r.get('icap_total', 0) or 0
        imor = r.get('imor', 0) or 0
        print(f'  {r[\"fecha\"]}  cartera={ct/1e6:,.0f}M  icap={icap:.4f}  imor={imor:.4f}')
else:
    print('ERROR: monthly_kpis no generado')

# Listar todas las tablas resultado
print(f'\nTablas generadas: {list(result.keys())}')
for k, v in result.items():
    if hasattr(v, 'collect'):
        v = v.collect()
    if hasattr(v, 'shape'):
        print(f'  {k}: {v.shape}')
"
```

**Criterio de éxito**:
- `monthly_kpis` contiene INVEX con Nov y Dic 2025
- INVEX cartera_total Nov ≈ 52,312M, Dic ≈ 51,912M (coincide con CNBV Excel en MDP)
- ICAP Dic ≈ 16.38
- **Solo ~7 bancos** (los dual-source del CNBV Excel). Esto es ESPERADO sin AG.

---

## Fase 6: Carga real con UPSERT (preserva datos existentes)

> **IMPORTANTE**: Usar `use_upsert=True` para NO borrar los 56 bancos AG-only.
> NO usar el orquestador (`RefreshOrchestrator`) porque usa TRUNCATE+INSERT.

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
import os

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

# UPSERT — preserva datos de bancos AG-only
save_to_normalized_schema(result, os.environ['DATABASE_URL'], use_upsert=True)
print('✓ Carga con UPSERT completada')
"
```

**Criterio de éxito**: Sin errores. Mensaje `✓ Carga con UPSERT completada`.

---

## Fase 7: IMOR Comercial

```bash
PYTHONPATH=plugins/bank-advisor-private $VENV -c "
import sys, os
sys.argv = ['',
    '--xlsx', 'plugins/bank-advisor-private/data/raw/current/CNBV_Cartera_Bancos_V2.xlsx',
    '--castigos', 'plugins/bank-advisor-private/data/raw/current/Castigos Comerciales.xlsx',
    '--db-url', os.environ['DATABASE_URL']
]
from etl.core.loaders.loaders_imor_comercial import main
main()
"
```

---

## Fase 8: Refresh Materialized Views

```sql
SELECT * FROM bank_mv_refresh_all();
```

Si falla con "concurrently":
```sql
REFRESH MATERIALIZED VIEW bank_mv_ranking_cartera_mensual;
REFRESH MATERIALIZED VIEW bank_mv_evolucion_cartera_banco;
REFRESH MATERIALIZED VIEW bank_mv_cartera_por_estado;
```

---

## Fase 9: Validacion post-carga

```bash
# 9.1 INVEX KPIs Oct-Dic 2025
psql $DATABASE_URL -c "
  SELECT banco_norm, fecha::date,
         ROUND(cartera_total::numeric/1e6) as cartera_MM,
         ROUND(icap_total::numeric,4) as icap,
         ROUND(imor::numeric,4) as imor,
         ROUND(imor_comercial::numeric,4) as imor_com
  FROM bank_fact_kpis_mensual
  WHERE banco_norm = 'INVEX'
    AND fecha >= '2025-10-01'
  ORDER BY fecha;
"

# 9.2 Verificar que bancos AG-only NO se perdieron
psql $DATABASE_URL -c "
  SELECT COUNT(DISTINCT banco_norm) as total_bancos,
         COUNT(*) as total_rows
  FROM bank_fact_kpis_mensual
  WHERE cartera_total > 0;
"

# 9.3 Comparar antes vs después
psql $DATABASE_URL -c "
  SELECT
    (SELECT COUNT(*) FROM bank_fact_kpis_mensual) as rows_after,
    (SELECT COUNT(*) FROM bank_fact_kpis_mensual_bak_20260304) as rows_before;
"

# 9.4 Verificar periodo_id no es NULL
psql $DATABASE_URL -c "
  SELECT COUNT(*) as nulls FROM bank_fact_kpis_mensual WHERE periodo_id IS NULL;
"

# 9.5 Fix periodo_id si hay NULLs
psql $DATABASE_URL -c "
  UPDATE bank_fact_kpis_mensual
  SET periodo_id = EXTRACT(YEAR FROM fecha)::int * 100 + EXTRACT(MONTH FROM fecha)::int
  WHERE periodo_id IS NULL;
"

# 9.6 Verificar escala (no debe haber ICAP < 1 ni cartera sospechosamente baja)
psql $DATABASE_URL -c "
  SELECT banco_norm, COUNT(*)
  FROM bank_fact_kpis_mensual
  WHERE icap_total > 0 AND icap_total < 1
  GROUP BY banco_norm;
"
```

**Criterios de éxito**:
- INVEX Nov: cartera ≈ 52,312M, Dic: ≈ 51,912M
- INVEX ICAP Dic ≈ 16.38
- Total bancos ≥ 17 (los que habia antes)
- `rows_after >= rows_before` (no se perdieron filas)
- 0 NULLs en periodo_id (o fix aplicado)
- 0 filas con ICAP < 1

---

## Fase 10: Limpieza

```bash
# Solo después de validar que todo está bien:

# 10.1 Drop tabla de backup (cuando estemos seguros)
# psql $DATABASE_URL -c "DROP TABLE IF EXISTS bank_fact_kpis_mensual_bak_20260304;"

# 10.2 Flush Redis cache del backend (si aplica)
# docker exec octavios-backend redis-cli FLUSHDB

# 10.3 Restart backend para que tome datos frescos
# docker compose -f infra/docker-compose.yml --env-file envs/.env restart backend
```

---

## Rollback

Si algo sale mal en cualquier fase:

```sql
-- Restaurar tabla completa desde backup
TRUNCATE bank_fact_kpis_mensual;
INSERT INTO bank_fact_kpis_mensual SELECT * FROM bank_fact_kpis_mensual_bak_20260304;

-- Restaurar symlinks al estado anterior (20260302)
-- Re-ejecutar promote con la entrega anterior
```

---

## Resumen de riesgos mitigados

| Riesgo | Mitigacion |
|--------|-----------|
| Perder 56 bancos AG-only | `use_upsert=True` (NO usar orquestador) |
| Romper escala cartera (MDP vs pesos) | Dry-run Fase 5 verifica valores esperados |
| ICAP en escala decimal | Validacion Fase 9.6 detecta ICAP < 1 |
| periodo_id NULL (invisible en frontend) | Fix automatico Fase 9.5 |
| Datos corruptos | Backup Fase 0, rollback disponible |
| Symlinks apuntando a entrega vieja | Dry-run promote Fase 2 verifica |
