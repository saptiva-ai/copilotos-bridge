# Plan: REFACTOR-002 - SOLID Refactoring

## Enfoque

Re-estructurar `main.py` y `analytics_service.py` aplicando:
- **SOLID Principles**
- **Design Patterns** apropiados
- **Zen of Python**

---

## Análisis de Violaciones Actuales

### `AnalyticsService` (2,525 líneas) - God Class

**Violaciones SOLID:**

| Principio | Violación | Evidencia |
|-----------|-----------|-----------|
| **S**RP | God Class con 30+ métodos | Una clase maneja: dashboard, ranking, segmentos, regiones, vivienda, etc. |
| **O**CP | No extensible | Agregar nueva métrica requiere modificar la clase |
| **L**SP | N/A (no hay herencia) | - |
| **I**SP | Interface monolítica | Todos los métodos en una sola clase |
| **D**IP | Dependencia directa en models | `MonthlyKPI`, `HipCarteraViviendaMensual` hardcoded |

**Anti-patterns:**
- **God Class**: Una clase hace todo
- **Primitive Obsession**: Diccionarios en lugar de objetos tipados
- **Long Method**: Métodos de 100+ líneas
- **Todos @staticmethod**: La clase es un namespace, no un objeto

### `main.py` (1,836 líneas) - Mixed Responsibilities

**Violaciones SOLID:**

| Principio | Violación | Evidencia |
|-----------|-----------|-----------|
| **S**RP | Mezcla de concerns | App bootstrap + validation + orchestration + endpoints |
| **D**IP | Globals mutables | `_query_parser`, `_context_service` como variables globales |

**Anti-patterns:**
- **Long Module**: Demasiadas responsabilidades
- **Global State**: Singletons como variables globales
- **Inline Functions**: Utilidades mezcladas con lógica de negocio

---

## Zen of Python Aplicable

```python
# "Simple is better than complex"
# → Clases pequeñas con una sola responsabilidad

# "Flat is better than nested"
# → Eliminar if/else anidados profundos

# "There should be one obvious way to do it"
# → Patterns consistentes en toda la codebase

# "Namespaces are one honking great idea"
# → Módulos separados en lugar de God Classes

# "Explicit is better than implicit"
# → Inyección de dependencias explícita
```

---

## Phase 1: Descomponer AnalyticsService (God Class → Strategy)

### Objetivo
Dividir `AnalyticsService` en servicios especializados por dominio.

### Antes
```
analytics_service.py (2,525 líneas)
└── class AnalyticsService
    ├── get_dashboard_data()
    ├── get_comparative_ratio_data()
    ├── get_market_share_data()
    ├── get_segment_evolution()
    ├── get_institution_ranking()
    ├── get_cartera_por_actividad_ranking()
    ├── get_cartera_por_tamano_breakdown()
    ├── get_cartera_por_destino_ranking()
    ├── get_vivienda_por_perfil()
    ├── get_cartera_por_region_ranking()
    └── ... (20+ métodos más)
```

### Después
```
services/
├── analytics/
│   ├── __init__.py              # Facade pattern
│   ├── base.py                  # Abstract base, contracts
│   ├── dashboard_service.py     # get_dashboard_data, get_filtered_data
│   ├── comparison_service.py    # get_comparative_ratio_data, get_market_share
│   ├── ranking_service.py       # get_institution_ranking, get_segment_ranking
│   ├── cartera_service.py       # actividad, tamaño, destino
│   ├── vivienda_service.py      # perfil, producto
│   └── region_service.py        # region ranking, comparison, breakdown
```

### Patrones a Aplicar

1. **Strategy Pattern**: Cada servicio implementa una interfaz común
2. **Facade Pattern**: `AnalyticsService` como fachada que delega
3. **Dependency Injection**: Servicios reciben repositorios por constructor

### Ejemplo de Transformación

```python
# ANTES: God Class con @staticmethod
class AnalyticsService:
    @staticmethod
    async def get_cartera_por_region_ranking(session, ...):
        # 100+ líneas de lógica mezclada
        pass

# DESPUÉS: Servicio especializado con DI
class RegionService(BaseAnalyticsService):
    def __init__(self, repository: RegionRepository):
        self._repo = repository

    async def get_ranking(self, session, filters: RegionFilters) -> RegionRankingResult:
        data = await self._repo.get_by_region(session, filters)
        return self._format_ranking(data)
```

---

## Phase 2: Extraer Orquestación de main.py

### Objetivo
Separar bootstrap (FastAPI/MCP setup) de lógica de negocio.

### Antes
```
main.py (1,836 líneas)
├── Imports (80 líneas)
├── Global state (_query_parser, etc.)
├── Startup logic (ensure_data_populated)
├── Lifespan
├── Validation utilities (_detect_injection, etc.)
├── Bank matching (_find_bank_candidates)
├── process_analytics_query() - 380 líneas
├── execute_bank_analytics() - 230 líneas
├── execute_sql_pipeline() - 300 líneas
├── MCP tool registrations
└── API endpoints
```

### Después
```
main.py (~200 líneas)
├── Imports
├── Lifespan (delega a startup_service)
├── FastAPI app creation
├── MCP registration (delega a mcp/tools.py)
└── API endpoints (delega a routers/)

services/
├── startup_service.py           # ensure_data_populated, init logic
├── orchestrator.py              # execute_bank_analytics orchestration
└── nl2sql/
    ├── __init__.py
    ├── pipeline.py              # execute_sql_pipeline
    └── query_builder.py

utils/
├── validation.py                # _detect_injection, _detect_date_issues
└── bank_matcher.py              # _find_bank_candidates, _suggest_bank

mcp/
└── tools.py                     # FastMCP tool registrations
```

### Patrón: Dependency Injection Container

```python
# ANTES: Globals mutables
_query_parser: Optional["QuerySpecParser"] = None

# DESPUÉS: Container con lifecycle management
@dataclass
class ServiceContainer:
    query_parser: QuerySpecParser
    context_service: Nl2SqlContextService
    sql_generator: SqlGenerationService

    @classmethod
    async def create(cls) -> "ServiceContainer":
        # Initialize all services
        return cls(...)

# En lifespan
async def lifespan(app: FastAPI):
    app.state.services = await ServiceContainer.create()
    yield
    await app.state.services.cleanup()
```

---

## Phase 3: Aplicar Interface Segregation

### Objetivo
Definir interfaces pequeñas y específicas.

### Interfaces Propuestas

```python
# base.py
from abc import ABC, abstractmethod
from typing import Protocol

class AnalyticsQuery(Protocol):
    """Interface for analytics query services."""
    async def execute(self, session: AsyncSession, filters: QueryFilters) -> QueryResult:
        ...

class RankingProvider(Protocol):
    """Interface for ranking operations."""
    async def get_ranking(self, session: AsyncSession, limit: int) -> List[RankingItem]:
        ...

class EvolutionProvider(Protocol):
    """Interface for time-series evolution."""
    async def get_evolution(self, session: AsyncSession, time_range: TimeRange) -> EvolutionData:
        ...
```

---

## Acceptance Criteria (Revisado)

| # | Criterio | Métrica |
|---|----------|---------|
| 1 | AnalyticsService descompuesto | God Class → 6 servicios especializados |
| 2 | main.py responsabilidades separadas | Bootstrap only, delegates to services |
| 3 | Dependency Injection | No globals mutables, services via container |
| 4 | Interfaces definidas | Protocols/ABCs para cada tipo de operación |
| 5 | Tests existentes pasan | 0 regresiones |
| 6 | Nuevos tests para servicios | +20 unit tests mínimo |

---

## Implementation Order

1. **Phase 1.1**: Crear `services/analytics/base.py` con interfaces
2. **Phase 1.2**: Extraer `RegionService` (más autocontenido)
3. **Phase 1.3**: Extraer `ViviendaService`
4. **Phase 1.4**: Extraer `CarteraService`
5. **Phase 1.5**: Extraer `RankingService` y `ComparisonService`
6. **Phase 1.6**: Reducir `AnalyticsService` a Facade
7. **Phase 2.1**: Crear `ServiceContainer`
8. **Phase 2.2**: Mover orchestration a `services/orchestrator.py`
9. **Phase 2.3**: Mover utils a `utils/`
10. **Phase 2.4**: Limpiar main.py

---

## Rollback Strategy

1. **Feature flag**: `USE_NEW_ANALYTICS_SERVICES=false` por defecto
2. **Facade mantiene API**: `AnalyticsService` sigue siendo el entry point
3. **Tests E2E**: Ejecutar antes y después de cada fase
4. **Git tags**: `pre-refactor-002-phase-N` antes de cada fase

---

## Estimación

| Phase | Esfuerzo | Riesgo |
|-------|----------|--------|
| 1.1-1.2 | Bajo | Bajo |
| 1.3-1.5 | Medio | Bajo |
| 1.6 | Medio | Medio |
| 2.1-2.4 | Medio | Bajo |

**Total**: 4-6 sesiones de trabajo
