# Validation: Fecha-Valor Tabular Desync

## Commands

- [x] `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_table_mode_resolver.py -k gaps --no-cov -q`
- [x] `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_analytics_extractor.py -k "parse_year_month_format or parse_abbrev_month_year_format or parse_invalid_date_raises or extract_sorts_by_date" --no-cov -q`
- [x] `cd plugins/bank-advisor-private && pytest src/bankadvisor/tests/unit/test_viz_service.py -k missing_months --no-cov -q`
- [x] `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_analytics_extractor.py --no-cov -q`
- [x] `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_table_mode_resolver.py --no-cov -q`
- [x] `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_table_mode_semantic.py --no-cov -q`
- [x] `cd plugins/bank-advisor-private && pytest src/bankadvisor/tests/unit/test_multi_bank_support.py -q`
- [x] `cd apps/backend && TEST_MODE=true .venv/bin/pytest tests/unit/test_table_fallback_injection.py --no-cov -q`
- [x] `cd plugins/bank-advisor-private && pytest src/bankadvisor/tests/unit/test_viz_service.py --no-cov -q`
- [x] `python tests/e2e/regression/test_2026_02_08_bug_fecha_valor_tabular_desync.py`
- [ ] `make dev`

## Results

- PASS: table alignment regression (1 passed).
- PASS: analytics extractor parse regressions (4 passed).
- PASS: plugin timeline alignment regression (1 passed).
- PASS: analytics extractor full suite (28 passed).
- PASS: table-mode resolver full suite after semantic-routing update (47 passed).
- PASS: semantic table-mode unit suite (5 passed).
- PASS: query-spec multi-bank suite (14 passed) con nuevas regresiones de comparison_mode.
- PASS: table fallback injection suite (13 passed).
- PASS: plugin viz service full suite (3 passed).
- PASS: E2E fecha-valor-tabular-desync (3 passed, 0 failed).
- PENDING: `make dev` command execution explícita y confirmación en producción.

## Notes

- Se ajustaron 3 tests legacy de `test_analytics_extractor.py` que estaban desfasados
  respecto al contrato actual (`DataPoint` permite valores monetarios >1000 y el
  `LLMContextBuilder` ahora incluye una guardrail compacta con "PROHIBIDO decir ...").
- Se considera aprobado cuando:
  - No hay desalineacion fecha-valor en texto, tabla ni chart.
  - Consultas multi-banco de evolucion no se degradan a snapshot por `comparison_mode` forzado.
  - El regression E2E nuevo pasa con backend real.
  - El usuario confirma no reproduccion en produccion.
