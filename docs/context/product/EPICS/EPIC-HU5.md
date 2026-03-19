# EPIC-HU5: Sistema Feedback

> **Status**: ✅ DONE
> **Priority**: P1
> **Completion Date**: 31 Dec 2025

---

## Agent Execution Context

> **CRITICAL**: This section provides everything a sub-agent needs to execute.

### Target Files

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `apps/web/src/components/FeedbackButtons/index.tsx` | Thumbs up/down UI component |
| CREATE | `apps/web/src/components/FeedbackButtons/FeedbackModal.tsx` | Comment modal for thumbs down |
| CREATE | `apps/web/src/components/FeedbackButtons/types.ts` | TypeScript types |
| CREATE | `apps/backend/src/routers/feedback.py` | Feedback API endpoints |
| CREATE | `apps/backend/src/services/feedback_service.py` | Feedback business logic |
| CREATE | `apps/backend/src/models/feedback.py` | Feedback MongoDB schema |
| MODIFY | `apps/web/src/components/ChatMessage/index.tsx` | Integrate FeedbackButtons |
| CREATE | `apps/backend/tests/unit/test_feedback_service.py` | Backend unit tests |
| CREATE | `apps/web/src/components/FeedbackButtons/FeedbackButtons.test.tsx` | Frontend tests |

### Integration Points

```
Usuario ve respuesta del sistema → Click en thumbs down
            │
            ▼
    ┌───────────────────┐
    │ FeedbackButtons   │ → Muestra modal de comentario (opcional)
    │  Component        │ → Captura: message_id, rating, comment
    └───────┬───────────┘
            │
            ▼ POST /api/feedback
            │
    ┌───────────────────┐
    │ Feedback Router   │ → Valida payload
    │                   │ → Extrae contexto adicional (session, query)
    └───────┬───────────┘
            │
            ▼
    ┌───────────────────┐
    │ Feedback Service  │ → Enriquece con metadata
    │                   │ → Almacena en MongoDB
    │                   │ → Triggerea análisis (async)
    └───────┬───────────┘
            │
            ▼
    ┌───────────────────┐
    │   MongoDB         │ Collection: feedback
    │                   │ Schema: {message_id, rating, comment, ...}
    └───────┬───────────┘
            │
            ▼ (Future: Analytics)
    ┌───────────────────┐
    │  Feedback Loop    │ → Identifica patrones de error
    │  Analysis         │ → Mejora few-shot examples
    │  (v1.2+)          │ → Ajusta confidence thresholds
    └───────────────────┘
```

### Example Input/Output

**Input** (user clicks thumbs down):
```json
{
  "message_id": "msg_12345",
  "rating": "down",
  "comment": "El dato no coincide con mi reporte interno",
  "session_id": "sess_123",
  "user_id": "user_456"
}
```

**Feedback Enrichment** (backend adds context):
```json
{
  "feedback_id": "fb_67890",
  "message_id": "msg_12345",
  "rating": "down",
  "comment": "El dato no coincide con mi reporte interno",
  "user_id": "user_456",
  "session_id": "sess_123",
  "timestamp": "2025-01-10T14:32:15Z",
  "context": {
    "original_query": "Dame IMOR de INVEX en diciembre 2024",
    "response_text": "El IMOR de INVEX en diciembre 2024 fue 2.34%.",
    "data_returned": {"bank": "INVEX", "metric": "IMOR", "value": 2.34},
    "sql_executed": "SELECT imor FROM v_cnbv_metrics_monthly WHERE ...",
    "intent": "SQL_QUERY",
    "confidence": 0.95
  },
  "metadata": {
    "user_agent": "Mozilla/5.0 ...",
    "device": "desktop",
    "session_duration_sec": 342
  }
}
```

**MongoDB Document**:
```json
{
  "_id": "fb_67890",
  "message_id": "msg_12345",
  "rating": "down",
  "comment": "El dato no coincide con mi reporte interno",
  "user_id": "user_456",
  "session_id": "sess_123",
  "timestamp": "2025-01-10T14:32:15Z",
  "context": {...},
  "metadata": {...},
  "analysis": {
    "category": null,  // To be populated by analysis job
    "root_cause": null,
    "priority": null
  },
  "status": "pending_review"
}
```

**Analytics Query** (future - identify patterns):
```javascript
// MongoDB aggregation
db.feedback.aggregate([
  { $match: { rating: "down", timestamp: { $gte: ISODate("2025-01-01") } } },
  { $group: { _id: "$context.intent", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
// Output: Most problematic intent types
```

### Validation Commands

```bash
# Preflight: ensure stack is up
make dev

# Backend tests
cd apps/backend
pytest tests/unit/test_feedback_service.py -v

# Frontend tests
cd apps/web
pnpm test FeedbackButtons.test.tsx

# Integration test (submit feedback)
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_test_123",
    "rating": "down",
    "comment": "Test comment",
    "session_id": "sess_test"
  }'

# Verify MongoDB storage
docker exec -it octavios-mongodb mongosh
> use octavios_chat
> db.feedback.find().limit(5).pretty()

# E2E test (manual - browser)
# 1. Start web: cd apps/web && pnpm dev
# 2. Navigate to http://localhost:3000
# 3. Submit a query and get a response
# 4. Click thumbs down
# 5. Verify modal appears
# 6. Enter comment and submit
# 7. Check MongoDB for new feedback document
```

---

## General Description

### Objective

Capturar feedback de usuarios (thumbs up/down + comentario opcional) para identificar patrones de error y mejorar el sistema iterativamente.

### Solution enables

- Botones de feedback en cada mensaje (thumbs up/down)
- Modal de comentario opcional para thumbs down
- Almacenamiento en MongoDB con contexto completo (query, respuesta, SQL)
- Analytics para identificar tipos de error más frecuentes
- Feedback loop para ajustar few-shot examples y confidence thresholds

### Problems solved

| Current Problem | Impact | Solution |
|-----------------|--------|----------|
| No hay señal de calidad de respuestas | Sistema no mejora con uso | Feedback explícito de usuarios |
| Errores no se detectan automáticamente | Problemas se acumulan sin visibilidad | Thumbs down + categorización |
| Sin contexto de por qué falló | Difícil diagnosticar root cause | Almacenar query + respuesta + SQL |
| Mejora del sistema es manual y lenta | No hay feedback loop automatizado | Analytics + triggers para ajustes |

### Expected benefits

- **Para el usuario**: Sentimiento de ser escuchado, mejora visible del sistema
- **Para el negocio**: Trust metric mejorado, señal temprana de problemas
- **Para el sistema**: Datos para mejorar QuerySpec Builder, ajustar thresholds, agregar few-shot examples

### Success metrics

| Metric | Baseline | Target | How to measure |
|--------|----------|--------|----------------|
| Feedback submissions/week | 0 | 20+ | Count feedback documents in MongoDB |
| Thumbs up rate | N/A | > 80% | up_count / (up_count + down_count) |
| Comment rate (on thumbs down) | N/A | > 50% | down_with_comment / down_count |
| Time to review feedback | N/A | < 48h | Review timestamp - submission timestamp |

---

## Strategic Alignment

### Why this epic? (BRD Alignment)

**BRD use case**: UC-4 - Feedback de usuario

> "Error en respuesta → usuario indica 'pulgar abajo' → captura de texto adicional → Mejorar el sistema"
> — BRD.md, Sección 4: Casos de Uso

**BRD design principle**: #5 - Feedback continuo del usuario para mejora del sistema

> "Feedback continuo del usuario para mejora del sistema."
> — BRD.md, Sección 3.2: Principios de Diseño

**Direct connection**:
- Implementa el **feedback loop** fundamental para mejora continua
- Señal de calidad para **trust metric** (thumbs up rate)
- Contribuye indirectamente al **WAU**: usuarios ven mejoras → regresan
- Permite validar hipótesis de producto (¿qué features generan más value?)

**BRD Success Metrics Contribution**:

| BRD Metric | How HU5 Contributes |
|------------|---------------------|
| WAU (North Star) | Improved system quality → higher retention |
| Trust (implicit) | Thumbs up rate = leading indicator |
| TTI | Feedback identifies slow queries → optimization targets |

### How does it integrate? (Architecture Alignment)

**Components involved**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     EPIC-HU5 Architecture                        │
├──────────────┬─────────────────┬──────────────────┬─────────────┤
│  Web UI      │  Feedback       │   MongoDB        │  Analytics  │
│ Feedback     │   Service       │   feedback       │   (Future)  │
│ Buttons      │    (New)        │  collection      │             │
├──────────────┼─────────────────┼──────────────────┼─────────────┤
│ 1. Renders   │ 1. Validates    │ Stores:          │ Identifies  │
│    thumbs    │    payload      │ - rating         │ patterns:   │
│    buttons   │ 2. Enriches     │ - comment        │ - Most      │
│ 2. Captures  │    with context │ - context        │   problematic│
│    rating +  │    (query, SQL) │ - metadata       │   intents   │
│    comment   │ 3. Stores in    │                  │ - Common    │
│ 3. POSTs to  │    MongoDB      │                  │   error types│
│    /api/     │                 │                  │ - Improvement│
│    feedback  │                 │                  │   priorities │
└──────────────┴─────────────────┴──────────────────┴─────────────┘
```

**Integration with existing architecture**:

| Existing Component | Integration Point | HU5 Responsibility |
|-------------------|-------------------|-------------------|
| ChatMessage Component | Message rendering | Add FeedbackButtons to each message |
| MongoDB (session storage) | Database | Add feedback collection |
| Backend router | API | Add /api/feedback endpoints |
| Session Service | Context retrieval | Enrich feedback with query/response context |

**Technical dependencies**:

| Component | Status | Required for | Blocker? |
|-----------|--------|--------------|----------|
| ChatMessage Component | ✅ DONE | UI integration | No |
| MongoDB | ✅ DONE | Storage | No |
| Backend API structure | ✅ DONE | Endpoints | No |
| Session Service | ✅ DONE | Context enrichment | No |
| Feedback Service | ❌ NOT STARTED | Business logic | **YES** |
| FeedbackButtons Component | ❌ NOT STARTED | UI | **YES** |

**No blocking gaps** - All dependencies exist, needs implementation.

---

## Deliverables List

| # | Deliverable | File Path | Completion Criteria |
|---|-------------|-----------|---------------------|
| E1 | FeedbackButtons Component | `apps/web/src/components/FeedbackButtons/index.tsx` | Renders thumbs up/down |
| E2 | FeedbackModal Component | `apps/web/src/components/FeedbackButtons/FeedbackModal.tsx` | Modal for comment entry |
| E3 | Feedback Router | `apps/backend/src/routers/feedback.py` | POST /api/feedback endpoint |
| E4 | Feedback Service | `apps/backend/src/services/feedback_service.py` | Validates, enriches, stores |
| E5 | Feedback Model | `apps/backend/src/models/feedback.py` | MongoDB schema definition |
| E6 | ChatMessage Integration | `apps/web/src/components/ChatMessage/index.tsx` | Integrate FeedbackButtons |
| E7 | Backend Tests | `apps/backend/tests/unit/test_feedback_service.py` | 15+ tests |
| E8 | Frontend Tests | `apps/web/src/components/FeedbackButtons/FeedbackButtons.test.tsx` | 10+ tests |

---

## Acceptance Criteria

### Functional

- [ ] **CA-01**: Thumbs up/down buttons appear on every assistant message
- [ ] **CA-02**: Clicking thumbs up submits feedback (no modal)
- [ ] **CA-03**: Clicking thumbs down opens modal for optional comment
- [ ] **CA-04**: User can submit comment or skip (both valid)
- [ ] **CA-05**: Feedback stored in MongoDB with message_id, rating, comment
- [ ] **CA-06**: Feedback enriched with context (original query, response, SQL)
- [ ] **CA-07**: User can only submit feedback once per message (button disabled after submit)
- [ ] **CA-08**: Feedback includes session_id for conversation tracking

### Non-Functional

- [ ] **CA-09**: Feedback submission completes in < 1 segundo
- [ ] **CA-10**: Modal is accessible (keyboard navigation, screen reader)
- [ ] **CA-11**: Feedback stored with timestamp for time-series analysis
- [ ] **CA-12**: MongoDB schema includes indexes on: user_id, session_id, timestamp
- [ ] **CA-13**: Feedback endpoint handles 100 req/sec (load test)

---

## Implementation Phases

### Phase 1: Backend Feedback Service (1 día)

**Deliverables**: E3, E4, E5

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `apps/backend/src/routers/feedback.py` | CREATE | API endpoints |
| `apps/backend/src/services/feedback_service.py` | CREATE | Business logic |
| `apps/backend/src/models/feedback.py` | CREATE | MongoDB schema |
| `apps/backend/tests/unit/test_feedback_service.py` | CREATE | Unit tests |
| `apps/backend/src/main.py` | MODIFY | Register feedback router |

**Sub-agent delegation**:

```yaml
Agent: plan-architect
Task: Design Feedback Service architecture and MongoDB schema
Input: This mini-PRD Phase 1
Output: Detailed schema with indexes and API contract
```

```yaml
Agent: code-implementer
Task: Implement Feedback Service with TDD
Input: plan-architect output + this mini-PRD
Output: Working Feedback Service with 15+ tests passing
```

**Acceptance Criteria (Phase 1)**:
- [ ] POST /api/feedback endpoint works
- [ ] Feedback stored in MongoDB with enriched context
- [ ] Unit tests pass (15+ tests)
- [ ] Indexes created on user_id, session_id, timestamp

---

### Phase 2: Frontend FeedbackButtons Component (1 día)

**Deliverables**: E1, E2, E6

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/components/FeedbackButtons/index.tsx` | CREATE | Thumbs buttons |
| `apps/web/src/components/FeedbackButtons/FeedbackModal.tsx` | CREATE | Comment modal |
| `apps/web/src/components/FeedbackButtons/types.ts` | CREATE | TypeScript types |
| `apps/web/src/components/ChatMessage/index.tsx` | MODIFY | Integrate FeedbackButtons |
| `apps/web/src/components/FeedbackButtons/FeedbackButtons.test.tsx` | CREATE | Frontend tests |

**Sub-agent delegation**:

```yaml
Agent: code-implementer
Task: Implement FeedbackButtons component with accessibility
Input: Feedback API contract + this mini-PRD
Output: Working React component with 10+ tests passing
```

**Acceptance Criteria (Phase 2)**:
- [ ] Thumbs buttons render on each message
- [ ] Thumbs down opens modal
- [ ] Modal submits comment to API
- [ ] Button disabled after submission
- [ ] Component tests pass (10+ tests)

---

### Phase 3: Integration & E2E Testing (0.5 días)

**Deliverables**: E7, E8

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `apps/backend/tests/integration/test_feedback_flow.py` | CREATE | E2E test full flow |
| `apps/web/tests/e2e/feedback.spec.ts` | CREATE | Playwright E2E test |

**Sub-agent delegation**:

```yaml
Agent: test-runner
Task: Execute E2E tests for feedback flow
Input: All phases completed + validation commands
Output: Test report with pass/fail status
```

**Acceptance Criteria (Phase 3)**:
- [ ] E2E test: Submit thumbs down → modal → comment → verify MongoDB
- [ ] E2E test: Submit thumbs up → verify MongoDB (no comment)
- [ ] E2E test: Button disables after submission

---

### Phase 4: Analytics Foundation (Future - v1.2+)

**Deliverables**: Analytics queries (not in v1.0 scope)

**Files to create/modify**:

| File | Action | Purpose |
|------|--------|---------|
| `apps/backend/src/services/feedback_analytics.py` | CREATE | Pattern detection |
| `apps/backend/src/scripts/generate_feedback_report.py` | CREATE | Weekly report |

**Out of scope for v1.0** - foundation (data collection) only

---

## Definition of Done

| Criterion | Verification Command | Pass Condition | Status |
|-----------|---------------------|----------------|--------|
| Backend tests | `pytest tests/unit/test_feedback_service.py -v` | 15+ passing | ⚠️ PENDING |
| Frontend tests | `cd apps/web && pnpm test FeedbackButtons` | 10+ passing | ⚠️ PENDING |
| Integration test | `pytest tests/integration/test_feedback_flow.py` | E2E passing | ⚠️ PENDING |
| Lint (backend) | `ruff check src/` | 0 errors | ⚠️ PENDING |
| Lint (frontend) | `cd apps/web && pnpm lint` | 0 errors | ⚠️ PENDING |
| Accessibility | `axe-core` scan on FeedbackModal | WCAG 2.1 AA | ⚠️ PENDING |
| MongoDB storage | Submit feedback, check MongoDB | Document exists | ⚠️ PENDING |
| Load test | `locust` 100 req/sec | < 1s p95 | ⚠️ PENDING |

---

## Risks and Mitigation

| Risk | Prob | Impact | Mitigation |
|------|------|--------|------------|
| Low submission rate | Media | Alta | Make thumbs buttons prominent, incentivize with "Help improve" messaging |
| Spam submissions | Baja | Media | Rate limit by user_id + session_id, flag duplicates |
| MongoDB storage growth | Media | Baja | Set TTL for old feedback (1 year), archive to S3 |
| Comment toxicity | Baja | Media | Add content filter, moderate flagged comments |
| Context enrichment failure | Baja | Alta | Graceful degradation: store rating even if context missing |

---

## References

| Document | Relevant Section |
|----------|------------------|
| [BRD.md](../BRD.md) | Section 3.2: Design Principles (#5 - Feedback continuo) |
| [BRD.md](../BRD.md) | Section 4: Use Cases (UC-4 - Feedback de usuario) |
| [PRD.md](../product/PRD.md) | HU5: Sistema Feedback |
| [architecture/OPERATIONS.md](../architecture/OPERATIONS.md) | Metrics and observability |

---

## Notes

- **Effort estimate**: 2.5 days (1 backend + 1 frontend + 0.5 testing)
- **No blockers** - all dependencies exist, straightforward implementation
- MongoDB collection `feedback` separate from `conversations` for clean separation
- Future analytics (v1.2+) will use feedback data to:
  - Identify most problematic intent types
  - Find common error patterns (e.g., "date parsing always fails")
  - Prioritize QuerySpec Builder improvements
  - Adjust confidence thresholds based on false positives/negatives
- Consider adding "Was this helpful?" as neutral option (3-point scale)
- Thumbs up can trigger celebration animation (micro-interaction)
- For v1.0, focus on **data collection** - analytics is Phase 4 (future)
- Privacy consideration: ensure user_id is anonymized in exports/reports

**Next Steps**:
1. Plan-architect designs Feedback Service schema and indexes
2. Code-implementer implements backend (Phase 1)
3. Code-implementer implements frontend (Phase 2)
4. Test-runner validates E2E flow
5. Deploy and monitor submission rate (target: 20+ submissions/week)
