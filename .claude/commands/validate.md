# /validate - Task Validation (default) or Config Consistency (--config)

Validate a task using `plan.md` commands, or validate Claude Code config when requested.

## Task Validation (default)

### Inputs
- Task folder: `<KANBAN_ROOT>/DOING/TASK-...__slug/`
- `KANBAN_ROOT` (optional): defaults to `docs/kanban`

### Steps
1. Read `plan.md` for validation commands. If missing, stop and request update.
2. Run only existing project commands (from plan). If plan is missing commands, use existing repo entry points (e.g., `make test T=api`) or update the plan first.
3. Write results to `validate.md` (commands + PASS/FAIL + notes).
4. Update `card.md` with `test_status`. If PASS, set `status: DONE`; if FAIL, set `status: BLOCKED`.
5. If PASS, move task folder to DONE:

```bash
KANBAN_ROOT=\"${KANBAN_ROOT:-docs/kanban}\"
git mv \"$KANBAN_ROOT/DOING/TASK-...__slug\" \"$KANBAN_ROOT/DONE/TASK-...__slug\"
```

If FAIL, leave task in DOING and set `status: BLOCKED`.

## Config Consistency Mode

Use this mode when `$ARGUMENTS` includes `--config` or any of: `--fix`, `--quiet`, `--json`.

```bash
chmod +x .claude/scripts/validate-consistency.sh 2>/dev/null || true
.claude/scripts/validate-consistency.sh $ARGUMENTS
```

## Exit Codes
- `0`: Validation passed
- `1`: Validation failed
- `2`: Script error
