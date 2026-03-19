# Plan: BUG-CH-006 - Cartera Por Banco Por Año Fix (v2)

> Updated 2026-02-08: New root cause found (handler priority collision).
> Previous plan addressed intent/clarification. This plan addresses handler routing.

## Root Cause (Updated)

`ViviendaPerfilHandler` (position 8 in handler chain) captures the query before
`InstitutionRankingHandler` (position 13) can evaluate it.

- `"hipotecaria"` matches `VIVIENDA_GENERAL_KEYWORDS`
- `"por"` (from "por banco") matches breakdown keywords
- Result: returns product breakdown instead of bank ranking

Additionally, `InstitutionRankingHandler` wouldn't match either because
it doesn't recognize "por banco" as a ranking signal.

## Phase 1: Handler Guard Fix (ViviendaPerfilHandler)

**File**: `plugins/bank-advisor-private/src/bankadvisor/handlers/vivienda_perfil_handler.py`

Add guard in `matches()` to exclude queries with "por banco/institución":

```python
def matches(self, user_query, entities=None, spec=None) -> bool:
    query_lower = user_query.lower()

    # Guard: "por banco/institución" = ranking intent, not vivienda profile
    RANKING_ESCAPE = ["por banco", "por institución", "por institucion"]
    if any(esc in query_lower for esc in RANKING_ESCAPE):
        return False

    # ... rest of existing logic unchanged
```

## Phase 2: Ranking Pattern Expansion (InstitutionRankingHandler)

**File**: `plugins/bank-advisor-private/src/bankadvisor/handlers/ranking_handler.py`

### 2.1 Add "por banco" matching pattern

In `matches()`, add a new condition:

```python
# Pattern 5: "por banco/institución" + rankable metric (breakdown)
has_bank_breakdown = any(
    kw in query_lower
    for kw in ["por banco", "por institución", "por institucion"]
)
if has_bank_breakdown and has_rankable_metric:
    return True
```

### 2.2 Improve metric resolution in `handle()`

Replace hardcoded metric selection (line 185) with smarter mapping:

```python
# Map query keywords to specific metrics
METRIC_MAP = {
    "hipotecaria": "cartera_vivienda_total",
    "vivienda": "cartera_vivienda_total",
    "comercial": "cartera_comercial_total",
    "consumo": "cartera_consumo_total",
    "gobierno": "entidades_gubernamentales_total",
    "morosidad": "imor",
    "mora": "imor",
    "capitalización": "icap",
    "capitalizacion": "icap",
}

metric = "activo_total"  # default
for keyword, mapped_metric in METRIC_MAP.items():
    if keyword in query_lower:
        metric = mapped_metric
        break
# Fallback: if "cartera" mentioned but no specific type
if metric == "activo_total" and "cartera" in query_lower:
    metric = "cartera_total"
```

### 2.3 Add "hipotecaria"/"vivienda" to RANKABLE_METRICS

```python
RANKABLE_METRICS = [
    "cartera", "activo", "imor", "icap", "icor",
    "captacion", "captación", "capital", "utilidad",
    "rentabilidad", "roa", "roe", "reserva",
    "hipotecaria", "hipotecario", "vivienda",  # NEW
    "comercial", "consumo",                     # NEW
]
```

## Phase 3: Unit Tests

### 3.1 ViviendaPerfilHandler guard test

```python
def test_vivienda_handler_excludes_por_banco():
    handler = ViviendaPerfilHandler()
    # Should NOT match - "por banco" is ranking intent
    assert not handler.matches("cartera hipotecaria por banco por año")
    assert not handler.matches("vivienda por institución")
    # Should still match - vivienda profile queries
    assert handler.matches("cartera hipotecaria por género")
    assert handler.matches("vivienda por producto")
```

### 3.2 InstitutionRankingHandler expansion test

```python
def test_ranking_handler_matches_por_banco():
    handler = InstitutionRankingHandler()
    # Should match - "por banco" + rankable metric
    assert handler.matches("cartera hipotecaria por banco por año")
    assert handler.matches("cartera por banco")
    assert handler.matches("imor por institución")
    # Should NOT match - no rankable metric
    assert not handler.matches("clima por banco")
```

## Phase 4: Validation

```bash
# Unit tests
cd plugins/bank-advisor-private
python -m pytest tests/ -v -k "vivienda or ranking"

# E2E ranking detection
python tests/e2e/regression/test_ranking_detection.py

# Manual PROD test (via tunnel)
python3 -c "
import requests, json, time
PROD = 'http://localhost:18000'
resp = requests.post(f'{PROD}/api/auth/login', json={'identifier':'demo','password':'Demo1234'})
token = resp.json()['access_token']
r = requests.post(f'{PROD}/api/chat',
    headers={'Authorization': f'Bearer {token}'},
    json={'message': 'cartera hipotecaria por banco por año',
          'conversation_id': f'verify-{int(time.time())}'},
    timeout=90)
data = r.json()
print(f'Type: {data.get(\"type\")}')
artifact = data.get('artifact', {})
print(f'Metric: {artifact.get(\"metric_name\")}')
print(f'Banks: {artifact.get(\"bank_names\")}')
"
```

## Files to Modify

| File | Change |
|------|--------|
| `plugins/.../handlers/vivienda_perfil_handler.py` | Add ranking escape guard |
| `plugins/.../handlers/ranking_handler.py` | Add "por banco" pattern + metric mapping |
| Unit tests (inline in existing test files) | Guard + expansion tests |

## Rollback Plan

Both changes are additive guards. To rollback:
1. Remove the `RANKING_ESCAPE` guard from vivienda handler
2. Remove the "por banco" pattern from ranking handler
3. Both handlers revert to previous behavior
