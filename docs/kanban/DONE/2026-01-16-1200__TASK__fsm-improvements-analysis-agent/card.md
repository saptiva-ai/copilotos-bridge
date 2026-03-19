---
id: "TASK-2026-01-16-1200__fsm-improvements-analysis-agent"
title: "FSM Improvements + Intelligent Analysis Agent"
status: "DOING"
phase: "Implement"
scope_in:
  - "Migrate FSM to python-statemachine library"
  - "Create BankClassification config (SISTEMA rules)"
  - "Implement AnalysisAgent for intelligent conclusions"
  - "Fix chart_formatter bank counting"
  - "Optimize Docker image size"
scope_out:
  - "Full FSM production migration (keep legacy as fallback)"
  - "UI changes"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "cd plugins/bank-advisor-private && python -c 'from bankadvisor.fsm.machine import QueryStateMachine; print(\"FSM OK\")'"
  - "cd plugins/bank-advisor-private && python -c 'from bankadvisor.config.bank_rules import BankClassification; print(BankClassification.count_banks([\"INVEX\", \"SISTEMA\", \"BBVA\"]))'"
  - "make test T=api TEST_ARGS='-k fsm or bank_classification'"
pr_files:
  - plugins/bank-advisor-private/pyproject.toml
  - plugins/bank-advisor-private/src/bankadvisor/config/bank_rules.py
  - plugins/bank-advisor-private/src/bankadvisor/fsm/machine.py
  - plugins/bank-advisor-private/src/bankadvisor/fsm/agents/analysis_agent.py
  - plugins/bank-advisor-private/src/bankadvisor/services/chart_formatter.py
  - plugins/bank-advisor-private/Dockerfile
test_status: "pending"
---

# Summary
- **Objective**: Improve bank-advisor FSM architecture, add intelligent analysis for chart conclusions, and fix SISTEMA counting issues
- **Constraints**: Keep legacy FSM as fallback, no breaking changes to API

# Background
Current issues identified:
1. FSM is manual implementation - migrate to python-statemachine for better tooling
2. Conclusions are static strings like "INVEX en posicion X de Y" - need LLM-based analysis
3. SISTEMA is counted as a bank in rankings (incorrect - it's an aggregate)
4. Docker image can be optimized

# Updates
- 2026-01-16 12:00 - Created task after analysis of FSM architecture and conclusion quality issues
