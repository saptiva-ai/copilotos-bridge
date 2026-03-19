# Plan: Tarjetas de Credito Data Source

**Fecha**: 2026-01-28
**Opcion Seleccionada**: B - Materialized View
**Esfuerzo Estimado**: 4-6 horas

---

## Resumen

Crear una materialized view `bank_mv_cartera_tdc` que exponga los datos de tarjetas de credito desde `hip_analisis_general`, siguiendo el patron de las 8 MVs existentes (migrations 030-049).

---

## Phase 1: Migration SQL

**Archivo**: `plugins/bank-advisor-private/migrations/052_create_mv_cartera_tdc.sql`

### 1.1 Crear Materialized View

```sql
-- ============================================
-- Migration 052: Materialized View Cartera TDC
-- ============================================
-- Expone datos de tarjetas de credito desde hip_analisis_general
-- Sigue patron de bank_mv_cartera_por_actividad (migration 047)

CREATE MATERIALIZED VIEW IF NOT EXISTS bank_mv_cartera_tdc AS
WITH tdc_data AS (
    SELECT
        ag.institucion,
        ag.periodo,
        ag.concepto,
        ag.valor
    FROM hip_analisis_general ag
    WHERE ag.concepto IN (
        -- Balance Sheet: Cartera TDC por etapa IFRS9
        40100207,  -- Tarjeta de credito (total)
        40100246,  -- Tarjeta de credito etapa 1
        40100285,  -- Tarjeta de credito etapa 2
        40100324,  -- Tarjeta de credito etapa 3 (vencida)
        40100363,  -- Tarjeta de credito (variante)
        40100402,  -- Tarjeta de credito (variante)
        -- Indicadores
        40200041,  -- IMOR TDC
        40200102,  -- Cobertura TDC
        40200124   -- IMOR TDC (variante)
    )
)
SELECT
    i.institucion_id,
    i.nombre_corto AS banco,
    i.clave_cnbv,
    p.periodo_id,
    p.periodo,
    p.fecha,
    p.anio,
    p.mes,
    -- Cartera TDC Total (MDP)
    COALESCE(SUM(CASE WHEN d.concepto = 40100207 THEN d.valor END), 0) AS cartera_tdc,
    -- Cartera por Etapa IFRS9
    COALESCE(SUM(CASE WHEN d.concepto = 40100246 THEN d.valor END), 0) AS cartera_tdc_etapa1,
    COALESCE(SUM(CASE WHEN d.concepto = 40100285 THEN d.valor END), 0) AS cartera_tdc_etapa2,
    COALESCE(SUM(CASE WHEN d.concepto = 40100324 THEN d.valor END), 0) AS cartera_tdc_vencida,
    -- Indicadores
    MAX(CASE WHEN d.concepto IN (40200041, 40200124) THEN d.valor END) AS imor_tdc,
    MAX(CASE WHEN d.concepto = 40200102 THEN d.valor END) AS icor_tdc,
    -- Metricas calculadas
    CASE
        WHEN COALESCE(SUM(CASE WHEN d.concepto = 40100207 THEN d.valor END), 0) > 0
        THEN COALESCE(SUM(CASE WHEN d.concepto = 40100324 THEN d.valor END), 0) /
             COALESCE(SUM(CASE WHEN d.concepto = 40100207 THEN d.valor END), 1) * 100
        ELSE 0
    END AS imor_tdc_calc
FROM tdc_data d
JOIN bank_dim_institucion i ON d.institucion = i.clave_cnbv
JOIN bank_dim_periodo p ON d.periodo = p.periodo
GROUP BY
    i.institucion_id, i.nombre_corto, i.clave_cnbv,
    p.periodo_id, p.periodo, p.fecha, p.anio, p.mes;

-- Comentario
COMMENT ON MATERIALIZED VIEW bank_mv_cartera_tdc IS
'Cartera de Tarjetas de Credito por banco y periodo. Fuente: hip_analisis_general (040_TO.csv)';
```

### 1.2 Crear Indices

```sql
-- Indice unico para refresh concurrente
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_tdc_inst_periodo
ON bank_mv_cartera_tdc(institucion_id, periodo_id);

-- Indices de busqueda
CREATE INDEX IF NOT EXISTS idx_mv_tdc_banco
ON bank_mv_cartera_tdc(banco);

CREATE INDEX IF NOT EXISTS idx_mv_tdc_fecha
ON bank_mv_cartera_tdc(fecha DESC);

CREATE INDEX IF NOT EXISTS idx_mv_tdc_periodo
ON bank_mv_cartera_tdc(periodo DESC);
```

### 1.3 Funcion de Refresh

```sql
-- Funcion para refresh concurrente
CREATE OR REPLACE FUNCTION refresh_bank_mv_cartera_tdc()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_cartera_tdc;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_bank_mv_cartera_tdc() IS
'Refresh concurrente de MV cartera TDC. Llamar despues de ETL.';
```

### 1.4 Refresh Inicial

```sql
-- Poblado inicial
REFRESH MATERIALIZED VIEW bank_mv_cartera_tdc;
```

---

## Phase 2: Actualizar Analytics Service

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/services/analytics_service.py`

### 2.1 Agregar Import y Modelo

```python
# En la seccion de imports, agregar:
from sqlalchemy import text

# Definir columnas del MV
TDC_COLUMNS = {
    "cartera_tdc": "Cartera TDC total (MDP)",
    "cartera_tdc_etapa1": "Cartera TDC Etapa 1 (vigente)",
    "cartera_tdc_etapa2": "Cartera TDC Etapa 2 (deterioro)",
    "cartera_tdc_vencida": "Cartera TDC Etapa 3 (vencida)",
    "imor_tdc": "IMOR Tarjeta de Credito (%)",
    "icor_tdc": "Cobertura TDC (%)",
}
```

### 2.2 Agregar Metodo de Query

```python
async def get_cartera_tdc(
    self,
    banco: str | None = None,
    periodo: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Obtiene datos de cartera de tarjetas de credito.

    Args:
        banco: Filtro por nombre de banco (opcional)
        periodo: Filtro por periodo YYYYMM (opcional)
        limit: Limite de resultados

    Returns:
        Lista de diccionarios con metricas TDC
    """
    query = """
        SELECT
            banco,
            periodo,
            fecha,
            cartera_tdc,
            cartera_tdc_vencida,
            imor_tdc,
            icor_tdc
        FROM bank_mv_cartera_tdc
        WHERE 1=1
    """
    params = {}

    if banco:
        query += " AND LOWER(banco) LIKE LOWER(:banco)"
        params["banco"] = f"%{banco}%"

    if periodo:
        query += " AND periodo = :periodo"
        params["periodo"] = periodo

    query += " ORDER BY fecha DESC, banco LIMIT :limit"
    params["limit"] = limit

    async with self.session() as session:
        result = await session.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]
```

---

## Phase 3: Actualizar Query Parser

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

### 3.1 Completar Mapping CARTERA_TDC

```python
# Buscar la definicion de CARTERA_TDC y actualizar:
CARTERA_TDC = MetricDefinition(
    name="cartera_tdc",
    triggers=[
        "tarjeta de credito", "tarjetas de credito", "tarjeta credito",
        "tdc", "credit card", "credit cards", "cartera tdc",
        "cartera de tarjetas", "portafolio tdc"
    ],
    table="bank_mv_cartera_tdc",  # <-- Agregar
    column="cartera_tdc",          # <-- Agregar
    description="Cartera total de tarjetas de credito",
    unit="MDP",
)

# Agregar metricas relacionadas:
IMOR_TDC = MetricDefinition(
    name="imor_tdc",
    triggers=[
        "imor tarjeta", "imor tdc", "morosidad tarjeta",
        "morosidad tdc", "indice morosidad tarjeta"
    ],
    table="bank_mv_cartera_tdc",
    column="imor_tdc",
    description="Indice de morosidad de tarjetas de credito",
    unit="%",
)

CARTERA_TDC_VENCIDA = MetricDefinition(
    name="cartera_tdc_vencida",
    triggers=[
        "cartera vencida tdc", "tdc vencida", "tarjeta vencida",
        "cartera vencida tarjeta"
    ],
    table="bank_mv_cartera_tdc",
    column="cartera_tdc_vencida",
    description="Cartera vencida de tarjetas de credito (Etapa 3)",
    unit="MDP",
)
```

---

## Phase 4: Agregar Refresh al ETL

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/etl_runner.py`

### 4.1 Agregar Refresh de MV

```python
# En la funcion run_etl_once(), despues de cargar datos:

async def refresh_materialized_views(session):
    """Refresh all analytics materialized views."""
    mvs = [
        "bank_mv_ranking_cartera_mensual",
        "bank_mv_evolucion_cartera",
        "bank_mv_cartera_por_actividad",
        "bank_mv_cartera_por_tamano",
        "bank_mv_vivienda_por_producto",
        "bank_mv_vivienda_por_perfil",
        "bank_mv_cartera_por_estado",
        "bank_mv_metricas_financieras",
        "bank_mv_cartera_tdc",  # <-- Agregar
    ]
    for mv in mvs:
        await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
        logger.info(f"Refreshed {mv}")
```

---

## Phase 5: Tests

**Archivo**: `plugins/bank-advisor-private/tests/unit/test_analytics_tdc.py`

### 5.1 Test de MV

```python
import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_mv_cartera_tdc_exists(db_session):
    """Verifica que la MV existe y tiene datos."""
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM bank_mv_cartera_tdc")
    )
    count = result.scalar()
    assert count > 0, "MV cartera_tdc debe tener datos"

@pytest.mark.asyncio
async def test_mv_cartera_tdc_columns(db_session):
    """Verifica columnas esperadas."""
    result = await db_session.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'bank_mv_cartera_tdc'
        """)
    )
    columns = {row[0] for row in result.fetchall()}
    expected = {"banco", "periodo", "cartera_tdc", "imor_tdc", "cartera_tdc_vencida"}
    assert expected.issubset(columns)

@pytest.mark.asyncio
async def test_analytics_get_cartera_tdc(analytics_service):
    """Test del metodo get_cartera_tdc."""
    result = await analytics_service.get_cartera_tdc(limit=10)
    assert len(result) > 0
    assert "cartera_tdc" in result[0]
```

---

## Phase 6: Validacion

### 6.1 Comandos de Validacion

```bash
# 1. Aplicar migration
cd plugins/bank-advisor-private
psql $DATABASE_URL -f migrations/052_create_mv_cartera_tdc.sql

# 2. Verificar MV creada
psql $DATABASE_URL -c "SELECT COUNT(*) FROM bank_mv_cartera_tdc;"

# 3. Query de ejemplo
psql $DATABASE_URL -c "
SELECT banco, periodo, cartera_tdc, imor_tdc
FROM bank_mv_cartera_tdc
WHERE periodo = '202412'
ORDER BY cartera_tdc DESC
LIMIT 10;
"

# 4. Correr tests
make test T=api TEST_ARGS="-k tdc"

# 5. Test de lint
make pre-deploy.lint
```

### 6.2 Query de Usuario Esperado

Despues de implementar, el sistema debera responder:

**Pregunta**: "Cual es la cartera de tarjetas de credito de BBVA?"

**Respuesta esperada**:
```
La cartera de tarjetas de credito de BBVA al periodo 202412 es:
- Cartera Total TDC: $XX,XXX MDP
- Cartera Vencida TDC: $X,XXX MDP
- IMOR TDC: X.XX%
```

---

## Archivos a Modificar

| Archivo | Accion | Phase |
|---------|--------|-------|
| `migrations/052_create_mv_cartera_tdc.sql` | Crear | 1 |
| `src/bankadvisor/services/analytics_service.py` | Modificar | 2 |
| `src/bankadvisor/services/query_spec_parser.py` | Modificar | 3 |
| `src/bankadvisor/etl_runner.py` | Modificar | 4 |
| `tests/unit/test_analytics_tdc.py` | Crear | 5 |

---

## Riesgos y Mitigacion

| Riesgo | Probabilidad | Mitigacion |
|--------|--------------|------------|
| Conceptos incorrectos | Baja | Validar con catalogo_conceptos_040.xlsx |
| Join falla | Baja | Verificar FK institucion/periodo |
| Performance | Baja | Indices ya definidos |
| Datos incompletos | Media | Agregar WHERE valor IS NOT NULL |

---

## Dependencias

- `hip_analisis_general` debe estar poblada (11.78M registros)
- `bank_dim_institucion` debe tener todas las instituciones
- `bank_dim_periodo` debe tener todos los periodos

---

## Rollback

```sql
-- Si hay problemas, revertir:
DROP MATERIALIZED VIEW IF EXISTS bank_mv_cartera_tdc CASCADE;
DROP FUNCTION IF EXISTS refresh_bank_mv_cartera_tdc();
```
