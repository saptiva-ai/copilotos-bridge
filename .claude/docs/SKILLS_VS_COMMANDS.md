# Skills vs Commands: Architectural Distinction

## TL;DR

| Aspect | Skills | Commands |
|--------|--------|----------|
| **What** | Reusable knowledge + procedures | Manual invocation sequences |
| **When** | Dynamically loaded when relevant | Explicitly invoked by user |
| **How** | Declared in agent `skills:` | `/command` in conversation |
| **Scope** | Context across session | One-time execution |

## Skills: "How We Do Things Here"

Skills are **discoverable knowledge modules** that Claude Code can load when relevant.

### Characteristics

- **Auto-discoverable**: Claude reads them when agent has `skills: [name]`
- **Declarative context**: Define conventions, patterns, constraints
- **Include scripts**: Zero-context execution (only output uses tokens)
- **Progressive disclosure**: SKILL.md → references/ → scripts/

### Structure

```
.claude/skills/<name>/
├── SKILL.md           # Main entry (< 500 lines)
├── references/        # Detailed docs (loaded on demand)
│   ├── patterns.md
│   └── examples.md
└── scripts/           # Deterministic execution
    └── validate.sh
```

### When to Use

- Teaching Claude "how things work in this repo"
- Encoding team conventions
- Providing reference material for decisions
- Automating deterministic checks

### Example: `code` skill

```yaml
# In agent definition
skills: [code, test, explore]
```

```markdown
# .claude/skills/code/SKILL.md
---
name: code
description: Write code following project conventions
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, LSP]
---

## Instructions
1. Follow Clean Architecture layers
2. Apply SOLID principles
3. Run guardrails before commit

## References
- conventions.md - Naming, style
- architecture.md - Layers, dependencies
```

## Commands: "Do This Now"

Commands are **manual invocations** for specific workflows.

### Characteristics

- **User-triggered**: `/command` or `$ARGUMENTS`
- **Imperative**: Sequence of steps
- **One-shot**: Execute and done
- **May call agents**: Orchestrate subagents

### Structure

```
.claude/commands/<name>.md
```

With frontmatter:

```yaml
---
name: command-name
description: What it does
argument-hint: "[optional args]"
allowed-tools: [Tool, List]
---
```

### When to Use

- User-initiated workflows
- Multi-step processes
- Orchestrating multiple agents
- Quick utilities

### Example: `/quick-checks`

```markdown
---
name: quick-checks
description: Run pre-commit validation
allowed-tools: [Bash]
---

Run .claude/skills/project-navigation/scripts/quick_checks.sh
```

## Key Differences

### Inheritance

```
Skills:  Agent declares → Claude loads → Available for session
Commands: User invokes → Executes once → Done
```

### Subagent Context

```yaml
# Skills are EXPLICIT - subagents don't inherit from parent
---
name: software-developer
skills: [code, test, explore]  # Must declare here
---
```

### Token Usage

| Aspect | Skills | Commands |
|--------|--------|----------|
| SKILL.md | Loaded into context | N/A |
| References | On-demand | N/A |
| Scripts | Only output | Inline execution |

## Anti-Patterns

### ❌ Skill as Command

```markdown
# Wrong: Skill that's really a command sequence
## Steps
1. Do this
2. Then this
3. Finally this
```

### ❌ Command with Knowledge

```markdown
# Wrong: Command trying to teach conventions
## Background
Here's how our architecture works...
```

### ❌ Subagent Without Skills

```yaml
# Wrong: Expects parent context
---
name: my-agent
tools: [Edit]
# No skills declared - can't access code conventions!
---
```

## Decision Framework

```
┌─────────────────────────────────────────┐
│ Is it reusable knowledge or procedure?  │
└─────────────┬───────────────────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
   YES                 NO
     │                 │
     ▼                 ▼
  SKILL            COMMAND
     │                 │
     ├─ SKILL.md       ├─ frontmatter
     ├─ references/    ├─ inline bash or
     └─ scripts/       └─ agent invocation
```

## Examples

### Skill: `compliance-citations`

```markdown
# SKILL.md
---
name: compliance-citations
description: How to cite sources in compliance context
allowed-tools: [Read, Grep]
---

## Rules
- Never invent sources
- Always include date
- Disclaimer required

## References
- disclaimer-templates.md
```

### Command: `/review-pr`

```markdown
---
name: review-pr
description: Review a pull request
allowed-tools: [Bash, Read, Task]
---

1. Get PR diff
2. Invoke code-reviewer agent
3. Generate report
```

## Summary

| Use Case | Solution |
|----------|----------|
| "How do we name services?" | Skill (code/conventions.md) |
| "Run tests and report" | Command (/quick-checks) |
| "What's our API style?" | Skill (api-patterns/SKILL.md) |
| "Deploy to staging" | Command (/deploy staging) |
| "How do agents communicate?" | Skill (orchestration/SKILL.md) |
| "Create a feature" | Command (/implement feature) |
