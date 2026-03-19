# Plan

## Objective
- Eliminar la discrepancia entre la linea promedio de la app y la referencia de Tableau para `cartera_total` en modo target-vs-average.

## Scope
### In
- Definir semantica oficial del promedio (peers-only vs peers+target).
- Implementar modo explicito de poblacion del promedio.
- Exponer metadata de formula en la respuesta del chart.
- Cubrir con tests unitarios/E2E la definicion elegida.

### Out
- Ajustes de ETL y recarga historica.
- Cambios funcionales en otros handlers no relacionados con peer-average.

## Phases
### Phase 1 - Decision de negocio y contrato de respuesta
- [ ] Validar con Bajaware si benchmark oficial debe incluir INVEX.
- [ ] Congelar contrato: `average_population` en metadata.
- [ ] Definir comportamiento por defecto por tenant.

#### Phase 1 Files
- `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py`
- `plugins/bank-advisor-private/src/bankadvisor/tools/schemas/comparison.py`
- `apps/backend/src/services/llm_context_builder.py`

### Phase 2 - Implementacion de formula
- [ ] Implementar modo `peers_plus_target` en repository/use case.
- [ ] Mantener `peers_only` para backward compatibility si aplica.
- [ ] Ajustar texto/tabla para reflejar la poblacion real del promedio.

#### Phase 2 Files
- `plugins/bank-advisor-private/src/bankadvisor/repositories/kpi_repository.py`
- `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py`
- `plugins/bank-advisor-private/src/main.py`
- `plugins/bank-advisor-private/src/bankadvisor/tools/comparison_tools.py`

### Phase 3 - Validacion y regression
- [ ] Unit tests formula peers-only y peers+target.
- [ ] E2E con prompt de cartera total (enero 2021 a dato mas reciente).
- [ ] Validacion numerica de octubre 2021 contra expected labels.

#### Phase 3 Files
- `plugins/bank-advisor-private/tests/unit/application/test_use_cases.py`
- `tests/e2e/charts/test_peer_avg_cartera_total_chart.py` (nuevo)
- `tests/e2e/charts/*_results.json` (nuevo)

## Validation Commands
- `python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/application/test_use_cases.py -k PeerAverageUseCase`
- `python3.11 -m pytest -q plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_query_spec_parser_financial_metrics.py -k peer_average`
- `cd apps/backend && PYTEST_ADDOPTS='--no-cov' python3.11 -m pytest -q tests/unit/test_delta_context_injection.py -k peer_average`
- `python3.11 tests/e2e/charts/test_peer_avg_cartera_total_chart.py`

## Success Criteria
- [ ] Unicidad semantica: cada chart declara explicitamente su poblacion de promedio.
- [ ] Coincidencia numerica con la definicion seleccionada para octubre 2021.
- [ ] No regresion en rutas de peer-average existentes.
