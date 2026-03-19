---
id: "TASK-2026-02-09-1802__loader-quebrantos"
title: "New loader + table for QUEBRANTOS.csv"
status: "DONE"
phase: "Validate"
resolution: "Closed — data confirmed redundant (exact match with bank_fact_kpis_mensual Jan 2022)"
scope_in:
  - "Define target table bank_src_quebrantos schema"
  - "Create loader function using scan_csv_smart() (UTF-16 support already done)"
  - "Create migration for the new table"
  - "Add transform logic if needed"
scope_out:
  - "Production writes"
  - "Frontend / dashboard integration"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands: []
pr_files: []
test_status: ""
---

# Summary
- Objective: Ingest `QUEBRANTOS.csv` (write-off / charge-off data by institution) into a new `bank_src_quebrantos` table.
- Parent: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/`

# Problem
`QUEBRANTOS.csv` is a UTF-16 LE tab-delimited file. The encoding issue is already solved (`scan_csv_smart()` in `etl/core/loaders/smart_csv.py`), and the file is already in the promotion specs. But there is no loader that writes it to a database table, and no target table exists.

# Research Findings (from parent task)
- **Encoding**: UTF-16 LE with BOM (`\xff\xfe`), tab-delimited
- **Columns** (from header): `Institucion1`, `Bancos`, `Quebrantos CC` (at minimum — full schema TBD)
- **Sample row**: `5\t\t16907.84354854`
- **Reading**: `scan_csv_smart()` already handles transcoding to UTF-8 + tab detection

# Solution
1. Research: Read full column list and data types.
2. Define `bank_src_quebrantos` table schema.
3. Create `load_quebrantos()` loader.
4. Create migration SQL.
5. File already in promotion specs (Step 2 of parent task).

# Verification
- [ ] Full column schema documented
- [ ] Loader dry-run succeeds
- [ ] Migration SQL reviewed
- [ ] Data types validated (institution codes, numeric values)
