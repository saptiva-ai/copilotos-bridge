# Delegation Matrix

> Which agent to invoke for each task type.

## Agent Catalog

| Agent | Model | Specialization | Tools |
|-------|-------|----------------|-------|
| `prd-architect` | sonnet | Generate mini-PRDs from BRD | Read, Write, Grep, Glob |
| `plan-architect` | sonnet | Design implementation plans | Read, Grep, Glob, LSP, TodoWrite |
| `software-developer` | opus | TDD, self-correction, SOLID | All tools |
| `code-reviewer` | sonnet | Review bugs, security, conventions | Read, Grep, Glob, LSP |
| `test-runner` | sonnet | Execute tests with MCP, analysis | Bash, Read, Grep |
| `doc-sync` | sonnet | Sync docs with code changes | Read, Edit, Grep, Glob, Bash |
| `dev-validator` | haiku | Fast validation (<30s) | Bash, Read, Grep |
| `infra-doctor` | haiku | Docker/service diagnostics | Bash, Read, Grep |
| `repo-scout` | haiku | Map repo structure | Read, Glob, Grep, Bash, LSP |

## Task → Agent Routing

### Strategic Tasks (Planning & Requirements)

| Task Pattern | Agent | Notes |
|--------------|-------|-------|
| "Create PRD for..." | `prd-architect` | From BRD/requirements |
| "Decompose epic HUx" | `prd-architect` | Mini-PRD generation |
| "Plan implementation of..." | `plan-architect` | Architecture decisions |
| "Design approach for..." | `plan-architect` | Multi-file changes |

### Tactical Tasks (Implementation)

| Task Pattern | Agent | Notes |
|--------------|-------|-------|
| "Implement feature X" | `software-developer` | TDD with self-correction |
| "Fix bug in..." | `software-developer` | Includes test updates |
| "Add endpoint for..." | `software-developer` | Full stack implementation |
| "Review PR/changes" | `code-reviewer` | Security + conventions |
| "Check code quality" | `code-reviewer` | SOLID + patterns |

### Operational Tasks (Execution)

| Task Pattern | Agent | Notes |
|--------------|-------|-------|
| "Run tests for..." | `test-runner` | Full test suite |
| "Quick validation" | `dev-validator` | Fast feedback (<30s) |
| "Check services" | `infra-doctor` | Docker health |
| "Map the codebase" | `repo-scout` | Structure discovery |
| "Update docs for..." | `doc-sync` | After implementation |

## Model Selection Rationale

| Model | When to Use | Cost/Quality |
|-------|-------------|--------------|
| **Sonnet** | Code generation, analysis, planning | High quality, moderate cost |
| **Haiku** | Simple I/O, validation, diagnostics | Fast, low cost |

## Direct Execution vs Delegation

### Execute Directly (No Agent)

- Single-line fixes (typos, obvious bugs)
- Reading specific files
- Simple bash commands
- Answering questions about code

### Delegate to Agent

- Multi-file changes
- TDD implementation cycles
- Complex analysis requiring focus
- Tasks needing specialized tools

## Escalation Path

```
Agent fails/blocks → Main session analyzes → User decides

Example:
  test-runner (fails 3x) → analyze failure pattern → suggest fix to user
```
