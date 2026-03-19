# EPIC-HU3: UI Clarificación

> **Status**: ⚠️ IN PROGRESS
> **Priority**: P1
> **Target Date**: 15 Jan 2026

---

## Agent Execution Context

> **CRITICAL**: This section provides everything a sub-agent needs to execute.

### Target Files

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `apps/web/src/components/ClarificationPrompt/index.tsx` | Clarification UI component |
| CREATE | `apps/web/src/components/ClarificationPrompt/types.ts` | TypeScript types |
| CREATE | `apps/web/src/components/ClarificationPrompt/ClarificationPrompt.test.tsx` | Frontend tests |
| MODIFY | `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | Add ambiguity detection |
| MODIFY | `plugins/bank-advisor-private/src/models/query_spec.py` | Add `ambiguity_flags` field |
| CREATE | `plugins/bank-advisor-private/src/services/clarification_service.py` | Generate clarification options |
| MODIFY | `apps/web/src/components/ChatMessage/index.tsx` | Integrate ClarificationPrompt |
| CREATE | `plugins/bank-advisor-private/tests/unit/test_clarification_service.py` | Unit tests |

### Integration Points

```
Usuario: "Dame IMOR" (ambiguo - falta banco y período)
            │
            ▼
    ┌───────────────────┐
    │ QuerySpec Builder │ → Detecta ambigüedad
    │                   │ → confidence = 0.45 (< 0.7 threshold)
    │                   │ → ambiguity_flags = ["bank", "period"]
    └───────┬───────────┘
            │
            ▼ QuerySpec: {confidence: 0.45, ambiguity_flags: ["bank", "period"]}
            │
    ┌─────────────────────┐
    │ Clarification       │ → Genera opciones
    │ Service             │ → bancos: top 5 más consultados
    │                     │ → períodos: últimos 12 meses
    └───────┬─────────────┘
            │
            ▼ Clarification: {type: "bank", options: [...]}
            │
    ┌───────────────┐
    │  Web UI       │ → Muestra botones clickeables
    │ Clarification │ → Usuario selecciona: "INVEX"
    │ Prompt        │ → Re-envía query con contexto
    └───────┬───────┘
            │
            ▼ Refined Query: "Dame IMOR de INVEX"
            │
    ┌───────────────────┐
    │ QuerySpec Builder │ → confidence = 0.88
    │                   │ → Procede normalmente
    └───────────────────┘
```

### Example Input/Output

**Input** (ambiguous query):
```json
{
  "user_query": "Dame IMOR",
  "session_id": "sess_123",
  "user_id": "user_456"
}
```

**QuerySpec Output** (with ambiguity):
```json
{
  "query_id": "q_791",
  "intent": "SQL_QUERY",
  "banks": null,
  "metrics": ["IMOR"],
  "period": null,
  "confidence": 0.45,
  "ambiguity_flags": [
    {
      "field": "bank",
      "reason": "No bank specified",
      "suggested_action": "clarify"
    },
    {
      "field": "period",
      "reason": "No time period specified",
      "suggested_action": "clarify"
    }
  ]
}
```

**Clarification Response** (to user):
```json
{
  "response_type": "clarification_needed",
  "message": "Para obtener el IMOR, necesito que especifiques:",
  "clarifications": [
    {
      "field": "bank",
      "question": "¿De qué banco?",
      "options": [
        {"label": "INVEX", "value": "INVEX"},
        {"label": "BBVA", "value": "BBVA"},
        {"label": "Santander", "value": "Santander"},
        {"label": "Banorte", "value": "Banorte"},
        {"label": "HSBC", "value": "HSBC"}
      ],
      "allow_custom": false
    },
    {
      "field": "period",
      "question": "¿De qué período?",
      "options": [
        {"label": "Último mes (Diciembre 2024)", "value": "2024-12"},
        {"label": "Último trimestre (Q4 2024)", "value": "2024-Q4"},
        {"label": "Año completo 2024", "value": "2024"}
      ],
      "allow_custom": true
    }
  ]
}
```

**User Selection** (frontend sends):
```json
{
  "original_query": "Dame IMOR",
  "clarifications": {
    "bank": "INVEX",
    "period": "2024-12"
  },
  "session_id": "sess_123"
}
```

**Refined QuerySpec** (after clarification):
```json
{
  "query_id": "q_792",
  "intent": "SQL_QUERY",
  "banks": ["INVEX"],
  "metrics": ["IMOR"],
  "period": {
    "start": "2024-12-01",
    "end": "2024-12-31",
    "granularity": "monthly"
  },
  "confidence": 0.95,
  "ambiguity_flags": []
}
```

### Validation Commands

```bash
# Preflight: ensure stack is up
make dev

# Backend tests (ambiguity detection)
cd plugins/bank-advisor-private
pytest tests/unit/test_clarification_service.py -v

# Frontend tests (UI component)
cd apps/web
pnpm test ClarificationPrompt.test.tsx

# Integration test (full clarification flow)
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Dame IMOR"}'  # Should return clarification response

# E2E test (manual - browser)
# 1. Start web: cd apps/web && pnpm dev
# 2. Navigate to http://localhost:3000
# 3. Enter "Dame IMOR" (ambiguous)
# 4. Verify clarification UI appears with clickable options
# 5. Click "INVEX" and "Diciembre 2024"
# 6. Verify refined query executes and returns data
```

---

## General Description

### Objective

Eliminar alucinaciones mediante un sistema de clarificación que pregunta al usuario cuando la query es ambigua, en lugar de inventar respuestas.

### Solution enables

- Detección automática de queries ambiguas (confidence < 0.7)
- UI con opciones clickeables (no texto libre)
- Contexto de conversación mantenido (session_id)
- Abstención explícita: sistema no inventa, pide clarificación
- Logging de clarificaciones para mejorar el modelo

### Problems solved

| Current Problem | Impact | Solution |
|-----------------|--------|----------|
| Sistema alucina cuando query es ambigua | Datos incorrectos, pérdida de confianza | Abstención + clarificación |
| Usuario no sabe qué falta en su query | Frustración, múltiples intentos | Opciones clickeables guiadas |
| Sin contexto de conversación | Cada query es aislada | Session tracking |
| No hay feedback loop para mejorar | Sistema no aprende de ambigüedades | Log clarifications → few-shot examples |

### Expected benefits

- **Para el usuario**: Confianza en el sistema (nunca inventa), guía clara cuando falta información
- **Para el negocio**: Trust metric mejora (cero alucinaciones), señal de qué queries son problemáticas
- **Para el sistema**: Feedback loop para mejorar QuerySpec Builder con few-shot examples

### Success metrics

| Metric | Baseline | Target | How to measure |
|--------|----------|--------|----------------|
| Abstention rate | N/A | < 10% | Clarifications / total queries |
| Clarification resolution rate | N/A | > 90% | Refined queries / clarifications shown |
| User frustration (abandoned clarifications) | N/A | < 5% | Abandoned / total clarifications |
| Zero hallucination incidents | N/A | 100% | Manual audit of ambiguous queries |

---

## Strategic Alignment

### Why this epic? (BRD Alignment)

**BRD use case**: UC-5 - UX de chat fluida

> "Interacción rápida → Incrementar adopción"
> — BRD.md, Sección 4: Casos de Uso

**BRD design principle**: #1 - Precisión regulatoria por encima de creatividad (no alucinar)

> "Precisión regulatoria por encima de creatividad (no alucinar)."
> — BRD.md, Sección 3.2: Principios de Diseño

**Direct connection**:
- Implementa el principio **más crítico** del producto: no alucinar
- UX fluida **no significa** responder siempre, sino responder **correctamente**
- Contribuye al **WAU** porque usuarios confían y regresan
- Reduce **churn** por frustración con datos incorrectos

**BRD Success Metrics Contribution**:

| BRD Metric | How HU3 Contributes |
|------------|---------------------|
| WAU (North Star) | Trust drives repeat usage |
| TTI | Clarification adds latency BUT ensures correctness |
| Trust (implicit) | Zero hallucinations = foundation for ARR |

### How does it integrate? (Architecture Alignment)

**Components involved**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     EPIC-HU3 Architecture                        │
├──────────────┬─────────────────┬──────────────────┬─────────────┤
│ QuerySpec    │  Clarification  │   Web UI         │  Session    │
│ Builder      │   Service       │ ClarificationPro │  Manager    │
│ (Modified)   │    (New)        │    mpt (New)     │  (Existing) │
├──────────────┼─────────────────┼──────────────────┼─────────────┤
│ 1. Detects   │ 1. Generates    │ 1. Renders       │ Maintains   │
│    ambiguity │    options      │    buttons       │ session     │
│    (conf<0.7)│    based on     │ 2. Captures      │ context     │
│ 2. Sets      │    field type   │    selection     │ across      │
│    flags     │ 2. Logs to DB   │ 3. Re-sends      │ queries     │
│              │    for analysis │    refined query │             │
└──────────────┴─────────────────┴──────────────────┴─────────────┘
```

**Integration with existing architecture**:

| Existing Component | Integration Point | HU3 Responsibility |
|-------------------|-------------------|-------------------|
| QuerySpec Builder (HU1) | Confidence scoring | Add ambiguity detection logic |
| Router/Orchestrator | Response routing | Return clarification response vs normal response |
| ChatMessage Component | Response rendering | Conditionally render ClarificationPrompt |
| MongoDB (session storage) | Session tracking | Store clarifications for learning |

**Technical dependencies**:

| Component | Status | Required for | Blocker? |
|-----------|--------|--------------|----------|
| QuerySpec Builder | ✅ DONE (HU1) | Ambiguity detection | No |
| Confidence scoring | ⚠️ PARTIAL | Threshold logic | **YES (P1-1)** |
| Session management | ✅ DONE | Context tracking | No |
| Frontend routing | ✅ DONE | Response types | No |

**Blocking Gap**: P1-1 (Modo Abstención Robusto) - see [GAPS.md](../PRD-old/GAPS.md)

---

## Deliverables List

| # | Deliverable | File Path | Completion Criteria |
|---|-------------|-----------|---------------------|
| E1 | Ambiguity Detection | `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | Flags ambiguity when confidence < 0.7 |
| E2 | Clarification Service | `plugins/bank-advisor-private/src/services/clarification_service.py` | Generates options by field type |
| E3 | ClarificationPrompt Component | `apps/web/src/components/ClarificationPrompt/index.tsx` | Renders clickable options |
| E4 | QuerySpec Schema Extension | `plugins/bank-advisor-private/src/models/query_spec.py` | Add `ambiguity_flags` field |
| E5 | Session Context Integration | `plugins/bank-advisor-private/src/services/session_service.py` | Track clarifications in session |
| E6 | Backend Tests | `plugins/bank-advisor-private/tests/unit/test_clarification_service.py` | 15+ tests for ambiguity cases |
| E7 | Frontend Tests | `apps/web/src/components/ClarificationPrompt/ClarificationPrompt.test.tsx` | 10+ tests for UI |
| E8 | Logging & Analytics | `plugins/bank-advisor-private/src/services/clarification_logger.py` | Log to MongoDB for analysis |

---

## Acceptance Criteria

### Functional

- [ ] **CA-01**: Query ambigua (confidence < 0.7) muestra UI de clarificación (no respuesta inventada)
- [ ] **CA-02**: Clarificación funciona para: banco, métrica, período
- [ ] **CA-03**: Opciones son clickeables (botones, no texto libre)
- [ ] **CA-04**: Usuario puede seleccionar múltiples campos a la vez
- [ ] **CA-05**: Selección re-envía query refinada automáticamente
- [ ] **CA-06**: Query refinada tiene confidence > 0.7
- [ ] **CA-07**: Contexto de sesión se mantiene (no pierde conversación previa)
- [ ] **CA-08**: Sistema nunca inventa banco/período cuando falta información

### Non-Functional

- [ ] **CA-09**: Clarificación se muestra en < 2 segundos
- [ ] **CA-10**: Opciones limitan a top 5 para evitar sobrecarga cognitiva
- [ ] **CA-11**: UI es accesible (keyboard navigation, screen reader friendly)
- [ ] **CA-12**: Todas las clarificaciones se loggean a MongoDB
- [ ] **CA-13**: Abstention rate < 10% (sistema no es demasiado estricto)

---

## Implementation Phases

### Phase 1: Backend Ambiguity Detection (1 día)

**Deliverables**: E1, E2, E4

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/src/agents/queryspec_builder.py` | MODIFY | Add ambiguity detection |
| `plugins/bank-advisor-private/src/models/query_spec.py` | MODIFY | Add `ambiguity_flags` field |
| `plugins/bank-advisor-private/src/services/clarification_service.py` | CREATE | Generate clarification options |
| `plugins/bank-advisor-private/tests/unit/test_clarification_service.py` | CREATE | Unit tests |

**Sub-agent delegation**:

```yaml
Agent: plan-architect
Task: Design ambiguity detection logic and confidence thresholds
Input: This mini-PRD Phase 1
Output: Decision tree for when to clarify vs proceed
```

```yaml
Agent: code-implementer
Task: Implement ambiguity detection with TDD
Input: plan-architect output + this mini-PRD
Output: Working ambiguity detection with 15+ tests passing
```

**Acceptance Criteria (Phase 1)**:
- [ ] QuerySpec Builder sets `confidence < 0.7` for ambiguous queries
- [ ] `ambiguity_flags` populated with missing fields
- [ ] Clarification Service generates top 5 options for each field type
- [ ] Unit tests pass (15+ tests)

---

### Phase 2: Frontend Clarification UI (1 día)

**Deliverables**: E3, E7

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/components/ClarificationPrompt/index.tsx` | CREATE | Clarification UI |
| `apps/web/src/components/ClarificationPrompt/types.ts` | CREATE | TypeScript types |
| `apps/web/src/components/ClarificationPrompt/ClarificationPrompt.test.tsx` | CREATE | Frontend tests |
| `apps/web/src/components/ChatMessage/index.tsx` | MODIFY | Integrate ClarificationPrompt |

**Sub-agent delegation**:

```yaml
Agent: code-implementer
Task: Implement ClarificationPrompt component with accessibility
Input: Clarification Service API contract + this mini-PRD
Output: Working React component with 10+ tests passing
```

**Acceptance Criteria (Phase 2)**:
- [ ] ClarificationPrompt renders clickable options
- [ ] User can select multiple fields
- [ ] Component re-sends refined query on selection
- [ ] Keyboard navigation works (tab, enter)
- [ ] Component tests pass (10+ tests)

---

### Phase 3: Session Context & Logging (0.5 días)

**Deliverables**: E5, E8

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/src/services/session_service.py` | MODIFY | Track clarifications |
| `plugins/bank-advisor-private/src/services/clarification_logger.py` | CREATE | Log to MongoDB |
| `plugins/bank-advisor-private/tests/unit/test_clarification_logger.py` | CREATE | Unit tests |

**Sub-agent delegation**:

```yaml
Agent: code-implementer
Task: Implement session tracking and logging
Input: Session Service (existing) + this mini-PRD
Output: Clarification logging integrated with session
```

**Acceptance Criteria (Phase 3)**:
- [ ] Clarifications logged to MongoDB with session_id, user_id, original_query, selections
- [ ] Session context includes clarification history
- [ ] Unit tests pass

---

### Phase 4: Integration & E2E Testing (0.5 días)

**Deliverables**: E6

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `plugins/bank-advisor-private/tests/integration/test_clarification_flow.py` | CREATE | E2E test full flow |
| `apps/web/tests/e2e/clarification.spec.ts` | CREATE | Playwright E2E test |

**Sub-agent delegation**:

```yaml
Agent: test-runner
Task: Execute E2E tests for clarification flow
Input: All phases completed + validation commands
Output: Test report with pass/fail status
```

**Acceptance Criteria (Phase 4)**:
- [ ] E2E test: Ambiguous query → clarification UI → selection → refined query → result
- [ ] E2E test: Verify no hallucination on ambiguous queries

---

## Definition of Done

| Criterion | Verification Command | Pass Condition | Status |
|-----------|---------------------|----------------|--------|
| Backend tests | `pytest tests/unit/test_clarification_service.py -v` | 15+ passing | ⚠️ PENDING |
| Frontend tests | `cd apps/web && pnpm test ClarificationPrompt` | 10+ passing | ⚠️ PENDING |
| Integration test | `pytest tests/integration/test_clarification_flow.py` | E2E passing | ⚠️ PENDING |
| Lint (backend) | `ruff check src/` | 0 errors | ⚠️ PENDING |
| Lint (frontend) | `cd apps/web && pnpm lint` | 0 errors | ⚠️ PENDING |
| Accessibility | `axe-core` scan on ClarificationPrompt | WCAG 2.1 AA | ⚠️ PENDING |
| Manual QA | Test 10 ambiguous queries | 0 hallucinations | ⚠️ PENDING |
| Abstention rate | Analytics query | < 10% | ⚠️ PENDING (measure post-deploy) |

---

## Risks and Mitigation

| Risk | Prob | Impact | Mitigation |
|------|------|--------|------------|
| Abstention rate too high (>10%) | Media | Alta | Tune confidence threshold, add few-shot examples |
| User abandons clarification | Media | Media | Limit options to 5, clear UI, pre-select most likely |
| Clarification latency | Baja | Media | Cache top options (banks, periods), generate async |
| Confidence scoring inaccurate | Alta | Alta | Validate with 50+ test queries, tune threshold |
| Session context lost | Baja | Alta | Persist session to MongoDB, restore on page refresh |

---

## References

| Document | Relevant Section |
|----------|------------------|
| [BRD.md](../BRD.md) | Section 3.2: Design Principles (#1 - No alucinar) |
| [BRD.md](../BRD.md) | Section 4: Use Cases (UC-5 - UX fluida) |
| [PRD.md](../product/PRD.md) | HU3: UI Clarificación |
| [architecture/AGENTS.md](../architecture/AGENTS.md) | QuerySpec Builder contract |
| [EPIC-HU1.md](EPIC-HU1.md) | QuerySpec Builder (dependency) |
| [GAPS.md](../PRD-old/GAPS.md) | P1-1: Modo Abstención Robusto |

---

## Notes

- **Blocker**: Confidence threshold logic not fully robust (P1-1 in GAPS.md)
- **Effort estimate**: 2-3 days (1 backend + 1 frontend + 0.5 logging + 0.5 testing)
- **Dependencies**: Requires HU1 (QuerySpec Builder) to be complete - ✅ DONE
- Confidence threshold (0.7) is initial estimate - must tune based on real usage
- Consider adding "I don't know" option if none of the clarification options fit
- Clarification data = gold mine for improving QuerySpec Builder with few-shot examples
- UI should gracefully degrade on mobile (smaller buttons, scrollable)
- Future: Predict likely clarifications proactively ("Did you mean INVEX?")

**Next Steps**:
1. Plan-architect designs ambiguity detection decision tree
2. Code-implementer implements backend (Phase 1)
3. Code-implementer implements frontend (Phase 2)
4. Test-runner validates no hallucinations on ambiguous queries
