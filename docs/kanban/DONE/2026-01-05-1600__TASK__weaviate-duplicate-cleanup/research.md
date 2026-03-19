# Research: Weaviate Duplicate Investigation

## Investigation Timeline

### 2026-01-05 15:00 - Initial Discovery
**Context**: HU4 validation (TASK-2026-01-02-2048) showing CA-02/CA-03 failures

**Finding**: IMOR/ICOR/ICAP in Weaviate have incorrect definitions and missing formulas

**Initial Hypothesis**: Seed terms not merged by ETL

### 2026-01-05 15:15 - ETL Code Review
**File**: `archive/scripts/etl_ontology_v2_0.py`

**Finding**: `_merge_seed_terms()` method EXISTS and executes correctly
- Step 4.7 in pipeline shows "Merged 3 seed terms"
- Seeds are correctly loaded from `data/ontology_seed_terms.json`
- Override logic appears correct

**Revised Hypothesis**: ETL merges correctly in Python, but Weaviate has stale data

### 2026-01-05 15:30 - Weaviate Schema Investigation
**Query**: Check all collections in Weaviate

**Results**:
```python
Collections found: 3
1. Ontology_Term_V2: 583 objects (PRODUCTION)
2. Ontology_Term: 4,418 objects (LEGACY)
3. BankingGlossaryV5: 204 objects (OTHER)
```

**Key Finding**: 583 objects in V2, but ETL output has only 581 terms
→ **Indicates 2-3 extra objects (duplicates?)**

### 2026-01-05 15:45 - Duplicate Detection
**Query**: Search for IMOR by name in Ontology_Term_V2

**Results**:
```
IMOR: Found 2 object(s)
  Object #1:
    - name: IMOR
    - definition: "IMOR total - Detalle del reporte regulatorio"
    - source: regulatory_concepts
    - formula_text: null

  Object #2:
    - name: IMOR
    - definition: "Porcentaje de cartera vencida..."
    - source: ontology_seed_terms
    - formula_text: "IMOR = (Cartera Vencida / Cartera Total) * 100"
```

**Confirmation**: ICOR also has 2 objects with same pattern

**Root Cause Identified**:
- Weaviate has duplicate entries from different sources
- Query returns first match (the wrong one from regulatory_concepts)
- ETL merge works in Python but doesn't clean Weaviate before reload

## Data Verification

### Source File Analysis

**File**: `data/ontology_seed_terms.json`
```json
[
  {
    "name": "IMOR",
    "definition": "Porcentaje de cartera vencida...",
    "formula_text": "IMOR = (Cartera Vencida / Cartera Total) * 100",
    "source": "ontology_seed_terms"
  },
  {
    "name": "ICOR",
    "definition": "Porcentaje de reservas...",
    "formula_text": "ICOR = (Reservas / Cartera Vencida) * 100",
    "source": "ontology_seed_terms"
  },
  {
    "name": "ICAP",
    "definition": "Mide la suficiencia de capital...",
    "formula_text": "ICAP = (Capital Neto / Activos Ponderados) * 100",
    "source": "ontology_seed_terms"
  }
]
```
**Status**: ✅ Correct data with formulas

**File**: `data/results/etl_v2_results/ontology_terms_v2.json`
**Analysis**: 581 terms total, seeds correctly merged in Python output
**Status**: ✅ ETL output correct

**Weaviate Ontology_Term_V2**:
**Analysis**: 583 objects (2 extra), duplicates found
**Status**: ❌ Stale duplicates persist

## ETL Pipeline Analysis

### Current Flow (Step 4.7)
```
1. Load regulatory_concepts (includes IMOR/ICOR/ICAP with wrong definitions)
2. Load other sources
3. _merge_seed_terms() - Override IMOR/ICOR/ICAP in self.terms ✅
4. _save_results() - Write ontology_terms_v2.json ✅
5. _load_to_weaviate() - Insert into Ontology_Term_V2 ❌ (doesn't remove old duplicates)
```

### Collection Deletion Logic
**File**: `archive/scripts/etl_ontology_v2_0.py:1044-1048`
```python
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)
    print(f"   Deleted existing collection: {collection_name}")
```

**Issue**: No verification that deletion succeeded before creating new collection

**Hypothesis**: Collection deletion may be failing silently or timing out

## Weaviate Query Behavior

**Test Query**: `search_similar_terms("IMOR")`
**Returns**: First object found (by vector similarity)
**Problem**: First object is the incorrect one from regulatory_concepts

**Why**: Weaviate returns results by relevance/similarity, not by source priority

## Production Code Review

**File**: `src/bankadvisor/services/weaviate_ontology_service.py:83`
```python
DEFAULT_COLLECTION = "Ontology_Term_V2"
```
**Status**: ✅ Correctly using V2 collection

**No code changes needed** - production service is correct, data issue only

## Legacy Collections Analysis

### Ontology_Term (4,418 objects)
**Usage**: Deprecated, replaced by Ontology_Term_V2
**References**: Need to grep codebase to verify no active usage
**Action**: Delete after 2-week stability period of V2

### BankingGlossaryV5 (204 objects)
**Usage**: Unknown - possibly separate system/plugin
**Action**: Investigate in separate task if needed

## Deduplication Strategies Research

### Option 1: ETL-Level Deduplication (Recommended)
**Approach**: Use dict with case-insensitive keys
```python
final_terms = {}
for term in self.terms:
    key = term.name.lower()
    # Seeds override non-seeds
    if key not in final_terms or term.source == "ontology_seed_terms":
        final_terms[key] = term
self.terms = list(final_terms.values())
```
**Pros**: Prevents duplicates at source, clean data
**Cons**: Requires ETL re-run

### Option 2: Query-Level Filtering
**Approach**: Filter results by source priority in WeaviateOntologyService
```python
# Prioritize ontology_seed_terms > other sources
results.sort(key=lambda x: 0 if x.source == "ontology_seed_terms" else 1)
return results[0]
```
**Pros**: Quick fix, no ETL re-run
**Cons**: Bandaid solution, duplicates remain

### Option 3: Manual Cleanup + Verification
**Approach**: Delete specific duplicates, add verification
```python
# Delete IMOR/ICOR with source="regulatory_concepts"
for name in ["IMOR", "ICOR"]:
    delete_where = {
        "path": ["name"],
        "operator": "Equal",
        "valueText": name,
        "path": ["source"],
        "operator": "Equal",
        "valueText": "regulatory_concepts"
    }
    collection.delete_many(where=delete_where)
```
**Pros**: Immediate fix, surgical precision
**Cons**: Manual intervention, doesn't prevent future duplicates

## Recommended Solution: Hybrid (1 + 3)

### Phase 1: Manual Cleanup (Immediate)
Delete IMOR/ICOR duplicates with source="regulatory_concepts"

### Phase 2: ETL Fix (Preventive)
Implement dict-based deduplication in `_merge_seed_terms()`

### Phase 3: Verification (Safety)
Add verification step in `_load_to_weaviate()` to ensure deletion succeeds

## Files to Read for Implementation

1. `archive/scripts/etl_ontology_v2_0.py` - Main ETL pipeline
2. `data/ontology_seed_terms.json` - Seed data source
3. `src/bankadvisor/services/weaviate_ontology_service.py` - Production query service
4. `data/results/etl_v2_results/ontology_terms_v2.json` - ETL output to verify

## External Resources (for best practices research)

### Weaviate Documentation
- Schema versioning: https://weaviate.io/developers/weaviate/manage-data/collections
- Deletion behavior: https://weaviate.io/developers/weaviate/manage-data/delete
- Duplicate prevention: https://weaviate.io/developers/weaviate/config-refs/schema

### Vector Database Best Practices
- Deduplication strategies
- Schema migration patterns
- Production deployment safety

## Questions for User (if needed)

1. Should we delete Ontology_Term (legacy, 4,418 objects) now or wait?
   - Recommendation: Wait 2 weeks for V2 stability
2. Is BankingGlossaryV5 used by any system we should be aware of?
   - Recommendation: Investigate in separate task
3. Preferred approach: Manual cleanup first, or full ETL re-run?
   - Recommendation: Manual cleanup (Phase 1) for immediate unblock, then ETL fix (Phase 2) for prevention

## Summary

**Root Cause**: Weaviate collection deletion not properly verified, leading to duplicate entries persisting across ETL runs

**Impact**: IMOR/ICOR queries return incorrect definitions without formulas, blocking HU4 CA-02/CA-03

**Solution**: Hybrid approach - manual cleanup + ETL deduplication fix + verification

**Timeline**: 2-4 hours (cleanup + ETL re-run + validation)

**Risk**: Low - surgical fix to specific duplicates, no production code changes needed
