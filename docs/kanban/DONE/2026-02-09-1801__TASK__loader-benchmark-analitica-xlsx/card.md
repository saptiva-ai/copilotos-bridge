---
id: "TASK-2026-02-09-1801__loader-benchmark-analitica-xlsx"
title: "New loader for Catera Analitica Benchmark v2.xlsx"
status: "REVIEW"
phase: "Validate"
scope_in:
  - "Parse formula-heavy Excel (309K rows) with EDATE-generated date columns"
  - "Create loader function in etl/core/loaders/"
  - "Create target table bank_src_benchmark_analitica (or equivalent)"
  - "Add migration for the new table"
  - "Wire into data_promotion.py specs"
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
- Objective: Ingest `Catera Analitica Benchmark v2.xlsx` (cross-bank R04A-structure benchmark) into a new `bank_src_*` table.
- Parent: `docs/kanban/DOING/2026-02-09-1430__TASK__secure-prod-db-comparison-and-data-drop-policy/`

# Problem
This Excel file contains 309,537 rows in Sheet1 with formula-driven date headers (`=EDATE()` spanning Dec 2000 through ~2025). Sheet2 has a 100-row concept catalog with R04A-style codes (e.g., `130000000000` = "Cartera de Credito con Riesgo de Credito Etapa 1"). No existing loader handles this structure.

# Root Cause
The file is a Bajaware-generated cross-bank analytical benchmark. It uses Excel formulas for date columns instead of literal values, and the data layout is wide-format (months as columns) rather than long-format.

# Research Findings (from parent task)
- **Sheet1**: 309,537 rows. Row 1 has 280+ date columns via `=EDATE(B1,1)`. Data rows contain concept codes and monthly values.
- **Sheet2**: 100 rows. Concept catalog: `Concepto`, `Etapa`, `Descripcion`, `Desc entrada`, `ORDEN ENTRADA`. R04A concept codes (12-digit).
- **Challenge**: `openpyxl` in `read_only=True` mode returns formula strings, not computed values. Need `data_only=True` or `xlcalc` / pre-processing.
- **Note**: Filename has typo ("Catera" vs "Cartera") — loader should handle both.

# Solution
1. Research: Determine if `openpyxl(data_only=True)` resolves formulas (requires file was last saved by Excel with cached values).
2. Unpivot wide-format (months as columns) into long-format `(concepto, fecha, valor)`.
3. Join with Sheet2 concept catalog for enrichment.
4. Create `load_benchmark_analitica()` in `etl/core/loaders/`.
5. Create migration for target table.
6. Add to promotion specs with glob: `*Benchmark*.xlsx`.

# Verification
- [ ] Formula resolution confirmed (data_only or alternative)
- [ ] Wide-to-long unpivot produces correct row counts
- [ ] Concept catalog join works
- [ ] Loader dry-run succeeds
- [ ] Migration SQL reviewed
