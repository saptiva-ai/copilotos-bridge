---
id: TASK-2026-02-09-1430__secure-prod-db-comparison-and-data-drop-policy
title: Secure prod DB comparison and recurring data-drop policy
status: REVIEW
phase: Implement
scope_in:
  - >-
    Define a secure workflow to run production DB comparisons without sharing
    secrets in chat or repo files
  - >-
    Map incoming Bajaware files to current ETL loaders and destination bank_*
    tables
  - >-
    Define ingestion policy for recurring drops in data/raw/incoming with
    promotion gates
  - >-
    Identify required adapters for schema-drift files (R04A_419, headerless or
    UTF-16 CSVs)
scope_out:
  - Database schema redesign or business metric definition changes
  - Production write operations or destructive data migrations
  - Non-ingestion frontend or UX work
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - >-
    cd plugins/bank-advisor-private && .venv/bin/python
    scripts/promote_incoming_drop.py --dry-run
  - >-
    cd plugins/bank-advisor-private && .venv/bin/python
    scripts/promote_incoming_drop.py
  - >-
    cd plugins/bank-advisor-private && .venv/bin/python -m etl.core.etl_unified
    --data-root data/raw/current --dry-run
  - >-
    cd plugins/bank-advisor-private && .venv/bin/python
    scripts/reconcile_instituciones_dim.py --limit 50
  - >-
    psql "service=bankadvisor_prod" -w -c "SELECT MAX(fecha), COUNT(*) FROM
    bank_fact_kpis_mensual;"
  - >-
    psql "service=bankadvisor_prod" -w -c "SELECT
    MAX(to_date(periodo,'YYYYMM')), COUNT(*) FROM bank_src_reporte_r04a;"
pr_files: []
test_status: ''
---

# Summary
- Objective: Establish a secure, repeatable process for production data validation and recurring raw data deliveries.
- Constraints: No credential exposure, no secret persistence in repo, and no production mutations during analysis.

# Problem
Current ETL loaders use canonical filenames and fixed schemas, while new data drops can arrive with naming, encoding, and structure drift. This creates integration risk and makes prod parity checks inconsistent.

# Root Cause
- No explicit promotion workflow from `data/raw/incoming/*` to canonical ETL paths.
- No formal manifest contract for incoming deliveries (schema, encoding, delimiter, freshness).
- Production comparison steps are ad-hoc and can tempt unsafe credential sharing.

# Solution
- Define secure credential handling and read-only prod comparison workflow.
- Define ingestion policy with: landing, manifest, validation gates, promote, rollback.
- Create explicit mapping matrix: `incoming file -> loader/adapter -> transform -> bank_* target`.
- Identify and prioritize adapters for non-canonical files before promotion.

# Verification
- [x] Documented secure workflow for `DATABASE_URL*` (no secrets in chat/repo).
- [x] File mapping matrix completed for current incoming drop.
- [x] Validation gates defined (schema, encoding, row counts, freshness, FK coverage).
- [x] Dry-run ETL works against canonicalized inputs.
- [x] Read-only production baseline queries executed and compared.
- [x] Clear list of follow-up implementation tickets generated for adapters.

# User Feedback
- User requested guidance on safely passing `DATABASE_URL*` and formalization of recurring data-drop integration.

# Updates
- 2026-02-09 14:30 - Task created from ongoing data integration and production parity analysis.
- 2026-02-09 16:15 - Implemented promotion workflow (`data/raw/incoming/*` -> `data/raw/current/`) and institutions reconcile script; added unit tests; ETL dry-run validated against promoted inputs.
- 2026-02-09 17:21 - Added drift adapters (smart UTF-16 CSV reader, report loader schema/filename discovery, Hipotecarios folder aliases) and made R12A validator max period configurable; created follow-up backlog tickets for `nuevo2.csv`, benchmark XLSX, quebrantos, and tasas loaders.
- 2026-02-10 - Begin prod deployment roadmap execution. Note: migrations 056+057 (from dim_institucion fix task) must also run before ETL re-run.
- 2026-02-10 - Prod baseline executed (read-only via pg_service.conf). 6 validation gates formalized. All 6 verification criteria met. New findings: metricas FK gap (83.3%, 27 NULL institucion_id rows), TDA coverage critical (5.8%), kpis row count delta (-299 from migration 056 dedup). Task ready for REVIEW.
