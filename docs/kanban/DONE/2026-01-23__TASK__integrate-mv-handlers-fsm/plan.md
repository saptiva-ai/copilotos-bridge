# Plan de Implementación: Integrar Handlers MV en FSM

## Resumen
Integrar los 5 handlers MV existentes en el flujo del FSM modificando `AnalyticsAgent.execute()`.

---

## Phase 1: Modificar AnalyticsAgent (Core)

### Archivo: `plugins/bank-advisor-private/src/bankadvisor/fsm/agents/__init__.py`

**Líneas afectadas**: 400-480 (clase AnalyticsAgent)

### Cambio 1.1: Importar handlers
```python
# Al inicio del archivo, agregar:
from bankadvisor.handlers import get_specific_handlers
from bankadvisor.pipelines.query_router import QueryRouter
```

### Cambio 1.2: Modificar execute() para invocar handlers primero

**ANTES** (líneas 418-480):
```python
async def execute(self, model: QueryModel) -> QueryModel:
    """Execute analytics query and update model with result."""
    # ... validation ...

    service = AnalyticsService()
    metric_id = model.entities.metric_id if model.entities else None

    if model.intent == "ranking":
        data = await service.get_ranking(...)
    else:
        data = await service.get_filtered_data(...)
```

**DESPUÉS**:
```python
async def execute(self, model: QueryModel) -> QueryModel:
    """Execute analytics query via handlers or fallback to AnalyticsService."""
    self._log_start(model, "analytics_execution")

    try:
        if self._session is None:
            model.execution_result = ExecutionResult(
                success=True,
                data={"type": "placeholder", "message": "No database session"},
                execution_path="analytics",
            )
            return model

        # =====================================================================
        # NUEVO: Intentar handlers MV primero (fast path con visualizaciones)
        # =====================================================================
        handler_result = await self._try_handlers(model)
        if handler_result:
            model.execution_result = ExecutionResult(
                success=True,
                data=handler_result,
                execution_path="handler",
            )
            self._log_complete(model, "analytics_execution", success=True)
            return model

        # =====================================================================
        # FALLBACK: AnalyticsService para queries que no matchean handlers
        # =====================================================================
        from bankadvisor.services.analytics_service import AnalyticsService
        service = AnalyticsService()

        metric_id = model.entities.metric_id if model.entities else None
        banks = list(model.entities.banks) if model.entities else []

        if not metric_id:
            # Sin métrica y sin handler → no podemos procesar
            model.execution_result = ExecutionResult(
                success=False,
                error="No metric specified and no handler matched",
                execution_path="analytics",
            )
            return model

        if model.intent == "ranking":
            data = await service.get_ranking(
                self._session,
                metric=metric_id,
                limit=10,
            )
        else:
            data = await service.get_filtered_data(
                self._session,
                metric=metric_id,
                banks=banks or ["SISTEMA"],
                limit=24,
            )

        model.execution_result = ExecutionResult(
            success=True,
            data=data,
            execution_path="analytics_service",
        )
        self._log_complete(model, "analytics_execution", success=True)

    except Exception as e:
        self._log_error(model, "analytics_execution", str(e))
        model.execution_result = ExecutionResult(
            success=False,
            error=str(e),
            execution_path="analytics",
        )

    return model
```

### Cambio 1.3: Agregar método _try_handlers()

```python
async def _try_handlers(self, model: QueryModel) -> Optional[Dict[str, Any]]:
    """
    Try to match and execute a specialized handler.

    Handlers are checked in priority order:
    1. MultiMetricHandler (stacked charts)
    2. CarteraActividadHandler (economic activity)
    3. CarteraTamanoHandler (company size)
    4. CarteraDestinoHandler (credit destination)
    5. ViviendaPerfilHandler (housing profile)
    6. CarteraRegionHandler (geographic region)
    7. ComparativeRatioHandler, MarketShareHandler, etc.

    Returns:
        Handler result dict with data/visualization, or None if no match
    """
    from bankadvisor.handlers import get_specific_handlers
    from bankadvisor.specs import QuerySpec

    handlers = get_specific_handlers()
    user_query = model.query
    entities = model.entities

    # Build spec from entities if available
    spec = None
    if entities:
        try:
            # Extract bank from entities for spec
            bank = entities.banks[0] if entities.banks else None
            spec = QuerySpec(
                bank=bank,
                metric=entities.metric_id,
                time_range="latest",
            )
        except Exception:
            spec = None

    # Try each handler in priority order
    for handler in handlers:
        try:
            # Check if handler matches this query
            matched = handler.matches(user_query, entities=entities, spec=spec)
        except TypeError:
            # Some handlers have different signatures
            try:
                matched = handler.matches(user_query, entities=entities)
            except TypeError:
                matched = handler.matches(user_query)

        if matched:
            logger.info(
                "analytics_agent.handler_matched",
                handler=handler.name,
                query=user_query[:50],
            )

            # Execute handler
            try:
                result = await handler.handle(
                    self._session,
                    user_query,
                    entities=entities,
                    spec=spec,
                )
                if result and result.get("type") != "error":
                    logger.info(
                        "analytics_agent.handler_success",
                        handler=handler.name,
                        visualization=result.get("visualization"),
                    )
                    return result
            except Exception as e:
                logger.warning(
                    "analytics_agent.handler_error",
                    handler=handler.name,
                    error=str(e),
                )
                # Continue to next handler or fallback
                continue

    # No handler matched
    logger.debug("analytics_agent.no_handler_match", query=user_query[:50])
    return None
```

---

## Phase 2: Extender can_use_fast_path (Opcional)

### Archivo: `plugins/bank-advisor-private/src/bankadvisor/fsm/machine.py`

**Objetivo**: Permitir que queries sin metric_id pero con handler match lleguen al AnalyticsAgent.

### Cambio 2.1: Modificar can_use_fast_path

**ANTES** (líneas 182-196):
```python
@property
def can_use_fast_path(self) -> bool:
    """Check if we can use the deterministic fast path (no LLM needed)."""
    if not self.entities:
        return False
    has_metric = self.entities.metric_id is not None
    has_banks = len(self.entities.banks) > 0
    return has_metric and (has_banks or self.is_ranking_query)
```

**DESPUÉS**:
```python
@property
def can_use_fast_path(self) -> bool:
    """Check if we can use the deterministic fast path (no LLM needed)."""
    # Option 1: Original logic (metric + banks/ranking)
    if self.entities:
        has_metric = self.entities.metric_id is not None
        has_banks = len(self.entities.banks) > 0
        if has_metric and (has_banks or self.is_ranking_query):
            return True

    # Option 2: Handler can match this query (NEW)
    if self._has_matching_handler():
        return True

    return False

def _has_matching_handler(self) -> bool:
    """Check if any specialized handler can process this query."""
    from bankadvisor.handlers import get_specific_handlers

    handlers = get_specific_handlers()
    for handler in handlers:
        try:
            if handler.matches(self.query, entities=self.entities):
                return True
        except TypeError:
            if handler.matches(self.query):
                return True
    return False
```

---

## Phase 3: Nuevos Handlers para MVs Sin Cobertura (Opcional)

### MVs sin handler dedicado:
1. `bank_mv_comparativa_bancos` → ComparativaBancosHandler
2. `bank_mv_evolucion_cartera_banco` → EvolucionBancoHandler
3. `bank_mv_ranking_cartera_mensual` → RankingMensualHandler
4. `bank_mv_resumen_sistema` → ResumenSistemaHandler

### Queries que habilitarían:
```
"market share de INVEX vs BBVA"
"ranking de bancos por cartera total"
"crecimiento YoY de INVEX"
"concentración del sistema bancario"
"resumen del sistema bancario 2025"
"top 10 bancos por market share"
```

**Decisión**: Implementar en task separado si se requieren.

---

## Phase 4: Testing

### Test 1: Handler Invocation via FSM
```python
# test_fsm_handler_integration.py
async def test_regional_query_uses_handler():
    """Regional query should route through CarteraRegionHandler."""
    orchestrator = create_async_orchestrator(session)
    result = await orchestrator.process("comparativo regional 2024 vs 2025")

    assert result.execution_result.success
    assert result.execution_result.execution_path == "handler"
    assert "table_data" in result.execution_result.data
```

### Test 2: Fallback Still Works
```python
async def test_fallback_to_analytics_service():
    """Queries without handler match should use AnalyticsService."""
    orchestrator = create_async_orchestrator(session)
    result = await orchestrator.process("IMOR de BBVA últimos 3 meses")

    assert result.execution_result.success
    assert result.execution_result.execution_path in ["analytics_service", "handler"]
```

### Test 3: All MV Handlers Match Correctly
```python
@pytest.mark.parametrize("query,expected_handler", [
    ("cartera por actividad económica", "cartera_actividad"),
    ("cartera a PyMEs", "cartera_tamano"),
    ("capital de trabajo vs activo fijo", "cartera_destino"),
    ("hipotecas por género", "vivienda_perfil"),
    ("cartera por región", "cartera_region"),
])
async def test_handler_matching(query, expected_handler):
    """Each MV handler should match its target queries."""
    handlers = get_specific_handlers()
    matched = None
    for h in handlers:
        if h.matches(query, entities=None):
            matched = h.name
            break
    assert matched == expected_handler
```

---

## Checklist de Implementación

### Phase 1 (Core) ✅ COMPLETADO
- [x] Agregar imports de handlers en `agents/__init__.py`
- [x] Implementar método `_try_handlers()` en AnalyticsAgent
- [x] Modificar `execute()` para llamar handlers primero
- [x] Agregar logging estructurado

### Pre-requisito Completado ✅
- [x] Migración 049: `bank_mv_metricas_financieras` (ROA/ROE)
- [x] Migración 050: Cleanup `monthly_kpis` → VIEW
- [x] Handler: `MetricasFinancierasHandler`
- [x] Tests unitarios: 24/24 passed

### Phase 2 (Opcional) ✅ COMPLETADO
- [x] Modificar `can_use_fast_path` en machine.py
- [x] Agregar método `_has_matching_handler()`

### Phase 3 (Handlers Adicionales) ✅ COMPLETADO
- [x] Crear EvolucionBancoHandler (crecimiento YoY/MoM, evolución)
- [x] Crear ResumenSistemaHandler (resumen, concentración)
- [ ] ComparativaBancosHandler (no necesario - cubierto por otros handlers)
- [ ] RankingMensualHandler (no necesario - cubierto por handlers existentes)

### Phase 4 (Testing) ✅ COMPLETADO
- [x] Test: handler invocation via FSM (19/19 passed)
- [x] Test: fallback to AnalyticsService
- [x] Test: all 6 MV handlers match correctly (incluye MetricasFinancierasHandler)
- [x] Test: error handling and logging
- [x] Test: handler priority (multi_metric first, metricas_financieras before ranking)

### Phase 5 (Database Cleanup) ✅ COMPLETADO
- [x] Migración 051: Drop empty partition tables (2000-2021)
  - 44 particiones vacías eliminadas (22 r04a + 22 r12a)
  - 8 particiones con datos conservadas (2022-2025)
  - Total liberado: ~1.6 MB schema overhead
- [x] Vistas de compatibilidad mantenidas (backward compat)
  - `monthly_kpis` → VIEW a `bank_fact_kpis_mensual`

### Phase 6 (Code Migration to Normalized Tables) ✅ COMPLETADO
- [x] `sql_generation_service.py` - FROM monthly_kpis → bank_fact_kpis_mensual
- [x] `sql_validator.py` - Added 11 MVs to whitelist
- [x] `llm_client.py` - Updated prompts
- [x] `data_tools.py`, `sql_agent.py` - Updated allowed tables
- [x] `schema_validator.py` - Added bank_fact_kpis_mensual mappings
- [x] `nl2sql_orchestrator.py` - Updated table lists
- [x] `main.py` - Health checks use normalized table
- [x] `db.py` - Init creates normalized table + compatibility view
- [x] `specs.py`, `sql_display.py`, `contextual_suggestion_service.py` - Docstrings/defaults
- [ ] Tests (pendiente - backward compat permite funcionar)

---

## Notas de Implementación

### QuerySpec Construction
El handler espera un `QuerySpec` con campos requeridos. Si `entities` no tiene métrica, usar defaults:
```python
spec = QuerySpec(
    bank=entities.banks[0] if entities.banks else None,
    metric=entities.metric_id or "saldo",  # default
    time_range="latest",
)
```

### Handler Signature Variations
Algunos handlers tienen firmas diferentes:
- `matches(query, entities, spec)` - nuevos handlers
- `matches(query, entities)` - handlers legacy
- `matches(query)` - handlers muy simples

El código debe manejar todas las variantes con try/except.

### Logging Pattern
```python
logger.info(
    "analytics_agent.handler_matched",
    handler=handler.name,
    query=user_query[:50],
    request_id=model.request_id,
)
```
