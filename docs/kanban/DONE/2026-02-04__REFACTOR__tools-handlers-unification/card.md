# REFACTOR: Tools & Handlers Unification

## Tipo: Refactor - Architecture Cleanup

## Prioridad: 🟡 Medium

## Contexto

Análisis arquitectónico identificó 3 patrones coexistentes para consultas bancarias:
1. `SaptivaTool` (legacy) - 3 clases muertas + 1 en uso
2. `BaseHandler` (FSM) - 13 handlers activos
3. `@register_tool` (MCP) - 21 tools activos

**Documento de diseño:** `plugins/bank-advisor-private/docs/architecture/2026-02-04_tools_handlers_unification.md`

## Problema

### Código Muerto
- `BankDataQueryTool` (~120 líneas) - nunca usado
- `FinancialMetricsTool` (~120 líneas) - nunca usado
- `SegmentedDataTool` (~125 líneas) - nunca usado

### Code Smells
- Shotgun Surgery: cambiar ranking = 3+ archivos
- Primitive Obsession: `entities: Any`, `Dict[str, Any]`
- Inappropriate Intimacy: SQL hardcodeado en handlers

### Duplicación Funcional
- `ranking_handler.py` ↔ `ranking_tools.py` (~60% similar)
- `comparative_handler.py` ↔ `comparison_tools.py` (~50% similar)

## Solución: Opción C (Unificación Mínima)

### Fase 1: Eliminar Código Muerto ✅ COMPLETADA 2026-02-04
- [x] Eliminar `BankDataQueryTool` de `data_tools.py`
- [x] Eliminar `FinancialMetricsTool` de `data_tools.py`
- [x] Eliminar `SegmentedDataTool` de `data_tools.py`
- [x] Limpiar exports de `tools/__init__.py`
- [x] Verificar que `SchemaDiscoveryTool` sigue funcionando
- [x] **~365 líneas de código muerto eliminadas**

### Fase 2: Crear Domain Services ✅ COMPLETADA 2026-02-04
- [x] Crear `domain/services/metric_normalizer.py` con `MetricNormalizer` class
- [x] Crear `domain/services/bank_resolver.py` con `BankResolver` class
- [x] Crear `domain/entities/__init__.py` con value objects (`Metric`, `Bank`, `DateRange`)
- [x] `utils/metrics.py` re-exporta desde domain (backward compatible)
- [x] **85 tests siguen pasando**

### Fase 3: Crear Application Layer ✅ COMPLETADA 2026-02-04
- [x] Crear `application/use_cases/ranking.py` con `RankingUseCase`
- [x] DTOs tipados: `RankingRequest`, `RankingResult`, `RankedBank`
- [x] Lógica extraída de `ranking_tools.py` (implementación más completa)
- [x] **309 tests siguen pasando**

### Fase 4: Refactorizar Handlers para usar Use Cases ✅ COMPLETADA 2026-02-04
- [x] `ranking_handler.py` → delega a `RankingUseCase`
- [x] `ranking_tools.py` → delega a `RankingUseCase`
- [x] **309 tests siguen pasando (20 failures pre-existentes)**
- [x] Líneas eliminadas: ~140 de lógica duplicada

### Fase 5: Unificar Comparison Use Cases ✅ COMPLETADA 2026-02-04
- [x] Crear `application/use_cases/compare.py` con `CompareUseCase`
- [x] Crear `application/use_cases/evolution.py` con `EvolutionUseCase`
- [x] `comparison_tools.py` → delega a use cases (368→167 líneas, -55%)
- [x] **309 tests siguen pasando**

### Fase 6: Unificar Portfolio Use Cases ✅ COMPLETADA 2026-02-04
- [x] Crear `application/use_cases/timeseries.py` con `TimeSeriesUseCase`
- [x] Crear `application/use_cases/bank_detail.py` con `BankDetailUseCase`
- [x] `portfolio_tools.py` → get_time_series y get_bank_detail delegados
- [x] **309 tests siguen pasando**

### Fase 7: Corregir 20 Test Failures en ClarificationService ✅ COMPLETADA 2026-02-04
- [x] **Bug 1**: `determine_strategy()` nunca retornaba `SMART_DEFAULT`
  - Añadido return path para evolution/comparison intents sin banco
- [x] **Bug 2**: `get_soft_ask_suggestions()` requería `session` pero tests no lo pasaban
  - Tests actualizados para usar mocking apropiado de `ContextualSuggestionService`
- [x] **Bug 3**: `spec.inferred_from_context` no existía en QuerySpec (Pydantic)
  - Eliminado, se loguea en el logger en su lugar
- [x] **Design Fix**: `SISTEMA_DEFAULT_INTENTS` ahora incluye `comparison`
- [x] **Design Fix**: `NO_BANK_REQUIRED_INTENTS` ahora incluye `comparison`
- [x] **62 tests de clarification pasando**
- [x] **286 tests unitarios pasando**

### Fase 8a: GrowthEvolutionUseCase ✅ COMPLETADA 2026-02-04
- [x] Crear `application/use_cases/growth_evolution.py` con `GrowthEvolutionUseCase`
- [x] DTOs tipados: `GrowthEvolutionRequest`, `GrowthRankingRequest`, `GrowthPeriod`
- [x] Resultados tipados: `GrowthEvolutionResult`, `GrowthRankingResult`, `GrowthDataPoint`
- [x] `evolucion_banco_handler.py` → delega a `GrowthEvolutionUseCase`
- [x] Handler reducido de **366→158 líneas** (-57%, ~208 líneas SQL eliminadas)

### Fase 8b: PortfolioDimensionUseCase ✅ COMPLETADA 2026-02-04
- [x] Crear `application/use_cases/portfolio_dimension.py` con `PortfolioDimensionUseCase`
- [x] DTOs tipados: `ActivityBreakdownRequest`, `CompanySizeBreakdownRequest`, `DestinationBreakdownRequest`
- [x] Resultados tipados con `to_response_dict()` para compatibilidad MCP
- [x] `dimension_tools.py` → 3 tools delegan a `PortfolioDimensionUseCase`
- [x] Tools reducidos de **714→451 líneas** (-37%, ~263 líneas SQL eliminadas)

### Fase 8c: FinancialMetricsUseCase ✅ COMPLETADA 2026-02-04
- [x] Crear `application/use_cases/financial_metrics.py` con `FinancialMetricsUseCase`
- [x] DTOs tipados: `FinancialRankingRequest`, `BankFinancialsRequest`, `FinancialMetric` enum
- [x] Resultados tipados: `FinancialRankingResult`, `BankFinancialsResult`
- [x] `metricas_financieras_handler.py` → delega a `FinancialMetricsUseCase`
- [x] Handler reducido de **342→154 líneas** (-55%, ~188 líneas SQL eliminadas)

### Resumen de Cambios
- **Fase 1**: ~365 líneas de código muerto eliminadas
- **Fase 2**: Domain layer creado (MetricNormalizer, BankResolver)
- **Fase 3**: Application layer creado (RankingUseCase)
- **Fase 4**: Handler y tool unificados bajo RankingUseCase
- **Fase 5**: CompareUseCase + EvolutionUseCase (~201 líneas de SQL eliminadas)
- **Fase 6**: TimeSeriesUseCase + BankDetailUseCase (~150 líneas de SQL eliminadas)
- **Fase 8a**: GrowthEvolutionUseCase (~208 líneas SQL eliminadas)
- **Fase 8b**: PortfolioDimensionUseCase (~263 líneas SQL eliminadas)
- **Fase 8c**: FinancialMetricsUseCase (~188 líneas SQL eliminadas)
- **Fase 8d**: SystemSummaryUseCase (~210 líneas SQL eliminadas)

## Archivos Modificados/Creados

### Fase 1 - Código Muerto
- `tools/data_tools.py` - Eliminadas 3 clases muertas
- `tools/__init__.py` - Limpiados exports

### Fase 2 - Domain Layer
- `domain/__init__.py` (nuevo)
- `domain/entities/__init__.py` (nuevo) - Metric, Bank, DateRange
- `domain/services/__init__.py` (nuevo)
- `domain/services/metric_normalizer.py` (nuevo) - MetricNormalizer
- `domain/services/bank_resolver.py` (nuevo) - BankResolver
- `tools/utils/metrics.py` - Re-exporta desde domain

### Fase 3-4 - Application Layer (Ranking)
- `application/__init__.py` (nuevo)
- `application/use_cases/__init__.py` (nuevo)
- `application/use_cases/ranking.py` (nuevo) - RankingUseCase
- `handlers/ranking_handler.py` - Delega a RankingUseCase
- `tools/ranking_tools.py` - Delega a RankingUseCase

### Fase 5 - Application Layer (Comparison)
- `application/use_cases/compare.py` (nuevo) - CompareUseCase
- `application/use_cases/evolution.py` (nuevo) - EvolutionUseCase
- `tools/comparison_tools.py` - Delega a use cases (368→167 líneas)

### Fase 6 - Application Layer (Portfolio)
- `application/use_cases/timeseries.py` (nuevo) - TimeSeriesUseCase
- `application/use_cases/bank_detail.py` (nuevo) - BankDetailUseCase
- `tools/portfolio_tools.py` - get_time_series y get_bank_detail delegados

### Fase 7 - Clarification Service Fixes
- `services/clarification_service.py` - Fixes de lógica de estrategia y API
- `tests/unit/test_clarification_service.py` - Tests actualizados con mocking
- `tests/unit/test_contextual_clarification.py` - Expectativas corregidas

### Fase 8a - Application Layer (GrowthEvolution)
- `application/use_cases/growth_evolution.py` (nuevo) - GrowthEvolutionUseCase
- `application/use_cases/__init__.py` - Exports actualizados
- `handlers/evolucion_banco_handler.py` - Delega a GrowthEvolutionUseCase (366→158 líneas)

### Fase 8b - Application Layer (PortfolioDimension)
- `application/use_cases/portfolio_dimension.py` (nuevo) - PortfolioDimensionUseCase
- `application/use_cases/__init__.py` - Exports actualizados
- `tools/dimension_tools.py` - 3 tools delegan a PortfolioDimensionUseCase (714→451 líneas)

### Fase 8c - Application Layer (FinancialMetrics)
- `application/use_cases/financial_metrics.py` (nuevo) - FinancialMetricsUseCase
- `application/use_cases/__init__.py` - Exports actualizados
- `handlers/metricas_financieras_handler.py` - Delega a FinancialMetricsUseCase (342→154 líneas)

### Fase 8d - Application Layer (SystemSummary)
- `application/use_cases/system_summary.py` (nuevo) - SystemSummaryUseCase
- `application/use_cases/__init__.py` - Exports actualizados
- `handlers/resumen_sistema_handler.py` - Delega a SystemSummaryUseCase (340→130 líneas)

## Criterios de Aceptación

### Fase 1 ✅
- [x] ~365 líneas de código muerto eliminadas
- [x] Tests existentes siguen pasando (309 tests)
- [x] `get_data_freshness()` sigue funcionando (usa SchemaDiscoveryTool)

### Fase 2 ✅
- [x] Domain services creados con tipado estricto
- [x] Utils existentes redirigen a domain services
- [x] Backward compatibility mantenida

### Fase 3-4 ✅
- [x] RankingUseCase creado con DTOs tipados
- [x] Handler y tool delegado a use case
- [x] Tests de regresión pasando

## Estado Final del Refactoring

### Handlers ✅ 100% Completo
- **0 handlers con SQL embebido** (todos delegan a Use Cases)
- 4 handlers principales refactorizados:
  - `ranking_handler.py` → RankingUseCase
  - `evolucion_banco_handler.py` → GrowthEvolutionUseCase
  - `metricas_financieras_handler.py` → FinancialMetricsUseCase
  - `resumen_sistema_handler.py` → SystemSummaryUseCase

### Tools - Estado por archivo

| Archivo | SQL Queries | Delegados a Use Case | Justificación |
|---------|-------------|---------------------|---------------|
| `comparison_tools.py` | 0 | ✅ CompareUseCase, EvolutionUseCase | 100% refactorizado |
| `ranking_tools.py` | 0 | ✅ RankingUseCase | 100% refactorizado |
| `dimension_tools.py` | 2 | ✅ PortfolioDimensionUseCase (3 tools) | SQL restante: trends/alerts (concern diferente) |
| `portfolio_tools.py` | 6 | ✅ TimeSeriesUseCase, BankDetailUseCase (2 tools) | SQL restante: commercial/housing breakdowns (fact tables, no MVs) |
| `catalog_tools.py` | 3 | N/A | CRUD simple de catálogos - Use Case sería overkill |

### Métricas Totales
- **~1,585 líneas de SQL/lógica duplicada eliminadas**
- **10 Use Cases creados** en Application Layer
- **DTOs tipados** para todas las operaciones
- **Backward compatibility** mantenida

## Dependencias

- **Habilitado por:** `2026-02-04__REFACTOR__mcp-tools-code-quality` (completado)
- **Bloquea:** Ninguno

## Validación Final ✅ COMPLETADA 2026-02-04

### Test Suites Creados

| Suite | Tests | Estado |
|-------|-------|--------|
| Unit Tests (Use Cases) | 53 | ✅ Pasando |
| Integration Tests (MCP Tools) | 60 | ✅ Pasando |
| **Total Unit Tests** | 382 | ✅ Pasando |

### Cobertura de Integration Tests

- **Catalog**: `list_institutions`, `lookup_bank_code`
- **Ranking**: `get_metric_ranking`, `get_segment_ranking`
- **Comparison**: `compare_banks`, `compare_bank_evolution`
- **Time Series**: `get_time_series` (4 métricas)
- **Bank Detail**: `get_bank_detail` (5 bancos principales)
- **Portfolio Dimension**: 3 tools (activity, company_size, destination)
- **System Summary**: `get_system_summary`
- **Commercial/Housing**: 3 tools
- **Regional**: 2 tools
- **Metrics/Alerts**: 3 tools
- **Bank Analytics**: NL query routing (6 tipos de query)

### Archivos de Tests Creados

- `tests/unit/application/test_use_cases.py` - 53 unit tests para 9 Use Cases
- `tests/integration/test_mcp_tools_comprehensive.py` - 60 integration tests via JSON-RPC

### Bugs Corregidos Durante Validación

1. **BankDetailUseCase SQL**: Columnas `roe_12m` y `roa_12m` no existen en la tabla - eliminadas del query
2. **EvolutionResponse schema**: Tests esperaban `series` pero el schema usa `evolution`
3. **RankingResponse**: Rankings son datos tabulares, `plotly_config` es opcional

## Referencias

- Análisis: `plugins/bank-advisor-private/docs/architecture/2026-02-04_tools_handlers_unification.md`
- MCP Best Practices: https://modelcontextprotocol.info/docs/best-practices/

## Completado

**Fecha**: 2026-02-04
**Estado**: ✅ DONE
