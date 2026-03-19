# REFACTOR: MCP Tools Code Quality & Best Practices

## Tipo: Refactor - Technical Debt

## Prioridad: 🟡 Medium

## Contexto

Durante el refactor `2026-02-03__REFACTOR__handlers-to-mcp-tools` se identificaron violaciones de DRY y SOLID en los 22 MCP tools implementados (~3,500 líneas en 10 archivos).

**Research completo:** `docs/kanban/DOING/2026-02-03__REFACTOR__handlers-to-mcp-tools/research.md`

## Problema

### Violaciones DRY
- ~100 líneas de boilerplate duplicado (session + error handling)
- Lógica de conversión de ratios repetida en 4+ archivos
- Queries de fecha máxima duplicadas en 6+ tools
- Normalización de banco sin centralizar

### Violaciones SOLID
- **S**: Cada tool hace 7 cosas (validation, session, query, transform, format, log, error)
- **O**: Nuevo tool = copy/paste 50 líneas de boilerplate
- **I**: `Dict[str, Any]` sin contrato de respuesta
- **D**: Dependencias hardcodeadas (`get_async_session`, `MonthlyKPI`)

### Gaps vs Best Practices MCP
- No hay validación de schemas (Pydantic)
- No hay health endpoint `/health`, `/ready`
- No hay unit tests ni contract tests
- No hay integración con MCP Inspector

## Solución Propuesta

### Fase A: Reducir Duplicación (DRY)

**A1. Metric Utils Module** (P1)
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

**A2. Query Helpers Module** (P1)
```python
# bankadvisor/tools/utils/queries.py
async def get_latest_date(session: AsyncSession) -> date:
    """Get most recent data date."""

async def find_bank_by_name(session: AsyncSession, name: str) -> Optional[dict]:
    """Normalize and find bank with fuzzy matching."""
```

**A3. Base Tool Class** (P3)
```python
class BaseMCPTool:
    async def execute(self, **kwargs) -> ToolResponse:
        self._log_start(kwargs)
        try:
            async with self._get_session() as session:
                result = await self._run(session, **kwargs)
                return ToolResponse(success=True, data=result)
        except Exception as e:
            return self._handle_error(e)
```

### Fase B: Response Schemas (SOLID)

```python
# bankadvisor/tools/schemas.py
from pydantic import BaseModel

class ToolResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # CLIENT_ERROR, SERVER_ERROR

class RankingResponse(ToolResponse):
    data: Optional[RankingData] = None

class InstitutionListResponse(ToolResponse):
    data: Optional[InstitutionList] = None
```

### Fase C: Testing Infrastructure

**C1. Unit Tests** (P2)
```
tests/unit/tools/
├── test_catalog_tools.py
├── test_ranking_tools.py
├── test_regional_tools.py
└── conftest.py  # fixtures, mocks
```

**C2. Contract Tests** (P3)
```python
def test_tools_list_returns_valid_mcp_schema():
    """Verify tools/list matches MCP spec."""

def test_tool_response_matches_declared_schema():
    """Verify tool output matches its inputSchema."""
```

### Fase D: Debugging & Observability

**D1. Health Endpoint** (P2)
```python
@app.get("/health")
async def health():
    return {"status": "healthy", "version": __version__}

@app.get("/ready")
async def ready():
    # Verify DB connection
    return {"status": "ready"}
```

**D2. MCP Inspector Integration** (P3)
- Agregar script `npm run inspect`
- Documentar flujo de debugging

## Archivos a Crear

```
plugins/bank-advisor-private/src/bankadvisor/tools/
├── utils/
│   ├── __init__.py
│   ├── metrics.py      # normalize_metric_value
│   ├── queries.py      # get_latest_date, find_bank
│   └── responses.py    # error handling helpers
├── schemas/
│   ├── __init__.py
│   ├── base.py         # ToolResponse
│   ├── catalog.py      # InstitutionList
│   ├── ranking.py      # RankingData
│   └── regional.py     # RegionalData
└── base.py             # BaseMCPTool (optional)
```

## Archivos a Modificar

- `catalog_tools.py` - usar utils y schemas
- `ranking_tools.py` - usar utils y schemas
- `regional_tools.py` - usar utils y schemas
- `comparison_tools.py` - usar utils y schemas
- `portfolio_tools.py` - usar utils y schemas
- `dimension_tools.py` - usar utils y schemas
- `main.py` - agregar health endpoints

## Criterios de Aceptación

### Fase A (DRY) ✅ COMPLETADA 2026-02-04
- [x] `utils/metrics.py` creado con `normalize_metric_value()`, `is_ratio_metric()`, `needs_multiplication()`
- [x] `utils/queries.py` creado con `normalize_bank_name()`, `build_bank_filter()`, `build_date_filter()`, `format_metric_value()`, `get_latest_date()`, `find_bank_by_name()`
- [x] Duplicación de ratio logic eliminada (5 occurrences → 1 centralized utility)
  - dimension_tools.py: Refactored + BUG FIXED (icap_total was incorrectly multiplied by 100)
  - ranking_tools.py: Refactored
  - comparison_tools.py: Refactored (2 occurrences)
  - portfolio_tools.py: Refactored
- [x] Unit tests: 44 tests passing (test_metrics_utils.py + test_query_utils.py)
- [ ] Duplicación de latest_date query reducida (pending tool-by-tool integration)

### Fase B (Schemas) ✅ COMPLETADA 2026-02-04
- [x] `schemas/base.py` con `ToolResponse` Pydantic model
- [x] `schemas/ranking.py` con `RankingResponse`, `RankingItem`
- [x] `schemas/catalog.py` con `Institution`, `InstitutionListResponse`, `BankLookupResponse`
- [x] `schemas/comparison.py` con `BankMetrics`, `ComparisonResponse`, `EvolutionResponse`
- [x] `schemas/timeseries.py` con `TimeSeriesPoint`, `TimeSeriesResponse`
- [x] `schemas/portfolio.py` con SectorData, CompanySizeData, DemographicData, BankDetailData, SystemSummaryData
- [x] `schemas/dimension.py` con ActivityData, TrendData, AlertData, AlertThresholds, TrendSummary
- [x] `schemas/regional.py` con RegionalPortfolioResponse, RegionBreakdownResponse
- [x] `schemas/meta.py` con MetricDefinition, MetricsResponse, DataFreshnessResponse
- [x] Helper functions: `success_response()`, `error_response()`, `ErrorCode`
- [x] 17 unit tests for schemas (test_schemas.py)
- [x] **21 MCP tools fully migrated to Pydantic schemas** (catalog, ranking, comparison, portfolio, dimension, regional, meta)

### Fase C (Testing) ✅ COMPLETADA 2026-02-04
- [x] Unit tests para `utils/metrics.py` (20 tests)
- [x] Unit tests para `utils/queries.py` (24 tests)
- [x] MCP contract tests (14 tests) - validates MCP protocol compliance
- [x] `list_tools()` updated to return MCP-compliant `inputSchema` format
- [x] **Total: 75 tests passing**

### Fase D (Observability) ✅ COMPLETADA 2026-02-04
- [x] `/health` endpoint funciona (ya existía, verificado)
- [x] `/ready` endpoint agregado - verifica DB + tools_loaded
- [x] `schemas/health.py` con HealthResponse, ReadyResponse, ReadyChecks
- [x] 10 unit tests for health endpoints (test_health_endpoints.py)
- [ ] Documentación de MCP Inspector (opcional, P3)

## Estimación por Fase

| Fase | Scope | Prioridad |
|------|-------|-----------|
| A1-A2 | Utils modules | 🔴 P1 |
| D1 | Health endpoints | 🟡 P2 |
| B | Response schemas | 🟡 P2 |
| C1 | Unit tests | 🟡 P2 |
| A3 | Base tool class | 🟢 P3 |
| C2 | Contract tests | 🟢 P3 |
| D2 | Inspector docs | 🟢 P3 |

## Dependencias

- **Bloquea:** Ninguno (mejora interna)
- **Habilitado por:** `2026-02-03__REFACTOR__handlers-to-mcp-tools` (completado)

## Referencias

- [MCP Best Practices](https://modelcontextprotocol.info/docs/best-practices/)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- Research: `docs/kanban/DOING/2026-02-03__REFACTOR__handlers-to-mcp-tools/research.md`
