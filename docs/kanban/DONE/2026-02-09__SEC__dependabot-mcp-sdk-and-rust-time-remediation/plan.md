# Plan

## Objective
- Remove open Dependabot vulnerabilities in MCP SDK and Rust `time` crate with minimal and verifiable changes.

## Scope
### In
- Update npm dependency resolution for `@modelcontextprotocol/sdk` in `tools/mcp-kanban-sync`.
- Update rust lock resolution for `time` in `plugins/public/file-manager/rust_modules`.
- Execute targeted regression checks and verify alerts are closed.

### Out
- Enabling GitHub security products (code scanning/secret scanning).
- Broad upgrades not required to close these alerts.

## Phases
### Phase 1
- [ ] Upgrade `@modelcontextprotocol/sdk` to patched version and regenerate `package-lock.json`.
- [ ] Confirm MCP tool still builds and starts.

#### Phase 1 Files
- `tools/mcp-kanban-sync/package.json`
- `tools/mcp-kanban-sync/package-lock.json`
- `tools/mcp-kanban-sync/src/index.ts` (only if adaptation is required)

### Phase 2
- [ ] Upgrade rust `time` to patched version in lockfile.
- [ ] Validate PDF extraction paths remain stable.

#### Phase 2 Files
- `plugins/public/file-manager/rust_modules/Cargo.lock`
- `plugins/public/file-manager/rust_modules/Cargo.toml` (only if required)

### Phase 3
- [ ] Run regression checks and confirm Dependabot alerts are resolved.
- [ ] Document evidence in `validate.md`.

#### Phase 3 Files
- `docs/kanban/BACKLOG/2026-02-09__SEC__dependabot-mcp-sdk-and-rust-time-remediation/validate.md`

## Validation Commands
- `gh api '/repos/saptiva-ai/octavios-chat-bajaware_invex/dependabot/alerts?state=open&per_page=100'`
- `cd tools/mcp-kanban-sync && npm ls @modelcontextprotocol/sdk`
- `cd tools/mcp-kanban-sync && npm run build`
- `cd plugins/public/file-manager/rust_modules && cargo tree -i time`
- `cd plugins/public/file-manager && pytest -q tests/regression/test_python_fallback.py`

## Success Criteria
- Dependabot does not report open alerts #43 and #42.
- MCP kanban sync build path is green after dependency update.
- File-manager rust dependency tree resolves patched `time`.
- Targeted regression tests pass.
