# Validation: Delta Chart LLM Text Desync

## TDD Checklist

### Phase 1: DeltaResult response_text
- [ ] `test_delta_response_text.py` — test rojo creado
- [ ] `DeltaResult._build_response_text()` implementado
- [ ] Tests verdes: response_text presente, con metrica, periodos, bancos
- [ ] `docker compose restart bank-advisor`

### Phase 2: analytics_extractor table_data injection
- [ ] `test_analytics_extractor_delta.py` — test rojo creado
- [ ] `_format_table_context()` implementado
- [ ] `extract()` modificado para incluir table_data
- [ ] Tests verdes: table_data en contexto, non-delta no roto
- [ ] `docker compose restart backend`

### Phase 3: LLM context delta instruction
- [ ] `test_llm_context_builder_delta.py` — test rojo creado
- [ ] `DELTA_CONTEXT` string agregado
- [ ] Deteccion condicional implementada (orientation=h + table_data)
- [ ] Tests verdes: instruccion delta presente/ausente segun chart type

## Regression Checks

- [ ] `python -m pytest plugins/bank-advisor-private/tests/unit/test_delta_variation.py -v` — 21 tests pass
- [ ] `python -m pytest plugins/bank-advisor-private/tests/unit/test_cc_sin_gob_delta.py -v` — 23 tests pass
- [ ] E2E: `python tests/e2e/charts/test_variacion_cartera_comercial_bar_chart.py` — 12/12 pass
- [ ] E2E: `python tests/e2e/charts/test_variacion_cartera_bar_chart.py` — existing test pass

## PROD Validation

- [ ] Deploy develop to PROD
- [ ] Ejecutar prompt original en chat PROD
- [ ] Verificar: chart bar horizontal con 10 bancos
- [ ] Verificar: texto NO dice "no tengo datos"
- [ ] Verificar: texto menciona variaciones y periodos consistentes con chart
- [ ] Verificar: prompt con comillas `"periodo inicial"` produce mismos resultados

## Acceptance Criteria

1. LLM response text references the same data that the chart displays
2. table_data values are accessible to the LLM before it generates text
3. No regression: line charts, scatter charts, and other visualizations unaffected
4. Both quoted and unquoted period labels produce identical delta bar charts
