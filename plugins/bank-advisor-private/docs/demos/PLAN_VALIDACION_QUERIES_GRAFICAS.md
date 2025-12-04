# Plan de Validación: Queries, Gráficas y Coherencia

**Fecha**: 2025-12-03
**Objetivo**: Verificar que las queries generadas, tipos de gráficas y visualizaciones tengan sentido lógico y funcional.

---

## 📋 Hallazgos del Testing Actual

### ✅ Funcionalidades que Funcionan Bien

1. **Sistema de Clarificación** ✅
   - Queries ambiguas ("datos del banco", "INVEX") disparan clarificación correctamente
   - Retornan opciones de métricas disponibles
   - Estructura JSON correcta con `type: "clarification"`, `message`, `options`, `context`

2. **Pipeline NL2SQL** ✅
   - 95% confianza en detección de intents
   - Pipeline: `hu3_nlp` para queries bien formadas, `nl2sql` para fallback
   - Latencia: 1.5-2s primera query (cold start), <10ms queries subsecuentes (caché)

3. **Métricas Nuevas** ✅
   - ICAP, TDA, TASA_MN reconocidas correctamente
   - Generan SQL válido
   - Retornan datos (aunque algunos con valores 0.00)

### ⚠️ Problemas Identificados

#### P0: Datos con Valores Zero

**Problema**: ICAP retorna `Range: 0.00 - 0.00` (103 puntos todos en 0)

```
Query: ICAP de INVEX
Result: 103 dates, all values = 0.00
Expected: Valores reales de capitalización (típicamente 12-20%)
```

**Causa raíz**:
- Script de validación confirmó 89.2% cobertura de `icap_total`
- Pero datos de INVEX específicamente tienen NULLs o zeros
- SQL generado es correcto: `SELECT fecha, banco_norm, icap_total AS value FROM monthly_kpis WHERE banco_norm IN ('INVEX')`

**Impacto**:
- Visualizaciones muestran línea plana en 0
- Usuario no puede analizar capitalización de INVEX
- SISTEMA y otros bancos pueden tener datos

**Acción**:
1. Verificar datos reales en DB para INVEX: `SELECT fecha, icap_total FROM monthly_kpis WHERE banco_norm='INVEX' AND icap_total IS NOT NULL ORDER BY fecha DESC LIMIT 12;`
2. Si son NULLs: Investigar fuente de datos ETL (¿INVEX no reporta ICAP a CNBV?)
3. Si son zeros reales: Actualizar visualización para mostrar "Sin datos disponibles"

#### P1: Tipo de Gráfica para Comparaciones

**Problema**: Comparación ICAP INVEX vs BBVA muestra `bar_chart` con valores `nan`

```
Query: ICAP de INVEX vs BBVA
Result: bar_chart, 2 points, Range: nan - nan
Expected: comparative_line o clarificación si no hay datos
```

**Causa raíz**:
- Sistema detecta `comparison` intent ✅
- Pero elige `bar_chart` en vez de `comparative_line`
- Los valores `nan` indican división por zero o datos NULL

**Acción**:
1. Revisar lógica de selección de gráfica en `src/tools/query_engine.py` o `src/nl2sql/intent_detector.py`
2. Comparaciones temporales → `comparative_line`
3. Comparaciones punto-a-punto (latest value) → `bar_chart`
4. Si no hay datos suficientes → clarificación "Datos insuficientes para ICAP"

#### P2: TASA_MN con Valores Altos

**Problema**: TASA_MN retorna `Range: 0.00 - 2006.56`, Latest: 1838.14

```
Query: tasa mn de INVEX
Result: Max value = 2006.56 (¿2006%?)
Expected: Tasas de interés típicamente 8-15%
```

**Causa raíz**:
- Datos pueden estar en basis points (2006 bp = 20.06%)
- O almacenados como valor absoluto sin normalizar

**Acción**:
1. Verificar unidad de medida en DB: `SELECT tasa_mn, fecha FROM monthly_kpis WHERE banco_norm='INVEX' ORDER BY tasa_mn DESC LIMIT 5;`
2. Si son basis points: Dividir entre 100 en SQL o visualización
3. Actualizar metadata para indicar unidad correcta (%, bp, o absoluto)

#### P3: Queries Inválidas Retornan Clarificación (No Error)

**Problema**: "METRICA_INVENTADA de INVEX" retorna clarificación en vez de error

```
Query: METRICA_INVENTADA de INVEX
Result: type="clarification" (lista de métricas válidas)
Expected: type="error" con mensaje "Métrica no encontrada"
```

**Comportamiento actual**:
- Sistema no reconoce métrica → trigger clarification
- Muestra opciones disponibles

**Evaluación**:
- ✅ Es aceptable desde UX (ayuda al usuario)
- ⚠️ Pero debería diferenciar entre "métrica no detectada" vs "métrica inválida"

**Acción**: Bajo prioridad - comportamiento actual es usable

---

## 🎯 Plan de Validación (4 horas)

### Fase 1: Validación de Datos (1.5h)

**Objetivo**: Verificar que los datos en DB son correctos y completos

#### 1.1 Script de Validación de Integridad de Datos
```python
# scripts/validate_data_integrity.py

Verificar:
- ICAP: ¿Valores reales o NULLs para INVEX?
- TDA: ¿Cobertura por banco?
- TASA_MN/ME: ¿Unidad de medida? (%, bp, absoluto)
- Fechas: ¿Hay gaps en series temporales?

Output:
- Reporte por banco: % cobertura de cada métrica
- Identificar bancos con datos completos vs incompletos
- Recomendar acciones: forward-fill, marcar como "no disponible", etc.
```

#### 1.2 Validar ETL Source
```bash
# Revisar última ejecución de ETL
docker exec -it bank-advisor python -c "
from src.etl.etl_runner import last_run_status
print(last_run_status())
"

# Verificar logs de ETL para ICAP
grep "icap_total" logs/etl_*.log
```

**Resultado esperado**:
- Documento con estado de datos por métrica/banco
- Lista de acciones para corregir datos faltantes

---

### Fase 2: Validación de Query Generation (1h)

**Objetivo**: Verificar que SQL generado sea correcto y óptimo

#### 2.1 Test Suite de Query Patterns
```python
# scripts/validate_query_generation.py

Test cases:
1. Single metric, single bank → SELECT fecha, banco_norm, {metric}
2. Comparison (2 banks) → WHERE banco_norm IN ('X', 'Y')
3. Timeline (últimos N meses) → WHERE fecha >= DATE_SUB(NOW(), INTERVAL N MONTH)
4. Specific year → WHERE YEAR(fecha) = {year}
5. Latest value → ORDER BY fecha DESC LIMIT 1

Validar:
- SQL es sintácticamente correcto
- Usa índices (EXPLAIN ANALYZE)
- Retorna datos esperados
- Maneja NULLs correctamente
```

#### 2.2 Performance Testing
```sql
-- Verificar que índices se usan
EXPLAIN ANALYZE
SELECT fecha, banco_norm, imor
FROM monthly_kpis
WHERE banco_norm = 'INVEX'
  AND fecha >= '2024-01-01'
ORDER BY fecha DESC;

-- Debe usar: idx_monthly_kpis_banco_fecha (Bitmap Index Scan)
-- Execution time: < 5ms
```

**Resultado esperado**:
- 100% queries usan índices
- Latencia < 10ms para queries simples

---

### Fase 3: Validación de Tipos de Gráfica (1h)

**Objetivo**: Verificar que el tipo de visualización sea apropiado

#### 3.1 Matriz de Intents → Visualizations

| Intent | Patrón Query | Viz Esperada | Ejemplo |
|--------|--------------|--------------|---------|
| `point_value` | "IMOR de INVEX" | `line_chart` | Serie temporal completa |
| `comparison` (temporal) | "INVEX vs SISTEMA" | `comparative_line` | 2+ líneas superpuestas |
| `comparison` (punto) | "IMOR de INVEX vs SISTEMA hoy" | `bar_chart` | Barras lado a lado |
| `evolution` | "últimos 12 meses" | `line_chart` | Serie temporal filtrada |
| `ranking` | "Top 5 bancos por ICAP" | `bar_chart` | Barras ordenadas |
| `ambiguous` | Sin métrica clara | `clarification` | Opciones de métricas |

#### 3.2 Test de Coherencia Viz
```python
# scripts/validate_visualizations.py

Para cada intent:
1. Generar query de prueba
2. Ejecutar y obtener response
3. Validar:
   - data.visualization == expected_viz
   - plotly_config.data tiene estructura correcta
   - Si comparative_line → múltiples series en plotly_data
   - Si bar_chart → x/y apropiados para barras

Reportar inconsistencias
```

**Resultado esperado**:
- 100% intents mapeados correctamente a visualizaciones
- Documento con reglas de mapeo validadas

---

### Fase 4: Validación de Plotly Config (0.5h)

**Objetivo**: Verificar que configuración de Plotly sea renderizable

#### 4.1 Schema Validation
```python
# scripts/validate_plotly_schema.py

Validar estructura:
{
  "data": [
    {
      "x": [...],  # Fechas o categorías
      "y": [...],  # Valores numéricos (no NaN, no Infinity)
      "type": "scatter" | "bar",
      "mode": "lines+markers" | "markers",
      "name": "BANCO_NAME",
      "line": {"color": "#HEX", "width": int}
    }
  ],
  "layout": {
    "title": str,
    "xaxis": {"title": str},
    "yaxis": {"title": str (unidad correcta)}
  }
}

Validaciones:
- len(x) == len(y)
- No valores NaN/Infinity en y
- Colores válidos en line.color
- Títulos no vacíos
```

#### 4.2 Test de Rendering
```python
# Generar HTML de prueba con plotly.js
import plotly.graph_objects as go

for test_case in test_cases:
    fig = go.Figure(response['data']['plotly_config'])
    fig.write_html(f"test_viz_{test_case.name}.html")
    # Abrir en browser y verificar visualmente
```

**Resultado esperado**:
- 100% configs renderizables sin errores
- HTML previews generados para revisión manual

---

## 🔧 Mejoras Propuestas

### Mejora 1: Data Quality Warnings (P0)

**Implementación**: Agregar warnings en response cuando datos tienen problemas

```python
# En query_engine.py, después de fetch_data()

if all(v == 0 for v in values):
    response['metadata']['warnings'] = [
        {
            "type": "no_data",
            "message": f"No hay datos disponibles de {metric} para {banco}",
            "suggestion": "Intenta con otro banco o métrica"
        }
    ]
```

**Beneficio**: Usuario informado inmediatamente de problemas de datos

### Mejora 2: Normalización de Unidades (P0)

**Implementación**: Configurar unidades por métrica en `METRIC_CONFIGS`

```python
METRIC_CONFIGS = {
    "tasa_mn": {
        "unit": "basis_points",
        "display_unit": "%",
        "transform": lambda x: x / 100  # bp → %
    },
    "icap_total": {
        "unit": "percentage",
        "display_unit": "%",
        "transform": lambda x: x  # Ya en %
    }
}
```

**Beneficio**: Valores mostrados en unidades consistentes y comprensibles

### Mejora 3: Lógica de Selección de Viz (P1)

**Implementación**: Reglas explícitas en `visualization_selector.py`

```python
def select_visualization(intent, banks, time_range, data_points):
    if intent == "comparison":
        if time_range and data_points > 3:
            return "comparative_line"  # Serie temporal
        else:
            return "bar_chart"  # Punto a punto

    elif intent == "evolution":
        return "line_chart"

    elif intent == "ranking":
        return "bar_chart"

    # Default
    return "line_chart"
```

**Beneficio**: Visualizaciones consistentes y predecibles

### Mejora 4: Validación Pre-Render (P2)

**Implementación**: Validar plotly_config antes de enviar

```python
def validate_plotly_data(plotly_config):
    for series in plotly_config['data']:
        # Remover NaN/Infinity
        y_values = [v if np.isfinite(v) else None for v in series['y']]
        series['y'] = y_values

        # Verificar longitudes
        assert len(series['x']) == len(series['y']), "x/y length mismatch"

        # Validar colores
        assert re.match(r'^#[0-9A-Fa-f]{6}$', series['line']['color'])

    return plotly_config
```

**Beneficio**: Cero errores de rendering en frontend

---

## 📊 Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Queries con datos completos | 60% (estimado) | 90% |
| Visualizaciones correctas | 85% (estimado) | 100% |
| SQL con índices | 100% ✅ | 100% |
| Latencia P95 | 1911ms | <500ms |
| Zero rendering errors | ? | 100% |

---

## 🚀 Cronograma de Ejecución

### Día 1 (4h)
- ✅ Testing inicial del flujo (HECHO)
- ⏳ Fase 1: Validación de datos (1.5h)
- ⏳ Fase 2: Validación de queries (1h)
- ⏳ Fase 3: Validación de viz (1h)
- ⏳ Fase 4: Validación de plotly (0.5h)

### Día 2 (2h)
- Implementar mejoras P0 (warnings, normalización)
- Testing de regresión

### Día 3 (1h)
- Documentar hallazgos
- Actualizar README con limitaciones conocidas
- PR con mejoras

---

## 📝 Notas Finales

**Hallazgos clave del testing actual**:
1. ✅ Sistema funcional end-to-end
2. ✅ Clarificación funciona perfectamente
3. ⚠️ Datos de ICAP incompletos para INVEX
4. ⚠️ TASA_MN en unidades no normalizadas
5. ⚠️ Algunas visualizaciones con NaN values

**Próximos pasos inmediatos**:
1. Ejecutar script de validación de datos
2. Verificar valores de ICAP/TDA/TASA en DB
3. Crear script de validación de queries
4. Implementar warnings de calidad de datos
