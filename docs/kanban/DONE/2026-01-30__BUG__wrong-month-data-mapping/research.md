# Research: Wrong Month Data Mapping Bug

## Investigación Completa - 2026-01-30

### Resumen Ejecutivo

El LLM confunde los meses porque `extract_chart_statistics()` extrae valores numéricos **sin sus fechas correspondientes**. Cuando el usuario pregunta sobre un mes específico (ej: Septiembre), el LLM no tiene forma de saber qué valor corresponde a qué fecha, así que **inventa** la asociación.

---

## Flujo de Datos Completo

### 1. Base de Datos (PostgreSQL)

```sql
SELECT fecha, icap_total FROM bank_fact_kpis_mensual
WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01' ORDER BY fecha;

        fecha        | icap_total
---------------------+------------
 2025-01-01 00:00:00 |    19.1934   ← "first_val" en el código
 2025-02-01 00:00:00 |     20.449
 2025-03-01 00:00:00 |    20.1826
 ...
 2025-09-01 00:00:00 |    19.9711   ← Usuario pregunta por este
 2025-10-01 00:00:00 |    20.0594   ← "current_val" en el código
```

### 2. bank-advisor → Plotly Traces

El servicio bank-advisor genera trazas Plotly con:
- `x`: Array de fechas `['2025-01-01', '2025-02-01', ..., '2025-10-01']`
- `y`: Array de valores `[19.19, 20.45, ..., 20.06]`

### 3. chart_normalizer.py → extract_chart_statistics()

**Archivo**: `apps/backend/src/services/streaming/chart_normalizer.py`
**Líneas**: 254-305

```python
def extract_chart_statistics(bank_chart_data: Any) -> dict:
    # ...
    for trace in traces:
        y_values = trace.get("y", [])  # Solo extrae valores
        # x_values = trace.get("x", [])  # ← FECHAS IGNORADAS!

        for v in y_values:
            if first_val is None:
                first_val = v       # Enero (sin saber que es Enero)
            current_val = v         # Octubre (sin saber que es Octubre)

        stats_by_bank[bank_name] = {
            "current": current_val,   # 20.06 (sin fecha)
            "first": first_val,       # 19.19 (sin fecha)
            "change_pct": ((20.06 - 19.19) / 19.19) * 100,  # 4.5%
            "trend": "creciente",
        }
```

**Problema**: Los `x` values (fechas) existen en las trazas pero son completamente ignorados.

### 4. analytics_context.py → _build_success_context()

**Archivo**: `apps/backend/src/services/streaming/analytics_context.py`
**Líneas**: 302-308

```python
for bank, stats in banks_to_show:
    context += f"""
- **{bank}**: Actual: {stats["current"]:.2f}%, Tendencia: {stats["trend"]} ({stats["change_pct"]:+.1f}%)"""
```

Genera contexto:
```
**Estadísticas de ICAP:**
- **BBVA**: Actual: 20.06%, Tendencia: creciente (+4.5%)

Período: 2025-01-01 a 2025-10-01
```

**Problema**: El contexto NO dice que "Actual" = Octubre, ni que el +4.5% es desde Enero.

### 5. LLM (Saptiva/OpenAI) → Respuesta

El LLM recibe el contexto incompleto y cuando el usuario pregunta:
> "¿Cómo obtuviste que BBVA creció 4.5% en septiembre?"

El LLM:
1. Sabe que el período es Enero-Octubre
2. Sabe que el cambio fue +4.5%
3. **NO SABE** cuál valor corresponde a cuál mes
4. **INVENTA**: "En septiembre fue 19.19%" (cuando 19.19% es ENERO!)

---

## Evidencia del Bug en Producción

### Feedback de rhernandez@bajaware.com

**Query**: "explícame como obtuviste que bbva creció un 4.5%?"

**Respuesta del LLM (incorrecta)**:
```
El ICAP_TOTAL de BBVA fue de **19.19%** en septiembre de 2025.
En octubre de 2025, se registró un valor de **20.06%**.
```

**Datos reales**:
- Septiembre 2025: **19.97%** (no 19.19%)
- Enero 2025: **19.19%** (este valor fue confundido con septiembre)
- Octubre 2025: 20.06% (correcto)

El LLM tomó el `first_val` (19.19% de Enero) y lo presentó como Septiembre.

---

## Archivos Clave Analizados

| Archivo | Función | Rol en el Bug |
|---------|---------|---------------|
| `chart_normalizer.py` | `extract_chart_statistics()` | **ORIGEN** - No extrae fechas |
| `analytics_context.py` | `_build_success_context()` | Propaga el problema - No incluye fechas en contexto |
| `chart_formatter.py` | `format_evolution()` | Crea stats correctas pero tampoco incluye fechas |
| `analysis_agent.py` | `_build_prompt()` | Usa stats sin fechas |

---

## Solución Propuesta

### Cambio 1: chart_normalizer.py

```python
def extract_chart_statistics(bank_chart_data: Any) -> dict:
    # ...
    for trace in traces:
        x_values = trace.get("x", [])  # ← AÑADIR: Extraer fechas
        y_values = trace.get("y", [])

        # ... iteración existente ...

        stats_by_bank[bank_name] = {
            "current": current_val,
            "current_date": str(x_values[-1]) if x_values else None,  # ← AÑADIR
            "first": first_val,
            "first_date": str(x_values[0]) if x_values else None,      # ← AÑADIR
            "previous": y_values[-2] if len(y_values) >= 2 else None,
            "previous_date": str(x_values[-2]) if len(x_values) >= 2 else None,
            "change_pct": change_pct,
            "trend": trend,
        }
```

### Cambio 2: analytics_context.py

```python
for bank, stats in banks_to_show:
    current_date = stats.get("current_date", "N/A")
    first_date = stats.get("first_date", "N/A")

    context += f"""
- **{bank}**: {stats["current"]:.2f}% (al {current_date}),
  cambio desde {first_date}: {stats["change_pct"]:+.1f}%"""
```

### Resultado Esperado

Contexto mejorado:
```
**Estadísticas de ICAP:**
- **BBVA**: 20.06% (al 2025-10-01), cambio desde 2025-01-01: +4.5%
```

El LLM ahora sabrá exactamente qué fecha corresponde a qué valor.

---

## Tests de Regresión Necesarios

1. **test_chart_statistics_includes_dates**: Verificar que `extract_chart_statistics` retorna fechas
2. **test_llm_context_has_explicit_dates**: Verificar que el contexto LLM tiene fechas explícitas
3. **test_month_value_association**: Test E2E que valide asociación mes-valor correcta

---

## Impacto de la Corrección

- **Usuarios afectados**: Todos los que preguntan por períodos específicos
- **Métricas afectadas**: Todas las series temporales (ICAP, IMOR, Cartera, etc.)
- **Riesgo**: Bajo - solo agrega datos, no cambia lógica existente
- **Beneficio**: Elimina 100% de los bugs de "mes equivocado"
