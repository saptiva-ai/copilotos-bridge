# ETL Enhancement - BankAdvisor Plugin

Este documento describe el proceso de carga de datos para las métricas ICAP, TDA, TASA_MN y TASA_ME.

## Resumen

El ETL Enhancement carga datos desde archivos Excel/CSV hacia la tabla `monthly_kpis` de PostgreSQL.

**Archivos procesados**:
- `ICAP_Bancos.xlsx` → columna `icap_total`
- `TDA.xlsx` → columna `tda_cartera_total`
- `CorporateLoan_CNBVDB.csv` → columnas `tasa_mn`, `tasa_me`

**Resultados**:
- ✅ ICAP: 204 registros cargados (102 INVEX + 102 SISTEMA)
- ✅ TDA: 206 registros cargados (103 INVEX + 103 SISTEMA)
- ✅ TASA_MN: 205 registros cargados (102 INVEX + 103 SISTEMA)
- ✅ TASA_ME: 203 registros cargados (100 INVEX + 103 SISTEMA)

## Estructura de Archivos

```
plugins/bank-advisor-private/
├── src/bankadvisor/
│   ├── etl_loader.py              # ETL base (cartera, IMOR, ICOR, etc.)
│   └── etl_loader_enhanced.py     # ETL enhancement (ICAP, TDA, Tasas)
├── scripts/
│   ├── run_etl_enhancement.sh     # Script ejecutable para correr ETL
│   └── inspect_excel_files.py     # Utilidad para inspeccionar archivos
├── data/raw/
│   ├── ICAP_Bancos.xlsx
│   ├── TDA.xlsx
│   ├── CorporateLoan_CNBVDB.csv
│   └── ...
├── migrations/
│   └── 001_add_missing_columns.sql
└── docs/
    ├── etl_data_status.md         # Estado detallado del ETL
    └── nl2sql_status_report.md    # Estado del pipeline NL2SQL
```

## Uso

### Ejecutar ETL Enhancement

**Opción 1: Docker (recomendado)**
```bash
cd plugins/bank-advisor-private
./scripts/run_etl_enhancement.sh
```

**Opción 2: Local (requiere virtualenv)**
```bash
cd plugins/bank-advisor-private
./scripts/run_etl_enhancement.sh --local
```

### Verificar Resultados

**Conteo de registros**:
```bash
docker exec -i octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor -c "
  SELECT
    COUNT(*) as total_rows,
    COUNT(icap_total) as icap_count,
    COUNT(tda_cartera_total) as tda_count,
    COUNT(tasa_mn) as tasa_mn_count,
    COUNT(tasa_me) as tasa_me_count
  FROM monthly_kpis;
"
```

**Output esperado**:
```
 total_rows | icap_count | tda_count | tasa_mn_count | tasa_me_count
------------+------------+-----------+---------------+---------------
        206 |        204 |       206 |           205 |           203
```

**Ver datos de ejemplo**:
```bash
docker exec -i octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor -c "
  SELECT fecha, banco_norm, icap_total, tda_cartera_total, tasa_mn
  FROM monthly_kpis
  WHERE banco_norm = 'INVEX'
  ORDER BY fecha DESC
  LIMIT 5;
"
```

## Detalles Técnicos

### Funciones Principales

#### `load_icap_data(data_root: str) -> pd.DataFrame`
- Lee `ICAP_Bancos.xlsx`
- Procesa 13,559 registros
- Normaliza nombres de bancos (INVEX, otros)
- Retorna DataFrame con: `[fecha, banco_norm, icap_total]`

#### `load_tda_data(data_root: str) -> pd.DataFrame`
- Lee `TDA.xlsx`
- Procesa 17,261 registros
- Mapea códigos de institución (40059 → INVEX)
- Retorna DataFrame con: `[fecha, cve_inst, tda_cartera_total]`

#### `load_tasas_data(data_root: str) -> pd.DataFrame`
- Lee `CorporateLoan_CNBVDB.csv` (228 MB)
- Usa chunking (50,000 rows/chunk) para manejar tamaño
- Procesa 1,746,826 registros totales (1.38M MN + 366K ME)
- **IMPORTANTE**: Usa columna `'Currency'` (no `'Currency type'`) para distinguir:
  - `'Moneda nacional'` → TASA_MN
  - `'Moneda extranjera'` → TASA_ME
- Retorna DataFrame con: `[fecha, cve_inst, currency_type, tasa_promedio]`

#### `aggregate_sistema_metrics(df, metric_col) -> pd.DataFrame`
- Agrega todos los bancos excepto INVEX en "SISTEMA"
- Calcula promedio simple (TODO: implementar promedio ponderado por cartera)
- Retorna DataFrame con: `[fecha, banco_norm='SISTEMA', metric_col]`

#### `update_monthly_kpis_with_metrics(engine, icap_df, tda_df, tasas_df)`
- Actualiza tabla `monthly_kpis` vía SQL UPDATE con JOIN
- Crea tablas temporales para cada métrica
- Procesa INVEX y SISTEMA por separado
- Limpia tablas temporales al finalizar

### Estrategia de Actualización

El ETL usa **UPDATE** en lugar de **INSERT** porque:
1. Los registros base ya existen (creados por `etl_loader.py`)
2. Solo agrega valores a columnas previamente vacías
3. Hace JOIN por `(fecha, banco_norm)` para encontrar filas correctas

**SQL de ejemplo** (ICAP):
```sql
UPDATE monthly_kpis mk
SET icap_total = ti.icap_total
FROM temp_icap ti
WHERE DATE_TRUNC('month', mk.fecha) = DATE_TRUNC('month', ti.fecha)
  AND mk.banco_norm = ti.banco_norm
  AND mk.banco_norm = 'INVEX';
```

### Manejo de Datos Faltantes

**ICAP**: 2 registros sin datos (204/206 = 99.0% coverage)
- Probablemente meses recientes donde aún no se publica ICAP

**TDA**: Cobertura completa (206/206 = 100%)

**TASA_MN**: 1 registro sin datos (205/206 = 99.5% coverage)

**TASA_ME**: 3 registros sin datos (203/206 = 98.5% coverage)
- Archivo fuente contiene 366,045 registros de Moneda Extranjera
- 12,797 registros INVEX en ME procesados
- Fechas disponibles: 2016-06 a 2025-07

## Tiempo de Ejecución

**Total**: ~30 segundos

Desglose:
- ICAP: ~2 segundos
- TDA: ~1 segundo
- Tasas: ~25 segundos (archivo grande 228 MB)
- Actualizaciones SQL: ~2 segundos

## Dependencias

El script requiere:
- Python 3.11+
- pandas
- sqlalchemy
- openpyxl (para leer Excel)
- structlog
- core.config (settings del proyecto)

Estas dependencias ya están instaladas en el contenedor Docker.

## Troubleshooting

### Error: "Permission denied" al ejecutar script
```bash
# Dar permisos de ejecución
chmod +x scripts/run_etl_enhancement.sh
```

### Error: "Container not running"
```bash
# Levantar contenedores
docker-compose up -d bank-advisor postgres
```

### Error: "No module named 'bankadvisor'"
```bash
# Asegurarse de estar en el directorio correcto
cd plugins/bank-advisor-private

# Si ejecutas local, activa virtualenv
source venv/bin/activate
```

### Verificar que archivos existan
```bash
ls -lh data/raw/ICAP_Bancos.xlsx
ls -lh data/raw/TDA.xlsx
ls -lh data/raw/CorporateLoan_CNBVDB.csv
```

### Ver logs del contenedor
```bash
docker logs octavios-chat-bajaware_invex-bank-advisor
```

## Mantenimiento

### Re-ejecutar ETL

El ETL es **idempotente**: puede ejecutarse múltiples veces sin duplicar datos.

Si hay nuevos datos en los archivos fuente:
1. Reemplazar archivos en `data/raw/`
2. Re-ejecutar `./scripts/run_etl_enhancement.sh`
3. Verificar resultados

### Agregar Nueva Métrica

Para agregar una nueva columna/métrica:

1. **Migración SQL**:
```sql
ALTER TABLE monthly_kpis
ADD COLUMN IF NOT EXISTS nueva_metrica DOUBLE PRECISION;
```

2. **Función de carga** en `etl_loader_enhanced.py`:
```python
def load_nueva_metrica_data(data_root: str) -> pd.DataFrame:
    file_path = os.path.join(data_root, "NuevaMetrica.xlsx")
    df = pd.read_excel(file_path)
    # ... procesamiento ...
    return df
```

3. **Actualizar `run_etl_enhancement()`**:
```python
nueva_metrica_df = load_nueva_metrica_data(data_root)
update_monthly_kpis_with_metrics(engine, ..., nueva_metrica_df)
```

4. **Actualizar documentación** en `docs/etl_data_status.md`

## Referencias

- **Estado del ETL**: `docs/etl_data_status.md`
- **Pipeline NL2SQL**: `docs/nl2sql_status_report.md`
- **Migración SQL**: `migrations/001_add_missing_columns.sql`
- **Código fuente**: `src/bankadvisor/etl_loader_enhanced.py`

## Contacto

Para preguntas o problemas con el ETL, revisar:
1. Documentación en `docs/etl_data_status.md`
2. Logs del contenedor Docker
3. Verificar estructura de archivos fuente

---

**Última actualización**: 2025-11-27
**Versión**: 1.0.0
**Estado**: ✅ Producción
