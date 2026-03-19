---
name: review
description: Review code for bugs, security issues, and convention adherence. Use PROACTIVELY before merging code changes. (project)
allowed-tools: [Read, Grep, Glob, LSP]
---

# Code Review Skill

> Review code changes with evidence-based feedback and security awareness.

## Review Flow

```
┌─────────────────┐
│   Code Changes  │  git diff, staged files, PR
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Correctness   │  Logic errors, edge cases, null handling
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Security     │  OWASP Top 10, injection, secrets
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Conventions    │  Project patterns, SOLID, naming
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Test Coverage  │  Missing tests, edge cases
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Verdict      │  APPROVE | REQUEST_CHANGES | COMMENT
└─────────────────┘
```

## Quick Reference

### Severity Levels

| Level | Definition | Action |
|-------|------------|--------|
| CRITICAL | Security vulnerability, data loss risk | Block merge |
| HIGH | Logic error, likely bug | Must fix |
| MEDIUM | Code smell, maintainability issue | Should fix |
| LOW | Style, minor improvement | Nice to have |

### Review Commands

```bash
# See what changed
git diff main...HEAD
git diff --staged

# Check specific file history
git log -p --follow -- path/to/file.py

# Find related tests
grep -r "test_function_name" tests/
```

### Evidence Format

Always cite with `file:line`:

```markdown
| File:Line | Issue | Severity | Fix |
|-----------|-------|----------|-----|
| src/services/auth.py:42 | SQL injection risk | CRITICAL | Use parameterized query |
| src/routers/chat.py:88 | Missing null check | HIGH | Add guard clause |
```

## Reference Files

| File | Content |
|------|---------|
| `security.md` | OWASP Top 10 checks, common vulnerabilities |
| `patterns.md` | Code smell detection, anti-patterns |
| `checklist.md` | Review checklist by file type |

## Verdict Criteria

### APPROVE
- No CRITICAL or HIGH issues
- Tests exist for new code
- Conventions followed

### REQUEST_CHANGES
- Any CRITICAL or HIGH issue
- Missing tests for critical path
- Security vulnerability

### COMMENT
- Only MEDIUM/LOW issues
- Suggestions for improvement
- Questions about design choices

## Quick Checklist

- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Error handling appropriate
- [ ] Tests cover new code
- [ ] SOLID principles followed
- [ ] No obvious security issues
