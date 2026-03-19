# Research: MCP Tools Integration Gap

## Fecha: 2026-02-04

## Hallazgo Principal

**Los 21 MCP tools granulares existen pero el backend NO los usa.**

### Evidencia

```bash
# call_bank_advisor_tool EXISTE pero NUNCA se invoca:
grep -r "call_bank_advisor_tool(" apps/backend/src/
# Solo muestra la DEFINICIÓN en bank_analytics_client.py:132

# Todo el tráfico va por query_bank_analytics():
grep -r "query_bank_analytics(" apps/backend/src/
# apps/backend/src/services/bank_analytics_client.py:1140
# apps/backend/src/services/tool_execution_service.py:731
```

## Arquitectura Actual (Broken)

```
User Query
    │
    ▼
┌───────────────────────────────────────┐
│ tool_execution_service.py             │
│ invoke_bank_analytics()               │
│   └── query_bank_analytics()  ◄───────┼──── SIEMPRE llama al tool monolítico
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ bank_analytics_client.py              │
│ query_bank_analytics()                │
│   method: "tools/call"                │
│   name: "bank_analytics" ◄────────────┼──── DEPRECATED tool
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ bank-advisor /rpc                     │
│ - bank_analytics (deprecated)         │
│ - list_institutions ◄─────────────────┼──── NUNCA se llaman directamente
│ - lookup_bank_code  ◄─────────────────┤
│ - get_metric_ranking ◄────────────────┤
│ - ... 18 tools más                    │
└───────────────────────────────────────┘
```

## Arquitectura Objetivo

```
User Query
    │
    ▼
┌───────────────────────────────────────┐
│ tool_execution_service.py             │
│ invoke_bank_analytics()               │
│   ├── detect_tool_from_query()  ◄─────┼──── NUEVO: routing inteligente
│   └── call_bank_advisor_tool()  ◄─────┼──── USA función existente
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ bank_analytics_client.py              │
│ call_bank_advisor_tool(tool_name)     │
│   method: "tools/call"                │
│   name: <tool específico> ◄───────────┼──── Tool granular correcto
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ bank-advisor /rpc                     │
│ - list_institutions      ✓            │
│ - lookup_bank_code       ✓            │
│ - get_metric_ranking     ✓            │
│ - get_time_series        ✓            │
│ - ... tools específicos               │
└───────────────────────────────────────┘
```

## Funciones Existentes (Ya Implementadas)

### 1. call_bank_advisor_tool() - bank_analytics_client.py:132

```python
async def call_bank_advisor_tool(
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Call a specific MCP tool on bank-advisor service.
    Phase 2 (2026-02-03 REFACTOR: handlers-to-mcp-tools):
    Enables calling granular tools by name instead of only bank_analytics.
    """
    # ... implementación completa y funcional
```

**Status:** ✅ Implementada, lista para usar

### 2. list_bank_advisor_tools() - bank_analytics_client.py

```python
async def list_bank_advisor_tools() -> List[Dict[str, Any]]:
    """Fetch available tools from bank-advisor /rpc tools/list."""
```

**Status:** ✅ Implementada, usada para system prompt

### 3. format_tools_for_llm() - bank_analytics_client.py

```python
def format_tools_for_llm(tools: List[Dict[str, Any]]) -> str:
    """Format tools as markdown for LLM system prompt."""
```

**Status:** ✅ Implementada, usada en streaming_handler.py

## Lo Que FALTA

### 1. Tool Router (detect_tool_from_query)

No existe función que mapee query → tool específico. Opciones:

**Opción A: Regex-based (Simple)**
```python
TOOL_PATTERNS = {
    r"(instituciones|bancos|listado)": "list_institutions",
    r"(clave|código).*institucional": "lookup_bank_code",
    r"(ranking|top|mejores|peores)": "get_metric_ranking",
    r"(evolución|serie|histórico)": "get_time_series",
    r"(comparar|vs|versus)": "compare_banks",
    r"(region|estado|entidad)": "get_regional_portfolio",
}
```

**Opción B: Semantic Router (Robusto)**
- Usar Saptiva Embed para clasificar query
- Ya existe `semantic_scorer.py` con embeddings
- Más robusto pero más complejo

**Opción C: Usar _handle_catalog_query() de bank-advisor**
- Bank-advisor ya tiene `_handle_catalog_query()` que detecta catalog queries
- Extender ese patrón al backend

### 2. Wiring en tool_execution_service.py

Modificar `invoke_bank_analytics()` para:
1. Detectar tipo de query
2. Llamar tool específico via `call_bank_advisor_tool()`
3. Fallback a `query_bank_analytics()` si no hay match

## Queries Afectadas

| Query | Tool Esperado | Actualmente |
|-------|---------------|-------------|
| "dame las instituciones" | `list_institutions` | `bank_analytics` (hallucina) |
| "clave de santander" | `lookup_bank_code` | `bank_analytics` (routing interno) |
| "ranking IMOR" | `get_metric_ranking` | `bank_analytics` (funciona) |
| "evolución BBVA" | `get_time_series` | `bank_analytics` (funciona) |
| "cartera por estado" | `get_regional_portfolio` | `bank_analytics` (funciona) |

**Nota:** Algunas queries funcionan porque bank-advisor tiene routing interno, pero el LLM no tiene visibilidad de los tools disponibles para queries complejas.

## Impacto del Gap

1. **Catalog queries** (`list_institutions`, `lookup_bank_code`) - Parcialmente arreglado con `_handle_catalog_query()` en bank-advisor
2. **Observability** - No hay logs de qué tool se usó realmente
3. **LLM capability** - LLM no puede pedir tools específicos
4. **Error granularity** - Errores genéricos en lugar de específicos por tool

## Recomendación

**Fase 2.5: Wire call_bank_advisor_tool() for catalog queries**

Empezar con catalog queries que son las más afectadas:
- `list_institutions` - para "dame las instituciones"
- `lookup_bank_code` - para "clave de X"

Implementación mínima:
```python
# tool_execution_service.py
async def invoke_bank_analytics(self, ...):
    # NUEVO: Detectar catalog queries
    if is_catalog_query(user_query):
        tool_name = detect_catalog_tool(user_query)
        return await call_bank_advisor_tool(tool_name, {})

    # Fallback existente
    return await query_bank_analytics(...)
```

## Archivos a Modificar

1. `apps/backend/src/services/tool_execution_service.py`
   - Agregar routing a tools específicos

2. `apps/backend/src/services/bank_analytics_client.py`
   - Agregar helper `detect_catalog_tool()`
   - (Opcional) Mover routing aquí

## Tests Necesarios

1. Verificar `call_bank_advisor_tool()` funciona end-to-end
2. Test de routing: query → tool correcto
3. Test de fallback: query desconocida → `query_bank_analytics()`

## Validación de Tools (2026-02-04)

### Test Directo de MCP Tools

```bash
# list_institutions - FUNCIONA ✅
curl -s http://localhost:8002/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"test","method":"tools/call","params":{"name":"list_institutions","arguments":{"limit":5}}}'
# → {"success":true,"institutions":[...5 bancos...],"total":5}

# lookup_bank_code - FUNCIONA ✅
curl -s http://localhost:8002/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"test","method":"tools/call","params":{"name":"lookup_bank_code","arguments":{"code":"040014"}}}'
# → {"success":true,"bank":{"nombre_corto":"SANTANDER","clave_cnbv":"0000040014"}}
```

### Flujo Actual (Workaround)

```
Backend → query_bank_analytics()
        → bank_analytics (deprecated tool)
          ├── _handle_catalog_query()     ← Workaround interno (línea 770)
          │     └── list_institutions()   ← Llamada interna
          └── ... resto del pipeline
```

El workaround funciona para catalog queries pero:
1. Todo sigue pasando por el tool monolítico
2. Backend no sabe qué tool se usó realmente
3. No hay logs específicos por tool en backend

## Implementación Phase 2.5 (2026-02-04)

### Código Agregado

**`bank_analytics_client.py`:**
- `CATALOG_PATTERNS` - regex patterns para detectar catalog queries
- `detect_catalog_tool()` - detecta query tipo y retorna tool + args
- `handle_catalog_query()` - ejecuta tool y formatea respuesta

**`tool_execution_service.py`:**
- Import de `handle_catalog_query`
- Routing antes de `query_bank_analytics()`:
  ```python
  catalog_result = await handle_catalog_query(combined_message)
  if catalog_result:
      return catalog_result
  ```

### Tests de Validación

```
Testing catalog queries:
✅ "dame las instituciones" → list_institutions → 121 instituciones
✅ "clave de santander" → list_institutions + filter → SANTANDER: 0000040014
✅ "imor de bbva" → query_bank_analytics() → IMOR chart (fallback correcto)
```

### Logs de Observabilidad

```
catalog_routing.list_institutions_detected pattern=... query='dame las instituciones'
bank_advisor_tool.call tool=list_institutions url=http://bank-advisor:8002
bank_advisor_tool.success success=True tool=list_institutions
bank_analytics.catalog_routed query='dame las instituciones' type=catalog
```

## E2E Test Results (2026-02-04)

```
======================================================================
CATALOG ROUTING E2E TEST SUITE - Phase 2.5
======================================================================

[1/4] Detection: list_institutions (11 cases)    11/11 passed
[2/4] Detection: lookup_bank_by_name (9 cases)    9/9 passed
[3/4] Detection: non-catalog returns None         9/9 passed
[4/4] Handlers E2E                               10/10 passed

======================================================================
TOTAL: 39/39 passed (100.0%)
======================================================================
```

### Test Coverage
- **Detection patterns:** 29 queries tested
- **Handler E2E:** 10 scenarios (list, lookup, fallback, edge cases)
- **Bank lookups verified:** SANTANDER, BBVA, HSBC, BANORTE, BANAMEX

### Files Created
- `tests/e2e/metrics/test_catalog_routing_suite.py` - Comprehensive test suite
- `tests/e2e/metrics/catalog_routing_results.json` - Test results

## Fix: Regional Tools Banco Name Mismatch (2026-02-04)

### Problema
Los tools `get_regional_portfolio` y `get_region_breakdown` retornaban "No hay datos" cuando se pasaba un banco.

```bash
# Antes del fix:
curl ... get_regional_portfolio {"banco":"BBVA"}
# → {"success": false, "error": "No hay datos de cartera por región"}
```

### Root Cause
La MV `bank_mv_cartera_por_estado` usa nombres largos como "BBVA México", pero los usuarios pasan códigos cortos como "BBVA".

| Lo que pasamos | Lo que tiene la MV |
|----------------|-------------------|
| "BBVA" | "BBVA México" |
| "SANTANDER" | "Santander" |
| "HSBC" | "HSBC" (match exacto) |
| "BANORTE" | "Banorte" |

### Solución
Cambié el filtro de banco en `RegionService` de match exacto a JOIN con `bank_dim_institucion`:

```sql
-- Antes:
AND LOWER(banco) = LOWER(:bank)

-- Después:
JOIN bank_dim_institucion di ON mv.clave_cnbv = di.clave_cnbv
...
AND LOWER(di.nombre_corto) = LOWER(:bank)
```

### Métodos Actualizados
- `get_ranking()` - línea 79
- `get_comparison()` - línea 204
- `get_breakdown()` - línea 337
- `get_evolution()` - línea 437

### Validación
```bash
# Después del fix:
✅ BBVA: 4 regiones, $847B
✅ SANTANDER: 5 regiones, $387B
✅ HSBC: 4 regiones, $221B
✅ BANORTE: 4 regiones, $466B
✅ INVEX: 4 regiones, $14B
```

### MCP Tools Test Suite: 28 passed, 1 skipped
```
pytest tests/e2e/metrics/test_mcp_tools_suite.py -v
...
tests/e2e/metrics/test_mcp_tools_suite.py::TestMCPToolsExecution::test_tool_executes_successfully[get_regional_portfolio] PASSED
======================== 28 passed, 1 skipped in 9.25s =========================
```

## Estado

- [x] Identificar gap ✅
- [x] Validar MCP tools funcionan ✅
- [x] Documentar flujo actual ✅
- [x] Implementar routing en backend para catalog queries ✅
- [x] Tests E2E de flujo backend → tool específico ✅ **39/39 (100%)**
- [x] Fix regional tools banco name mismatch ✅ **28/28 passed**
- [ ] Deprecar uso de `query_bank_analytics()` para catalog queries (future)

---

## Research: MCP Tools Best Practices Analysis (2026-02-04)

### Objetivo
Evaluar la arquitectura actual de MCP tools contra mejores prácticas de la industria para identificar oportunidades de mejora en calidad de código, debugging y extensibilidad.

### Fuentes Consultadas
- [MCP Official Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Best Practices Guide](https://modelcontextprotocol.info/docs/best-practices/)
- [MCP Best Practice Community](https://mcp-best-practice.github.io/mcp-best-practice/best-practice/)
- [MCP Inspector Tool](https://modelcontextprotocol.io/docs/tools/inspector)

---

## Estado Actual del Código

### Métricas
- **10 archivos** en `bankadvisor/tools/`
- **~3,500 líneas** de código
- **22 MCP tools** registrados (21 activos, 1 deprecated)

### Estructura Actual
```
bankadvisor/tools/
├── __init__.py          # Registry + register_tool decorator
├── catalog_tools.py     # list_institutions, lookup_bank_code
├── meta_tools.py        # get_available_metrics, get_data_freshness
├── regional_tools.py    # get_regional_portfolio, get_region_breakdown
├── ranking_tools.py     # get_metric_ranking, get_segment_ranking
├── comparison_tools.py  # compare_banks, compare_bank_evolution
├── portfolio_tools.py   # 6 tools for portfolio analysis
├── dimension_tools.py   # 5 tools for dimensional breakdowns
├── data_tools.py        # Class-based tools (legacy)
└── ontology_tools.py    # BM dictionary tools (stubs)
```

---

## Violaciones DRY Identificadas

### 1. Boilerplate Repetido en Cada Tool (CRÍTICO)

**Patrón repetido ~22 veces:**
```python
async def some_tool(...) -> Dict[str, Any]:
    logger.info("tool_name.start", param1=..., param2=...)

    try:
        async with get_async_session() as session:
            # ... lógica específica ...

            logger.info("tool_name.success", ...)
            return {"success": True, "data": ...}

    except Exception as e:
        logger.error("tool_name.error", error=str(e))
        return {"success": False, "error": f"Error: {str(e)}", ...}
```

**Impacto:**
- ~100 líneas duplicadas solo en manejo de sesión y errores
- Inconsistencia en manejo de errores entre tools
- Dificultad para agregar features globales (ej: métricas, tracing)

### 2. Lógica de Conversión de Ratios Duplicada

**Repetido en 4+ archivos:**
```python
is_ratio = metric_lower in ["imor", "icor", "roe_12m", "roa_12m"]
skip_multiply = metric_lower in ["icor", "roe_12m", "roa_12m", "icap_total"]
if is_ratio and not skip_multiply:
    value = value * 100
```

### 3. Queries de Fecha Máxima Duplicadas

**Repetido en múltiples tools:**
```python
latest_date_q = select(func.max(MonthlyKPI.fecha))
date_result = await session.execute(latest_date_q)
latest_date = date_result.scalar()
```

### 4. Normalización de Nombres de Banco Duplicada

**Repetido sin abstracción:**
```python
func.upper(MonthlyKPI.banco_norm) == bank.upper()
```

---

## Violaciones SOLID Identificadas

### S - Single Responsibility (VIOLADO)
Cada tool hace demasiado:
1. Validación de input
2. Gestión de sesión de BD
3. Query SQL
4. Transformación de datos
5. Construcción de plotly config
6. Logging
7. Manejo de errores

**Recomendación:** Separar en capas (validation → query → transform → format)

### O - Open/Closed (VIOLADO)
Agregar un nuevo tool requiere:
- Copiar/pegar ~50 líneas de boilerplate
- Replicar patrones de error handling
- No hay forma de extender sin modificar

**Recomendación:** Base class o decorador que maneje boilerplate

### L - Liskov Substitution (OK)
No aplica directamente - no hay jerarquía de herencia

### I - Interface Segregation (VIOLADO)
Todos los tools retornan `Dict[str, Any]` sin contrato claro:
- Algunos retornan `{"success": bool, "data": ...}`
- Otros retornan `{"success": bool, "plotly_config": ...}`
- No hay validación de respuesta

**Recomendación:** Pydantic models para requests y responses

### D - Dependency Inversion (VIOLADO)
Tools dependen de implementaciones concretas:
- `get_async_session()` hardcodeado
- `MonthlyKPI` model importado directamente
- No inyección de dependencias

**Recomendación:** Dependency injection para testabilidad

---

## Best Practices de MCP (Industria)

### 1. Single Purpose Servers
> "Each MCP server should have one clear, well-defined purpose. Avoid monolithic 'mega-servers'."

**Estado actual:** ✅ Bank-advisor tiene propósito claro (analytics bancarios)

### 2. Tool Granularity
> "Define a clear toolset. Avoid mapping every API endpoint to a new MCP tool. Group related tasks and design higher-level functions."

**Estado actual:** ⚠️ Parcial - 22 tools es manejable pero algunos podrían agruparse

### 3. Schema Validation
> "Strict schema adherence is critical - proper schema validation prevents subtle bugs."

**Estado actual:** ❌ No hay validación Pydantic de inputs ni outputs

### 4. Structured Error Handling
> "Implement structured error handling with proper classification: ClientError (4xx), ServerError (5xx), ExternalError (502/503)"

**Estado actual:** ❌ Todo es `{"success": False, "error": str}` sin clasificación

### 5. Logging Standards
> "Enable verbose logging during development. Structured logging with context can slash MTTR by 40%."

**Estado actual:** ✅ Usando structlog con contexto

### 6. Health/Readiness Endpoints
> "Implement health/readiness endpoints for orchestration."

**Estado actual:** ❌ No hay `/health` endpoint en bank-advisor

### 7. Testing Layers
> "Multi-layer testing: Unit, Integration, Contract, Load, Chaos"

**Estado actual:** ⚠️ Solo E2E tests, faltan unit tests y contract tests

---

## Herramientas de Debugging Disponibles

### MCP Inspector
Herramienta oficial para testing y debugging de MCP servers.

**Instalación:**
```bash
npx @modelcontextprotocol/inspector
```

**Uso con bank-advisor:**
```bash
# Si el server expone stdio transport
npx @modelcontextprotocol/inspector python -m bankadvisor

# Para HTTP transport (nuestro caso)
# Conectar via UI a http://localhost:8002/rpc
```

**Capacidades:**
- Listar tools disponibles
- Ejecutar tools con inputs arbitrarios
- Ver respuestas raw JSON
- Probar edge cases e inputs inválidos

**Integración recomendada:**
1. Agregar transport stdio para desarrollo local
2. Crear script `npm run inspect` en package.json
3. Documentar flujo de debugging

---

## Plan de Mejora Propuesto

### Fase A: Reducir Duplicación (DRY)

#### A1. Base Tool Class
```python
class BaseMCPTool:
    """Base class for MCP tools with common functionality."""

    async def execute(self, **kwargs) -> ToolResponse:
        """Template method pattern."""
        self._log_start(kwargs)
        try:
            async with self._get_session() as session:
                result = await self._run(session, **kwargs)
                self._log_success(result)
                return ToolResponse(success=True, data=result)
        except ValidationError as e:
            return self._client_error(e)
        except Exception as e:
            self._log_error(e)
            return self._server_error(e)

    @abstractmethod
    async def _run(self, session: AsyncSession, **kwargs) -> Any:
        """Implement tool-specific logic."""
        pass
```

#### A2. Metric Utils Module
```python
# bankadvisor/tools/utils/metrics.py
RATIO_METRICS = {"imor", "icor", "roe_12m", "roa_12m"}
SKIP_MULTIPLY = {"icor", "roe_12m", "roa_12m", "icap_total"}

def normalize_metric_value(metric: str, value: float) -> float:
    """Apply ratio conversion if needed."""
    if metric.lower() in RATIO_METRICS and metric.lower() not in SKIP_MULTIPLY:
        return value * 100
    return value
```

#### A3. Query Helpers Module
```python
# bankadvisor/tools/utils/queries.py
async def get_latest_date(session: AsyncSession) -> date:
    """Get most recent data date."""
    result = await session.execute(
        select(func.max(MonthlyKPI.fecha))
    )
    return result.scalar()

async def find_bank_id(session: AsyncSession, bank_name: str) -> Optional[str]:
    """Normalize and find bank identifier."""
    # Centralized bank name resolution
    pass
```

### Fase B: Response Schemas (SOLID - Interface Segregation)

```python
# bankadvisor/tools/schemas.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class ToolResponse(BaseModel, Generic[T]):
    """Standard tool response format."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # CLIENT_ERROR, SERVER_ERROR, etc.
    metadata: dict = {}

class RankingData(BaseModel):
    ranking: list[RankingItem]
    metric: str
    as_of_date: str

class InstitutionList(BaseModel):
    institutions: list[Institution]
    total: int
```

### Fase C: Testing Infrastructure

#### C1. Unit Tests para Tools
```python
# tests/unit/tools/test_catalog_tools.py
@pytest.mark.asyncio
async def test_list_institutions_returns_expected_schema():
    """Test response matches expected Pydantic model."""
    result = await list_institutions(active_only=True, limit=10)
    response = InstitutionList.model_validate(result)
    assert response.total <= 10

@pytest.mark.asyncio
async def test_lookup_bank_code_invalid_input():
    """Test client error for invalid input."""
    result = await lookup_bank_code("abc")
    assert result["success"] is False
    assert "inválido" in result["error"]
```

#### C2. Contract Tests
```python
# tests/contract/test_mcp_protocol.py
def test_tools_list_returns_valid_mcp_schema():
    """Verify tools/list response matches MCP spec."""
    response = call_rpc("tools/list", {})
    for tool in response["result"]["tools"]:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
```

### Fase D: Debugging & Observability

#### D1. Health Endpoint
```python
# main.py
@app.get("/health")
async def health():
    """Health check for orchestration."""
    return {
        "status": "healthy",
        "version": __version__,
        "tools_count": len(REGISTERED_TOOLS),
    }

@app.get("/ready")
async def ready():
    """Readiness check - verify DB connection."""
    async with get_async_session() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}
```

#### D2. Request Tracing
```python
# Agregar correlation ID a cada request
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

---

## Priorización de Mejoras

| Mejora | Impacto | Esfuerzo | Prioridad |
|--------|---------|----------|-----------|
| A2. Metric Utils | Alto | Bajo | 🔴 P1 |
| A3. Query Helpers | Alto | Bajo | 🔴 P1 |
| D1. Health Endpoint | Medio | Bajo | 🟡 P2 |
| C1. Unit Tests | Alto | Medio | 🟡 P2 |
| B. Response Schemas | Alto | Medio | 🟡 P2 |
| A1. Base Tool Class | Alto | Alto | 🟢 P3 |
| C2. Contract Tests | Medio | Medio | 🟢 P3 |
| D2. Request Tracing | Medio | Bajo | 🟢 P3 |

---

## Resumen Ejecutivo

### Lo que está bien
- ✅ Tools granulares y bien nombrados
- ✅ Logging estructurado con structlog
- ✅ Registry pattern para descubrimiento
- ✅ Tests E2E funcionando

### Lo que necesita mejora
- ❌ ~100 líneas de boilerplate duplicado
- ❌ No hay validación de schemas
- ❌ Manejo de errores inconsistente
- ❌ Faltan unit tests y contract tests
- ❌ No hay health endpoint
- ❌ No hay integración con MCP Inspector

### Recomendación
Crear un **nuevo card en BACKLOG** para "REFACTOR: MCP Tools Code Quality" con las fases A, B, C, D como sub-tareas antes de agregar más tools.

---

## Referencias

- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Inspector GitHub](https://github.com/modelcontextprotocol/inspector)
- [MCP Best Practices Guide](https://modelcontextprotocol.info/docs/best-practices/)
- [MCP Security Updates June 2025](https://auth0.com/blog/mcp-specs-update-all-about-auth/)
