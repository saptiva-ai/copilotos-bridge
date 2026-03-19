---
id: "TASK-2026-01-27-1030__dashboard-engagement-metrics"
title: "Dashboard: Engagement Metrics + UX Improvements"
status: "DONE"
phase: "Validate"
scope_in:
  - "Nuevas métricas de engagement (DAU, WAU, DAU/MAU, Queries/Usuario)"
  - "Fix bug latencia = 0 (instrumentación backend)"
  - "Time to First Insight (TTFI) metric"
  - "Mejoras de diseño (tipografía IBM Plex, legibilidad gráficas)"
  - "Export de historiales de conversación"
scope_out:
  - "Integración PostHog (evaluar en futuro)"
  - "Modo oscuro (nice-to-have)"
  - "Alertas en tiempo real"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "docker exec octavios-chat-bajaware_invex-dashboard python -c 'from queries.engagement import EngagementQueries; print(\"OK\")'"
  - "curl -s http://localhost:8050/dashboard/ | grep -q 'DAU'"
pr_files:
  - "apps/dashboard/queries/engagement.py"
  - "apps/dashboard/layouts/engagement.py"
  - "apps/dashboard/callbacks/engagement.py"
  - "apps/dashboard/app.py"
  - "apps/backend/src/services/streaming/*.py"
test_status: ""
priority: "HIGH"
estimated_effort: "16-24h"
stakeholders:
  - "Carlos Lara (Head of Product)"
  - "Ronald (PM)"
  - "Jaziel Flores (Tech Lead)"
---

# Summary

- **Objective**: Agregar métricas de engagement empresarial al dashboard de Bank Advisor para medir adopción real, stickiness y time-to-value, además de mejorar la UX visual.
- **Constraints**:
  - No romper métricas existentes
  - Mantener refresh interval de 60s para no sobrecargar MongoDB
  - Compatible con datos históricos (no requiere backfill)

---

# Business Context

## Conversación con Stakeholders (2026-01-27)

**Carlos Lara (Head of Product)**:
> - Time to Value: Time to First Insight - desde login inicial hasta primer insight accionable
> - Latencia: Hoy dice cero, probablemente está mal
> - DAU/MAU ratio: nos dice qué tan sticky es la herramienta
> - WAU es mejor que DAU para Bank Advisor - ciclos de análisis semanales
> - ¿Pueden darme los historiales de conversación para estudiar qué preguntan?

**Ronald (PM)**:
> - DAU/MAU mensual nos dilata mucho el tiempo de reacción
> - Verlo semana a semana nos da más oportunidad de entender cambios que desplegamos
> - WAU es definitivamente mejor que DAU para este caso

**Conclusión**: Métricas semanales (WAU) son prioritarias. DAU/MAU se incluye pero WAU es el KPI principal.

---

# Technical Analysis

## Estado Actual del Dashboard

**Arquitectura**: Plotly Dash (Python) + MongoDB queries directos
**Ubicación**: `apps/dashboard/`
**Puerto**: 8050 (path: `/dashboard/`)
**Versión actual**: v1.0.1

### Tabs Existentes

| Tab | KPIs | Charts |
|-----|------|--------|
| Users & Activity | Total Users, Active (24h), New Today, Recent Logins | Registrations Trend, Activity Distribution |
| Conversations | Total, Active Chats, **Avg Latency (BUG=0)**, Messages Today | Messages Trend, Role Distribution, Latency Percentiles |
| Feedback | Satisfaction Rate, Total, Thumbs Up/Down | Feedback Trend, Satisfaction Gauge, Recent Comments |
| Infrastructure | Documents, Storage, Processing, Failed | Upload Trend, Status Distribution, File Types |

### Bug Crítico: Latencia = 0

```python
# apps/dashboard/queries/conversations.py:31-44
def get_average_latency(self) -> float:
    pipeline = [
        {"$match": {
            "latency_ms": {"$exists": True, "$ne": None},  # ❌ Campo NO existe en colección
            "role": "assistant",
        }},
        ...
    ]
```

**Root Cause**: El backend NO está guardando `latency_ms` en los mensajes de assistant.
**Fix Required**: Instrumentar en `apps/backend/src/services/streaming/` para medir tiempo de respuesta.

---

# Design Analysis (UX/UI)

## Problemas Actuales

### Tipografía
- **Font actual**: Inter (Google Fonts)
- **Problema**: En gráficas Plotly, los labels pequeños no son legibles
- **Solución propuesta**: IBM Plex Sans/Mono
  - Mejor legibilidad en tamaños pequeños
  - Mono para números/datos tabulares
  - Usado por IBM, Carbon Design System

### Layout Issues

| Problema | Impacto | Solución |
|----------|---------|----------|
| 4 KPIs en fila muy apretados | Difícil escanear | 3 KPIs principales + expandibles |
| Sin sparklines en KPIs | No se ve tendencia rápida | Mini-gráficos inline |
| Tabs sin iconos | Menos intuitivo | Agregar iconos + badges |
| Sin filtro de fechas | No se puede comparar periodos | Date range picker global |
| Sin comparación temporal | No se detectan cambios | "+15% vs semana pasada" |
| Charts estáticos | Poca interactividad | Tooltips mejorados, zoom, export |

### Propuesta Visual

```
┌─────────────────────────────────────────────────────────────────────┐
│  HEADER                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 🏦 Bank Advisor Metrics    [Date Range: Last 7 days ▼]   🟢 LIVE│ │
│  └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  TABS (con iconos)                                                   │
│  [👥 Engagement] [💬 Conversations] [⭐ Feedback] [🗄️ Infrastructure]│
├─────────────────────────────────────────────────────────────────────┤
│  KPI CARDS (3 principales + hover para más)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                    │
│  │ WAU    45   │ │ Stickiness  │ │ Avg Queries │                    │
│  │ ▲ +12%     │ │ 26.7%       │ │ 4.2/user    │                    │
│  │ ▁▂▃▅▆▇    │ │ ▁▂▂▃▃▄     │ │ ▅▆▆▇▇▇     │   <- sparklines    │
│  └─────────────┘ └─────────────┘ └─────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Font Stack Propuesto

```css
:root {
    --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
}

/* KPI values - monospace para alineación */
.kpi-value {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}

/* Chart labels */
.plotly .gtitle, .plotly .xtick, .plotly .ytick {
    font-family: var(--font-sans) !important;
    font-size: 11px !important;
}
```

---

# New Metrics Specification

## 1. Engagement Tab (NUEVO)

### KPIs

| Métrica | Query | Descripción |
|---------|-------|-------------|
| **DAU** | Usuarios únicos con query hoy | `messages.distinct("user_id", {created_at: {$gte: today}, role: "user"})` |
| **WAU** | Usuarios únicos últimos 7 días | Similar, ventana 7d |
| **DAU/MAU** | Ratio stickiness | DAU / MAU * 100 |
| **Queries/User** | Promedio queries por usuario activo | total_queries / active_users |

### Charts

1. **WAU Trend (8 semanas)**: Line chart con anotación de cambios importantes
2. **Queries per User Distribution**: Histograma (¿cuántos usuarios hacen 1, 2-5, 5-10, 10+ queries?)
3. **Session Duration Distribution**: ¿Cuánto tiempo pasan en la app?

## 2. Time to First Insight (TTFI)

```python
def get_time_to_first_insight(self) -> dict:
    """
    Mide tiempo desde created_at del usuario hasta su primer mensaje
    que generó un chart (metadata.bank_chart_data exists).
    """
    pipeline = [
        {"$lookup": {
            "from": "messages",
            "let": {"user_id": "$_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$user_id", "$$user_id"]},
                    "metadata.bank_chart_data": {"$exists": True}
                }},
                {"$sort": {"created_at": 1}},
                {"$limit": 1}
            ],
            "as": "first_insight"
        }},
        {"$unwind": {"path": "$first_insight", "preserveNullAndEmptyArrays": False}},
        {"$project": {
            "ttfi_minutes": {
                "$divide": [
                    {"$subtract": ["$first_insight.created_at", "$created_at"]},
                    60000  # ms to minutes
                ]
            }
        }},
        {"$group": {
            "_id": None,
            "avg_ttfi": {"$avg": "$ttfi_minutes"},
            "p50_ttfi": {"$percentile": {"input": "$ttfi_minutes", "p": [0.5]}}
        }}
    ]
```

## 3. Latency Fix (Instrumentación Backend)

**Archivos a modificar**:
- `apps/backend/src/services/streaming/stream_processor.py`
- `apps/backend/src/services/streaming/message_service.py`

**Cambio requerido**:
```python
# Al inicio del procesamiento
start_time = time.perf_counter()

# Al guardar el mensaje de assistant
latency_ms = (time.perf_counter() - start_time) * 1000
message_doc["latency_ms"] = latency_ms
```

## 4. Export de Historiales

Endpoint o botón para descargar:
- CSV con: timestamp, user_email, query, response_summary, had_chart
- Filtrable por fecha
- Para análisis offline por Carlos

---

# Implementation Phases

## Phase 1: Bug Fixes (4h) ✅ COMPLETE
- [x] Fix latency instrumentation en backend
- [x] Verificar que latency_ms se guarda en nuevos mensajes
- [x] Dashboard muestra latencia real

## Phase 2: Engagement Metrics (8h) ✅ COMPLETE
- [x] Crear `queries/engagement.py` con DAU/WAU/Stickiness
- [x] Crear `layouts/engagement.py` con nueva tab
- [x] Crear `callbacks/engagement.py` para refresh
- [x] Registrar callbacks en `callbacks/__init__.py`

## Phase 3: Design Improvements (6h) ✅ COMPLETE
- [x] Migrar a IBM Plex Sans/Mono
- [x] Agregar sparklines a KPI cards
- [x] Iconos en tabs
- [x] Date range picker global
- [x] Comparación temporal (vs periodo anterior)

## Phase 4: Export & Analytics (4h) ✅ COMPLETE
- [x] Export query `export_conversation_history()` en ConversationQueries
- [x] Botón de download en dashboard
- [x] Callback para generar CSV con filtro de fechas

---

# Files to Create/Modify

## New Files
```
apps/dashboard/
├── queries/engagement.py          # DAU, WAU, Stickiness queries
├── layouts/engagement.py          # New tab layout
├── callbacks/engagement.py        # Refresh callbacks
└── components/sparkline.py        # Inline mini-charts
```

## Modified Files
```
apps/dashboard/
├── app.py                         # Register new tab, update fonts
├── layouts/main.py                # Add Engagement tab
├── components/kpi_card.py         # Add sparkline support
└── config.py                      # Font config

apps/backend/src/services/streaming/
├── stream_processor.py            # Add latency tracking
└── message_service.py             # Save latency_ms
```

---

# Acceptance Criteria

1. **Latency**: Dashboard muestra latencia promedio > 0 para mensajes nuevos
2. **WAU**: Muestra usuarios activos últimos 7 días (número razonable, no 0)
3. **Stickiness**: Ratio DAU/MAU calculado correctamente
4. **Typography**: Charts usan IBM Plex, labels legibles a 11px
5. **Sparklines**: KPI cards muestran tendencia de 7 días
6. **Export**: Botón descarga CSV con historiales filtrados

---

# Updates

- 2026-01-27 10:30 - Created. Context from Carlos Lara, Ronald discussion.
- 2026-01-27 10:30 - Technical analysis of current dashboard completed.
- 2026-01-27 10:30 - Identified latency bug (field not being saved).
- 2026-01-27 ~14:00 - Phase 1 complete: Latency tracking implemented in streaming_handler.py → FinalizerContext → message_persistence.py
- 2026-01-27 ~14:00 - Phase 2 complete: New Engagement tab with DAU, WAU, Stickiness, Queries/User, TTFI, trend charts
- 2026-01-27 ~14:00 - Committed: `b83e4ee4 feat(dashboard): add engagement metrics tab and fix latency tracking`
- 2026-01-27 ~15:00 - Phase 3 complete: IBM Plex fonts, sparklines, trend indicators, tab icons, date picker
- 2026-01-27 ~15:00 - Phase 4 complete: CSV export with date filtering
- 2026-01-27 ~15:00 - Committed: `5248512b feat(dashboard): add design improvements and CSV export (Phase 3 & 4)`
- 2026-01-27 ~15:00 - All phases complete. Ready for deployment.
