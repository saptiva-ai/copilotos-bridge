---
id: BUG-2026-01-30__wrong-month-data-mapping
title: LLM Confunde Meses - Usa Enero como Septiembre en Analisis ICAP
status: DONE
phase: Implement
priority: critical
scope_in:
  - Investigar como el LLM interpreta fechas en el contexto
  - Revisar como se pasan los datos al LLM para analisis
  - Verificar que el chart y el analisis usen la misma fuente de datos
  - Asegurar coherencia temporal en respuestas
scope_out:
  - Cambios a la UI
  - Cambios a otros indicadores
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - make test T=api TEST_ARGS='-k icap'
  - Validar query 'ICAP de BBVA septiembre 2025' retorna 19.97%
pr_files: []
test_status: ''
reported_by: rhernandez@bajaware.com
reported_at: '2026-01-30, 2026-01-29'
---

# Resumen

**Objetivo**: Corregir bug critico donde el sistema toma datos de ENERO 2025 y los presenta como si fueran de SEPTIEMBRE 2025 en sus analisis textuales.

**Impacto**: Analisis financieros completamente erroneos. El usuario recibe datos de meses equivocados.

---

# Feedback de Usuarios

## Reporte 1 - rhernandez@bajaware.com (2026-01-30 00:02)
> "el ICAP de sep 2025 es de 20.02% no de 17.78% (valor de enero 2025)"
> "toma el valor en enero 2025 y lo pone como si fuera de sep 2025"

**Query del usuario**: "explícame como obtuviste que santander creció un 12% en el periodo analizado en ICAP total?"

**Respuesta erronea del sistema**:
- Dijo que ICAP_TOTAL en septiembre 2025 fue **17.78%**
- Valor real en septiembre: **20.02%**
- El 17.78% corresponde a **ENERO 2025** (17.7924%)

## Reporte 2 - rhernandez@bajaware.com (2026-01-29 23:51)
> "el ICAP total de bbva en septiembre 2025 no es de 19.19% como lo menciona el analisis, es de 19.97%"
> "el crecimiento que menciona es de septiembre a octubre pero esta tomando el dato de enero en lugar de septiembre"

**Query del usuario**: "explícame como obtuviste que bbva creció un 4.5% en el periodo analizado en ICAP total?"

**Respuesta erronea del sistema**:
- Dijo que ICAP_TOTAL de BBVA en septiembre 2025 fue **19.19%**
- Valor real en septiembre: **19.97%**
- El 19.19% corresponde a **ENERO 2025** (19.1934%)

---

# Verificacion con Datos Reales (PostgreSQL)

```sql
-- BBVA 2025
SELECT fecha, icap_total FROM bank_fact_kpis_mensual
WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01';

 fecha       | icap_total
-------------|------------
 2025-01-01  |    19.1934   <- Sistema uso ESTE como "septiembre"
 2025-09-01  |    19.9711   <- Valor REAL de septiembre
 2025-10-01  |    20.0594

-- SANTANDER 2025
SELECT fecha, icap_total FROM bank_fact_kpis_mensual
WHERE banco_norm = 'SANTANDER' AND fecha >= '2025-01-01';

 fecha       | icap_total
-------------|------------
 2025-01-01  |    17.7924   <- Sistema uso ESTE como "septiembre"
 2025-09-01  |    20.0193   <- Valor REAL de septiembre
 2025-10-01  |      19.92
```

---

# Analisis Tecnico Preliminar

## Hipotesis de Root Cause

**Hipotesis 1 (MAS PROBABLE)**: El LLM recibe un array de datos ordenados por fecha pero sin etiquetas de fecha explicitas, y asume incorrectamente que el primer elemento es el mes mas reciente.

**Hipotesis 2**: El contexto que se le pasa al LLM incluye un resumen de estadisticas donde el primer valor listado es Enero, y el LLM lo interpreta como el "periodo actual".

**Hipotesis 3**: El SQL generado es correcto, pero el analisis textual del LLM usa datos de una query diferente almacenada en memoria/contexto.

## Evidencia

En el metadata del feedback:
```json
{
  "sql_generated": "SELECT banco_norm, fecha, icap_total FROM bank_fact_kpis_mensual WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01' AND fecha <= '2025-12-31' ORDER BY fecha ASC"
}
```

El SQL es correcto y ordena ASC, pero el LLM puede estar tomando el primer registro (Enero) como referencia.

---

# Datos de Contexto

| Campo | Valor |
|-------|-------|
| Conversation ID | d9c03ef5-5a6f-4dd0-be78-829532fc9306 |
| User | rhernandez@bajaware.com |
| Fecha | 2026-01-29/30 |
| Servicio afectado | bank-advisor MCP + LLM analysis |
| Metrica | ICAP_TOTAL |

---

# CAUSA RAÍZ IDENTIFICADA

## Ubicación del Bug

**Archivo**: `apps/backend/src/services/streaming/chart_normalizer.py`
**Función**: `extract_chart_statistics()` (líneas 254-305)

## Problema Específico

La función extrae estadísticas de las trazas Plotly pero **NO incluye las fechas**:

```python
# Líneas 265-275: Itera sobre y_values (valores)
for v in y_values:
    if v is not None and isinstance(v, (int, float)):
        if first_val is None:
            first_val = v      # Primer valor (Enero)
        current_val = v        # Último valor (Octubre)
        # ...

# Líneas 296-305: Guarda estadísticas SIN fechas
stats_by_bank[bank_name] = {
    "current": current_val,    # ← Sin fecha!
    "first": first_val,        # ← Sin fecha!
    "change_pct": change_pct,
    "trend": trend,
}
```

Los `x` values de las trazas **SÍ contienen las fechas** pero son ignorados.

## Flujo del Bug

1. **DuckDB/PostgreSQL**: Retorna datos ordenados por fecha ASC
   ```
   2025-01-01: 19.19%  (first)
   2025-09-01: 19.97%
   2025-10-01: 20.06%  (current)
   ```

2. **chart_normalizer.py**: Extrae solo valores sin fechas
   ```python
   {"first": 19.19, "current": 20.06, "change_pct": 4.5}
   ```

3. **analytics_context.py**: Construye contexto para LLM sin fechas específicas
   ```
   **BBVA**: Actual: 20.06%, Tendencia: creciente (+4.5%)
   Período: 2025-01-01 a 2025-10-01
   ```

4. **LLM**: Cuando usuario pregunta "¿cómo obtuviste que BBVA creció 4.5%?":
   - El LLM sabe que el período es Enero a Octubre
   - Pero NO sabe cuál valor corresponde a cuál mes
   - **INVENTA**: "En septiembre fue 19.19%" (cuando 19.19% es ENERO!)

## Solución Propuesta

Modificar `extract_chart_statistics()` para incluir las fechas:

```python
# En chart_normalizer.py, líneas 254-305
x_values = trace.get("x", [])  # ← Fechas
y_values = trace.get("y", [])  # ← Valores

# ...después de iterar...
stats_by_bank[bank_name] = {
    "current": current_val,
    "current_date": x_values[-1] if x_values else None,    # ← AÑADIR
    "first": first_val,
    "first_date": x_values[0] if x_values else None,       # ← AÑADIR
    "previous": y_values[-2] if len(y_values) >= 2 else None,
    "previous_date": x_values[-2] if len(x_values) >= 2 else None,  # ← AÑADIR
    "change_pct": change_pct,
    "trend": trend,
}
```

Y actualizar `analytics_context.py` para usar las fechas:

```python
# Línea 304-305 actual:
context += f"""
- **{bank}**: Actual: {stats["current"]:.2f}%, Tendencia: {stats["trend"]}"""

# Propuesta:
context += f"""
- **{bank}**: {stats["current"]:.2f}% (al {stats["current_date"]}),
  cambio desde {stats["first_date"]}: {stats["change_pct"]:+.1f}%"""
```

---

# Archivos a Modificar

1. `apps/backend/src/services/streaming/chart_normalizer.py`
   - Función `extract_chart_statistics()` - añadir fechas a stats

2. `apps/backend/src/services/streaming/analytics_context.py`
   - Función `_build_success_context()` - usar fechas en el contexto LLM

---

# Actualizaciones

- 2026-01-30 - Creado desde analisis de feedback de produccion
- 2026-01-30 - Verificado con datos reales de PostgreSQL - el bug es 100% confirmado
- 2026-01-30 - **CAUSA RAÍZ IDENTIFICADA**: `extract_chart_statistics()` no incluye fechas
- 2026-01-30 - **IMPLEMENTACIÓN COMPLETADA** - Nueva arquitectura simplificada:
  - `src/schemas/analytics_data.py` - Pydantic schemas que NUNCA separan fechas de valores
  - `src/services/analytics_extractor.py` - Extractor que preserva AMBOS ejes (x=fechas, y=valores)
  - `src/services/llm_context_builder.py` - Contexto simplificado (~80 líneas vs 536)
  - `tests/unit/test_analytics_extractor.py` - 23 tests que validan la corrección
  - `src/services/streaming/system_prompt_builder.py` - Integración con backward compatibility
- 2026-01-30 - **TESTS PASANDO**: 23/23 tests nuevos + todos los tests de streaming existentes
