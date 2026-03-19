# OctaviOS Chat Manuals

This directory contains operational manuals, deployment guides, and procedures.

## Directory Structure

- **[dev/](dev/README.md)**: **Developer Guides**. Setup, tooling, and workflow.
  - [Getting Started](dev/getting_started.md)
  - [Kanban Sync](dev/kanban_sync.md) - 3-layer task sync (local + MongoDB + GitHub Issues)
  - [Reference](dev/reference/)

- **[qa/](qa/README.md)**: **Quality Assurance**. Testing strategies and guides.
  - [Master Plan](qa/strategies/master_plan.md)
  - [Guides](qa/guides/)
  - [Playwright Conversation Test Kit](qa/guides/playwright_conversation_test_kit.md)

- **[deploy/](deploy/README.md)**: **Operations & Deploy**.
  - [Procedures](deploy/procedures/) - Step-by-step deploy guides
  - [Runbooks](deploy/runbooks/) - Fix specific issues
  - [Architectures](deploy/architectures/) - UV builds, CI/CD pipeline
  - [Lessons](deploy/lessons/) - Post-mortems and incident reports

- **[deprecated/](deprecated/README.md)**: Old documentation.

- **[_triage/](_triage/README.md)**: Documents awaiting classification.

## Quick Links

- **New Developer?** [Start Here](dev/getting_started.md)
- **Deploying?** [Current Guide (v1.4.0)](deploy/procedures/current_v1.4.0.md)
- **Fixing an Issue?** [Incident Index](deploy/runbooks/incident-index.md)
