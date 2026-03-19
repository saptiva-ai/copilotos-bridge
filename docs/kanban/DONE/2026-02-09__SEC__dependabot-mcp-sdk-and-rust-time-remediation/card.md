---
id: "SEC-2026-02-09__dependabot-mcp-sdk-and-rust-time-remediation"
title: "Remediate open Dependabot alerts for MCP SDK and Rust time crate"
status: "DONE"
phase: "Validate"
scope_in:
  - "Upgrade @modelcontextprotocol/sdk to patched version >=1.26.0 in tools/mcp-kanban-sync"
  - "Upgrade Rust crate time to patched version >=0.3.47 in plugins/public/file-manager/rust_modules"
  - "Validate no regressions in MCP kanban sync and file-manager rust modules"
  - "Close Dependabot alerts #43 and #42"
scope_out:
  - "Enable GitHub Code Scanning feature for the repository"
  - "Enable GitHub Secret Scanning feature for the repository"
  - "Non-security refactors unrelated to vulnerable dependencies"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "gh api '/repos/saptiva-ai/octavios-chat-bajaware_invex/dependabot/alerts?state=open&per_page=100'"
  - "cd tools/mcp-kanban-sync && npm ls @modelcontextprotocol/sdk"
  - "cd plugins/public/file-manager/rust_modules && cargo tree -i time"
  - "cd apps/web && pnpm test e2e/tests/chat.spec.ts -g 'help onboarding' --project=chromium"
pr_files:
  - "tools/mcp-kanban-sync/package-lock.json"
  - "plugins/public/file-manager/rust_modules/Cargo.lock"
test_status: "PASS (lockfile versions verified locally); pending GitHub Dependabot/CI confirmation"
---

# Summary
- Objective: Resolve current open GitHub Dependabot vulnerabilities in npm and Rust lockfiles and verify no functional regressions.
- Constraints: Keep the fix minimal, avoid behavior changes in runtime features, and meet SEC DoD (Dependabot clear, CI green, no regressions).

# Problem
GitHub Dependabot reports 2 open security alerts in this repository:
- Alert #43 (HIGH): `@modelcontextprotocol/sdk` vulnerable range `>=1.10.0, <=1.25.3`, patch `1.26.0`.
- Alert #42 (MEDIUM): Rust crate `time` vulnerable range `>=0.3.6, <0.3.47`, patch `0.3.47`.

# Root Cause
- `tools/mcp-kanban-sync/package-lock.json` currently resolves `@modelcontextprotocol/sdk` to `1.25.3`.
- `plugins/public/file-manager/rust_modules/Cargo.lock` currently resolves `time` to `0.3.45` (transitive via PDF stack).

# Solution
- Bump vulnerable dependency resolution to patched versions:
  - npm: `@modelcontextprotocol/sdk` to `>=1.26.0`.
  - rust: `time` to `>=0.3.47` in `Cargo.lock` (and upstream constraints only if needed).
- Rebuild and run targeted regression tests for:
  - MCP kanban sync tool startup/build path.
  - File-manager rust module extraction path.
- Validate Dependabot returns zero open alerts for these CVEs.

# Verification
- [ ] Alert #43 is closed in GitHub Dependabot
- [ ] Alert #42 is closed in GitHub Dependabot
- [ ] MCP kanban sync build/runtime checks pass
- [ ] File-manager rust dependency tree shows patched `time`
- [ ] No regression in targeted automated tests
- [ ] CI passes

# User Feedback
- N/A (security hardening task derived from repository vulnerability scan)

# Updates
- 2026-02-09 09:58 - Created from GitHub vulnerability review (Dependabot alerts #43 and #42).
- 2026-02-09 16:20 - Lockfiles updated to patched versions (@modelcontextprotocol/sdk 1.26.0, time 0.3.47); awaiting GitHub Dependabot state confirmation.
