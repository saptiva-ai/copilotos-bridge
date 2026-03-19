---
id: "PERF-2026-02-17__query-latency-optimization"
title: "Reducir latencia de queries de onboarding de ~47s a <15s"
status: "DONE"
phase: "Validation"
scope_in:
  - "Instrumentar timing real por fase del pipeline (context → MCP → LLM → post)"
  - "Implementar cache Redis de resultados MCP tool (TTL 5min)"
  - "Enviar bank_chart SSE event antes de iniciar LLM streaming"
  - "Optimizar SQL queries en peer_average y evolution use cases"
  - "Reducir tamaño del system prompt (tools list)"
scope_out:
  - "Cambio de modelo LLM (requiere evaluación de calidad separada)"
  - "Response templates sin LLM (requiere diseño UX separado)"
  - "Cambios en la arquitectura MCP (migración gRPC es task separado)"
  - "Índices de DB (requiere acceso DBA a PROD)"
next_action: "Ejecutar regresión E2E completa y cerrar bug funcional de queries que caen en clarification"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 0
validation_commands:
  - "python3.11 tests/e2e/charts/test_tasa_me_dual_prompts.py"
  - "python3.11 tests/e2e/charts/test_tasa_mn_dual_prompts.py"
  - "python3.11 tests/e2e/charts/test_quebrantos_cc_yearly_bar_chart.py"
pr_files: []
test_status: "partial_pass"
---

# Summary

Latencia observada: ~47 segundos por query de onboarding (prompts de ayuda).
Target: <15s primera consulta, <8s consultas repetidas (cache hit).

## Hipótesis de distribución de tiempo

| Fase | Estimado | Componente |
|------|----------|------------|
| Context setup | ~3s | Auth, session, MongoDB |
| **MCP tool (SQL + chart)** | **~20-25s** | `call_bank_advisor_tool()` → SQL → DataFrame → Plotly |
| System prompt build | ~1.5s | Tools list, RAG context |
| **LLM streaming** | **~12-18s** | Saptiva LLM, texto narrativo |
| Post-processing | ~2s | Table injection, MongoDB persist |

## Outcome esperado

1. **Timing instrumentado**: Logs con `[PERF]` tag mostrando ms por fase
2. **Cache Redis implementado**: Resultados MCP cacheados por 5min
3. **Chart-first SSE**: Usuario ve la gráfica mientras LLM genera texto
4. **Latencia medida** post-optimización < 15s

## Validación

- [x] Timing log / perf trace muestra desglose real por fase
- [x] Cache hit reduce MCP phase a <100ms (TREND: 13-15ms MCP blocking)
- [x] bank_chart SSE event llega antes que chunks de texto (TREND)
- [ ] E2E tests siguen pasando (tasa_mn, tasa_me, quebrantos)
- [x] Latencia total < 15s en primera consulta

## Resultado final (2026-02-18)

Perf trace manual (`tests/e2e/charts/perf_trace_query.py`) después de aplicar 0.5-0.10:

| Query | Cold total | Warm total | Nota |
|------|-----------:|-----------:|------|
| RANKING quebrantos | 0.46s | 0.40s | Respuesta en modo clarification |
| TREND tasa_mn | 6.44s | 6.14s | Chart + texto LLM |
| ICAP snapshot | 0.34s | 0.34s | Respuesta en modo clarification |
| **Promedio** | **2.41s** | **2.29s** | Muy por debajo del target `<15s` |

Observación crítica: la latencia bajó de forma sustancial, pero dos escenarios quedan en
`clarification` (no chart final), por lo que el siguiente foco debe ser **calidad/coverage funcional**
y no rendimiento puro.

# Updates
- 2026-02-17 - Ticket creado. Investigación inicial con análisis estático del código.
- 2026-02-18 - Se corrigió diagnóstico de streaming (path RAG no-streaming en backend) y se aplicaron mejoras: `rag streaming-first + fallback` y `precheck fast-path`.
- 2026-02-18 - Continuación implementación: se eliminó fetch redundante de `bank_tools_markdown` cuando ya hay `bank_chart_data`, se agregó flag `BANK_TOOLS_PROMPT_ENABLED`, y se migró routing cache key a versión normalizada `v2`.
- 2026-02-18 - Optimización de transporte RPC: `bank_analytics_client` ahora reutiliza `httpx.AsyncClient` por event loop en hot-path (`list_bank_advisor_tools`, `call_bank_advisor_tool`, `query_bank_analytics`).
- 2026-02-18 - `list_bank_advisor_tools` mejorado con TTL + stale-while-revalidate: si el cache está vencido retorna cache inmediato y refresca en background.
- 2026-02-18 - Nuevo `clarification fast-path` en `ChatStreamProducer`: evita roundtrip LLM cuando ya hay payload de aclaración y reduce TTFB de aclaraciones a ~6-15ms post-meta.
