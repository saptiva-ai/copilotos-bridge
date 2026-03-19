# Validation: Semantic Intent Router

## Validation Commands

```bash
# 1. Unit tests for semantic scorer
docker compose -f infra/docker-compose.yml --env-file envs/.env exec backend python -m pytest tests/unit/test_semantic_intent_router.py -v --no-cov

# 2. Existing bank advisor precheck tests (must still pass)
docker compose -f infra/docker-compose.yml --env-file envs/.env exec backend python -m pytest tests/unit/test_streaming_services.py -v -k BankAdvisorPreCheckService --no-cov

# 3. Full backend unit tests
docker compose -f infra/docker-compose.yml --env-file envs/.env exec backend python -m pytest tests/unit/ --no-cov -q
```

## Acceptance Criteria

### Functional Requirements

- [x] **AC1:** Greetings detected semantically
  - "Hola" → skip ✓
  - "Holi" → skip (typo handled) ✓
  - "Hey que tal" → skip ✓

- [x] **AC2:** Data queries routed to bank-advisor
  - "Dame el IMOR de BBVA" → invoke ✓
  - "Top 5 bancos por morosidad" → invoke ✓
  - "Compara INVEX con Banorte" → invoke ✓

- [x] **AC3:** Knowledge queries routed to bank-advisor
  - "¿Qué es el IMOR?" → invoke ✓
  - "Explica capitalización" → invoke ✓

- [x] **AC4:** Follow-ups with context routed correctly
  - [After chart shown] "¿Por qué subió?" → invoke ✓
  - [After ranking] "El primero" → invoke ✓

- [x] **AC5:** Explicit enablement overrides
  - `tools_enabled={"bank-advisor": True}` → always invoke ✓

### Non-Functional Requirements

- [x] **NFR1:** Latency <50ms for cached queries (embedding service caches vectors)
- [x] **NFR2:** No external API dependencies
- [x] **NFR3:** Uses only Saptiva EmbeddingService (paraphrase-multilingual-MiniLM-L12-v2)
- [x] **NFR4:** Backward compatible with existing tests (all 171 streaming tests pass)

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| `test_should_run_advisor_explicitly_enabled_bank_advisor` | ✅ PASS | |
| `test_should_run_advisor_explicitly_enabled_bank_analytics` | ✅ PASS | |
| `test_should_run_advisor_knowledge_trigger_que_es` | ✅ PASS | |
| `test_should_run_advisor_knowledge_trigger_define` | ✅ PASS | |
| `test_should_run_advisor_knowledge_trigger_definicion` | ✅ PASS | |
| `test_should_run_advisor_no_triggers` | ✅ PASS | |
| `test_should_run_advisor_case_insensitive` | ✅ PASS | |
| `test_knowledge_triggers_list_completeness` | ✅ PASS | |
| `test_load_recent_messages_empty_session` | ✅ PASS | |

### New Semantic Intent Router Tests (21 tests)

| Test | Status |
|------|--------|
| `TestIntentScores::test_from_dict_basic` | ✅ PASS |
| `TestIntentScores::test_from_dict_empty` | ✅ PASS |
| `TestIntentScores::test_to_dict` | ✅ PASS |
| `TestContextEnhancer::test_extract_context_empty` | ✅ PASS |
| `TestContextEnhancer::test_extract_context_with_chart_in_memory` | ✅ PASS |
| `TestContextEnhancer::test_extract_context_with_chart_in_messages` | ✅ PASS |
| `TestContextEnhancer::test_enhance_with_follow_up_and_chart` | ✅ PASS |
| `TestContextEnhancer::test_enhance_short_message_after_chart` | ✅ PASS |
| `TestDecisionAggregator::test_explicit_enablement_always_wins` | ✅ PASS |
| `TestDecisionAggregator::test_negative_cache_skips` | ✅ PASS |
| `TestDecisionAggregator::test_high_banking_score_invokes` | ✅ PASS |
| `TestDecisionAggregator::test_high_non_banking_score_skips` | ✅ PASS |
| `TestDecisionAggregator::test_ambiguous_delegates` | ✅ PASS |
| `TestDecisionAggregator::test_follow_up_with_context_invokes` | ✅ PASS |
| `TestDecisionAggregator::test_to_tuple_conversion` | ✅ PASS |
| `TestIntentFeedbackCollector::test_hash_message_normalization` | ✅ PASS |
| `TestIntentFeedbackCollector::test_is_known_negative_no_redis` | ✅ PASS |
| `TestIntentFeedbackCollector::test_record_feedback_false_positive` | ✅ PASS |
| `TestBankAdvisorPreCheckServiceIntegration::test_fallback_explicit_enabled` | ✅ PASS |
| `TestBankAdvisorPreCheckServiceIntegration::test_fallback_knowledge_trigger` | ✅ PASS |
| `TestBankAdvisorPreCheckServiceIntegration::test_fallback_greeting_skipped` | ✅ PASS |

## Validation Log

**2026-01-27:**
- All 21 semantic intent router tests pass
- All 171 streaming tests pass (9 BankAdvisorPreCheckService tests updated for async)
- Full backend suite: 3823 passed, 28 skipped
- Commit: `70cab4f6` pushed to `develop`
