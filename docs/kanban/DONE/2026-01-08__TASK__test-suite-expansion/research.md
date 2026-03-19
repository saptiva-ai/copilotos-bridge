# Research: Test Suite Expansion

**Status**: BACKLOG (not started)
**Task**: TASK-2026-01-08__test-suite-expansion

## Existing Test Coverage

### Current State
| Área | Estado Anterior | Propuesto |
|------|-----------------|-----------|
| Seguridad avanzada | 6 casos básicos | 65 vectores de ataque |
| Autenticación | Sin cobertura | 20 casos de manipulación JWT |
| Conversaciones multi-turn | 2 turnos máx | 10 escenarios de 5-7 turnos |
| Unit tests parser | 2 funciones | 33 tests comprehensivos |
| Unicode/emoji | Sin cobertura | 23 casos de stress |
| Validación de datos | Sin cobertura | 10 validadores |

### Existing Test Files
- `tests/e2e/security/test_security_prompt_injection.py`
- `tests/e2e/test_happy_path_suite.py`
- `tests/fixtures/`

### Parser Source
- `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

## Research Notes
When this task moves to DOING, add research findings here.
