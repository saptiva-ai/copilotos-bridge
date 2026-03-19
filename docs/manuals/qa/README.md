# QA & Testing Manuals

> **Source of Truth**: This directory establishes the testing strategies, plans, and guides for ensuring quality in OctaviOS Chat.

## Testing Strategy

- [Master Test Plan](strategies/master_plan.md) - The high-level vision and coverage goals.

## Guides & Runbooks

| Type | Guide | Description |
|------|-------|-------------|
| **Integration** | [Integration Testing](guides/integration_testing.md) | How to run and write E2E/Integration tests. |
| **MCP** | [MCP Testing](guides/mcp_testing.md) | Validating Model Context Protocol agents and tools. |
| **Playwright E2E** | [Conversation Test Kit](guides/playwright_conversation_test_kit.md) | Reusable pattern for multi-turn chat tests, grounding checks, and evidence attachments. |

## Quick Commands

```bash
# Run all backend tests
make test T=api

# Run E2E happy path
python tests/e2e/test_happy_path_suite.py

# Run full suite (CI simulation)
./scripts/tests/run_full_suite.sh
```
