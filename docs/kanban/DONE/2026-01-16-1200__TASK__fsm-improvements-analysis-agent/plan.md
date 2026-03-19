# Plan

## Objective
- Migrate FSM to python-statemachine for better maintainability and debugging
- Create BankClassification config to handle SISTEMA rules consistently
- Implement AnalysisAgent that uses LLM for intelligent chart conclusions
- Fix chart_formatter to exclude SISTEMA from bank counts
- Optimize Docker image size

## Scope
### In
- python-statemachine integration
- BankClassification config module
- AnalysisAgent with LLM prompts
- chart_formatter fixes
- Docker multi-stage build optimization

### Out
- Full migration of production code to new FSM (keep as opt-in)
- Frontend changes
- Database schema changes

## Phases

### Phase 1: Foundation
- [x] Add python-statemachine to dependencies
- [x] Create BankClassification config module
- [x] Write unit tests for BankClassification

#### Phase 1 Files
- `plugins/bank-advisor-private/pyproject.toml`
- `plugins/bank-advisor-private/src/bankadvisor/config/__init__.py`
- `plugins/bank-advisor-private/src/bankadvisor/config/bank_rules.py`
- `plugins/bank-advisor-private/tests/unit/test_bank_rules.py`

### Phase 2: FSM Migration
- [x] Implement QueryStateMachine with python-statemachine
- [x] Create state handlers as methods
- [x] Add async support
- [x] Write FSM tests (40 tests passing)

#### Phase 2 Files
- `plugins/bank-advisor-private/src/bankadvisor/fsm/machine.py`
- `plugins/bank-advisor-private/tests/unit/test_fsm_machine.py`

### Phase 3: Analysis Agent
- [x] Create AnalysisAgent class
- [x] Define system prompts with SISTEMA rules
- [x] Integrate with response enrichment
- [x] Add tests (48 tests passing)

#### Phase 3 Files
- `plugins/bank-advisor-private/src/bankadvisor/fsm/agents/analysis_agent.py`
- `plugins/bank-advisor-private/tests/unit/test_analysis_agent.py`

### Phase 4: Chart Formatter Fixes
- [x] Update chart_formatter to use BankClassification
- [x] Fix total_banks counting
- [x] Update summary text generation
- [x] Verify all formatters updated (ranking, yoy, financial_ranking)

#### Phase 4 Files
- `plugins/bank-advisor-private/src/bankadvisor/services/chart_formatter.py`

### Phase 5: Docker Optimization
- [x] Review current Dockerfile
- [x] Implement multi-stage build
- [x] Remove unnecessary dependencies (requirements-runtime.txt)
- [x] Test image size reduction (~7GB → 845MB)

#### Phase 5 Files
- `plugins/bank-advisor-private/Dockerfile`

## Validation Commands
```bash
# Phase 1
cd plugins/bank-advisor-private && python -c "from bankadvisor.config.bank_rules import BankClassification; print(BankClassification.count_banks(['INVEX', 'SISTEMA', 'BBVA']))"

# Phase 2
cd plugins/bank-advisor-private && python -c "from bankadvisor.fsm.machine import QueryStateMachine; sm = QueryStateMachine(); print(sm.current_state)"

# Phase 3
make test T=api TEST_ARGS="-k analysis_agent"

# Phase 4
make test T=api TEST_ARGS="-k chart_formatter"

# Phase 5
docker images | grep bank-advisor
```

## Success Criteria
- BankClassification.count_banks(["INVEX", "SISTEMA", "BBVA"]) returns 2 (not 3)
- FSM can transition through all states without errors
- AnalysisAgent generates contextual conclusions
- All existing tests pass
- Docker image size reduced by at least 10%
