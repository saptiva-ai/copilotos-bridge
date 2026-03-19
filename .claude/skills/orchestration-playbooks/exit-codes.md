# Exit Codes

> Standardized exit codes for agents and commands.

## Standard Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Proceed to next phase |
| `1` | Tests failed | Fix failing tests, retry |
| `2` | Infra/preflight failure | Run `/infra-doctor`, check services |

## Detailed Breakdown

### Exit Code 0 - Success

All operations completed successfully:
- Tests passed
- Code compiles/builds
- Services healthy
- No errors

**Next step:** Proceed to next workflow phase

### Exit Code 1 - Tests Failed

Test suite ran but failures detected:
- Unit test assertions failed
- Integration tests failed
- Type errors
- Lint errors

**Recovery:**
1. Read test output for failure details
2. Fix the failing code/tests
3. Run tests again
4. If stuck after 3 attempts, escalate

### Exit Code 2 - Infra/Preflight Failure

Infrastructure or prerequisites not met:
- Docker services not running
- Database connection failed
- Missing dependencies
- Network issues
- Missing environment variables

**Recovery:**
1. Run `/infra-doctor` for diagnostics
2. Run `make dev` to start services
3. Check `.env` files (without exposing secrets)
4. Verify Docker health: `docker compose -f infra/docker-compose.yml ps`

## Agent-Specific Handling

### test-runner

```
0 → All tests pass
1 → Test failures detected (provides analysis)
2 → Cannot run tests (infra issue)
```

### dev-validator

```
0 → Quick validation passes
1 → Validation failed (provides specific errors)
2 → Cannot validate (missing deps)
```

### software-developer

```
0 → Implementation complete, tests pass
1 → Implementation blocked (test failures after 3 retries)
2 → Cannot proceed (missing context/blockers)
```

### infra-doctor

```
0 → All services healthy
1 → Services unhealthy (provides remediation)
2 → Cannot diagnose (Docker not running)
```

## Command Exit Codes

### /quick-checks

```bash
# Success
Exit 0: All quick checks pass

# Test failures
Exit 1: Tests failed (unit or integration)

# Infra failure
Exit 2: Services not running, deps missing
```

### /dev-up

```bash
# Success
Exit 0: All services started

# Partial failure
Exit 1: Some services failed to start

# Docker failure
Exit 2: Docker daemon not running
```

## Error Escalation

```
┌─────────────────┐
│  Exit Code 1    │──▶ Retry up to 3 times
└────────┬────────┘
         │ still failing
         ▼
┌─────────────────┐
│  Analyze Error  │──▶ Different approach?
└────────┬────────┘
         │ still blocked
         ▼
┌─────────────────┐
│  Escalate to    │──▶ User decides
│  User           │
└─────────────────┘
```

## Logging Convention

```
✓ Success message (exit 0)
✗ Failure message (exit 1)
⚠ Infra warning (exit 2)
```
