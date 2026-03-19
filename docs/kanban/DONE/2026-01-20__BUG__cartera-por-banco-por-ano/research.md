# Research: BUG-CH-006 - Cartera Por Banco Por Ano

## Investigation Date: 2026-01-20

## 1. Request Flow Architecture

```
User Query: "cartera hipotecaria por banco por ano"
    |
    v
[Frontend] --> [Backend API /api/chat]
    |
    v
[Backend: tool_execution_service.py]
    |
    +--> Detects "bank_advisor" tool needed
    |
    +--> Calls bank-advisor /api/v1/query
    |
    v
[Bank-Advisor: main.py -> process_analytics_query()]
    |
    +--> Uses query_spec_parser.py to create QuerySpec
    |    - Sets intent based on ranking_keywords
    |    - Extracts metric via synonyms.yaml
    |    - Extracts banks (empty for this query)
    |
    +--> Uses clarification_service.py to determine_strategy()
    |    - Checks: has_metric, has_bank, intent, confidence
    |
    v
[ClarificationService.determine_strategy()]
    |
    +--> If intent="ranking" + has_metric + has_confidence → NONE (no clarification)
    |    ELSE IF metric + no bank + intent not in ["ranking", "bank_knowledge"] → HARD_ASK
    |
    v
[Response to User]
```

## 2. Key Investigation Points

### 2.1 Query Spec Parser Intent Detection

File: `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py` (lines 822-857)

**Finding**: "por banco" IS in ranking_keywords (line 845)
```python
ranking_keywords = [
    ...
    # BUG-CH-006: "por banco" patterns indicate breakdown (all banks)
    "por banco", "por institución", "por institucion",
    ...
]
is_ranking = any(kw in query_lower for kw in ranking_keywords)
```

**Expected**: "cartera hipotecaria por banco por año" → is_ranking = True → intent = "ranking"

### 2.2 Metric Extraction

File: `plugins/bank-advisor-private/config/synonyms.yaml`

**Finding**: "cartera hipotecaria" IS mapped to cartera_vivienda_total
```yaml
cartera_vivienda_total:
  display_name: "Cartera Vivienda"
  column: "cartera_vivienda_total"
  synonyms:
    - "cartera vivienda"
    - "vivienda"
    - "cartera hipotecaria"  # <-- MATCHES
```

**Expected**: metric = "CARTERA_VIVIENDA" should be extracted

### 2.3 Clarification Strategy

File: `plugins/bank-advisor-private/src/bankadvisor/services/clarification_service.py` (lines 56, 117-130)

```python
NO_BANK_REQUIRED_INTENTS = ["ranking", "bank_knowledge"]

# In determine_strategy():
# Line 122-123:
if has_metric and spec.intent == "ranking" and has_confidence:
    return ClarificationStrategy.NONE, "Ranking query - bank not required"

# Line 129-130:
if has_metric and not has_bank and spec.intent not in NO_BANK_REQUIRED_INTENTS:
    return ClarificationStrategy.HARD_ASK, "Bank required for this query"
```

**Expected**: If intent="ranking" + has_metric=True + confidence>=0.7 → Should return NONE (no clarification)

## 3. Findings - What Should Happen vs What IS Happening

### Expected Flow:
1. Query: "cartera hipotecaria por banco por ano"
2. "por banco" matches → is_ranking = True → intent = "ranking"
3. "cartera hipotecaria" matches synonyms → metric = "CARTERA_VIVIENDA"
4. clarification_service.determine_strategy():
   - has_metric = True ✅
   - spec.intent = "ranking" ✅
   - has_confidence = True (needs to verify)
   - → Returns NONE (no clarification needed)
5. Query executes → Returns chart with all banks by year

### What IS Happening:
1. System asks for clarification asking for metric AND bank
2. Shows menu with options instead of data

### Possible Root Causes:
1. **Metric NOT being extracted** - config not loading synonyms correctly?
2. **Intent NOT being set to "ranking"** - query_spec_parser issue?
3. **Confidence too low** - confidence < 0.7 causing fallback?
4. **Production code differs** - deployment issue?

## 4. Deep Dive Analysis (2026-01-20 Session 2)

### 4.1 Config Service `find_metric()` Logic

File: `plugins/bank-advisor-private/src/bankadvisor/config_service.py` (lines 171-213)

```python
def find_metric(self, text: str) -> Optional[str]:
    """Uses regex word boundary matching for aliases"""
    pattern_alias = r'\b' + re.escape(alias_lower) + r'(?:s|es|dos)?\b'
    if re.search(pattern_alias, text_lower):
        # Match found
```

**For "cartera hipotecaria por banco por año":**
- Pattern: `\bcartera hipotecaria(?:s|es|dos)?\b`
- Should match ✅

### 4.2 Critical Decision Points

The clarification decision happens in `determine_strategy()`:

```python
# Line 110-112 (clarification_service.py)
has_metric = bool(spec.metric)        # True if metric extracted
has_bank = bool(spec.bank_names)      # False (ranking = no bank)
has_confidence = spec.confidence_score >= 0.7  # Need to verify!

# Line 122-123 - RANKING PATH (should hit this)
if has_metric and spec.intent == "ranking" and has_confidence:
    return ClarificationStrategy.NONE, "Ranking query - bank not required"

# Line 129-130 - HARD_ASK PATH (buggy behavior)
if has_metric and not has_bank and spec.intent not in NO_BANK_REQUIRED_INTENTS:
    return ClarificationStrategy.HARD_ASK, "Bank required for this query"
```

### 4.3 Hypothesis: Root Cause

The bug hits the HARD_ASK path if ANY of these conditions fail:
1. `has_metric = False` → Metric extraction failed
2. `spec.intent != "ranking"` → Intent not detected as ranking
3. `has_confidence = False` (confidence < 0.7) → Low confidence skip

**Most Likely Root Cause:**
- **Intent is not "ranking"** - The heuristic parser might be defaulting to "evolution"
- OR the LLM parser is being used and returns a different intent
- OR the "por banco" keyword check runs BEFORE intent is determined in another code path

### 4.4 Key Log Statement for Debugging

In `main.py` lines 700-708:
```python
logger.info(
    "hu3_nlp.clarification_strategy",
    strategy=strategy.value,
    reason=reason,
    metric=spec.metric,
    banks=spec.bank_names,
    intent=spec.intent,
    confidence=spec.confidence_score
)
```

**To debug: Check production logs for this log entry with the exact query**

## 5. E2E Test to Add

Add to `tests/e2e/regression/test_ranking_detection.py`:

```python
# --- CATEGORY: BUG-CH-006 Breakdown Queries ---
BUG_CH_006_CASES = [
    RankingTestCase(
        100,
        "cartera hipotecaria por banco por ano",
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda", "hipotecaria"],
    ),
    RankingTestCase(
        101,
        "cartera hipotecaria por banco por año",  # with accent
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda"],
    ),
    RankingTestCase(
        102,
        "quiero que me des la cartera hipotecaria por banco por año",  # user's exact query
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda"],
    ),
]
```

Also add unit test to `plugins/bank-advisor-private/tests/unit/test_clarification_service.py`:

```python
def test_scenario_cartera_hipotecaria_por_banco(self, service):
    """
    BUG-CH-006: "cartera hipotecaria por banco por año"
    Should: NONE → Ranking query, bank not required
    """
    spec = QuerySpec(
        metric="CARTERA_VIVIENDA_TOTAL",
        bank_names=[],  # Empty = all banks for ranking
        time_range=TimeRangeSpec(type="year", start_date="2024-01-01"),
        intent="ranking",  # Critical: must be "ranking"
        confidence_score=0.85,
        requires_clarification=False,
    )

    strategy, reason = service.determine_strategy(spec)
    assert strategy == ClarificationStrategy.NONE, \
        f"Expected NONE for ranking query, got {strategy} ({reason})"
```

## 6. UPDATED Investigation (2026-02-08) — Handler Priority Collision

### 6.1 New Evidence

PROD test on 2026-02-08 shows the query returns data but **wrong data**:
```
metric_name: "CARTERA VIVIENDA POR PRODUCTO HIPOTECARIO"
bank_names: []
```
Response says: "Los datos no incluyen desglose por banco ni por año completo"

This is NOT a clarification bug anymore. The system processes the query but
routes it to the **wrong handler**.

### 6.2 Root Cause — Handler Chain Priority

The QueryRouter uses a Chain of Responsibility pattern (query_router.py).
Handler order from `handlers/__init__.py:get_specific_handlers()`:

```
Position  Handler                    Matched?
────────  ─────────────────────────  ────────
1         MultiMetricHandler         No
2         MetricasFinancierasHandler No
3         EvolucionBancoHandler      No
4         ResumenSistemaHandler      No
5         CarteraActividadHandler    No
6         CarteraTamanoHandler       No
7         CarteraDestinoHandler      No
8  >>>    ViviendaPerfilHandler      YES ← captures query here
9         CarteraRegionHandler       (never reached)
10        ComparativeRatioHandler    (never reached)
11        MarketShareHandler         (never reached)
12        SegmentHandler             (never reached)
13        InstitutionRankingHandler  (never reached)
```

### 6.3 Why ViviendaPerfilHandler Matches

`vivienda_perfil_handler.py` lines 99-106:
```python
has_vivienda = any(kw in query_lower for kw in VIVIENDA_GENERAL_KEYWORDS)
# "hipotecaria" is in VIVIENDA_GENERAL_KEYWORDS → True

has_breakdown = any(kw in query_lower for kw in [
    "distribución", "distribucion", "desglose", "por", ...
])
# "por" appears in "por banco por año" → True

return has_vivienda and has_breakdown  # True + True → MATCH
```

The `matches()` is too greedy: it triggers on ANY "por" regardless of what
follows. "por banco" (ranking intent) and "por género" (profile intent) are
treated the same.

### 6.4 Why InstitutionRankingHandler Would NOT Match Either

`ranking_handler.py` lines 69-123:
- `has_ranking_keyword`: "ranking" not in query → False
- `has_implicit_ranking`: needs "mayor", "menor", "top", etc → False
- `has_top_n`: no "top N" pattern → False
- All match conditions require at least one of the above → **Would return False**

So even if ViviendaPerfilHandler didn't capture it, the ranking handler
ALSO wouldn't match "cartera hipotecaria por banco por año".

### 6.5 The "por banco" Signal is Lost

The `query_spec_parser.py` correctly detects "por banco" as ranking (line 882),
but this classification happens INSIDE `process_analytics_query()` which runs
AFTER `route_and_enrich()` fails. However, `route_and_enrich()` succeeds
because ViviendaPerfilHandler matches first, so the parser never gets a chance
to classify it as ranking.

Flow:
```
execute_bank_analytics()
  → process_analytics_query()
    → orchestrator.route_and_enrich()        ← ViviendaPerfilHandler matches here
      → query_router.route()
        → ViviendaPerfilHandler.matches() → True → handle() → product data
      → Returns handler response
    → Returns immediately (line 534-535)     ← Never reaches parser below
    → [SKIPPED] QuerySpecParser.parse()      ← Would have classified as "ranking"
    → [SKIPPED] ClarificationService         ← Would have returned NONE
```

### 6.6 Fix Strategy (Two-Layer)

**Layer 1: ViviendaPerfilHandler guard** — Exclude queries with "por banco/institución":
```python
# In ViviendaPerfilHandler.matches():
# If "por banco" or "por institución" → NOT a vivienda profile query
RANKING_ESCAPE = ["por banco", "por institución", "por institucion"]
if any(esc in query_lower for esc in RANKING_ESCAPE):
    return False
```

**Layer 2: InstitutionRankingHandler expansion** — Add "por banco" as ranking signal:
```python
# In InstitutionRankingHandler.matches():
# Pattern 4: "por banco" + rankable metric (ranking breakdown)
has_bank_breakdown = "por banco" in query_lower or "por institución" in query_lower
if has_bank_breakdown and has_rankable_metric:
    return True
```

### 6.7 Files to Modify

1. `plugins/bank-advisor-private/src/bankadvisor/handlers/vivienda_perfil_handler.py`
   - Add ranking escape guard in `matches()`
2. `plugins/bank-advisor-private/src/bankadvisor/handlers/ranking_handler.py`
   - Add "por banco" + metric pattern in `matches()`
   - Handle `cartera_vivienda_total` metric mapping in `handle()`
3. Tests: unit tests for both handlers with the specific query

## 7. Original Action Plan (2026-01-20)

1. **Add E2E test case** to `test_ranking_detection.py` for "cartera hipotecaria por banco por año"
2. **Add unit test** to verify ClarificationService returns NONE for ranking queries
3. **Check production logs** for "hu3_nlp.clarification_strategy" to see actual values
4. **If intent != ranking**: Fix in `query_spec_parser.py` - ensure "por banco" triggers ranking
5. **If metric is empty**: Fix in `config_service.py` - verify synonyms.yaml loaded
