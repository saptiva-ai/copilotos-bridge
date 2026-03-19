# Plan de Normalización de Base de Datos a 3NF

> **Objetivo**: Normalizar el esquema de base de datos a 3NF, consolidar catálogos duplicados, y estandarizar nomenclatura.

## Convención de Nomenclatura (Aprobada por Usuario)

| Tipo | Prefijo | Ejemplo |
|------|---------|---------|
| Dimensiones | `bank_dim_*` | `bank_dim_institucion` |
| Tablas de Hechos | `bank_fact_*` | `bank_fact_kpis_mensual` |
| Vistas Materializadas | `bank_mv_*` | `bank_mv_ranking_cartera` |

**Legacy**: Migrar datos y eliminar tablas antiguas (no mantener en paralelo)

---

## Análisis de Impacto

### Tablas Afectadas (Principales)

| Tabla Actual | Nueva Tabla | Registros Est. |
|--------------|-------------|----------------|
| `monthly_kpis` | `bank_fact_kpis_mensual` | ~15K |
| `hip_cat_institucion` | `bank_dim_institucion` | ~100 |
| `hip_ag_catalogo_instituciones` | (ELIMINAR - duplicado) | - |
| `hip_bm_catalogo_instituciones` | (ELIMINAR - duplicado) | - |
| `hip_cartera_comercial_base_total` | `bank_fact_cartera_comercial` | ~4.2M |
| `hip_cartera_comercial_base_marginal` | `bank_fact_cartera_comercial_marginal` | ~767K |
| `hip_cartera_vivienda_*` | `bank_fact_cartera_vivienda` | ~1.5M |
| `hip_cartera_total_mensual` | `bank_fact_cartera_total_mensual` | ~3K |
| `metricas_financieras_ext` | `bank_fact_metricas_financieras` | ~650 |
| `hip_info_operativa_consolidada` | `bank_fact_info_operativa` | ~500 |

### Catálogos a Consolidar → Dimensiones

| Catálogos Actuales | Nueva Dimensión |
|--------------------|-----------------|
| `hip_cat_institucion`, `hip_ag_catalogo_instituciones`, `hip_bm_catalogo_instituciones` | `bank_dim_institucion` |
| (NUEVO) | `bank_dim_periodo` |
| `hip_cat_pais_estado` | `bank_dim_estado` |
| `hip_cat_sector` | `bank_dim_sector` |
| `hip_cat_moneda` | `bank_dim_moneda` |
| `hip_cat_tipo_cartera` | `bank_dim_tipo_cartera` |
| `hip_cat_tamano_empresa` | `bank_dim_tamano_empresa` |
| `hip_cat_actividad_economica` | `bank_dim_actividad_economica` |
| `hip_cat_destino_credito` | `bank_dim_destino_credito` |
| `hip_cat_apoyo` | `bank_dim_apoyo` |

### Archivos de Código Afectados (170 archivos, críticos resaltados)

| Archivo | Impacto | Prioridad |
|---------|---------|-----------|
| `src/bankadvisor/services/template_sql_generator.py` | `METRIC_TABLE_ROUTING` completo | **CRÍTICO** |
| `config/synonyms.yaml` | `data_source` references | **CRÍTICO** |
| `src/bankadvisor/models/kpi.py` | `__tablename__`, columns | **CRÍTICO** |
| `src/bankadvisor/models/hip_cartera_total.py` | `__tablename__` | Alto |
| `etl/core/loaders/*.py` | Table names | Alto |
| `migrations/*.sql` | Schema definitions | Medio |
| Tests (`170+ archivos`) | Assertions con nombres | Medio |

---

## Fases de Implementación

### Fase 0: Preparación y Backup (Pre-requisito)
**Duración estimada**: 1 sesión

1. [ ] Crear backup de todas las tablas afectadas
2. [ ] Documentar estado actual de datos (row counts, checksums)
3. [ ] Crear script de rollback

### Fase 1: Crear Dimensiones (Sin downtime)
**Duración estimada**: 1-2 sesiones

#### 1.1 Migración SQL: Crear Dimensiones

```sql
-- migrations/020_bank_dim_institucion.sql
CREATE TABLE bank_dim_institucion (
    institucion_id SERIAL PRIMARY KEY,
    clave_cnbv VARCHAR(20) UNIQUE NOT NULL,
    nombre_corto VARCHAR(100) NOT NULL,
    nombre_completo VARCHAR(200),
    tipo_institucion VARCHAR(50),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Poblar desde catálogo existente
INSERT INTO bank_dim_institucion (clave_cnbv, nombre_corto, tipo_institucion)
SELECT clave_institucion, institucion, tipo
FROM hip_cat_institucion;
```

```sql
-- migrations/021_bank_dim_periodo.sql
CREATE TABLE bank_dim_periodo (
    periodo_id INTEGER PRIMARY KEY,  -- YYYYMM format
    fecha DATE NOT NULL,
    anio SMALLINT NOT NULL,
    mes SMALLINT NOT NULL,
    trimestre SMALLINT NOT NULL,
    semestre SMALLINT NOT NULL,
    nombre_mes VARCHAR(20),
    es_cierre_anual BOOLEAN DEFAULT FALSE
);

-- Poblar 2000-2030
INSERT INTO bank_dim_periodo (...)
SELECT ... FROM generate_series(2000, 2030);
```

```sql
-- migrations/022_bank_dim_estado.sql
CREATE TABLE bank_dim_estado (
    estado_id SERIAL PRIMARY KEY,
    clave_pais VARCHAR(3) NOT NULL DEFAULT 'MEX',
    clave_estado VARCHAR(5) NOT NULL,
    nombre_estado VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    UNIQUE(clave_pais, clave_estado)
);
```

#### 1.2 Tareas
- [ ] Crear `migrations/020_bank_dim_institucion.sql`
- [ ] Crear `migrations/021_bank_dim_periodo.sql`
- [ ] Crear `migrations/022_bank_dim_estado.sql`
- [ ] Crear `migrations/023_bank_dim_auxiliares.sql` (sector, moneda, etc.)
- [ ] Ejecutar migraciones en entorno de desarrollo
- [ ] Validar integridad de datos en dimensiones

### Fase 2: Renombrar Tablas de Hechos + Agregar FKs
**Duración estimada**: 2-3 sesiones

#### 2.1 Migración SQL: Renombrar y Agregar FKs

```sql
-- migrations/024_rename_fact_tables.sql

-- 2.1 Renombrar monthly_kpis
ALTER TABLE monthly_kpis RENAME TO bank_fact_kpis_mensual;

-- 2.2 Agregar columnas FK (nullable inicialmente)
ALTER TABLE bank_fact_kpis_mensual
ADD COLUMN institucion_id INTEGER,
ADD COLUMN periodo_id INTEGER;

-- 2.3 Poblar FKs
UPDATE bank_fact_kpis_mensual bfk
SET institucion_id = bdi.institucion_id
FROM bank_dim_institucion bdi
WHERE LOWER(TRIM(bfk.banco_norm)) = LOWER(TRIM(bdi.nombre_corto));

UPDATE bank_fact_kpis_mensual
SET periodo_id = EXTRACT(YEAR FROM fecha)::INT * 100 + EXTRACT(MONTH FROM fecha)::INT;

-- 2.4 Verificar integridad
SELECT COUNT(*) as sin_match FROM bank_fact_kpis_mensual WHERE institucion_id IS NULL;

-- 2.5 Aplicar constraints (después de validar 0 sin match)
ALTER TABLE bank_fact_kpis_mensual
ADD CONSTRAINT fk_bfk_institucion FOREIGN KEY (institucion_id)
REFERENCES bank_dim_institucion(institucion_id);

ALTER TABLE bank_fact_kpis_mensual
ADD CONSTRAINT fk_bfk_periodo FOREIGN KEY (periodo_id)
REFERENCES bank_dim_periodo(periodo_id);
```

#### 2.2 Tareas
- [ ] Crear `migrations/024_rename_monthly_kpis.sql`
- [ ] Crear `migrations/025_rename_hip_cartera_comercial.sql`
- [ ] Crear `migrations/026_rename_hip_cartera_vivienda.sql`
- [ ] Crear `migrations/027_rename_metricas_financieras.sql`
- [ ] Crear `migrations/028_rename_info_operativa.sql`
- [ ] Ejecutar migraciones en desarrollo
- [ ] Validar integridad de FKs (0 huérfanos)

### Fase 3: Actualizar Código de Aplicación
**Duración estimada**: 2-3 sesiones

#### 3.1 template_sql_generator.py

```python
# ANTES
METRIC_TABLE_ROUTING = {
    "sucursales": {"table": "hip_info_operativa_consolidada", "date_col": "fecha", "bank_col": "banco_norm"},
    ...
}

# DESPUÉS
METRIC_TABLE_ROUTING = {
    "sucursales": {"table": "bank_fact_info_operativa", "date_col": "fecha", "bank_col": "banco_norm"},
    ...
}
```

#### 3.2 synonyms.yaml

```yaml
# ANTES
hip_cartera_comercial_total:
    data_source: "hip_cartera_total_mensual"

# DESPUÉS
cartera_comercial_total_hip:
    data_source: "bank_fact_cartera_total_mensual"
```

#### 3.3 Modelos SQLAlchemy

```python
# ANTES
class MonthlyKPI(Base):
    __tablename__ = "monthly_kpis"

# DESPUÉS
class BankFactKpisMensual(Base):
    __tablename__ = "bank_fact_kpis_mensual"

    # Nuevas FKs
    institucion_id = Column(Integer, ForeignKey("bank_dim_institucion.institucion_id"))
    periodo_id = Column(Integer, ForeignKey("bank_dim_periodo.periodo_id"))
```

#### 3.4 Tareas
- [ ] Actualizar `METRIC_TABLE_ROUTING` en `template_sql_generator.py`
- [ ] Actualizar `synonyms.yaml` - todos los `data_source`
- [ ] Actualizar modelos SQLAlchemy (`kpi.py`, `hip_cartera_total.py`, etc.)
- [ ] Actualizar ETL loaders (`etl/core/loaders/*.py`)
- [ ] Actualizar `schema_validator.py` si existe whitelist de tablas

### Fase 4: Crear Vistas Materializadas
**Duración estimada**: 1-2 sesiones

#### 4.1 Vistas Materializadas

```sql
-- migrations/030_bank_mv_ranking_cartera.sql
CREATE MATERIALIZED VIEW bank_mv_ranking_cartera_mensual AS
WITH ultimo_periodo AS (
    SELECT MAX(periodo_id) as periodo_id FROM bank_fact_kpis_mensual
)
SELECT
    up.periodo_id,
    bdi.nombre_corto as banco,
    bfk.cartera_total,
    bfk.imor,
    bfk.market_share_pct,
    RANK() OVER (ORDER BY bfk.cartera_total DESC) as ranking_cartera
FROM bank_fact_kpis_mensual bfk
JOIN bank_dim_institucion bdi ON bfk.institucion_id = bdi.institucion_id
CROSS JOIN ultimo_periodo up
WHERE bfk.periodo_id = up.periodo_id
  AND bfk.cartera_total > 0
ORDER BY bfk.cartera_total DESC;

CREATE UNIQUE INDEX idx_bank_mv_ranking_banco
ON bank_mv_ranking_cartera_mensual(periodo_id, banco);
```

#### 4.2 Tareas
- [ ] Crear `migrations/030_bank_mv_ranking_cartera.sql`
- [ ] Crear `migrations/031_bank_mv_evolucion_cartera.sql`
- [ ] Crear `migrations/032_bank_mv_comparativa_bancos.sql`
- [ ] Crear `migrations/033_bank_mv_cartera_por_estado.sql`
- [ ] Crear `migrations/034_bank_mv_resumen_sistema.sql`
- [ ] Configurar refresh automático (cron o post-ETL)

### Fase 5: Limpieza y Eliminación de Legacy
**Duración estimada**: 1 sesión

#### 5.1 Tareas
- [ ] Eliminar columnas redundantes (`banco_norm`, `fecha` después de validación)
- [ ] Eliminar catálogos duplicados (`hip_ag_catalogo_instituciones`, `hip_bm_catalogo_instituciones`)
- [ ] Renombrar catálogos restantes a `bank_dim_*_legacy` (transición)
- [ ] Actualizar documentación
- [ ] Actualizar tests

### Fase 6: Testing y Validación
**Duración estimada**: 1-2 sesiones

- [ ] Ejecutar suite completa de tests
- [ ] Verificar queries NL2SQL generan SQL correcto
- [ ] Verificar performance (EXPLAIN ANALYZE)
- [ ] Verificar vistas materializadas se refrescan correctamente
- [ ] Smoke tests en entorno de staging

---

## Mapeo de Nombres Completo

### Tablas de Hechos

| Tabla Actual | Nueva Tabla |
|--------------|-------------|
| `monthly_kpis` | `bank_fact_kpis_mensual` |
| `hip_cartera_comercial_base_total` | `bank_fact_cartera_comercial` |
| `hip_cartera_comercial_base_marginal` | `bank_fact_cartera_comercial_marginal` |
| `hip_cartera_comercial_hist_tamano_total` | `bank_fact_cartera_comercial_hist_tamano` |
| `hip_cartera_comercial_hist_tamano_marginal` | `bank_fact_cartera_comercial_hist_tamano_marginal` |
| `hip_cartera_comercial_hist_tipo_total` | `bank_fact_cartera_comercial_hist_tipo` |
| `hip_cartera_comercial_hist_tipo_marginal` | `bank_fact_cartera_comercial_hist_tipo_marginal` |
| `hip_cartera_vivienda_marginales` | `bank_fact_cartera_vivienda` |
| `hip_cartera_total_mensual` | `bank_fact_cartera_total_mensual` |
| `hip_cartera_por_tamano` | `bank_fact_cartera_por_tamano` |
| `hip_cartera_por_moneda` | `bank_fact_cartera_por_moneda` |
| `hip_cartera_por_destino` | `bank_fact_cartera_por_destino` |
| `hip_cartera_por_destino_agrupado` | `bank_fact_cartera_por_destino_agrupado` |
| `metricas_financieras_ext` | `bank_fact_metricas_financieras` |
| `metricas_cartera_segmentada` | `bank_fact_cartera_segmentada` |
| `hip_info_operativa_consolidada` | `bank_fact_info_operativa` |
| `hip_balance_sheet_items` | `bank_fact_balance_sheet` |
| `hip_income_statement_items` | `bank_fact_income_statement` |
| `hip_capital_metrics_detail` | `bank_fact_capital_metrics` |
| `hip_analisis_general_metricas` | `bank_fact_analisis_general` |

### Dimensiones

| Catálogo Actual | Nueva Dimensión |
|-----------------|-----------------|
| `hip_cat_institucion` | `bank_dim_institucion` |
| `hip_cat_pais_estado` | `bank_dim_estado` |
| `hip_cat_sector` | `bank_dim_sector` |
| `hip_cat_moneda` | `bank_dim_moneda` |
| `hip_cat_tipo_cartera` | `bank_dim_tipo_cartera` |
| `hip_cat_tamano_empresa` | `bank_dim_tamano_empresa` |
| `hip_cat_actividad_economica` | `bank_dim_actividad_economica` |
| `hip_cat_destino_credito` | `bank_dim_destino_credito` |
| `hip_cat_apoyo` | `bank_dim_apoyo` |
| (NUEVO) | `bank_dim_periodo` |

### Vistas Materializadas

| Nueva Vista | Propósito |
|-------------|-----------|
| `bank_mv_ranking_cartera_mensual` | Rankings por cartera total |
| `bank_mv_evolucion_cartera_banco` | Evolución histórica + YoY/MoM |
| `bank_mv_comparativa_bancos` | Comparativa multi-banco últimos 3 periodos |
| `bank_mv_cartera_por_estado` | Distribución geográfica |
| `bank_mv_resumen_sistema` | Totales sistema financiero |

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Datos huérfanos en FKs | Validar 0 NULL antes de aplicar constraint |
| Downtime durante RENAME | Usar transacciones, hacer en horario bajo |
| Queries legacy fallan | Crear vistas de compatibilidad temporales |
| ETL falla post-migración | Actualizar loaders ANTES de ejecutar ETL |
| Performance degradada | Verificar índices, EXPLAIN ANALYZE |

---

## Checklist de Validación Post-Migración

- [ ] Todas las FKs apuntan a registros existentes (0 huérfanos)
- [ ] Row counts iguales antes/después del rename
- [ ] Índices creados y utilizados (verificar con EXPLAIN ANALYZE)
- [ ] Vistas materializadas pobladas correctamente
- [ ] Queries del Bank Advisor funcionan con nuevo schema
- [ ] Performance igual o mejor que schema anterior
- [ ] ETL actualizado para usar nuevas tablas
- [ ] Tests de regresión pasando

---

## Archivos a Crear/Modificar

### Nuevos Archivos (Migraciones)
```
plugins/bank-advisor-private/migrations/
├── 020_bank_dim_institucion.sql
├── 021_bank_dim_periodo.sql
├── 022_bank_dim_estado.sql
├── 023_bank_dim_auxiliares.sql
├── 024_rename_monthly_kpis.sql
├── 025_rename_hip_cartera_comercial.sql
├── 026_rename_hip_cartera_vivienda.sql
├── 027_rename_metricas_financieras.sql
├── 028_rename_info_operativa.sql
├── 030_bank_mv_ranking_cartera.sql
├── 031_bank_mv_evolucion_cartera.sql
├── 032_bank_mv_comparativa_bancos.sql
├── 033_bank_mv_cartera_por_estado.sql
└── 034_bank_mv_resumen_sistema.sql
```

### Archivos a Modificar
```
plugins/bank-advisor-private/
├── src/bankadvisor/services/template_sql_generator.py  # METRIC_TABLE_ROUTING
├── src/bankadvisor/models/kpi.py                       # __tablename__, FKs
├── src/bankadvisor/models/hip_cartera_total.py         # __tablename__
├── config/synonyms.yaml                                # data_source refs
├── etl/core/loaders/*.py                               # Table names
└── src/bankadvisor/utils/schema_validator.py           # Whitelist
```

---

*Plan creado: 2026-01-22*
*Versión: 1.0*
