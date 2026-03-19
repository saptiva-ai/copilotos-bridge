# Research: Bugs Cartera Hipotecaria (Chris Huertas)

## Status: ALL BUGS FIXED AND VALIDATED ✓

## Test Results (2026-01-12 - Final)

| Bug | Pass Rate | Status |
|-----|-----------|--------|
| BUG-CH-001 (hipotecario mapping) | 100% (8/8) | **FIXED** - synonyms work |
| BUG-CH-003 (sticky context) | 100% (4/4) | **FIXED** - effective_metric pattern |
| BUG-CH-004 (tarjetas credit) | 100% (2/2) | **FIXED** - no longer maps to commercial |
| BUG-CH-005 (dates 2017-01-01) | 100% (3/3) | **FIXED** - dates now 2019-2025 |
| BUG-CH-006 (breakdown) | 100% (2/2) | **FIXED** |
| REGRESSION | 100% (4/4) | **OK** - existing metrics work |
| EDGE | 100% (2/2) | **OK** |

**Overall: 100% (25/25)**

### Fix Aplicado - BUG-CH-005 (Fechas)

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/services/analytics_service.py`
**Función:** `get_filtered_data()` (líneas 682-747)
**Commit:** `da1cf107`

**Cambio:** Se obtienen dinámicamente `fecha_col` y `banco_col` desde `metric_column.table` en lugar de usar siempre `MonthlyKPI`. Esto permite que queries para `cartera_vivienda_total` usen la tabla correcta (`hip_cartera_vivienda_mensual`) con sus fechas reales (2019-2025).

### Fix Aplicado - BUG-CH-003 (Sticky Context)

**Archivo:** `apps/backend/src/services/tool_execution_service.py`
**Commit:** `529e41f1`

**Cambio:** Se agregó detección de métrica explícita en la query del usuario:

1. **METRIC_KEYWORDS dictionary** - Mapea sinónimos de métricas a identificadores canónicos
2. **_detect_metric_in_query()** - Detecta si el usuario menciona explícitamente una métrica
3. **effective_metric pattern** - `effective_metric = query_metric or context_metric`
   - Si el usuario dice "ahora dame la cartera hipotecaria", `query_metric = CARTERA_VIVIENDA`
   - El `context_metric` (ej. IMOR) se ignora y se usa `query_metric`

**Antes:** El `context_metric` siempre se pasaba a `query_bank_analytics()`, incluso si el usuario cambiaba de tema.

**Después:** El `effective_metric` prioriza la métrica explícita del usuario sobre el contexto previo.

## Resumen Ejecutivo

Se identificaron **2 causas raíz principales** que explican la mayoría de los 6 bugs reportados:

1. **BUG CRÍTICO**: Query usa tabla incorrecta para fechas (`MonthlyKPI.fecha` en lugar de `HipCarteraViviendaMensual.fecha`)
2. **BUG MENOR**: Falta parseo de rangos temporales ("últimos 12 meses")

---

## Análisis de Bugs

### BUG-CH-001: "hipotecario" vs "vivienda" + rango temporal

**Estado:** Parcialmente resuelto

**Hallazgos:**
- El mapping `hipotecario → cartera_vivienda_total` SÍ existe en `synonyms.yaml` (líneas 117-121)
- La query se construye correctamente para la métrica
- **Problema real:** Las fechas vienen de tabla incorrecta

**Evidencia (synonyms.yaml:110-122):**
```yaml
cartera_vivienda_total:
  display_name: "Cartera Vivienda"
  column: "cartera_vivienda_total"
  type: "currency"
  aliases:
    - "cartera vivienda"
    - "vivienda"
    - "hipotecario"
    - "hipoteca"
    - "cartera hipotecaria"
```

---

### BUG-CH-005: Gráfica con picos en enero (CRÍTICO)

**Estado:** CAUSA RAÍZ IDENTIFICADA

**Causa raíz:** `get_filtered_data()` en `analytics_service.py` (líneas 697-701)

```python
# CÓDIGO ACTUAL (BUGGY):
query = select(
    MonthlyKPI.fecha,           # ← SIEMPRE usa MonthlyKPI
    MonthlyKPI.banco_norm,
    metric_column.label('value')  # ← Pero metric_column puede ser de otra tabla!
)
```

**Problema:**
Cuando `metric_column = HipCarteraViviendaMensual.cartera_vivienda_total`, la query mezcla:
- `MonthlyKPI.fecha` (tabla 1, con datos viejos/limitados)
- `HipCarteraViviendaMensual.cartera_vivienda_total` (vista 2, con datos 2019-2025)

Esto crea un **cross-join implícito** que:
1. Devuelve fechas "2017-01-01" para todos los registros
2. Produce gráficas con picos porque solo una fecha hace match

**Solución correcta (ya implementada en `query_kpi_timeseries` líneas 503-515):**
```python
# CÓDIGO CORRECTO:
table = safe_column.table              # Obtener tabla de la columna
fecha_col = table.c.get("fecha")       # Obtener fecha de ESA tabla
banco_col = table.c.get("banco_norm")  # Obtener banco de ESA tabla

query = select(fecha_col, banco_col, safe_column)
```

---

### BUG-CH-002: Botón "Abrir" no muestra gráfica

**Estado:** Probablemente causado por BUG-CH-005

**Hipótesis:**
- Si los datos devueltos tienen fechas incorrectas ("2017-01-01" repetidas), la librería de gráficas puede:
  - No pintar nada (todos los puntos en el mismo lugar)
  - Generar error silencioso
  - Mostrar estado vacío

**Acción:** Verificar después de aplicar fix de BUG-CH-005

---

### BUG-CH-003: Sticky context (métrica "pegada")

**Estado:** Requiere investigación separada en backend session management

**Archivos relevantes:**
- `apps/backend/src/services/tool_execution_service.py`
- Context storage en session

---

### BUG-CH-004: "tarjetas de crédito" → "cartera comercial"

**Estado:** Limitación de datos

**Hallazgo:**
- No existe dataset de conteo de tarjetas
- El sistema solo tiene métricas de saldos (MDP)
- El LLM hace "best-effort mapping" incorrecto

**Recomendación:** Agregar respuesta explícita "esta métrica no está disponible"

---

### BUG-CH-006: No entrega breakdown banco x año

**Estado:** Requiere verificar después de fix de fechas

---

## Verificación de Datos

### Base de datos `hip_cartera_vivienda_mensual`

```sql
-- Rango de fechas real
Min: 2019-01-01
Max: 2025-10-01
Total: 1,502 registros

-- Datos de INVEX
2025-10-01 | INVEX | 507,528.17
2025-08-01 | INVEX | 2,718,402.51
...
Total INVEX: 23 registros
```

---

## Plan de Fix

### Fase 1: Fix crítico de query (BUG-CH-005)

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/services/analytics_service.py`
**Ubicación:** `get_filtered_data()` líneas 680-717

**Cambio:**
```python
# ANTES (líneas 695-701):
# Standard column query
query = select(
    MonthlyKPI.fecha,
    MonthlyKPI.banco_norm,
    metric_column.label('value')
)

# DESPUÉS:
# Get table from metric_column dynamically
table = metric_column.table
fecha_col = table.c.get("fecha")
banco_col = table.c.get("banco_norm")

query = select(
    fecha_col,
    banco_col,
    metric_column.label('value')
)
```

### Fase 2: Actualizar filtros para usar columnas dinámicas

**Cambio en líneas 704-711:**
```python
# ANTES:
if banks and len(banks) > 0:
    query = query.where(MonthlyKPI.banco_norm.in_(banks))

if date_start:
    query = query.where(MonthlyKPI.fecha >= date_start)

# DESPUÉS:
if banks and len(banks) > 0:
    query = query.where(banco_col.in_(banks))

if date_start:
    query = query.where(fecha_col >= date_start)
```

### Fase 3: Manejar caso especial `cartera_comercial_sin_gob`

La línea 684-694 tiene un caso especial que también necesita ajuste.

---

## Archivos Modificados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `analytics_service.py` | 695-717 | Usar tabla dinámica para fecha/banco |

---

## Tests de Validación

```bash
# Query de verificación post-fix
curl -X POST http://localhost:8002/api/chat \
  -d '{"query": "cartera hipotecaria de INVEX últimos 12 meses"}'

# Verificar que x[] tenga fechas 2019-2025, no "2017-01-01"
```

---

## Referencias

- `plugins/bank-advisor-private/src/bankadvisor/services/analytics_service.py` (bug location)
- `plugins/bank-advisor-private/src/bankadvisor/models/hipoteca_view.py` (correct table)
- `plugins/bank-advisor-private/config/synonyms.yaml` (mappings)

---

## Exploración: Extensión de Tablas hip_* (2026-01-12)

### Contexto

Después de resolver los bugs de hipotecario, se exploró la posibilidad de extender el sistema NL2SQL para soportar más tablas `hip_*` disponibles en PostgreSQL GCP.

### Tablas Disponibles

Se identificaron **145 tablas hip_*** en la base de datos, incluyendo:

| Tabla | Descripción | Filas |
|-------|-------------|-------|
| `hip_cartera_comercial_base_total` | Cartera comercial detallada | ~4.2M |
| `hip_cartera_total_mensual` | Vista pre-agregada mensual | ~10K |
| `hip_cat_tamano_empresa` | Catálogo tamaño empresa | 5 |
| `hip_cat_moneda` | Catálogo moneda | 3 |
| `hip_cat_destino_credito` | Catálogo destino crédito | 28 |

### Experimentos Realizados

#### Experimento A: Vistas Pre-agregadas ✅

**Implementación:** Integrar `hip_cartera_total_mensual` al flujo NL2SQL existente.

**Archivos modificados:**
- `src/bankadvisor/models/hip_cartera_total.py` (nuevo modelo SQLAlchemy)
- `src/bankadvisor/services/analytics_service.py` (7 métricas nuevas)
- `config/synonyms.yaml` (alias para nuevas métricas)

**Métricas habilitadas:**
- `hip_cartera_comercial_total` - Cartera comercial
- `hip_cartera_comercial_vigente` - Cartera vigente
- `hip_cartera_total` - Cartera total
- `hip_porcentaje_comercial` - % comercial

**Resultado:** ✅ Queries funcionan, datos 2016-2025

#### Experimento B: JOINs Dinámicos ✅

**Implementación:** PoC de queries con JOINs a tablas de catálogo.

**Script:** `scripts/analysis/experiment_b_dynamic_joins.py`

**Resultados:**
```
Query: "cartera por tamaño de empresa"
✓ Grande: $13.27B (90%)
✓ MiPyMEs: $1.14B (8%)

Query: "cartera en moneda extranjera"
✓ MXN: $11.80B (80%)
✓ USD: $2.88B (20%)

Query: "destinos de crédito"
✓ Capital de Trabajo: $10.34B
✓ Crédito Puente: $2.74B
```

### Decisión de Arquitectura

| Criterio | Exp. A (Vistas) | Exp. B (JOINs) |
|----------|-----------------|----------------|
| Complejidad | Baja | Alta |
| Flexibilidad | Limitada | Alta |
| Performance | Óptima | Variable |
| Recomendación | **Fase 1** | Fase 3 |

### Próximos Pasos

1. ✅ Commit cambios de Experimento A
2. 📋 Crear vistas pre-agregadas adicionales en PostgreSQL
3. 🔮 Integrar JOINs dinámicos para queries ad-hoc

### Scripts de Análisis Generados

```
plugins/bank-advisor-private/scripts/analysis/
├── hip_tables_report.md           # Análisis completo
├── explore_hip_tables_simple.py   # Script exploración
├── test_hip_experiments.py        # Tests automatizados
├── experiment_b_dynamic_joins.py  # PoC JOINs
└── hip_experiments_summary.md     # Comparación
```
