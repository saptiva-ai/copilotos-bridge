---
status: REVIEW
---
# BUG: Ranking intent no detecta patrón "Lista de X de mayor a menor"

**Prioridad:** P3
**Fecha:** 2026-02-05
**Status:** DOING → REVIEW (verificado en PROD)

---

## Resumen

El patrón de query "Lista de bancos por X de mayor a menor" no activa el intent de ranking, por lo que no genera gráfica.

## Evidencia

Test `test_ranking_detection.py` - 39/40 pasaron (97.5%)

**Falló:**
- Test 51: "Lista de bancos por capitalización de mayor a menor" → No chart returned

**Queries similares que SÍ funcionan:**
- "Top bancos por capitalización" ✅
- "Ranking de capitalización" ✅
- "¿Cuáles son los bancos más capitalizados?" ✅
- "Posiciones de los bancos por cartera" ✅

## Causa Raíz

`InstitutionRankingHandler.IMPLICIT_RANKING` no incluía:
- "de mayor a menor" / "de menor a mayor" (ordering patterns)
- "lista de" (listing intent)
- "mayor" / "menor" singular (solo tenía "mayores" / "menores" plural)

Además, `RANKABLE_METRICS` no tenía "capitalización" / "capitalizacion" / "solvencia" explícitos (solo matcheaba vía substring de "capital").

## Fix Implementado (2026-02-08)

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/handlers/ranking_handler.py`

1. Agregado a `IMPLICIT_RANKING`: `"de mayor a menor"`, `"de menor a mayor"`, `"lista de"`
2. Agregado a `RANKABLE_METRICS`: `"capitalización"`, `"capitalizacion"`, `"solvencia"`
3. Detección de `ascending`: "de menor a mayor" → `ascending=True` en `RankingRequest`

**Tests**: 47/47 passed (6 nuevos tests para este bug)

### Validación E2E en PROD (2026-02-08)

Test: `tests/e2e/regression/test_feedback_replay_2026_02_08.py`
Target: `http://localhost:18000` (SSH tunnel a PROD)

| # | ID | Query | Resultado | Detalle |
|---|-----|-------|-----------|---------|
| 1 | RANK-051 | Lista de bancos por capitalización de mayor a menor | PASSED | Ranking chart OK: 19 banks |
| 2 | RANK-051b | lista de bancos por IMOR de menor a mayor | PASSED | Ranking chart OK: 19 banks |
| 3 | RANK-051c | lista de bancos por IMOR de menor a mayor | PASSED | Ascending order confirmed: 0.00 → 5.62 |

**3/3 PASSED** — En PROD, "por banco" + substring "capital" en "capitalización"
ya activa condition 5 (`has_bank_breakdown && has_rankable_metric`) del handler.
Los cambios en IMPLICIT_RANKING agregan cobertura explícita para el patrón
"de mayor a menor" sin depender del fallback por substring.

## Criterios de Aceptación

- [x] "Lista de bancos por capitalización de mayor a menor" genera chart
- [x] "lista de bancos por IMOR de menor a mayor" genera chart (ascending)
- [x] "lista de compras" NO matchea (negative case)
- [x] Tests unitarios pasan (47/47)
- [x] Verificar en PROD — 3/3 E2E replay passed
