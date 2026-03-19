---
id: FEAT-2026-02-26__benchmark-report-generation
title: Benchmark Report Generation (PPTX + PDF)
status: REVIEW
phase: Implement
scope_in:
  - >-
    Plugin: MCP tool generate_benchmark_report with chart_exporter,
    pptx_builder, pdf_builder
  - 'Plugin: 24 preset queries mirroring HELP_PRESET_SECTIONS'
  - 'Backend: Proxy endpoints POST /generate, GET /status, GET /download'
  - 'Backend: Remove reportlab (moved to plugin)'
  - 'Frontend: ReportGenerator component in HelpOnboardingMenu'
  - 'Frontend: useReportGeneration hook with polling'
  - 'Frontend: Hidden checkboxes for customization, all selected by default'
scope_out:
  - E2E tests (follow-up task)
  - 'Redis-backed progress store (future, for multi-worker)'
  - Preset sync endpoint (future)
  - Custom logo injection in PPTX
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 3
validation_commands:
  - cd apps/web && pnpm lint
  - cd apps/web && pnpm typecheck
pr_files:
  - plugins/bank-advisor-private/src/bankadvisor/services/chart_exporter.py
  - plugins/bank-advisor-private/src/bankadvisor/services/pptx_builder.py
  - plugins/bank-advisor-private/src/bankadvisor/services/pdf_builder.py
  - plugins/bank-advisor-private/src/bankadvisor/services/report_generator.py
  - plugins/bank-advisor-private/src/bankadvisor/tools/report_tools.py
  - plugins/bank-advisor-private/src/main.py
  - plugins/bank-advisor-private/requirements.txt
  - plugins/bank-advisor-private/requirements-runtime.txt
  - apps/backend/src/routers/reports_benchmark.py
  - apps/backend/src/main.py
  - apps/backend/requirements.txt
  - apps/backend/requirements-runtime.txt
  - apps/backend/pyproject.toml
  - apps/web/src/components/chat/ReportGenerator.tsx
  - apps/web/src/components/chat/HelpOnboardingMenu.tsx
  - apps/web/src/components/chat/help-onboarding-content.ts
  - apps/web/src/hooks/useReportGeneration.ts
  - apps/web/src/lib/api-client.ts
test_status: pending
---

# Summary
- Objective: Automate INVEX benchmark report generation (PPTX + PDF) from the 24 predefined help presets, replacing manual copy-paste from Tableau.
- Constraints: 100% server-side in plugin, both PPTX and PDF formats, all presets selected by default, checkboxes hidden but expandable.

# Architecture

```
Frontend (ReportGenerator.tsx)
  → POST /api/reports/benchmark/generate
    → Backend (reports_benchmark.py) → BackgroundTask
      → Plugin JSON-RPC: generate_benchmark_report
        → execute_bank_analytics() × 24 queries
        → plotly_config → kaleido → PNG
        → python-pptx → PPTX file
        → reportlab → PDF file
      → GET /reports/benchmark/{task_id}/download (plugin REST)
    ← FileResponse (binary)
  → Polling GET /api/reports/benchmark/status/{task_id}
  → GET /api/reports/benchmark/download/{task_id}?format=pptx
```

# New Files Created
1. `plugins/bank-advisor-private/src/bankadvisor/services/chart_exporter.py` — Plotly JSON → PNG via kaleido
2. `plugins/bank-advisor-private/src/bankadvisor/services/pptx_builder.py` — PowerPoint builder (16:9, INVEX branding)
3. `plugins/bank-advisor-private/src/bankadvisor/services/pdf_builder.py` — PDF builder (landscape A4, INVEX branding)
4. `plugins/bank-advisor-private/src/bankadvisor/services/report_generator.py` — Orchestrator + 24 preset registry
5. `plugins/bank-advisor-private/src/bankadvisor/tools/report_tools.py` — MCP tool wrappers
6. `apps/backend/src/routers/reports_benchmark.py` — Backend proxy router
7. `apps/web/src/components/chat/ReportGenerator.tsx` — Frontend UI component
8. `apps/web/src/hooks/useReportGeneration.ts` — React hook for generation + polling

# Dependencies Added (plugin)
- `python-pptx>=0.6.21` — PowerPoint generation
- `kaleido>=0.2.1` — Plotly static image export
- `plotly>=5.0.0` — Chart library for kaleido
- `reportlab>=4.0.0` — PDF generation (moved from backend)

# Dependencies Removed (backend)
- `reportlab>=4.0.0` — No longer used in backend (was dead weight per OPTIMIZATION_PLAN.md)

# Updates
- 2026-02-26 — Implementation: all 3 phases (Plugin, Backend, Frontend) complete.



# Testing Results (2026-02-26)

## Plugin Tests — 59/59 passed
| Suite | Tests | Status |
|-------|-------|--------|
| `test_chart_exporter.py` | 6 | ✅ |
| `test_pptx_builder.py` | 13 | ✅ |
| `test_pdf_builder.py` | 12 | ✅ |
| `test_report_generator.py` | 28 | ✅ |

## Backend Tests — 15/15 passed
| Suite | Tests | Status |
|-------|-------|--------|
| `test_reports_benchmark.py` | 15 | ✅ |

## Frontend Tests — 22/22 passed
| Suite | Tests | Status |
|-------|-------|--------|
| `ReportGenerator.test.tsx` | 22 | ✅ |

**Total: 96/96 tests passed**

## Local venv setup
- Plugin venv: `plugins/bank-advisor-private/.venv/` (Python 3.11.13)
- Installed: python-pptx 1.0.2, kaleido 1.2.0, plotly 6.5.2, reportlab 4.4.10

## Pending
- E2E validation against running stack (docker compose)
- Verify PPTX/PDF output quality with real data
