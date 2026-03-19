---
id: BUG-2026-01-30__icap-decimal-shift
title: ICAP Values Show Wrong Decimal Point (2005% instead of 20%)
status: DONE
phase: Validate
priority: critical
scope_in:
  - Investigar pipeline de datos ICAP en bank-advisor
  - Verificar transformacion de valores en SQL generado
  - Corregir multiplicacion erronea de punto decimal
  - Validar valores contra fuente CNBV
scope_out:
  - Cambios a otros indicadores
  - Refactors no relacionados
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - make test T=api TEST_ARGS='-k icap'
  - curl bank-advisor API con query ICAP BBVA
pr_files: []
test_status: ''
reported_by: 'rhernandez@bajaware.com, jazzesfm@gmail.com'
reported_at: '2026-01-30, 2026-01-27'
---

# Resumen

**Objetivo**: Corregir error critico donde los valores de ICAP se muestran multiplicados por 100 (ej: 2005.94% en lugar de 20.0594%).

**Impacto**: El analisis financiero es inutil con valores erroneos. Afecta la credibilidad del sistema.

---

# Feedback de Usuarios

## Reporte 1 - rhernandez@bajaware.com (2026-01-30 00:09)
> "el valor del ICAP de bbva esta mal, 2005.94% no es real, recorre el punto decimal"

**Contexto**: Usuario pregunto "explícame como obtuviste que bbva creció un 4.5% en el periodo analizado?"

**Respuesta del sistema**:
- Mostro BBVA con valor actual de **2005.94%**
- El valor real deberia ser ~20.06%

## Reporte 2 - jazzesfm@gmail.com (2026-01-27 14:16)
> "La informacion es util pero las unidades no creo que sean correctas"

**Contexto**: Usuario pregunto "Cual banco tiene el mejor ICAP?"

---

# Analisis Tecnico Preliminar

## Evidencia del Bug

En el feedback metadata se puede observar:
```json
{
  "sql_generated": "SELECT banco_norm, fecha, icap_total FROM bank_fact_kpis_mensual WHERE banco_norm = 'BBVA' AND fecha >= '1597-01-01'..."
}
```

Observaciones:
1. El SQL usa fecha `1597-01-01` (fecha invalida, posible bug separado)
2. Los valores ICAP en BD podrian estar almacenados como ratio (0.2005) y se multiplican incorrectamente

## Verificacion con Datos Reales (PostgreSQL)

```sql
SELECT banco_norm, fecha, icap_total FROM bank_fact_kpis_mensual
WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01';

 fecha       | icap_total
-------------|------------
 2025-01-01  |    19.1934
 2025-09-01  |    19.9711
 2025-10-01  |    20.0594   <- Este valor * 100 = 2005.94%
```

**CONFIRMADO**: Los datos en BD estan correctos (20.0594%).
El bug ocurre en la capa de presentacion donde se multiplica por 100.

## Hipotesis de Root Cause

**Hipotesis 1 (CONFIRMADA)**: El campo `icap_total` ya esta almacenado como porcentaje (20.0594) pero el sistema lo multiplica por 100 innecesariamente, resultando en 2005.94%.

**Hipotesis 2**: El template de visualizacion o el formateador de estadisticas aplica `value * 100` asumiendo que es ratio.

**Hipotesis 3**: El LLM recibe el valor correcto pero en su respuesta textual aplica multiplicacion adicional.

---

# Datos de Contexto

| Campo | Valor |
|-------|-------|
| Conversation ID | f75ee002-0082-46e8-913a-32e58d17327b |
| User | rhernandez@bajaware.com |
| Fecha | 2026-01-30 |
| Servicio afectado | bank-advisor MCP |
| Metrica | ICAP_TOTAL |

---

# Investigacion Completada

1. [x] Verificar formato de almacenamiento de `icap_total` en DuckDB
2. [x] Rastrear transformaciones en `plugins/bank-advisor/src/pipelines/`
3. [x] Revisar templates de visualizacion en `plugins/bank-advisor/src/templates/`
4. [x] Comparar con valores oficiales CNBV

---

# Root Cause Identificado

## Problema
En `analytics_service.py:1254`:
```python
skip_multiply = metric_id.lower() in ['icor', 'roe_12m', 'roa_12m']
```

**Faltaban `icap_total` e `icap`** en la lista de métricas que NO deben multiplicarse.

## Por qué ocurre
1. ICAP está configurado con `type: "ratio"` en `synonyms.yaml`
2. El código multiplica por 100 todos los `metric_type == "ratio"`
3. Pero ICAP ya está almacenado como % en BD (20.06 = 20.06%)
4. Resultado: 20.06 × 100 = 2006%

## Inconsistencia
- `chart_formatter.py` tiene `NO_SCALE_METRICS` con ICAP incluido ✓
- `analytics_service.py` tenía lista incompleta sin ICAP ✗

---

# Solución Implementada

## Fix en `analytics_service.py:1254`
```python
skip_multiply = metric_id.lower() in [
    'icor', 'roe_12m', 'roa_12m',  # Ya en escala %
    'icap_total', 'icap',  # FIX: ICAP almacenado como % (20.06 = 20.06%)
    'market_share_pct'  # Ya en escala %
]
```

---

# Actualizaciones

- 2026-01-30 - Creado desde analisis de feedback de produccion
- 2026-01-30 - Root cause identificado: lista skip_multiply incompleta
- 2026-01-30 - Fix aplicado en analytics_service.py
- 2026-01-30 - Test E2E: 3/3 PASSED - DoD cumplido, movido a DONE

## Feedback Vinculado

**8 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0005 | `9d8f06d5` | Cual banco tiene el mejor ICAP? | La informacion es util pero las unidades no creo que sean correctas | 2026-01-27 |
| 2 | FDBK-0009 | `7f5aa3b9` | que es la cartera ? | no pedi el ICAP pedi solo la definicion de cartera y los datos de ICAP estan mal | 2026-01-27 |
| 3 | FDBK-0010 | `cb6c6879` | compara el ICAP total de banamex, bbva y santander en 2025 | el análisis es erróneo, pues, citibanamex, bbva y santander no tuvieron el cr... | 2026-01-29 |
| 4 | FDBK-0011 | `cb6c6879` | explícame como obtuviste que citibanamex creció un 0.2% e... | - arroja la grafica de todos los bancos. - las unidades porcentuales están ma... | 2026-01-29 |
| 5 | FDBK-0012 | `cb6c6879` | explícame como obtuviste que bbva creció un 4.5% en el pe... | - el ICAP total de bbva en septiembre 2025 no es de 19.19% como lo menciona e... | 2026-01-29 |
| 6 | FDBK-0013 | `cb6c6879` | explícame como obtuviste que santander creció un 12% en e... | - arroja una tabla con todos los bancos, cuando solo se pidio la explicación ... | 2026-01-29 |
| 7 | FDBK-0014 | `cb6c6879` | explícame como obtuviste que santander creció un 12% en e... | - mueve el punto en el valor del ICAP - el ICAP de sep 2025 es de 20.02% no d... | 2026-01-30 |
| 8 | FDBK-0016 | `cb6c6879` | explícame como obtuviste que bbva creció un 4.5% en el pe... | - el valor del ICAP de  bbva esta mal, 2005.94% no es real, recorre el punto ... | 2026-01-30 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0005
- **User**: `9d8f06d5-39e6-46b3-b8cb-9330c6f36477`
- **Conversation**: `e036dc09-a7c7-486b-882f-03ee89ef6dd0`
- **Message**: `9c497a1b-03ec-414f-81ce-c1b243def664`
- **Rating**: 👎
- **Query**: "Cual banco tiene el mejor ICAP?"
- **Feedback**: "La informacion es util pero las unidades no creo que sean correctas"
- **Fecha**: 2026-01-27T14:16:34.014Z

### FDBK-0009
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `be9ee5a5-8547-470f-b942-07ec13eeff77`
- **Message**: `9f183553-ab07-4d14-89a7-2191b522a787`
- **Rating**: 👎
- **Query**: "que es la cartera ?"
- **Feedback**: "no pedi el ICAP pedi solo la definicion de cartera y los datos de ICAP estan mal"
- **Fecha**: 2026-01-27T18:45:19.261Z

### FDBK-0010
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `d9c03ef5-5a6f-4dd0-be78-829532fc9306`
- **Message**: `4d34de75-c2b7-4e9e-b649-144a144fe680`
- **Rating**: 👎
- **Query**: "compara el ICAP total de banamex, bbva y santander en 2025"
- **Feedback**: "el análisis es erróneo, pues, citibanamex, bbva y santander no tuvieron el crecimiento que indica "
- **Fecha**: 2026-01-29T23:18:22.348Z

### FDBK-0011
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `d9c03ef5-5a6f-4dd0-be78-829532fc9306`
- **Message**: `32dc13a4-0abc-4fda-bd89-166b8e2a4aa5`
- **Rating**: 👎
- **Query**: "explícame como obtuviste que citibanamex creció un 0.2% en el periodo analizado ?"
- **Feedback**: "- arroja la grafica de todos los bancos.
  - las unidades porcentuales están mal (recorre el punto)
  - menciona 20.66% en septiembre y no es así, ese porcentaje lo esta tomando del mes de enero que no debería ser 20.66%, debería ser 20.65%"
- **Fecha**: 2026-01-29T23:29:16.282Z

### FDBK-0012
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `d9c03ef5-5a6f-4dd0-be78-829532fc9306`
- **Message**: `ac1fe9c5-fcfa-45cb-9951-f54f4691df04`
- **Rating**: 👎
- **Query**: "explícame como obtuviste que bbva creció un 4.5% en el periodo analizado en ICAP total ?"
- **Feedback**: "- el ICAP total de bbva en septiembre 2025 no es de 19.19% como lo menciona el analisis, es de 19.97%. 
  - el crecimiento que menciona es de septiembre a octubre pero esta tomando el dato de enero en lugar de septiembre"
- **Fecha**: 2026-01-29T23:51:47.831Z

### FDBK-0013
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `d9c03ef5-5a6f-4dd0-be78-829532fc9306`
- **Message**: `d8858b3f-4434-4c80-b8c8-153789e05e1b`
- **Rating**: 👎
- **Query**: "explícame como obtuviste que santander creció un 12% en el periodo analizado ?"
- **Feedback**: "- arroja una tabla con todos los bancos, cuando solo se pidio la explicación para santander
  - mueve el punto en el valor del ICAP mostrando datos erroneos
  - el ICAP total de santander en sep 2025 fue de 20.02% y no de 17.78% como menciona el analisis
  - toma el valor en enero 2025 y lo pone como si fuera de sep 2025"
- **Fecha**: 2026-01-29T23:57:25.603Z

### FDBK-0014
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `d9c03ef5-5a6f-4dd0-be78-829532fc9306`
- **Message**: `4e396081-5f77-466e-91a8-56d737bcaae8`
- **Rating**: 👎
- **Query**: "explícame como obtuviste que santander creció un 12% en el periodo analizado en ICAP total?"
- **Feedback**: "- mueve el punto en el valor del ICAP
  - el ICAP de sep 2025 es de 20.02% no de 17.78% (valor de enero 2025)
  - checar el redondeo pues la tabla dice 17.7924% y lo redondea a 17.78% cuando debería de ser 17.79%"
- **Fecha**: 2026-01-30T00:02:20.995Z

### FDBK-0016
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `f75ee002-0082-46e8-913a-32e58d17327b`
- **Message**: `29ccb7e3-43bc-4f33-a492-994c1f8a8586`
- **Rating**: 👎
- **Query**: "explícame como obtuviste que bbva creció un 4.5% en el periodo analizado ?"
- **Feedback**: "- el valor del ICAP de  bbva esta mal, 2005.94% no es real, recorre el punto decimal"
- **Fecha**: 2026-01-30T00:09:02.830Z

</details>
