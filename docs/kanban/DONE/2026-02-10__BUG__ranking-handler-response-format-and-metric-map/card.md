---
status: REVIEW
---
# BUG: ranking-handler-response-format-and-metric-map

**Prioridad:** P1
**Fecha:** 2026-02-10
**Status:** DOING

---

## Resumen

## Problem

`InstitutionRankingHandler` has two bugs causing ALL ranking queries to fail silently:

### Bug A — Missing `type` in response format
The handler returns `{"success": True, "data": [...]}` but `execute_bank_analytics()` at `main.py:819` gates on:
```python
if hu3_result.get("type") in ["data", "clarification", "error", "empty", "knowledge"]
```
Since `type` is missing, the response is silently dropped → falls to NL2SQL → generic fallback.

### Bug B — Incomplete `METRIC_KEYWORD_MAP`
- `"capitalización"` maps to `"icap"` but DB column is `"icap_total"` → KPI query fails
- `"imor"`, `"icor"`, `"icap"` not present as keys → defaults to wrong metric `"activo_total"`

## Failing Tests
- RANK-051: "Lista de bancos por capitalización de mayor a menor"
- RANK-051b: "lista de bancos por IMOR de menor a mayor"
- RANK-051c: ascending order check

## Fix
1. Add `"type": "data"` + `"visualization": "bar"` + `plotly_config` to handler response
2. Add missing entries to `METRIC_KEYWORD_MAP`: `"imor"`, `"icor"`, `"icap"` → correct columns
3. Fix `"capitalización"` mapping from `"icap"` to `"icap_total"`

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
