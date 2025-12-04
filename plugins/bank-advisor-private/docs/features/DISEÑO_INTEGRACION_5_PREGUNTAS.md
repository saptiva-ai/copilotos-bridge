# Diseño de Integración - 5 Preguntas de Negocio
**Fecha:** 2025-12-02
**Plugin:** Bank Advisor MCP Server
**Estado:** Diseño Completo - Listo para Implementación

---

## 🎯 Resumen Ejecutivo

Este documento proporciona un plan de implementación completo para integrar 5 preguntas críticas de negocio al plugin Bank Advisor, incluyendo:
- Generación SQL automática (NL2SQL)
- Visualizaciones Plotly interactivas
- Detección de intenciones NLP
- Extracción de entidades
- Integración completa con MCP tool

**Filosofía de Arquitectura:** Extender patrones existentes sin romper compatibilidad. Aprovechar el esquema dual (legacy `monthly_kpis` + tablas normalizadas) para máxima flexibilidad.

---

## 📊 Las 5 Preguntas

### Q1: "¿Cuál es el IMOR de INVEX vs el mercado?"
- **Objetivo:** Comparar ratio de morosidad INVEX vs promedio del sistema
- **Fuente:** `monthly_kpis.imor`
- **Visualización:** Gráfica de líneas dual (INVEX en rojo sólido, SISTEMA en gris punteado)
- **Features:** Área sombreada cuando INVEX < SISTEMA (mejor performance)

### Q2: "¿Cómo está mi PDM/Market Share medido por cartera total?"
- **Objetivo:** Calcular participación de mercado de INVEX
- **Fuente:** `monthly_kpis.cartera_total` (con agregación window function)
- **Visualización:**
  - **Primaria:** Gráfica de pay (pie chart) con top 5 + "Otros"
  - **Secundaria:** Línea de tiempo mostrando evolución de market share
- **Cálculo:** `PDM = (cartera_INVEX / SUM(cartera_ALL)) * 100`

### Q3: "¿Cómo ha evolucionado la cartera de consumo en el último trimestre?"
- **Objetivo:** Trackear crecimiento de cartera de consumo en últimos 3 meses
- **Fuente:** `monthly_kpis.cartera_consumo_total`
- **Visualización:**
  - **Primaria:** Gráfica de cascada (waterfall) mes a mes
  - **Secundaria:** Línea con anotaciones de % de crecimiento
- **Features:** Filtro automático de tiempo (últimos 3 meses)

### Q4: "¿Cómo está mi IMOR en cartera automotriz frente al mercado?"
- **Objetivo:** Comparar IMOR automotriz INVEX vs sistema
- **Fuente:** `metricas_cartera_segmentada` (esquema normalizado)
  - `segmento_id = 2` (Automotriz)
  - Join con `instituciones` y `segmentos_cartera`
- **Visualización:** Igual a Q1 (líneas dual)
- **Hallazgo:** INVEX no tiene cartera automotriz (cartera = 0)

### Q5: "¿Cuál es el tamaño de los bancos por activos? ¿Qué % tiene cada banco?"
- **Objetivo:** Ranking de bancos por activos totales
- **Fuente:** `metricas_financieras.activo_total` (esquema normalizado)
- **Visualización:**
  - **Primaria:** Barras horizontales (top 20)
  - **Secundaria:** Pie chart (top 5 + "Otros")
- **Features:**
  - INVEX destacado en color diferente
  - Mostrar ranking explícitamente
  - Cálculo HHI (Herfindahl-Hirschman Index)

---

## 🏗️ Arquitectura de Integración

```
User Query (NL)
    ↓
FastMCP Server (main.py)
    ↓
HU3 NLP Pipeline
    ├─ EntityService (extracción)
    ├─ IntentService (clasificación)
    └─ Question Detection (routing)
         ↓
    ┌────┴────┬─────────┬─────────┬─────────┐
    Q1        Q2        Q3        Q4        Q5
    ↓         ↓         ↓         ↓         ↓
AnalyticsService (Enhanced)
    - get_comparative_ratio_data()
    - get_market_share_data()
    - get_segment_evolution()
    - get_institution_ranking()
         ↓
    ┌────┴────┐
Legacy        Normalized
monthly_kpis  metricas_*
    ↓
VisualizationService
    - _build_comparison_lines()
    - _build_market_share_pie()
    - _build_waterfall_chart()
    - _build_horizontal_ranking()
         ↓
Plotly JSON Response
```

---

## 📝 Templates SQL por Pregunta

### Q1: IMOR Comparison
```sql
SELECT
    fecha,
    banco_norm,
    imor * 100 AS imor_pct
FROM monthly_kpis
WHERE banco_norm IN ('INVEX', 'SISTEMA')
  AND fecha >= :date_start
  AND fecha <= :date_end
ORDER BY fecha ASC;
```

### Q2: Market Share (PDM)
```sql
WITH monthly_totals AS (
    SELECT
        fecha,
        banco_norm,
        cartera_total,
        SUM(cartera_total) OVER (PARTITION BY fecha) AS total_sistema
    FROM monthly_kpis
    WHERE fecha BETWEEN :date_start AND :date_end
)
SELECT
    fecha,
    banco_norm,
    (cartera_total / total_sistema) * 100 AS market_share_pct,
    RANK() OVER (PARTITION BY fecha ORDER BY cartera_total DESC) AS ranking
FROM monthly_totals
WHERE banco_norm = 'INVEX';
```

### Q3: Consumer Credit Evolution
```sql
WITH monthly_data AS (
    SELECT
        fecha,
        cartera_consumo_total,
        LAG(cartera_consumo_total, 1) OVER (ORDER BY fecha) AS prev_month
    FROM monthly_kpis
    WHERE banco_norm = 'INVEX'
      AND fecha >= :date_start
)
SELECT
    fecha,
    cartera_consumo_total AS current_value,
    prev_month,
    cartera_consumo_total - prev_month AS change_abs,
    ((cartera_consumo_total - prev_month) / NULLIF(prev_month, 0)) * 100 AS change_pct
FROM monthly_data;
```

### Q4: Automotive IMOR
```sql
SELECT
    mcs.fecha_corte,
    i.nombre_normalizado AS banco,
    mcs.imor * 100 AS imor_pct
FROM metricas_cartera_segmentada mcs
JOIN instituciones i ON mcs.institucion_id = i.id
WHERE mcs.segmento_id = 2  -- Automotriz
  AND i.nombre_normalizado IN ('INVEX', 'SISTEMA')
ORDER BY mcs.fecha_corte ASC;
```

### Q5: Bank Ranking by Assets
```sql
WITH asset_rankings AS (
    SELECT
        i.nombre_normalizado AS banco,
        mf.activo_total,
        (mf.activo_total / SUM(mf.activo_total) OVER ()) * 100 AS market_share_pct,
        RANK() OVER (ORDER BY mf.activo_total DESC) AS ranking
    FROM metricas_financieras mf
    JOIN instituciones i ON mf.institucion_id = i.id
    WHERE mf.fecha_corte = (SELECT MAX(fecha_corte) FROM metricas_financieras)
)
SELECT * FROM asset_rankings
ORDER BY ranking
LIMIT 20;
```

---

## 🎨 Especificaciones de Visualización Plotly

### Tipo 1: Comparison Lines (Q1, Q4)
```python
{
    "data": [
        {
            "x": dates,
            "y": invex_values,
            "type": "scatter",
            "mode": "lines+markers",
            "name": "INVEX",
            "line": {"color": "#E45756", "width": 3}
        },
        {
            "x": dates,
            "y": sistema_values,
            "type": "scatter",
            "mode": "lines+markers",
            "name": "SISTEMA",
            "line": {"color": "#AAB0B3", "width": 2, "dash": "dot"}
        }
    ],
    "layout": {
        "title": "IMOR: INVEX vs Sistema",
        "yaxis": {"ticksuffix": "%"}
    }
}
```

### Tipo 2: Market Share Pie + Line (Q2)
```python
# Pie chart
{
    "type": "pie",
    "labels": ["INVEX", "BBVA", "SANTANDER", "Otros"],
    "values": [5.2, 18.5, 15.3, 61.0],
    "marker": {"colors": ["#E45756", "#004481", "#EC0000", "#D3D3D3"]}
}

# Evolution line
{
    "type": "scatter",
    "x": dates,
    "y": market_share_pct,
    "fill": "tozeroy"
}
```

### Tipo 3: Waterfall Chart (Q3)
```python
{
    "type": "waterfall",
    "x": ["Jul", "Ago", "Sep", "Total"],
    "y": [1200, 150, -80, None],
    "measure": ["relative", "relative", "relative", "total"],
    "increasing": {"marker": {"color": "#2E8B57"}},
    "decreasing": {"marker": {"color": "#DC143C"}}
}
```

### Tipo 4: Horizontal Bar Ranking (Q5)
```python
{
    "type": "bar",
    "orientation": "h",
    "y": ["BBVA", "SANTANDER", "BANORTE", "INVEX", ...],
    "x": [2450000, 1980000, 1650000, 520000, ...],
    "marker": {
        "color": ["#004481", "#EC0000", "#D7282F", "#E45756", ...]
    }
}
```

---

## 🔌 Puntos de Integración por Servicio

### 1. AnalyticsService (analytics_service.py)
**Nuevos Métodos:**
- ✅ `get_comparative_ratio_data()` - Q1, Q4
- ✅ `get_market_share_data()` - Q2
- ✅ `get_segment_evolution()` - Q3
- ✅ `get_institution_ranking()` - Q5

### 2. VisualizationService (visualization_service.py)
**Nuevos Builders:**
- ✅ `_build_comparison_lines_with_shading()`
- ✅ `_build_market_share_pie()`
- ✅ `_build_waterfall_chart()`
- ✅ `_build_horizontal_ranking_bar()`

### 3. IntentService (intent_service.py)
**Nuevos Patrones:**
```python
# Q1, Q4: Comparación
["imor.*vs", "compara.*imor", "morosidad.*contra"]

# Q2: Market Share
["market share", "pdm", "participación.*mercado"]

# Q3: Trimestral
["último trimestre", "últimos 3 meses"]

# Q5: Ranking
["ranking", "top.*bancos", "tamaño.*bancos"]
```

### 4. EntityService (entity_service.py)
**Nuevas Detecciones:**
- Market share como métrica especial
- Segmento automotriz (segment_id=2)
- Ranking de activos
- Bandera `ranking_requested`

### 5. SqlGenerationService (sql_generation_service.py)
**Nuevos Templates:**
- ✅ `_generate_imor_comparison_sql()`
- ✅ `_generate_market_share_sql()`
- ✅ `_generate_segment_evolution_sql()`
- ✅ `_generate_ranking_sql()`

---

## 🗺️ Roadmap de Implementación

### Fase 1: Foundation (Días 1-2)
- ✅ Actualizar `synonyms.yaml`
- ✅ Extender `IntentService` con nuevos patrones
- ✅ Ampliar `EntityService` para segmentos
- ✅ Tests unitarios NL

### Fase 2: Q1 & Q4 - IMOR (Días 3-4)
- ✅ Implementar `get_comparative_ratio_data()`
- ✅ SQL template para comparación
- ✅ Visualización líneas dual con sombreado
- ✅ Tests integración

### Fase 3: Q2 - Market Share (Días 5-6)
- ✅ Implementar `get_market_share_data()`
- ✅ Window functions para PDM
- ✅ Pie chart + línea de evolución
- ✅ Tests E2E

### Fase 4: Q3 - Evolución Consumo (Días 7-8)
- ✅ Implementar `get_segment_evolution()`
- ✅ Waterfall chart builder
- ✅ Lógica period-over-period
- ✅ Tests visualización

### Fase 5: Q5 - Rankings (Días 9-10)
- ✅ Implementar `get_institution_ranking()`
- ✅ SQL con RANK() window
- ✅ Barras horizontales con highlights
- ✅ Métricas de concentración (HHI)

### Fase 6: Testing & Docs (Días 11-12)
- ✅ Tests E2E completos
- ✅ Smoke test script
- ✅ Documentación MCP tool
- ✅ Demo preparation

**Total:** 12 días de desarrollo

---

## 🧪 Estrategia de Testing

### Unit Tests
```python
# /tests/unit/test_5_questions_analytics.py
class TestQuestion1IMORComparison:
    async def test_imor_comparison_invex_vs_sistema()
    async def test_imor_comparison_invalid_metric()

class TestQuestion2MarketShare:
    async def test_market_share_calculation()
    async def test_market_share_ranking()

# ... Q3, Q4, Q5 ...
```

### Integration Tests
```python
# /tests/integration/test_5_questions_e2e.py
class TestFiveQuestionsEndToEnd:
    async def test_q1_imor_comparison_nl_query()
    async def test_q2_market_share_pdm()
    async def test_q3_consumer_credit_evolution()
    async def test_q4_automotive_imor()
    async def test_q5_bank_ranking_by_assets()
```

### Smoke Test
```bash
# /scripts/smoke_test_5_questions.py
python scripts/smoke_test_5_questions.py

# Valida que las 5 preguntas respondan correctamente
✅ Q1: IMOR Comparison - PASSED
✅ Q2: Market Share - PASSED
✅ Q3: Consumer Evolution - PASSED
✅ Q4: Automotive IMOR - PASSED
✅ Q5: Bank Ranking - PASSED
```

---

## 📁 Archivos Críticos

### Modificaciones Principales
1. `/src/bankadvisor/services/analytics_service.py` (4 métodos nuevos)
2. `/src/bankadvisor/services/visualization_service.py` (4 builders)
3. `/src/bankadvisor/services/intent_service.py` (patrones NL)
4. `/src/bankadvisor/entity_service.py` (detección segmentos)
5. `/src/main.py` (handlers en pipeline)

### Configuración
6. `/config/synonyms.yaml` (aliases nuevos)

### Testing
7. `/tests/unit/test_5_questions_analytics.py` (nuevo)
8. `/tests/integration/test_5_questions_e2e.py` (nuevo)
9. `/scripts/smoke_test_5_questions.py` (nuevo)

### Documentación
10. `/docs/5_QUESTIONS_GUIDE.md` (nuevo)

---

## 💡 Patrones de Consulta NL Soportados

### Q1: IMOR Comparison
- "¿Cuál es el IMOR de INVEX vs el mercado?"
- "Compara el IMOR de INVEX contra el sistema"
- "Morosidad INVEX versus promedio"
- "¿Cómo está mi IMOR comparado con el sistema?"

### Q2: Market Share
- "¿Cuál es mi market share?"
- "PDM de INVEX en cartera total"
- "Participación de mercado INVEX"
- "¿Qué porcentaje del mercado tenemos?"

### Q3: Consumer Evolution
- "Evolución cartera consumo últimos 3 meses"
- "Cartera de consumo último trimestre"
- "¿Cómo ha crecido mi cartera de consumo?"
- "Tendencia cartera consumo INVEX"

### Q4: Automotive IMOR
- "IMOR automotriz INVEX vs sistema"
- "Morosidad en créditos de auto"
- "¿Cómo está mi cartera de autos?"
- "Compara IMOR automotriz contra mercado"

### Q5: Bank Ranking
- "Ranking de bancos por activos"
- "¿Cuáles son los bancos más grandes?"
- "Tamaño de bancos por activos totales"
- "Top 10 bancos por activos"

---

## 🎯 Métricas de Éxito

### Funcionalidad
- ✅ 5/5 preguntas responden correctamente
- ✅ Visualizaciones Plotly generadas automáticamente
- ✅ SQL válido y optimizado
- ✅ Detección NL con >90% precisión

### Performance
- ⏱️ Respuesta < 2 segundos por query
- 💾 Queries optimizadas con índices
- 🔒 Validación SQL contra inyección

### Calidad
- 🧪 Cobertura de tests >80%
- 📊 Todas las visualizaciones renderizables
- 📝 Documentación completa
- 🚀 Ready para producción

---

## 📚 Referencias

**Documentos Relacionados:**
- `VALIDACION_COMPLETA.md` - Validación de datos existentes
- `ANALISIS_CAPACIDADES_DATOS.md` - Análisis de capacidades
- `ETL_CONSOLIDATION.md` - Arquitectura ETL

**Archivos Técnicos:**
- `src/main.py` - MCP Server principal
- `src/bankadvisor/services/` - Servicios core
- `config/synonyms.yaml` - Configuración NL
- `database_schema.sql` - Schema normalizado

---

## 🚀 Next Steps

1. **Revisar y Aprobar Diseño** (1 día)
2. **Implementar Fase 1** (Foundation) (2 días)
3. **Implementar Q1-Q5** en orden (8 días)
4. **Testing & QA** (2 días)
5. **Deploy a Staging** (0.5 días)
6. **Demo & User Acceptance** (0.5 días)

**Total Estimado:** 14 días

---

**Estado:** ✅ Diseño Completo - Listo para Implementación
**Autor:** Diseño Arquitectónico
**Fecha:** 2025-12-02
**Versión:** 1.0
