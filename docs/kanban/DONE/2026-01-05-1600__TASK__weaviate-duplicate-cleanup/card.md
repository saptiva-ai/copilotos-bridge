---
id: "TASK-2026-01-05-1600__weaviate-duplicate-cleanup"
title: "Fix Weaviate Ontology_Term_V2 duplicates and organize collections"
status: "DONE"
phase: "Complete"
date: "2026-01-06"
assignee: "Gemini"
completion_note: "Merged into TASK-2026-01-02-2048__complete-hu4-cas. Duplicates resolved via ETL v2.0 idempotence and Weaviate Cloud migration."
---
  - "Manual cleanup: Delete IMOR/ICOR duplicates with source='regulatory_concepts' from Ontology_Term_V2"
  - "Fix ETL deduplication: Modify _merge_seed_terms() to ensure unique terms by name (case-insensitive)"
  - "Verify collection deletion: Ensure _load_to_weaviate() properly deletes before recreating"
  - "Re-run ETL with deduplication fix and reload Weaviate"
  - "Validate: Verify IMOR/ICOR/ICAP have correct definitions + formulas"
  - "Document: Collection organization best practices and versioning strategy"
scope_out:
  - "BankingGlossaryV5 investigation (separate task if needed)"
  - "Ontology_Term (4,418 objects) legacy collection deletion (wait 2-week stability period)"
  - "Production code changes (WeaviateOntologyService works correctly)"
  - "New feature development"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands: []
pr_files: []
test_status: ""
---

# Summary
- **Objective**: Fix duplicate seed terms (IMOR/ICOR) in Weaviate Ontology_Term_V2 that are causing incorrect data to be returned, blocking HU4 acceptance
- **Constraints**: Production system using Ontology_Term_V2 - must maintain uptime, no breaking changes to WeaviateOntologyService
- **Context**: Unblocks HU4 task (TASK-2026-01-02-2048__complete-hu4-cas) CA-02/CA-03 acceptance criteria

# Problem Statement

## Root Cause
**Duplicate entries in Ontology_Term_V2 causing incorrect data returns:**
- IMOR: 2 objects (incorrect from `regulatory_concepts` + correct from `ontology_seed_terms`)
- ICOR: 2 objects (incorrect from `regulatory_concepts` + correct from `ontology_seed_terms`)
- ICAP: 1 object (correct - override worked)

**Why duplicates exist:**
1. ETL `_merge_seed_terms()` correctly overrides duplicates in Python list (`self.terms`)
2. BUT Weaviate still contains old duplicates from previous loads
3. Collection deletion in `_load_to_weaviate()` may have failed or been incomplete
4. When querying by name, Weaviate returns first match (the incorrect one)

## Evidence
**ETL Output** (`data/results/etl_v2_results/ontology_terms_v2.json`):
- 581 terms total
- Seed merge executes correctly (Step 4.7 shows "Merged 3 seed terms")
- But Weaviate collection has 583-584 objects (2-3 more than expected)

**Weaviate Query Results**:
```
IMOR:
  #1 - "IMOR total - Detalle del reporte regulatorio" (regulatory_concepts) ❌ WRONG
  #2 - "Porcentaje de cartera vencida..." + Formula (ontology_seed_terms) ✅ CORRECT

ICOR:
  #1 - "ICOR total - Detalle del reporte regulatorio" (regulatory_concepts) ❌ WRONG
  #2 - "Porcentaje de reservas..." + Formula (ontology_seed_terms) ✅ CORRECT
```

## Impact
- **Priority**: P0 - Blocking HU4 acceptance
- **User Impact**: Queries for IMOR/ICOR return wrong definitions without formulas
- **CA Status**: CA-02/CA-03 failing (definitions + formulas missing)
- **Remediation Time**: 2-4 hours (cleanup + ETL re-run + validation)

# Blocked By
None (ready to start)

# Blocks
- TASK-2026-01-02-2048__complete-hu4-cas (HU4 CAS completion - waiting for correct seed data)

# Related Tasks
- TASK-2026-01-02-2048__complete-hu4-cas (parent task - HU4 validation)

# Current Weaviate State
**Collections:**
- `Ontology_Term_V2`: 583 objects ← **PRODUCTION** (has duplicates)
- `Ontology_Term`: 4,418 objects ← **LEGACY** (deprecated, not used)
- `BankingGlossaryV5`: 204 objects ← **OTHER SYSTEM** (not used by bank-advisor)

**Production Code:**
- ✅ Uses `Ontology_Term_V2` correctly (`src/bankadvisor/services/weaviate_ontology_service.py:83`)
- ✅ ETL loads to `Ontology_Term_V2` correctly
- ❌ Duplicates cause incorrect results

# Solution Approach (Hybrid: Manual + ETL Fix)

## Phase 1: Immediate Fix (Manual Cleanup)
**Action**: Delete duplicate IMOR/ICOR with `source="regulatory_concepts"` from Weaviate
**Tool**: Python script using Weaviate client
**Verification**: Query for IMOR/ICOR and confirm only 1 object each with correct source

## Phase 2: Preventive Fix (ETL Deduplication)
**File**: `archive/scripts/etl_ontology_v2_0.py`
**Changes**:
1. Modify `_merge_seed_terms()` to use dict-based deduplication (case-insensitive name keys)
2. Ensure seeds override existing terms completely (DELETE then INSERT, not UPDATE)
3. Add verification step to check for duplicates before saving results

**Code Pattern**:
```python
def _merge_seed_terms(self) -> int:
    # Build dict to track unique terms by name (case-insensitive)
    final_terms = {}

    # First pass: Add all non-seed terms
    for term in self.terms:
        if term.source != "ontology_seed_terms":
            final_terms[term.name.lower()] = term

    # Second pass: Override with seeds (seeds have priority)
    for seed_term in seed_terms_list:
        key = seed_term.name.lower()
        if key in final_terms:
            print(f"   Overriding '{seed_term.name}' (was: {final_terms[key].source})")
        final_terms[key] = seed_term

    # Replace self.terms with deduplicated list
    self.terms = list(final_terms.values())
    return len(seed_terms_list)
```

## Phase 3: Verify Collection Deletion
**File**: `archive/scripts/etl_ontology_v2_0.py` - `_load_to_weaviate()`
**Changes**:
```python
# Before creating collection
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)
    print(f"   Deleted existing collection: {collection_name}")

    # VERIFY deletion
    if client.collections.exists(collection_name):
        raise RuntimeError(f"Failed to delete collection {collection_name}")
```

## Phase 4: Re-run & Validate
1. Re-run ETL with fixes: `python archive/scripts/etl_ontology_v2_0.py`
2. Verify Weaviate has exactly 581 objects (no duplicates)
3. Query IMOR/ICOR/ICAP and verify correct definitions + formulas
4. Update HU4 validate.md with CA-02/CA-03 PASS results

# Files to Modify

## Critical
1. `archive/scripts/etl_ontology_v2_0.py` - Fix deduplication in `_merge_seed_terms()` and `_load_to_weaviate()`
2. **New file**: `scripts/cleanup_weaviate_duplicates.py` - One-time cleanup script

## Documentation
3. `docs/kanban/DOING/TASK-2026-01-02-2048__complete-hu4-cas/validate.md` - Update CA-02/CA-03 results after fix
4. **New file**: `docs/architecture/weaviate_collections.md` - Document collection organization strategy

# Success Criteria
✅ IMOR/ICOR/ICAP return correct definitions with formulas
✅ No duplicates in Ontology_Term_V2 (exactly 581 objects)
✅ CA-02/CA-03 validation PASS
✅ ETL deduplication prevents future duplicates
✅ Collection deletion verified to work correctly
✅ Best practices documented

# Best Practices Documented

## Collection Naming Convention
```
{Domain}_{Version}
Examples:
- Ontology_Term_V2 (current)
- Ontology_Term_V3 (future)
- NOT: Ontology_Term (unversioned = deprecated)
```

## Deduplication Strategy
1. **At ETL**: Ensure unique terms by canonical key (lowercase name)
2. **At Load**: Verify no duplicates before Weaviate insert
3. **At Query**: Filter by source priority if needed (fallback)

## Migration Path
```
V1 (Ontology_Term) → V2 (Ontology_Term_V2) → V3 (future)
- Keep old version for 2 weeks
- Verify new version works
- Delete old version after stability confirmed
```

# Updates
- 2026-01-05 16:00 - Created. Identified during HU4 validation (TASK-2026-01-02-2048). Root cause: Weaviate duplicates causing incorrect seed term data returns. Hybrid approach (manual cleanup + ETL fix) recommended.
