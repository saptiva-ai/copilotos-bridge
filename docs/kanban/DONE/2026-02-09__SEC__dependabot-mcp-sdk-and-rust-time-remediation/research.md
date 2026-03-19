# Research

## Questions
- Which vulnerabilities are currently open in GitHub Dependabot?
- Are vulnerable versions present in this repository lockfiles?
- What is the practical exposure based on current runtime pattern?

## Findings
- Open Dependabot alerts:
  - #43 HIGH: `@modelcontextprotocol/sdk` (`CVE-2026-25536`, `GHSA-345p-7cg4-v4c7`), fixed in `1.26.0`.
  - #42 MEDIUM: `time` (`CVE-2026-25727`, `GHSA-r6v5-fh4h-64xc`), fixed in `0.3.47`.
- Repository state:
  - `tools/mcp-kanban-sync/package-lock.json` resolves `@modelcontextprotocol/sdk` to `1.25.3` (vulnerable).
  - `plugins/public/file-manager/rust_modules/Cargo.lock` resolves `time` to `0.3.45` (vulnerable).
- Exposure notes:
  - MCP tool uses `StdioServerTransport` and not HTTP multi-client transport, reducing practical impact of #43 but not eliminating need to patch.
  - File-manager processes user-supplied PDFs; transitive `time` exposure is relevant enough to patch promptly.

## References
- `https://github.com/saptiva-ai/octavios-chat-bajaware_invex/security/dependabot/43`
- `https://github.com/saptiva-ai/octavios-chat-bajaware_invex/security/dependabot/42`
- `https://github.com/advisories/GHSA-345p-7cg4-v4c7`
- `https://github.com/advisories/GHSA-r6v5-fh4h-64xc`
