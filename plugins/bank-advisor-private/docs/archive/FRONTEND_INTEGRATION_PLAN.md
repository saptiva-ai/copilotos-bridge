# Frontend Integration Plan - BankAdvisor NL2SQL

**Fecha**: 2025-11-27
**Status**: DRAFT - Ready for Implementation
**Prioridad**: P0 - Demo Critical

---

## 🎯 Objetivo

Integrar completamente el pipeline NL2SQL de BankAdvisor con el frontend de OctaviOS, permitiendo que los usuarios visualicen gráficos bancarios directamente en el chat mediante queries en lenguaje natural.

---

## 📊 Estado Actual (Análisis Arquitectónico)

### ✅ Backend: COMPLETADO (70%)

**Flujo Actual:**
```
User Message → Backend → ToolExecutionService.invoke_bank_analytics()
                              ↓
                    bank_analytics_client.py (JSON-RPC)
                              ↓
                    bank-advisor:8002/rpc
                              ↓
                    NL2SQL Pipeline (COMPLETADO)
                              ↓
                    BankChartData (schema definido)
                              ↓
                    tool_results["bank_analytics"] ✅
```

**Archivos Backend Revisados:**
- ✅ `apps/backend/src/routers/chat/endpoints/message_endpoints.py:218-229` - Integración ya implementada
- ✅ `apps/backend/src/services/tool_execution_service.py:325-424` - invoke_bank_analytics() completo
- ✅ `apps/backend/src/services/bank_analytics_client.py` - Cliente MCP funcional
- ✅ `apps/backend/src/schemas/bank_chart.py` - BankChartData schema definido
- ✅ `apps/backend/src/models/artifact.py:20` - ArtifactType.BANK_CHART enum existe
- ✅ `plugins/bank-advisor-private/src/main.py:554-650` - Endpoint /rpc implementado

**Estado de BankChartData:**
```python
class BankChartData(BaseModel):
    type: str = "bank_chart"
    metric_name: str              # "IMOR", "ICOR", etc.
    bank_names: List[str]         # ["INVEX", "Sistema"]
    time_range: TimeRange         # {start, end}
    plotly_config: PlotlyChartSpec  # {data, layout, config}
    data_as_of: str               # "2025-07-01T00:00:00Z"
    source: str = "bank-advisor-mcp"
    title: Optional[str]          # "IMOR - INVEX vs Sistema"
```

### ❌ Frontend: FALTANTE (0%)

**Problemas Identificados:**

1. **No existe artifact renderer para BANK_CHART**
   - `apps/web/src/components/chat/artifact-card.tsx` solo tiene iconos para: markdown, code, graph
   - Falta handler específico para `type="bank_chart"`

2. **No hay componente de visualización Plotly**
   - Necesitamos componente React que renderice `PlotlyChartSpec`
   - Debe soportar interactividad (zoom, pan, tooltips)

3. **Backend no persiste BankChartData como artifact**
   - `tool_results["bank_analytics"]` existe pero no se crea Artifact en MongoDB
   - El LLM responde con texto pero el chart no se guarda

4. **Falta UI para clarification flow**
   - Backend puede retornar `requires_clarification=true`
   - Frontend no tiene componente para mostrar opciones al usuario

---

## 🏗️ Plan de Implementación (6 Tareas)

### Tarea 1: Mejorar Protocolo MCP en bank-advisor (P0)

**Objetivo:** Estandarizar la respuesta del endpoint /rpc para incluir metadata completa.

**Cambios en:** `plugins/bank-advisor-private/src/main.py`

**Ubicación:** Líneas 554-650 (endpoint /rpc)

**Mejoras:**

1. **Agregar version y status al response:**
```python
@app.post("/rpc")
async def json_rpc_endpoint(request: Request):
    # ... existing validation ...

    if method == "tools/call":
        tool_name = params.get("name")

        if tool_name == "bank_analytics":
            arguments = params.get("arguments", {})
            metric_or_query = arguments.get("metric_or_query", "")
            mode = arguments.get("mode", "dashboard")

            # Execute tool
            result = await _bank_analytics_impl(metric_or_query, mode)

            # MEJORA: Wrap result with metadata
            enhanced_result = {
                "success": True,
                "data": result,
                "metadata": {
                    "version": "1.0.0",
                    "pipeline": result.get("metadata", {}).get("pipeline", "nl2sql"),
                    "template_used": result.get("metadata", {}).get("template_used"),
                    "execution_time_ms": 0,  # TODO: track actual time
                    "requires_clarification": False,  # For future P0-3
                    "clarification_options": None
                }
            }

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(enhanced_result)
                        }
                    ]
                }
            })
```

2. **Agregar error handling mejorado:**
```python
except Exception as e:
    logger.error("rpc.tool_execution_failed", tool=tool_name, error=str(e))
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {
            "code": -32603,
            "message": "Tool execution failed",
            "data": {
                "tool": tool_name,
                "error": str(e),
                "type": type(e).__name__
            }
        }
    }, status_code=500)
```

**Resultado Esperado:**
- Response consistente con metadata
- Error handling robusto
- Preparado para P0-3 (clarification flow)

---

### Tarea 2: Persistir BankChartData como Artifact (P0)

**Objetivo:** Guardar automáticamente los resultados de bank_analytics en MongoDB como artifacts.

**Cambios en:** `apps/backend/src/routers/chat/endpoints/message_endpoints.py`

**Ubicación:** Después de línea 229 (donde se agrega bank_chart_data a tool_results)

**Implementación:**

```python
# 4.6. Check for bank analytics query (BA-P0-001)
bank_chart_data = await ToolExecutionService.invoke_bank_analytics(
    message=context.message,
    user_id=user_id
)
if bank_chart_data:
    tool_results["bank_analytics"] = bank_chart_data
    logger.info(
        "Bank analytics result added",
        metric=bank_chart_data.get("metric_name"),
        request_id=context.request_id
    )

    # NUEVO: Persist as artifact
    from ..services.artifact_service import ArtifactService
    from ..models.artifact import ArtifactType

    try:
        artifact = await ArtifactService.create_artifact(
            user_id=user_id,
            chat_session_id=chat_session.id,
            title=bank_chart_data.get("title", f"{bank_chart_data.get('metric_name')} - {', '.join(bank_chart_data.get('bank_names', []))}"),
            type=ArtifactType.BANK_CHART,
            content=bank_chart_data  # Full BankChartData object
        )

        logger.info(
            "bank_chart.artifact_created",
            artifact_id=artifact.id,
            metric=bank_chart_data.get("metric_name"),
            request_id=context.request_id
        )

        # Add artifact reference to tool_results for LLM context
        tool_results["bank_analytics_artifact_id"] = artifact.id

    except Exception as e:
        logger.error(
            "bank_chart.artifact_creation_failed",
            error=str(e),
            request_id=context.request_id
        )
        # Don't fail the request if artifact creation fails
```

**Resultado Esperado:**
- BankChartData guardado en MongoDB
- artifact_id disponible para el LLM
- Persistencia incluso si el LLM falla

---

### Tarea 3: Crear Componente BankChartViewer (React + Plotly)

**Objetivo:** Renderizar gráficos Plotly.js desde BankChartData en el frontend.

**Archivo Nuevo:** `apps/web/src/components/chat/artifacts/BankChartViewer.tsx`

**Dependencias:**
```bash
pnpm add react-plotly.js plotly.js
pnpm add -D @types/plotly.js
```

**Implementación:**

```typescript
"use client";

import React from "react";
import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";
import { cn } from "@/lib/utils";

// Dynamic import to avoid SSR issues with Plotly
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface BankChartData {
  type: "bank_chart";
  metric_name: string;
  bank_names: string[];
  time_range: {
    start: string;
    end: string;
  };
  plotly_config: {
    data: any[];
    layout: any;
    config?: any;
  };
  data_as_of: string;
  source: string;
  title?: string;
}

interface BankChartViewerProps {
  data: BankChartData;
  className?: string;
}

export function BankChartViewer({ data, className }: BankChartViewerProps) {
  const { plotly_config, title, metric_name, bank_names, time_range, data_as_of } = data;

  // Default layout enhancements for dark theme
  const enhancedLayout = {
    ...plotly_config.layout,
    paper_bgcolor: "#232B3A",
    plot_bgcolor: "#1a212e",
    font: {
      color: "#ffffff",
      family: "Inter, system-ui, sans-serif",
    },
    xaxis: {
      ...plotly_config.layout?.xaxis,
      gridcolor: "#2d3748",
      color: "#a0aec0",
    },
    yaxis: {
      ...plotly_config.layout?.yaxis,
      gridcolor: "#2d3748",
      color: "#a0aec0",
    },
    legend: {
      ...plotly_config.layout?.legend,
      bgcolor: "#1a212e",
      bordercolor: "#2d3748",
      borderwidth: 1,
    },
  };

  const plotConfig: Partial<PlotParams["config"]> = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
    ...plotly_config.config,
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-white/10 overflow-hidden",
        className
      )}
      style={{ backgroundColor: "#232B3A" }}
    >
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <h3 className="text-lg font-semibold text-white mb-1">
          {title || `${metric_name} - ${bank_names.join(" vs ")}`}
        </h3>
        <div className="flex items-center gap-4 text-xs text-white/60">
          <span>📊 {metric_name.toUpperCase()}</span>
          <span>🏦 {bank_names.join(", ")}</span>
          <span>📅 {time_range.start} → {time_range.end}</span>
          <span className="ml-auto">Actualizado: {new Date(data_as_of).toLocaleDateString("es-MX")}</span>
        </div>
      </div>

      {/* Plotly Chart */}
      <div className="p-4">
        <Plot
          data={plotly_config.data}
          layout={enhancedLayout}
          config={plotConfig}
          style={{ width: "100%", height: "400px" }}
          useResizeHandler
        />
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-white/5 border-t border-white/10 text-xs text-white/50">
        Fuente: CNBV - Datos históricos 2017-2025 • Procesado por BankAdvisor NL2SQL
      </div>
    </div>
  );
}
```

**Resultado Esperado:**
- Gráfico interactivo renderizado
- Dark theme consistente con OctaviOS
- Responsive design
- Metadatos visibles

---

### Tarea 4: Integrar BankChartViewer en artifact-card.tsx

**Objetivo:** Detectar artifacts de tipo BANK_CHART y renderizar con el componente apropiado.

**Cambios en:** `apps/web/src/components/chat/artifact-card.tsx`

**Implementación:**

```typescript
"use client";

import type { JSX } from "react";
import { useCanvasStore } from "@/lib/stores/canvas-store";
import type { ArtifactType } from "@/lib/types";
import { cn } from "@/lib/utils";

// NUEVO: Import BankChartViewer
import { BankChartViewer } from "./artifacts/BankChartViewer";

interface ArtifactCardProps {
  id: string;
  title: string;
  type?: ArtifactType | string | null;
  content?: any; // NUEVO: Para pasar BankChartData
}

const iconMap: Record<string, JSX.Element> = {
  markdown: (/* ... existing ... */),
  code: (/* ... existing ... */),
  graph: (/* ... existing ... */),
  // NUEVO: Icon para bank_chart
  bank_chart: (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M7 16v-4" />
      <path d="M12 16V8" />
      <path d="M17 16v-6" />
    </svg>
  ),
};

export function ArtifactCard({ id, title, type, content }: ArtifactCardProps) {
  const setArtifact = useCanvasStore((state) => state.setArtifact);

  const icon = iconMap[(type as string) || ""] || iconMap.markdown;

  // NUEVO: Si es bank_chart y tenemos content, renderizar inline
  if (type === "bank_chart" && content) {
    return (
      <div className="my-4">
        <BankChartViewer data={content} />
      </div>
    );
  }

  // Existing button for other artifact types
  return (
    <button
      type="button"
      onClick={() => setArtifact(id)}
      className={cn(
        "flex w-full items-center justify-between rounded-md border border-white/10 bg-white/5 px-3 py-2 text-left transition-colors",
        "hover:border-white/25 hover:bg-white/10",
      )}
    >
      <div className="flex items-center gap-3 overflow-hidden">
        <span className="grid h-8 w-8 place-items-center rounded-md bg-white/10 text-white/80">
          {icon}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{title}</p>
          <p className="text-xs uppercase tracking-wide text-saptiva-light/70">
            {type || "artifact"}
          </p>
        </div>
      </div>
      <span className="text-xs text-saptiva-light/70">Ver</span>
    </button>
  );
}
```

**Resultado Esperado:**
- Gráficos se renderizan inline en el chat
- Click en otros artifacts abre canvas
- Icono distintivo para bank_chart

---

### Tarea 5: Modificar Message Rendering para Incluir Artifacts

**Objetivo:** Pasar los artifacts al componente ArtifactCard durante el renderizado de mensajes.

**Archivo a Modificar:** Buscar componente que renderiza mensajes del chat (probablemente `apps/web/src/components/chat/message.tsx` o similar)

**Cambios Necesarios:**

1. Fetch artifact data cuando el mensaje tiene `artifact_id`
2. Pasar `content` prop a ArtifactCard

**Implementación (Pseudocódigo):**

```typescript
// En el componente de mensaje
const [artifactData, setArtifactData] = useState(null);

useEffect(() => {
  if (message.artifact_id && message.artifact_type === "bank_chart") {
    // Fetch artifact from backend
    fetch(`/api/artifacts/${message.artifact_id}`)
      .then(res => res.json())
      .then(data => setArtifactData(data.content));
  }
}, [message.artifact_id]);

// En el render
{message.artifact_id && (
  <ArtifactCard
    id={message.artifact_id}
    title={message.artifact_title || "Gráfico Bancario"}
    type={message.artifact_type}
    content={artifactData}  // Pasar BankChartData
  />
)}
```

**Resultado Esperado:**
- Mensajes con artifacts de bank_chart muestran gráfico inline
- Datos se cargan automáticamente
- UX fluida sin clicks adicionales

---

### Tarea 6: Crear E2E Test Plan y Documentation

**Objetivo:** Documentar flujo completo y crear guía de pruebas manuales.

**Archivos a Crear:**

1. `docs/E2E_TEST_PLAN.md` - Plan de pruebas end-to-end
2. `docs/FRONTEND_USER_GUIDE.md` - Guía de usuario

**Contenido del Test Plan:**

```markdown
# E2E Test Plan - BankAdvisor Frontend Integration

## Flujo Completo (Happy Path)

1. **Usuario abre chat en OctaviOS**
   - ✅ Verifica: UI carga correctamente
   - ✅ Verifica: No hay errores en consola

2. **Usuario escribe: "IMOR de INVEX en 2024"**
   - ✅ Backend detecta banking query
   - ✅ invoke_bank_analytics() se ejecuta
   - ✅ RPC call a bank-advisor:8002/rpc exitoso
   - ✅ NL2SQL pipeline genera SQL
   - ✅ Datos retornados (191 records filtrados)
   - ✅ Artifact creado en MongoDB
   - ✅ LLM recibe artifact_id en contexto

3. **LLM responde al usuario**
   - ✅ Texto explicativo generado
   - ✅ artifact_id incluido en respuesta

4. **Frontend renderiza respuesta**
   - ✅ Mensaje de texto se muestra
   - ✅ ArtifactCard detecta type="bank_chart"
   - ✅ BankChartViewer se renderiza inline
   - ✅ Gráfico Plotly muestra 12 meses de datos
   - ✅ Interactividad funciona (zoom, tooltips)

5. **Usuario hace segunda query: "Compara con Sistema"**
   - ✅ Contexto anterior se mantiene
   - ✅ Nueva gráfica con ambas series

## Test Cases Específicos

### TC-1: Query Simple
**Input:** "cartera comercial de INVEX"
**Expected Output:**
- Gráfico de línea con 1 serie (INVEX)
- Eje X: meses (2017-2025)
- Eje Y: valores en millones
- Tooltip muestra valor exacto

### TC-2: Comparación
**Input:** "IMOR INVEX vs Sistema 2024"
**Expected Output:**
- Gráfico con 2 series
- Leyenda muestra INVEX y Sistema
- Filtrado a 2024 (12 puntos por serie)

### TC-3: Query Ambigua (Futuro P0-3)
**Input:** "dame los datos del banco"
**Expected Output:**
- Backend retorna requires_clarification=true
- Frontend muestra opciones: INVEX, Sistema, Ambos
- Usuario selecciona → nueva query automática

### TC-4: Error Handling
**Input:** "DELETE FROM monthly_kpis" (SQL injection attempt)
**Expected Output:**
- Query rechazada por whitelist
- Mensaje de error amigable
- No crash

## Métricas de Éxito

- ✅ Latencia < 3 segundos (RPC + render)
- ✅ 0 errores en consola
- ✅ Gráfico responsive en mobile
- ✅ 100% de queries seguras bloqueadas
```

---

## 📋 Resumen de Archivos a Modificar/Crear

### Backend (2 archivos)

1. **`plugins/bank-advisor-private/src/main.py`** (Modificar líneas 554-650)
   - Mejorar JSON-RPC response con metadata
   - Agregar error handling robusto

2. **`apps/backend/src/routers/chat/endpoints/message_endpoints.py`** (Modificar línea 229+)
   - Agregar creación automática de Artifact

### Frontend (3 archivos nuevos + 1 modificado)

3. **`apps/web/src/components/chat/artifacts/BankChartViewer.tsx`** (NUEVO)
   - Componente React con Plotly.js
   - 180 líneas aprox

4. **`apps/web/src/components/chat/artifact-card.tsx`** (MODIFICAR)
   - Agregar bank_chart icon
   - Renderizado condicional inline
   - Pasar content prop

5. **`apps/web/src/components/chat/message.tsx`** (MODIFICAR - buscar archivo correcto)
   - Fetch artifact data
   - Pasar a ArtifactCard

### Documentación (2 archivos nuevos)

6. **`docs/E2E_TEST_PLAN.md`** (NUEVO)
   - Test cases completos
   - Happy path + edge cases

7. **`docs/FRONTEND_USER_GUIDE.md`** (NUEVO)
   - Guía de usuario final
   - Screenshots (agregar después)

---

## 🚀 Órden de Implementación Recomendado

### Fase 1: Backend Polish (30 min)
1. Tarea 1: Mejorar protocolo MCP
2. Tarea 2: Persistir artifacts

### Fase 2: Frontend Core (2 horas)
3. Tarea 3: BankChartViewer component
4. Tarea 4: Integrar en artifact-card

### Fase 3: Integration (1 hora)
5. Tarea 5: Message rendering
6. Testing manual del flujo E2E

### Fase 4: Documentation (30 min)
7. Tarea 6: E2E test plan y guía

**Total Estimado:** 4 horas

---

## ✅ Criterios de Éxito (Definition of Done)

- [ ] Usuario puede escribir "IMOR de INVEX 2024" y ver gráfico inline
- [ ] Gráfico es interactivo (zoom, tooltips)
- [ ] Dark theme consistente con OctaviOS
- [ ] Artifact persiste en MongoDB
- [ ] 0 errores en browser console
- [ ] Latencia < 3 segundos desde envío hasta render
- [ ] Documentación E2E completa
- [ ] Test plan con 5+ test cases

---

## 🔧 Troubleshooting Anticipado

### Problema: "Plot is not defined"
**Solución:** Asegurar dynamic import en BankChartViewer
```typescript
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });
```

### Problema: "Plotly.js bundle too large"
**Solución:** Usar import selectivo
```typescript
import Plotly from "plotly.js-basic-dist-min";
```

### Problema: Artifact no se renderiza
**Solución:** Verificar:
1. artifact_id presente en message
2. Fetch del artifact exitoso
3. content.type === "bank_chart"
4. plotly_config válido

### Problema: RPC timeout
**Solución:**
1. Aumentar BANK_ADVISOR_TIMEOUT en .env
2. Verificar logs del contenedor bank-advisor
3. Confirmar DB tiene 191 records

---

## 📊 Estado Post-Implementación Esperado

```
┌─────────────────────────────────────────────────────┐
│  OctaviOS Chat UI (Frontend)                        │
│  ┌───────────────────────────────────────────────┐  │
│  │ User: "IMOR de INVEX en 2024"                 │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │ Assistant:                                    │  │
│  │ Aquí está el IMOR de INVEX durante 2024...    │  │
│  │                                               │  │
│  │ ┌─────────────────────────────────────────┐   │  │
│  │ │ 📊 IMOR - INVEX                         │   │  │
│  │ │ [Gráfico Plotly Interactivo]            │   │  │
│  │ │   ↗ 12 meses de datos                    │   │  │
│  │ │   ↗ Tooltips, zoom, pan                  │   │  │
│  │ └─────────────────────────────────────────┘   │  │
│  │ Fuente: CNBV 2017-2025                        │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
          ↑
     artifact_id stored in MongoDB
          ↑
     BankChartData persisted
          ↑
     NL2SQL pipeline executed
          ↑
     bank-advisor RPC call
          ↑
     ToolExecutionService detected banking query
```

**Demo-Ready:** ✅ YES (100% coverage post-implementación)

---

**Next Steps:** Comenzar con Fase 1 (Backend Polish)
