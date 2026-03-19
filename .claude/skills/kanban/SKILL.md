# Kanban Skill (V2 Frontmatter)

## Scripts

| Script | Usage |
|--------|-------|
| `task_new.sh` | `./task_new.sh "Title" P1` -> Creates `doing/T-xxx.md` |
| `task_update.sh` | `./task_update.sh T-xxx TESTING software-developer` |
| `task_list.sh` | `./task_list.sh` -> Shows active tasks table |

## Frontmatter Schema

```yaml
---
id: T-20260101-001
status: TODO | IN_PROGRESS | TESTING | DOCS | DONE
owner: agent-name
epic: EPIC-HU2
pr_files: []
test_status: PENDING
---
```

## Agent Protocol

1. **Read**: Parse YAML Frontmatter.
2. **Act**: Do work (write code, run tests).
3. **Update**: Use `Edit` tool to update YAML status/owner.
4. **Handoff**: Implicit via status change (next agent picks it up).