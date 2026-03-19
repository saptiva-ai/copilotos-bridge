# TASK: MV Regional Query Routing Fix

## Status: DONE

## Summary
Investigación y fix del routing de queries regionales que causaba alucinaciones del LLM.

## Problem
Queries como "Saldo por entidad federativa de INVEX" no se enrutaban al `CarteraRegionHandler`, causando que el sistema usara NL2SQL y el LLM alucinara datos regionales (18.6B MDP vs 14.7B MDP real, porcentajes sumando 113.7%).

## Solution
1. Mejorar logging en `FSM._has_matching_handler()` para debug
2. Agregar detección de banco directa desde query text en `CarteraRegionHandler`
3. Agregar tests E2E específicos para queries regionales

## Changes
- `plugins/bank-advisor-private/src/bankadvisor/fsm/machine.py` - Logging mejorado
- `tests/e2e/metrics/test_materialized_views_suite.py` - 3 nuevos tests
- `docs/kanban/.../research.md` - Análisis completo

## Test Results
- MV-GEO-004: "Saldo por entidad federativa de INVEX" → ✅ PASS (4 data points)
- MV-GEO-005: "Cartera por región de INVEX" → ✅ PASS (4 data points)
- Overall: 27/32 MV tests pass (84.4%)

## Key Findings
- `bank_mv_cartera_por_estado` tiene datos correctos (14,684 MDP para INVEX)
- El problema era de routing, no de datos faltantes
- No se necesitan nuevas MVs - las 11 existentes son suficientes

## Commits
- `ad507616` fix(bank-advisor): improve regional query routing and logging
- `da5940a7` fix(hallucination): prevent LLM from fabricating regional data

## Date Completed
2026-01-27
