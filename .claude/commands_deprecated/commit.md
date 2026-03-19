---
name: commit
description: Create conventional commit with staged changes.
argument-hint: "[type] [scope] [description]"
allowed-tools: [Bash, Read]
---

Create a conventional commit for staged changes.

## Conventional Commit Format
```
<type>(<scope>): <description>

[optional body]
```

## Types
| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Maintenance |

## Scopes
Common scopes: `backend`, `web`, `bank-advisor`, `auth`, `chat`, `agents`, `skills`

## Process
1. Check staged changes: `git diff --staged`
2. Analyze changes to determine type and scope
3. Generate commit message
4. Commit with conventional format

## Examples
```bash
/commit feat backend "add user metrics endpoint"
/commit fix chat "resolve streaming timeout"
/commit refactor agents "apply progressive disclosure"
```

Review staged changes and suggest an appropriate conventional commit message.
