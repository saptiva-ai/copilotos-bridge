# Task() Usage Guide - Deterministic Agent Invocation

> **CRITICAL**: This document explains how to use `Task()` correctly with custom agents for deterministic execution.

## Overview

Custom agents in `.claude/agents/*.md` **ARE valid subagents** that can be invoked using `Task()` with `subagent_type`.

## Deterministic Pattern

**Always use this pattern:**

```python
Task(
    subagent_type="<agent-name>",
    prompt=f"Feature description: $ARGUMENTS"
)
```

## Available Custom Agents

| Agent | Model | Use Case | Example |
|-------|-------|----------|---------|
| `prd-architect` | sonnet | Generate mini-PRDs | `Task(subagent_type="prd-architect", prompt="Feature description: HU5")` |
| `plan-architect` | sonnet | Create implementation plans | `Task(subagent_type="plan-architect", prompt="Feature description: plan auth system")` |
| `software-developer` | sonnet | TDD implementation | `Task(subagent_type="software-developer", prompt="Feature description: implement CA-01")` |
| `code-reviewer` | sonnet | Code review | `Task(subagent_type="code-reviewer", prompt="Feature description: review PR")` |
| `test-runner` | sonnet | Run tests | `Task(subagent_type="test-runner", prompt="Feature description: test feedback_router")` |
| `doc-sync` | haiku | Sync documentation | `Task(subagent_type="doc-sync", prompt="Feature description: update docs for HU5")` |
| `dev-validator` | haiku | Quick validation | `Task(subagent_type="dev-validator", prompt="Feature description: validate test_ca01")` |
| `infra-doctor` | haiku | Infrastructure diagnostics | `Task(subagent_type="infra-doctor", prompt="Feature description: check services")` |
| `repo-scout` | haiku | Map repository | `Task(subagent_type="repo-scout", prompt="Feature description: map codebase")` |

## Pattern: Feature Description

**Always start prompts with "Feature description:" for consistency:**

```python
# ✅ CORRECT
Task(subagent_type="software-developer", prompt="Feature description: implement user authentication")

# ❌ WRONG (inconsistent)
Task(subagent_type="software-developer", prompt="implement user authentication")
Task(subagent_type="software-developer", prompt="Task: implement user authentication")
```

## Pattern: Using $ARGUMENTS

When creating commands, use `$ARGUMENTS` to pass user input:

```python
# In command definition
Task(
    subagent_type="software-developer",
    prompt=f"Feature description: $ARGUMENTS"
)

# User invokes: /do implement CA-01
# Becomes: Task(subagent_type="software-developer", prompt="Feature description: implement CA-01")
```

## Pattern: Full Context

For complex tasks, include context in the prompt:

```python
Task(
    subagent_type="plan-architect",
    prompt=f"""
- Mini-PRD: docs/context/product/EPICS/EPIC-HU5.md
- BRD: docs/context/product/BRD.md
- Architecture: docs/architecture/
Create implementation plan following .claude/skills/plan/template.md
"""
)
```

## Built-in Agents vs Custom Agents

### Built-in Agents (Claude Code)

These are built into Claude Code and don't need `subagent_type`:

- `Plan` - Planning tasks
- `Explore` - Code exploration
- `Code` - Code generation
- `Review` - Code review

**Usage:**
```python
# Built-in agents use different syntax
Plan("What's missing in HU5?")
Explore("Find authentication patterns")
```

### Custom Agents (Your Agents)

These are defined in `.claude/agents/*.md` and **MUST** use `Task()`:

- `prd-architect`
- `plan-architect`
- `software-developer`
- `code-reviewer`
- `test-runner`
- `doc-sync`
- `dev-validator`
- `infra-doctor`
- `repo-scout`

**Usage:**
```python
# Custom agents use Task() with subagent_type
Task(subagent_type="software-developer", prompt="Feature description: implement CA-01")
Task(subagent_type="test-runner", prompt="Feature description: run tests")
```

## Examples

### Example 1: Simple Delegation

```python
# User: /do implement CA-01
Task(
    subagent_type="software-developer",
    prompt="Feature description: implement CA-01"
)
```

### Example 2: With Context

```python
# User: /do plan auth system
Task(
    subagent_type="plan-architect",
    prompt=f"""
Feature description: plan auth system

Context:
- Mini-PRD: docs/context/EPICS/EPIC-HU5.md
- Architecture: docs/context/architecture/auth.md

Create implementation plan.
"""
)
```

### Example 3: Chained Tasks

```python
# Step 1: Generate PRD
prd_result = Task(
    subagent_type="prd-architect",
    prompt="Feature description: HU5"
)

# Step 2: Create plan
plan_result = Task(
    subagent_type="plan-architect",
    prompt=f"Feature description: plan implementation for HU5"
)

# Step 3: Implement
impl_result = Task(
    subagent_type="software-developer",
    prompt=f"Feature description: implement according to plan"
)

# Step 4: Test
test_result = Task(
    subagent_type="test-runner",
    prompt=f"Feature description: run tests for HU5"
)
```

## Error Handling

If an agent fails:

1. **Check agent exists**: Verify `.claude/agents/<agent-name>.md` exists
2. **Check prompt format**: Ensure it starts with "Feature description:"
3. **Check context**: Verify referenced files exist
4. **Retry with more context**: Add more details to prompt

## Best Practices

1. ✅ **Always use "Feature description:" prefix**
2. ✅ **Use $ARGUMENTS for user input**
3. ✅ **Include context for complex tasks**
4. ✅ **Use appropriate agent for task type**
5. ❌ **Don't nest agents** (subagents can't spawn subagents)
6. ❌ **Don't mix built-in and custom agent syntax**

## Troubleshooting

### Agent not found
```
Error: Agent "xyz" not found
```
**Solution**: Check `.claude/agents/xyz.md` exists

### Agent returns unexpected result
**Solution**: Check agent's `.md` file for expected output format

### Task() fails silently
**Solution**: Verify prompt format and agent name spelling

## References

- `.claude/skills/orchestration-playbooks/delegation-matrix.md` - Agent catalog
- `.claude/rules/60_agent_hygiene.md` - Agent hygiene rules
- `.claude/commands/do.md` - Unified command router

