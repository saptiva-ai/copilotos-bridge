# Validation

## Commands
- `python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/application/test_use_cases.py -k PeerAverageUseCase`
- `python3.11 -m pytest -q plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_query_spec_parser_financial_metrics.py -k peer_average`
- `cd apps/backend && PYTEST_ADDOPTS='--no-cov' python3.11 -m pytest -q tests/unit/test_delta_context_injection.py -k peer_average`
- SQL checks (read-only) para:
  - cobertura por banco y periodo
  - duplicados por `(banco, fecha)`
  - comparacion `AVG(peers)` vs `AVG(peers + INVEX)`

## Results
### Automated tests
- NOT RUN (research-only): los comandos de pytest quedan como checklist para cuando se implemente el fix.

### Data checks (read-only)
- SQL auditoria de datos:
  - cobertura completa 2021-01 a 2025-11 para los 10 bancos
  - sin duplicados banco-fecha
  - `n_peers_usados = 9` en todos los meses
- SQL auditoria numerica octubre 2021:
  - INVEX: `20,552.54` -> `20,553`
  - AVG peers-only: `37,636.29` -> `37,636`
  - AVG peers+INVEX: `35,927.92` -> `35,928` (match con imagen)

## Notes
- La discrepancia actual con Tableau se explica por definicion de promedio (poblacion), no por faltantes de datos.
- Falta decision funcional de negocio para cerrar implementacion (modo oficial de promedio).
