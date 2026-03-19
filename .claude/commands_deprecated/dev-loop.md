# /dev-loop - Development Loop with Self-Correction

Orchestrate TDD implementation with incremental validation.

## Usage

```
/dev-loop <target>
```

### Examples

```
/dev-loop EPIC-HU5              # Full epic implementation
/dev-loop CA-06                 # Single acceptance criteria
/dev-loop fix feedback tests    # Fix specific tests
```

## How It Works

> **IMPORTANTE**: Los custom agents (.claude/agents/*.md) son PROMPTS, no subagent_types.
> El loop usa agentes built-in + contexto de los custom agents.

```
┌────────────────────────────────────────────────────────────────────┐
│                    /dev-loop EXECUTION MODEL                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SESIÓN PRINCIPAL actúa como orquestador:                          │
│                                                                     │
│  1. CARGAR CONTEXTO                                                 │
│     ├─ Read .claude/agents/software-developer.md (instrucciones)   │
|     ├─ Read docs/context/product/EPICS/EPIC-{target}.md (requisitos)       │
│     └─ Read relevant source files (código existente)               │
│                                                                     │
│  2. LOOP DE IMPLEMENTACIÓN (max 10 iteraciones)                    │
│     │                                                               │
│     ├─► PLAN: Task(subagent_type="plan-architect",                 │
│     │            prompt="Feature description: Identify next incomplete CA")
│     │      └─ Returns: CA-XX to implement                          │
│     │                                                               │
│     ├─► IMPLEMENT: Task(subagent_type="software-developer",        │
│     │                  prompt="Feature description: Implement CA-XX")
│     │      └─ Agent follows TDD: Test first, then implementation  │
│     │                                                               │
│     ├─► VALIDATE: Task(subagent_type="test-runner",                 │
│     │               prompt="Feature description: Run tests for CA-XX")
│     │      └─ Returns: PASS | FAIL + errors                        │
│     │                                                               │
│     ├─► Si FAIL:                                                    │
│     │      └─ Analizar error                                        │
│     │      └─ Corregir (max 3 retries por CA)                      │
│     │      └─ Re-validate                                           │
│     │                                                               │
│     └─► Si PASS: Marcar CA como done, continuar                    │
│                                                                     │
│  3. REPORT                                                          │
│     └─ Summary de CAs completados, bloqueados, tiempo              │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Execution Flow (Real)

```
Usuario: /dev-loop HU5
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SESIÓN PRINCIPAL                                                    │
│                                                                      │
│  Step 1: Read context                                                │
│    • .claude/agents/software-developer.md                           │
│    • docs/context/product/EPICS/EPIC-HU5.md                                 │
│    • Current test status via pytest discovery                       │
│                                                                      │
│  Step 2: Identify gap                                                │
│    • Task(subagent_type="plan-architect",                           │
│          prompt="Feature description: What's missing in HU5?")      │
│    • Result: "CA-06 context enrichment missing"                     │
│                                                                      │
│  Step 3: Implement CA-06                                             │
│    • Task(subagent_type="software-developer",                      │
│          prompt="Feature description: implement CA-06")            │
│    • Agent creates test first (TDD red)                             │
│    • Agent implements service (TDD green)                          │
│                                                                      │
│  Step 4: Validate                                                    │
│    • Task(subagent_type="test-runner",                              │
│          prompt="Feature description: Run feedback tests")          │
│    • If fail → fix → revalidate (max 3x)                           │
│                                                                      │
│  Step 5: Continue or Report                                          │
│    • If more CAs → repeat from Step 2                               │
│    • If blocked → report and ask user                               │
│    • If done → summary                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Insight (Updated: Deterministic Flow)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DETERMINISTIC APPROACH: Use Task() with subagent_type              │
│                                                                      │
│  Los custom agents (.claude/agents/*.md) SON subagents válidos     │
│  que se invocan con Task(subagent_type="agent-name", ...)          │
│                                                                      │
│  RESULTADO: El loop usa Task() determinísticamente:                │
│             1. Task(subagent_type="plan-architect", ...)           │
│             2. Task(subagent_type="software-developer", ...)        │
│             3. Task(subagent_type="test-runner", ...)              │
│             4. Itera hasta completar                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Circuit Breakers

| Breaker | Threshold | Action |
|---------|-----------|--------|
| Per-CA retries | 3 | Skip CA, continue with next |
| Total iterations | 10 | Pause and report partial |
| Consecutive failures | 3 | Stop and escalate to user |

## Built-in Agents Used

| Task | Built-in Agent | Purpose |
|------|----------------|---------|
| Gap analysis | `Plan` | Identify incomplete CAs |
| Test execution | `test-runner` | Run pytest with analysis |
| Exploration | `Explore` | Find relevant code patterns |

## Custom Agent Context

| File | Used As |
|------|---------|
| `.claude/agents/software-developer.md` | Instructions for TDD |
| `.claude/agents/dev-validator.md` | Quick validation rules |
| `.claude/agents/code-reviewer.md` | Review checklist |

## Example Session

```
> /dev-loop HU5

## Starting dev-loop for EPIC-HU5

### Loading Context
- Mini-PRD: docs/context/product/EPICS/EPIC-HU5.md
- Instructions: .claude/agents/software-developer.md
- Current tests: 42 passing, 0 failing

### Gap Analysis (via Plan agent)
Missing:
- CA-06: Context enrichment service
- Frontend tests

### Implementing CA-06

**Step 1: Write test (RED)**
Creating: apps/backend/tests/unit/test_feedback_service.py

**Step 2: Run validation**
Result: FAIL (expected - no implementation yet)

**Step 3: Implement (GREEN)**
Creating: apps/backend/src/services/feedback_service.py

**Step 4: Run validation**
Result: PASS ✓

### Summary

| Metric | Value |
|--------|-------|
| CAs Completed | 1 |
| Time | 4m 23s |
| Self-corrections | 0 |

### Next Steps
- Continue with frontend tests: `/dev-loop frontend-tests`
- Full validation: `/test HU5`
```

## References

- `.claude/skills/orchestration-playbooks/workflow.md`
- `.claude/agents/software-developer.md`
- `.claude/rules/60_agent_hygiene.md`
