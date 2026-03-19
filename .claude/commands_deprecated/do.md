# /do - Comando Unificado

> Un solo punto de entrada. El sistema rutea al agente apropiado.

## Uso

```
/do <tarea>
```

## Ejemplos

```bash
/do HU5                      # Generar PRD → prd-architect
/do plan auth system         # Diseñar plan → plan-architect
/do implement CA-01          # Implementar → software-developer
/do fix tests                # Arreglar → software-developer
/do review                   # Code review → code-reviewer
/do check                    # Quick validation → dev-validator
/do test feedback_router     # Run tests → test-runner
/do health                   # Diagnóstico → infra-doctor
/do map                      # Explorar repo → repo-scout
```

## Routing Logic

```
┌─────────────────────────────────────────────────────────────────┐
│                         /do <tarea>                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   Classify Task     │
                  │   (orchestration)   │
                  └──────────┬──────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   STRATEGIC     │ │    TACTICAL     │ │   OPERATIONAL   │
│                 │ │                 │ │                 │
│ • HU*, EPIC*    │ │ • fix *         │ │ • check         │
│ • plan *        │ │ • implement *   │ │ • test *        │
│ • design *      │ │ • review        │ │ • health        │
│ • architecture  │ │ • add *, update │ │ • map           │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
   prd-architect      software-dev         test-runner
   plan-architect     code-reviewer        dev-validator
                      doc-sync             infra-doctor
                                           repo-scout
```

## Task → Agent Mapping

### Strategic (Planning & Requirements)

| Pattern | Agent | Model |
|---------|-------|-------|
| `HU*`, `EPIC*`, `prd *` | `prd-architect` | sonnet |
| `plan *`, `design *` | `plan-architect` | sonnet |

### Tactical (Implementation)

| Pattern | Agent | Model |
|---------|-------|-------|
| `implement *`, `fix *`, `add *` | `software-developer` | sonnet |
| `review`, `review pr` | `code-reviewer` | sonnet |
| `docs *`, `update docs` | `doc-sync` | haiku |

### Operational (Execution)

| Pattern | Agent | Model |
|---------|-------|-------|
| `test *`, `run tests` | `test-runner` | sonnet |
| `check`, `validate` | `dev-validator` | haiku |
| `health`, `diagnose` | `infra-doctor` | haiku |
| `map`, `explore` | `repo-scout` | haiku |

## Execution (Deterministic Flow)

When `/do` is invoked with `$ARGUMENTS`:

1. **Parse** `$ARGUMENTS` to classify task type
2. **Select** the appropriate agent from routing table below
3. **Invoke** via Task tool with deterministic pattern:
   ```python
   Task(
       subagent_type="<agent-name>",
       prompt="Feature description: $ARGUMENTS"
   )
   ```
4. **Return** the result to user

### Deterministic Invocation Pattern

**CRITICAL**: Always use this exact pattern for consistency:

```python
# Strategic tasks
Task(subagent_type="prd-architect", prompt=f"Feature description: {args}")
Task(subagent_type="plan-architect", prompt=f"Feature description: {args}")

# Tactical tasks  
Task(subagent_type="software-developer", prompt=f"Feature description: {args}")
Task(subagent_type="code-reviewer", prompt=f"Feature description: {args}")
Task(subagent_type="doc-sync", prompt=f"Feature description: {args}")

# Operational tasks
Task(subagent_type="test-runner", prompt=f"Feature description: {args}")
Task(subagent_type="dev-validator", prompt=f"Feature description: {args}")
Task(subagent_type="infra-doctor", prompt=f"Feature description: {args}")
Task(subagent_type="repo-scout", prompt=f"Feature description: {args}")
```

### Examples with $ARGUMENTS

```python
# User: /do HU5
Task(subagent_type="prd-architect", prompt="Feature description: HU5")

# User: /do plan auth system
Task(subagent_type="plan-architect", prompt="Feature description: plan auth system")

# User: /do implement CA-01
Task(subagent_type="software-developer", prompt="Feature description: implement CA-01")

# User: /do test feedback_router
Task(subagent_type="test-runner", prompt="Feature description: test feedback_router")
```

## Escalation

```
Agent blocked/fails 3x → Main session analyzes → User decides

Example:
  test-runner (fails) → analyze failure → suggest fix → user confirms
```

## Shortcuts

| Shortcut | Equivale a |
|----------|------------|
| `/do` (sin args) | `/do check` (quick validation) |
| `/do ?` | Show orchestration-playbooks/SKILL.md |

## Related Commands

| Command | Use Case |
|---------|----------|
| `/quick-checks` | Run standard validation suite |
| `/dev-up` | Start development stack |
| `/repo-map` | Generate repository map |
| `/infra-doctor` | Diagnose infrastructure |

## References

- `.claude/skills/orchestration-playbooks/SKILL.md`
- `.claude/skills/orchestration-playbooks/delegation-matrix.md`
- `.claude/rules/60_agent_hygiene.md`
