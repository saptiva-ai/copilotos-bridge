# Plan: Fix Query de Métricas Multi-Tabla

## Objetivo

Corregir el bug donde `get_filtered_data()` usa hardcoded `MonthlyKPI.fecha/banco_norm` en lugar de obtener las columnas de la tabla correcta basándose en `metric_column`.

---

## Pre-requisitos

- [x] Investigación completada (ver `research.md`)
- [x] Causa raíz identificada
- [ ] Tests existentes pasan

---

## Fases de Implementación

### Fase 1: Fix de Query Principal

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/services/analytics_service.py`

**Ubicación:** Función `get_filtered_data()`, líneas ~680-720

**Cambios:**

1. Después de obtener `metric_column` (línea 680), extraer la tabla:
   ```python
   metric_column = AnalyticsService.SAFE_METRIC_COLUMNS[column_name]

   # NEW: Get table from metric column for dynamic fecha/banco columns
   metric_table = metric_column.table
   fecha_col = metric_table.c.get("fecha")
   banco_col = metric_table.c.get("banco_norm")
   ```

2. Modificar la query estándar (líneas 696-701):
   ```python
   # ANTES:
   query = select(
       MonthlyKPI.fecha,
       MonthlyKPI.banco_norm,
       metric_column.label('value')
   )

   # DESPUÉS:
   query = select(
       fecha_col,
       banco_col,
       metric_column.label('value')
   )
   ```

3. Modificar los filtros (líneas 704-711):
   ```python
   # ANTES:
   if banks and len(banks) > 0:
       query = query.where(MonthlyKPI.banco_norm.in_(banks))
   if date_start:
       query = query.where(MonthlyKPI.fecha >= date_start)
   if date_end:
       query = query.where(MonthlyKPI.fecha <= date_end)

   # DESPUÉS:
   if banks and len(banks) > 0:
       query = query.where(banco_col.in_(banks))
   if date_start:
       query = query.where(fecha_col >= date_start)
   if date_end:
       query = query.where(fecha_col <= date_end)
   ```

4. Modificar el order_by (línea 717):
   ```python
   # ANTES:
   query = query.order_by(MonthlyKPI.fecha.asc())

   # DESPUÉS:
   query = query.order_by(fecha_col.asc())
   ```

---

### Fase 2: Fix de Caso Especial `cartera_comercial_sin_gob`

**Ubicación:** Líneas 684-694

El caso especial ya usa `MonthlyKPI` explícitamente, pero debería validar que es la tabla correcta:

```python
if column_name == "cartera_comercial_sin_gob":
    # This metric is ONLY from MonthlyKPI, so keep using MonthlyKPI
    fecha_col = MonthlyKPI.fecha
    banco_col = MonthlyKPI.banco_norm
    calculated_value = (
        MonthlyKPI.cartera_comercial_total -
        func.coalesce(MonthlyKPI.entidades_gubernamentales_total, 0)
    ).label('value')
    query = select(fecha_col, banco_col, calculated_value)
```

---

### Fase 3: Agregar Logging para Debugging

```python
logger.info(
    "analytics.get_filtered_data.query_built",
    metric_id=metric_id,
    table_name=getattr(metric_table, "__tablename__", str(metric_table)),
    fecha_col=str(fecha_col),
    banco_col=str(banco_col)
)
```

---

## Validación

### Test Manual

```bash
# 1. Levantar servicios
make dev

# 2. Query de prueba
curl -X POST http://localhost:8002/api/v1/analytics/query \
  -H "Content-Type: application/json" \
  -d '{"metric_id": "cartera_vivienda_total", "banks": ["INVEX"]}'

# 3. Verificar respuesta
# - time_range.start debe ser ~2019-01-01 (no 2017-01-01)
# - time_range.end debe ser ~2025-10-01
# - plotly_config.data[0].x[] debe tener fechas válidas 2019-2025
```

### Criterios de Éxito

| Criterio | Antes | Después |
|----------|-------|---------|
| Fechas en x[] | "2017-01-01" (repetido) | Fechas 2019-2025 |
| time_range.start | null o incorrecto | "2019-01-01" |
| Gráfica renderiza | Vacía/picos | Serie temporal normal |

---

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Romper otras métricas | Media | Verificar que MonthlyKPI metrics siguen funcionando |
| `fecha_col` es None | Baja | Agregar validación y fallback |

---

## Rollback

Si hay problemas, revertir el commit y desplegar versión anterior.

---

## Tiempo Estimado

- Implementación: ~30 min
- Testing: ~15 min
- Total: ~45 min
