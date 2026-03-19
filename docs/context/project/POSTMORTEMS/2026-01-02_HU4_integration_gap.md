# Post-Mortem: HU4 RAG Integration Gap

**Date**: 2 January 2026
**Severity**: Medium (Feature not working despite being marked DONE)
**Status**: Resolved

---

## Executive Summary

HU4 (RAG con Glosario) was marked as "✅ DONE" on 28 Dec 2025, but the feature **was not functional**. Users asking definition questions ("¿Qué es ICOR?") received generic LLM responses without RAG grounding. The root cause was a missing handler in `main.py` that should route `BANK_KNOWLEDGE` intent to the Weaviate ontology service.

---

## Timeline

| Date | Event |
|------|-------|
| 26 Dec 2025 | Phase 1 (ETL) completed - 3,526 terms loaded to Weaviate |
| 27 Dec 2025 | Phase 2 (Knowledge Synthesizer) marked completed |
| 28 Dec 2025 | Phase 3 (Router Integration) marked completed |
| 28 Dec 2025 | Phase 4 (Manual Validation) marked completed with 98% accuracy |
| 28 Dec 2025 | **EPIC marked as DONE** |
| 2 Jan 2026 | User reports RAG not working for glossary queries |
| 2 Jan 2026 | Investigation reveals missing handler in main.py |
| 2 Jan 2026 | Phase 5 fix implemented |

---

## Root Cause Analysis

### What Failed

1. **Files documented as created never existed**:
   - `agents/knowledge_synthesizer.py` → NOT FOUND
   - `services/ontology_service.py` → NOT FOUND
   - `router/orchestrator.py` → EXISTS but at different path and without BANK_KNOWLEDGE handler
   - `tests/unit/test_knowledge_synthesizer.py` → NOT FOUND
   - `tests/integration/test_ontology_rag.py` → NOT FOUND

2. **Definition of Done was falsified or negligently verified**:
   - EPIC claimed "25/25 tests passing" for `test_knowledge_synthesizer.py`
   - EPIC claimed "10/10 tests passing" for `test_ontology_rag.py`
   - **These test files never existed**

3. **Manual validation (98% accuracy) impossible without working integration**:
   - If the handler didn't exist, how were 50 queries validated?
   - Either validation was performed differently than documented, or results were fabricated

4. **Intent classification worked, but routing was broken**:
   - `NlpIntentService.classify()` correctly identified `BANK_KNOWLEDGE` (0.95 confidence)
   - But no code in `main.py` acted on this classification
   - Queries fell through to SQL analytics pipeline

### Contributing Factors

| Factor | Impact | How it happened |
|--------|--------|-----------------|
| **No E2E smoke test** | High | No automated test that actually queried the API with "¿Qué es IMOR?" |
| **Documentation-driven completion** | High | EPIC marked DONE based on documented plan, not actual code |
| **No code review for integration** | High | Handler block in main.py was never written or reviewed |
| **Siloed testing** | Medium | WeaviateOntologyService was unit-tested in isolation, not integrated |
| **Validation commands not executed** | High | Commands in EPIC were copy-pasted, not run |

---

## What Should Have Been Caught

### Checkpoint 1: File Existence Verification
**When**: Before marking Phase 2 complete
**What**: Verify all documented files exist
```bash
# This would have failed immediately
ls -la plugins/bank-advisor-private/src/agents/knowledge_synthesizer.py
# No such file or directory
```

### Checkpoint 2: Test Execution
**When**: Before marking Phase 3 complete
**What**: Run the documented test commands
```bash
# This would have failed immediately
pytest tests/unit/test_knowledge_synthesizer.py -v
# FileNotFoundError
```

### Checkpoint 3: E2E Smoke Test
**When**: Before marking EPIC as DONE
**What**: Actually query the API and verify response format
```bash
curl -X POST http://localhost:8002/api/query \
  -d '{"query": "¿Qué es IMOR?"}' | jq '.type'

# Expected: "knowledge"
# Actual: "clarification" or SQL response (no type=knowledge)
```

### Checkpoint 4: Response Format Validation
**When**: During manual validation
**What**: Verify responses include `source_refs` as documented
```bash
curl -X POST http://localhost:8002/api/query \
  -d '{"query": "¿Qué es IMOR?"}' | jq '.source_refs'

# Expected: ["pdf:Glosario_CUB.pdf#p12", ...]
# Actual: null or missing field
```

---

## Human-in-the-Loop Requirements

### Mandatory Checkpoints for EPIC Completion

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPIC COMPLETION CHECKLIST                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ 1. FILE VERIFICATION (Automated + Manual)                    │
│     Run: ls -la <each file in Target Files table>               │
│     Evidence: Screenshot or CI log showing files exist          │
│                                                                  │
│  □ 2. TEST EXECUTION (Automated + Manual Review)                │
│     Run: <each command in Validation Commands>                  │
│     Evidence: CI pipeline output or screenshot of passing tests │
│                                                                  │
│  □ 3. E2E SMOKE TEST (Manual - REQUIRED)                        │
│     Perform: Query via actual UI or API                         │
│     Verify: Response matches Expected Output in EPIC            │
│     Evidence: Screenshot of actual response                     │
│                                                                  │
│  □ 4. CODE REVIEW (Human - REQUIRED)                            │
│     Review: All files in Target Files table                     │
│     Verify: Integration points are connected                    │
│     Evidence: PR approval with explicit integration checklist   │
│                                                                  │
│  □ 5. DEMO TO STAKEHOLDER (Human - REQUIRED)                    │
│     Demo: Live demonstration of feature                         │
│     Verify: Stakeholder confirms expected behavior              │
│     Evidence: Recorded demo or sign-off email                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Process Changes Required

| Current Process | Problem | Proposed Change |
|-----------------|---------|-----------------|
| EPIC author marks DONE | Self-attestation allows errors | **Require peer verification** |
| Definition of Done is manual | No enforcement | **Automate DoD checks in CI** |
| Tests documented but not run | No verification | **CI must run documented commands** |
| Manual validation self-reported | No evidence | **Require recorded demo** |

---

## Prevention Measures

### 1. Automated EPIC Validation Script

```bash
#!/bin/bash
# scripts/validate_epic.sh
# Run before marking any EPIC as DONE

EPIC_FILE=$1

# Extract Target Files from EPIC markdown
grep -E "^\| .+ CREATE \| " $EPIC_FILE | awk -F'|' '{print $3}' | tr -d ' `' | while read file; do
    if [ ! -f "$file" ]; then
        echo "❌ MISSING: $file"
        exit 1
    fi
    echo "✅ EXISTS: $file"
done

# Extract and run Validation Commands
# ... (parse and execute each command)
```

### 2. CI/CD Integration Test

Add to `.github/workflows/epic-validation.yml`:
```yaml
name: EPIC Validation
on:
  pull_request:
    paths:
      - 'docs/context/EPICS/*.md'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Verify Target Files Exist
        run: |
          ./scripts/validate_epic.sh docs/context/EPICS/EPIC-*.md

      - name: Run Validation Commands
        run: |
          # Parse and execute validation commands from EPIC
```

### 3. Definition of Done Automation

For HU4 specifically, add to test suite:
```python
# tests/e2e/test_hu4_rag.py
@pytest.mark.e2e
async def test_knowledge_query_returns_rag_response():
    """E2E: Verify RAG responses include required fields."""
    response = await client.post("/api/query", json={"query": "¿Qué es IMOR?"})

    assert response.json()["type"] == "knowledge"
    assert "source_refs" in response.json()
    assert len(response.json()["source_refs"]) > 0
```

### 4. Mandatory Demo Requirement

Add to EPIC template:
```markdown
## Demo Evidence (Required)

- [ ] Demo video uploaded to: `docs/demos/EPIC-XXX_demo.mp4`
- [ ] Stakeholder sign-off: @[name] on [date]
- [ ] Screenshot of working feature: `docs/demos/EPIC-XXX_screenshot.png`
```

---

## Lessons Learned

1. **Trust but verify**: Documentation can diverge from reality
2. **Self-attestation is insufficient**: Require peer verification for completion
3. **E2E tests are non-negotiable**: Unit tests alone don't prove integration works
4. **Run the documented commands**: Copy-paste without execution is dangerous
5. **Demo or it didn't happen**: Recorded evidence prevents false positives

---

## Action Items

| Action | Owner | Due | Status |
|--------|-------|-----|--------|
| Fix HU4 integration (Phase 5) | Claude | 2 Jan 2026 | ✅ Done |
| Add E2E test for RAG queries | TBD | Next sprint | Pending |
| Create EPIC validation script | TBD | Next sprint | Pending |
| Add demo requirement to EPIC template | TBD | Next sprint | Pending |
| Review all "DONE" EPICs for similar gaps | TBD | Next sprint | Pending |
