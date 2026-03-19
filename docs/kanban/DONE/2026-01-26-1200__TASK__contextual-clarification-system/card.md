---
id: "TASK-2026-01-26-1200__contextual-clarification-system"
title: "Sistema de Clarificación Contextual para Bank Advisor"
status: "DONE"
phase: "Validate"
priority: "HIGH"
scope_in:
  - "Enriquecer contexto usando SemanticIntentScorer (follow-up detection)"
  - "Calcular similaridad query-contexto con EmbeddingService"
  - "Resolver ambigüedad market_cap/ICAP usando WeaviateOntologyService.category"
  - "Inferir banco desde last_banks en follow-ups"
  - "Opciones de clarificación priorizando contexto"
  - "Tests e2e para escenarios conversacionales"
scope_out:
  - "Cambios a la UI de clarificación (solo backend/plugin)"
  - "Nuevas métricas o bancos"
  - "Crear módulos de detección de dominio (reusar Weaviate)"
  - "Modificar SemanticIntentScorer o EmbeddingService"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "make test T=api TEST_ARGS='-k clarification'"
  - "make test T=e2e TEST_ARGS='-k clarification'"
pr_files: []
test_status: "✅ 27 unit + 7 E2E passing"
---

# Summary

- **Objective**: Eliminar falsos positivos/negativos en el sistema de clarificación integrando el contexto conversacional existente (last_metric, last_banks, semantic_domain) en las decisiones de clarificación.
- **Problem Statement**: El sistema actual analiza cada mensaje de forma aislada, ignorando el contexto de la conversación. Esto causa que preguntas follow-up como "¿y la cartera?" pidan clarificación de banco cuando el contexto ya lo tiene.
- **Constraints**:
  - No modificar la UI de clarificación existente
  - Mantener backward compatibility con HARD_ASK/SOFT_ASK
  - No agregar latencia significativa al pipeline

# Key Metrics

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Falsos positivos en follow-ups | ~40% | < 10% |
| Resolución automática market_cap/ICAP | 0% | > 70% |
| Latencia adicional | N/A | < 50ms |

# Acceptance Criteria

## AC-1: Enriquecimiento de Contexto (Backend) ✅ PHASE 1 DONE
- [x] `context_enricher.py` usa SemanticIntentScorer para detectar follow-up
- [x] Calcula similaridad query-contexto con EmbeddingService (usa cache)
- [x] Retorna EnrichedContext con: is_followup, followup_confidence, context_similarity
- [x] Log "context_enriched" incluye métricas de follow-up y similaridad
- [x] 12 unit tests passing for context_enricher

## AC-2: Inferencia de Banco en Follow-ups ✅ PHASE 3 DONE
- [x] Si `is_followup=True` y `last_banks` existe → inferir banco
- [x] Si `context_similarity > 0.65` y `last_banks` existe → inferir banco
- [x] Agregar flag `inferred_from_context: true` al QuerySpec
- [x] No inferir si no hay chart reciente (has_recent_chart=False)
- [x] Heuristic fallback: short queries (<=5 words) after chart

## AC-3: Resolución de Ambigüedad con Weaviate ✅ PHASE 2 DONE
- [x] `WeaviateService.resolve_ambiguous_term()` usa category para desambiguar
- [x] Si last_metric="IMOR" (category=capital) y query="capitalización" → ICAP
- [x] Si last_metric="MARKET_SHARE" (category=mercado) y query="capitalización" → MARKET_CAP
- [x] Si no hay contexto o categorías no coinciden → return None (HARD_ASK)
- [x] `WeaviateService.get_term_category()` retorna categoría de métrica
- [x] 15 unit tests passing for ontology disambiguation

## AC-4: Opciones de Clarificación Contextuales ✅ PHASE 3 DONE
- [x] TOP_BANKS prioriza `last_banks` con label "(anterior)"
- [x] Máximo 2 bancos del contexto + 3 estáticos = 5 opciones
- [x] _get_options_for_field() accepts context parameter

## AC-5: Tests de Regresión ✅ ALL PASSING
- [x] E2E: "IMOR de BBVA" → "¿y la cartera?" → muestra CARTERA de BBVA ✅ PASSED
- [x] E2E: "ICAP de INVEX" → "capitalización" → resuelve a ICAP ✅ PASSED
- [x] E2E: Sin contexto, "capitalización de BBVA" → HARD_ASK ✅ PASSED
- [x] Unit: SemanticIntentScorer detecta follow-up con score > 0.5 ✅ PASSED
- [x] 7/7 E2E tests passing (90.74s)

## AC-6: Logging y Observabilidad ✅ DONE
- [x] Log "context_enricher.enriched" en backend (with is_followup, confidence, similarity)
- [x] Log "clarification.inferred_bank_from_context" en plugin (with banks, confidence)
- [x] Log "clarification.ambiguity_resolved" con original, resolved_to, category, context_metric

# Updates
- 2026-01-26 12:00 - Created. Investigation of current implementation completed.
- 2026-01-26 23:30 - Plan v2: Revised to reuse existing infrastructure (SemanticIntentScorer, EmbeddingService, WeaviateOntologyService) instead of creating new modules.
- 2026-01-26 - Phase 1 complete: context_enricher.py created with 12 passing tests.
- 2026-01-26 - Phase 2 complete (TDD): WeaviateService extended with resolve_ambiguous_term() and get_term_category() - 15 passing tests, 48 existing tests still pass.
- 2026-01-27 - Phase 3 complete: ClarificationService updated with PluginContext, contextual bank inference, ambiguity resolution via WeaviateService. 24 TDD tests written.
- 2026-01-27 - E2E tests created: test_contextual_clarification_e2e.py with 7 tests for multi-turn context scenarios (follow-up inference, ambiguity resolution, no-context baseline).
- 2026-01-27 - **AC-5 COMPLETE**: 7/7 E2E tests passing (90.74s). Contextual clarification working end-to-end.
- 2026-01-27 - **AC-6 COMPLETE**: All structured logging already in place (context_enricher.enriched, clarification.inferred_bank_from_context, clarification.ambiguity_resolved).
- 2026-01-27 - **TASK DONE**: All 6 acceptance criteria completed. 27 backend unit tests + 7 E2E tests passing.

# Files Modified

## Phase 1 (Backend Context Enrichment)
- `apps/backend/src/services/intent/context_enricher.py` (NEW - EnrichedContext, enrich_context)
- `apps/backend/src/services/intent/__init__.py` (MODIFIED - exports)
- `apps/backend/src/services/tool_execution_service.py` (MODIFIED - integrates enriched context)
- `apps/backend/tests/unit/services/intent/test_context_enricher.py` (NEW - 12 tests)

## Phase 2 (Weaviate Disambiguation)
- `apps/backend/src/services/weaviate_service.py` (MODIFIED - resolve_ambiguous_term, get_term_category)
- `apps/backend/tests/unit/services/test_weaviate_ontology_disambiguation.py` (NEW - 15 tests)

## Phase 3 (Plugin Contextual Clarification)
- `plugins/bank-advisor-private/src/bankadvisor/services/clarification_service.py` (MODIFIED - PluginContext, contextual inference, ambiguity resolution)
- `plugins/bank-advisor-private/tests/unit/test_contextual_clarification.py` (NEW - 24 tests)
- `tests/e2e/clarification/test_contextual_clarification_e2e.py` (NEW - 7 E2E tests for multi-turn context)
