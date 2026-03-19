---
id: "TASK-2026-01-05-0945__create-formula-parser__etl-utility"
title: "Create parse_uso_formula.py utility for formula extraction"
status: "BACKLOG"
phase: "Research"
scope_in:
  - "Create parse_uso_formula.py to extract formulas from anexo36_conceptos_uso_clean.xlsx"
  - "Parse formula_text and formula_uso columns"
  - "Extract variable dependencies from formulas"
  - "Return structured formula data for ETL integration"
scope_out:
  - "Loading formulas into Weaviate (handled by ETL)"
  - "Formula validation or execution"
  - "HTML parsing of Anexo 36 (separate task: TASK-2026-01-05-0915)"
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
- Objective: Create utility to parse formulas from Anexo 36 Excel conceptos_uso sheet for Phase 2A integration
- Constraints: Must extract formula_text, formula_uso, and variables from anexo36_conceptos_uso_clean.xlsx
- Context: Required for HU4 Phase 2A (TASK-2026-01-02-2048 plan.md lines 285-361)

# Blocked By
Phase 2A implementation discovered this utility doesn't exist (assumed by plan.md)

# Updates
- 2026-01-05 09:45 - Created. Identified during Phase 2 implementation of HU4 CAS completion task.
