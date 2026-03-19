# Research

## FSM Libraries Comparison

| Library | Async | Nested States | Diagrams | Pydantic | Maturity |
|---------|-------|---------------|----------|----------|----------|
| pytransitions | Yes | Yes | Yes | No | High |
| python-statemachine | Yes | Yes | Yes | No | High |
| statesman | Native | No | No | Yes | Medium |

**Decision**: Use `python-statemachine` because:
- Modern async support
- Good documentation
- Active maintenance
- Simple decorator-based API

## Current Issues

### 1. Static Conclusions
Current code in `chart_formatter.py:522`:
```python
"summary": f"Ranking de {display_name} - INVEX en posicion {invex_position} de {len(latest)}"
```
- No real analysis
- No context about market
- No insights

### 2. SISTEMA Counting
In `contextual_suggestion_service.py:56`:
```python
EXCLUDED_BANKS = ["SISTEMA"]  # SISTEMA es agregado, no un banco individual
```
But in `chart_formatter.py`:
```python
"total_banks": len(latest)  # Includes SISTEMA!
```

### 3. Inconsistent Handling
- Some places exclude SISTEMA (suggestions)
- Some places include SISTEMA (rankings, counts)
- No centralized configuration

## Proposed Architecture

```
bankadvisor/
  config/
    __init__.py
    bank_rules.py          # BankClassification
  fsm/
    machine.py             # QueryStateMachine (python-statemachine)
    agents/
      analysis_agent.py    # LLM-based analysis
```

## References
- https://python-statemachine.readthedocs.io/
- https://github.com/fgmacedo/python-statemachine
