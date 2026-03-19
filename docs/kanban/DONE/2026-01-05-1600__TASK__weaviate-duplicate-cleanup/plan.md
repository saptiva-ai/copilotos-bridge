# Implementation Plan: Weaviate Duplicate Cleanup

## Overview
Fix duplicate seed terms (IMOR/ICOR) in Weaviate Ontology_Term_V2 using hybrid approach: immediate manual cleanup + ETL deduplication fix + verification.

**Estimated Time**: 2-4 hours
**Risk Level**: Low (surgical fix, no production code changes)

---

## Phase 1: Manual Cleanup (Immediate Fix)

**Objective**: Delete duplicate IMOR/ICOR entries with source="regulatory_concepts" from Weaviate

### Files
- **New**: `scripts/cleanup_weaviate_duplicates.py`

### Steps

#### 1.1 Create Cleanup Script
**File**: `scripts/cleanup_weaviate_duplicates.py`

```python
#!/usr/bin/env python3
"""
One-time script to delete duplicate IMOR/ICOR entries from Weaviate.
Deletes entries with source="regulatory_concepts", keeping ontology_seed_terms.
"""
import weaviate
from weaviate.classes.query import Filter

def main():
    # Connect to Weaviate
    client = weaviate.connect_to_local(host="localhost", port=8080)

    try:
        collection = client.collections.get("Ontology_Term_V2")

        # Terms to clean
        duplicate_terms = ["IMOR", "ICOR"]

        for term_name in duplicate_terms:
            print(f"\n--- Processing {term_name} ---")

            # Query to find duplicates
            results = collection.query.fetch_objects(
                filters=Filter.by_property("name").equal(term_name),
                limit=10
            )

            print(f"Found {len(results.objects)} object(s) for {term_name}")

            # Display all objects
            for i, obj in enumerate(results.objects, 1):
                print(f"\n  Object #{i}:")
                print(f"    UUID: {obj.uuid}")
                print(f"    Name: {obj.properties.get('name')}")
                print(f"    Source: {obj.properties.get('source')}")
                print(f"    Definition: {obj.properties.get('definition', '')[:80]}...")
                print(f"    Formula: {obj.properties.get('formula_text', 'None')[:80] if obj.properties.get('formula_text') else 'None'}")

            # Delete objects with source="regulatory_concepts"
            deleted_count = 0
            for obj in results.objects:
                if obj.properties.get("source") == "regulatory_concepts":
                    print(f"\n  Deleting object {obj.uuid} (source: regulatory_concepts)")
                    collection.data.delete_by_id(obj.uuid)
                    deleted_count += 1

            print(f"\nDeleted {deleted_count} duplicate(s) for {term_name}")

            # Verify deletion
            verify_results = collection.query.fetch_objects(
                filters=Filter.by_property("name").equal(term_name),
                limit=10
            )
            print(f"After deletion: {len(verify_results.objects)} object(s) remaining")

            # Verify remaining object is correct
            if len(verify_results.objects) == 1:
                obj = verify_results.objects[0]
                if obj.properties.get("source") == "ontology_seed_terms":
                    print(f"✅ Verified: Remaining object has correct source (ontology_seed_terms)")
                else:
                    print(f"⚠️ WARNING: Remaining object source = {obj.properties.get('source')}")
            elif len(verify_results.objects) == 0:
                print(f"⚠️ WARNING: No objects found after deletion!")
            else:
                print(f"⚠️ WARNING: Still {len(verify_results.objects)} objects remaining!")

        print("\n" + "="*60)
        print("CLEANUP COMPLETE")
        print("="*60)

    finally:
        client.close()

if __name__ == "__main__":
    main()
```

#### 1.2 Run Cleanup Script
```bash
# Ensure Weaviate is running
docker ps | grep weaviate

# Run cleanup
python scripts/cleanup_weaviate_duplicates.py
```

#### 1.3 Verify Cleanup
```python
# Query IMOR/ICOR/ICAP to verify correct data
python3 - <<'PYEOF'
import weaviate
from weaviate.classes.query import Filter

client = weaviate.connect_to_local(host="localhost", port=8080)
collection = client.collections.get("Ontology_Term_V2")

for term in ["IMOR", "ICOR", "ICAP"]:
    results = collection.query.fetch_objects(
        filters=Filter.by_property("name").equal(term),
        limit=5
    )
    print(f"\n{term}: {len(results.objects)} object(s)")
    for obj in results.objects:
        print(f"  Source: {obj.properties.get('source')}")
        print(f"  Definition: {obj.properties.get('definition', '')[:80]}")
        print(f"  Formula: {obj.properties.get('formula_text', 'None')[:80] if obj.properties.get('formula_text') else 'None'}")

client.close()
PYEOF
```

**Expected Output**:
```
IMOR: 1 object(s)
  Source: ontology_seed_terms
  Definition: Porcentaje de cartera vencida...
  Formula: IMOR = (Cartera Vencida / Cartera Total) * 100

ICOR: 1 object(s)
  Source: ontology_seed_terms
  Definition: Porcentaje de reservas...
  Formula: ICOR = (Reservas / Cartera Vencida) * 100

ICAP: 1 object(s)
  Source: ontology_seed_terms
  Definition: Mide la suficiencia de capital...
  Formula: ICAP = (Capital Neto / Activos Ponderados) * 100
```

**Success Criteria**:
- ✅ IMOR: 1 object with source="ontology_seed_terms" and formula present
- ✅ ICOR: 1 object with source="ontology_seed_terms" and formula present
- ✅ ICAP: 1 object with source="ontology_seed_terms" and formula present
- ✅ Total Ontology_Term_V2 objects: 581 (down from 583)

---

## Phase 2: ETL Deduplication Fix (Preventive)

**Objective**: Modify ETL to prevent duplicate term insertion using dict-based deduplication

### Files
- **Modify**: `archive/scripts/etl_ontology_v2_0.py`

### Steps

#### 2.1 Modify `_merge_seed_terms()` Method
**File**: `archive/scripts/etl_ontology_v2_0.py` (lines ~903-964)

**Current Logic**:
```python
# Override existing terms with seeds
for term in self.terms:
    if term.name.lower() in existing_terms:
        idx = existing_terms[term.name.lower()]
        self.terms[idx] = term  # Override
```

**New Logic** (dict-based deduplication):
```python
def _merge_seed_terms(self) -> int:
    """
    Merge seed terms (IMOR/ICOR/ICAP) into self.terms.
    Seeds have priority and override any existing terms with same name.
    Returns number of seed terms merged.
    """
    seed_terms_file = self.config.data_dir / "ontology_seed_terms.json"

    if not seed_terms_file.exists():
        print(f"   Seed file not found: {seed_terms_file}")
        return 0

    # Load seed terms
    with open(seed_terms_file, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    print(f"   Loaded {len(seed_data)} seed terms from {seed_terms_file.name}")

    # Convert to OntologyTerm objects
    seed_terms_list = []
    for seed in seed_data:
        seed_term = OntologyTerm(
            term_id=seed.get("term_id", hashlib.sha256(seed["name"].encode()).hexdigest()[:16]),
            name=seed["name"],
            definition=seed.get("definition", ""),
            source="ontology_seed_terms",
            formula_text=seed.get("formula_text"),
            formula_uso=seed.get("formula_uso"),
            formula_variables=seed.get("formula_variables", []),
            synonyms=seed.get("synonyms", []),
            variations=seed.get("variations", []),
            source_refs=seed.get("source_refs", []),
            sql_column=seed.get("sql_column"),
            score=1.0,  # Seeds always have perfect score
            match_type="manual_override",
            acronym_equivalents=seed.get("acronym_equivalents", []),
            category=seed.get("category", ""),
            usage_context=seed.get("usage_context", ""),
            related_terms=seed.get("related_terms", []),
        )
        seed_terms_list.append(seed_term)

    # BUILD DICT FOR DEDUPLICATION (case-insensitive key)
    # This ensures each term name appears exactly once
    final_terms = {}

    # First pass: Add all non-seed terms
    for term in self.terms:
        key = term.name.lower()
        if term.source != "ontology_seed_terms":
            final_terms[key] = term

    # Second pass: Override with seeds (seeds have priority)
    override_count = 0
    add_count = 0
    for seed_term in seed_terms_list:
        key = seed_term.name.lower()
        if key in final_terms:
            old_source = final_terms[key].source
            print(f"   Overriding '{seed_term.name}' with seed term (was: {old_source})")
            override_count += 1
        else:
            print(f"   Adding seed term '{seed_term.name}'")
            add_count += 1

        final_terms[key] = seed_term

    # Replace self.terms with deduplicated list
    self.terms = list(final_terms.values())

    print(f"   Overridden: {override_count}, Added: {add_count}")
    print(f"   Total unique terms after merge: {len(self.terms)}")

    return len(seed_terms_list)
```

**Changes**:
1. Use `final_terms` dict with case-insensitive keys
2. First pass: Add non-seed terms
3. Second pass: Override with seeds (explicit priority)
4. Replace `self.terms` with deduplicated list
5. Add logging for overrides vs additions

#### 2.2 Verify Collection Deletion in `_load_to_weaviate()`
**File**: `archive/scripts/etl_ontology_v2_0.py` (lines ~1044-1070)

**Current Logic**:
```python
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)
    print(f"   Deleted existing collection: {collection_name}")
```

**Enhanced Logic** (add verification):
```python
# Delete existing collection if it exists
if client.collections.exists(collection_name):
    print(f"   Deleting existing collection: {collection_name}")
    client.collections.delete(collection_name)

    # VERIFY deletion succeeded
    import time
    time.sleep(1)  # Brief pause for deletion to complete

    if client.collections.exists(collection_name):
        raise RuntimeError(
            f"Failed to delete collection {collection_name}. "
            f"Collection still exists after deletion attempt."
        )

    print(f"   ✅ Verified: Collection {collection_name} deleted successfully")
```

**Changes**:
1. Add 1-second pause after deletion
2. Verify collection no longer exists
3. Raise error if deletion failed

#### 2.3 Add Deduplication Verification Before Insert
**File**: `archive/scripts/etl_ontology_v2_0.py` (after line ~1051, before insert)

**Add verification step**:
```python
# VERIFY: No duplicates in terms list before inserting
all_terms = list(self.terms)
term_names = [t.name.lower() for t in all_terms]
duplicates = [name for name in set(term_names) if term_names.count(name) > 1]

if duplicates:
    print(f"\n⚠️ WARNING: Duplicates found in terms list!")
    for dup_name in duplicates:
        dup_terms = [t for t in all_terms if t.name.lower() == dup_name]
        print(f"  {dup_name}: {len(dup_terms)} objects with sources: {[t.source for t in dup_terms]}")
    raise ValueError(
        f"Duplicate terms found before Weaviate insert: {duplicates}. "
        f"ETL deduplication failed."
    )

print(f"   ✅ Verified: No duplicates in {len(all_terms)} terms")
```

---

## Phase 3: Re-run ETL & Reload Weaviate

**Objective**: Execute full ETL pipeline with deduplication fixes and reload Weaviate

### Steps

#### 3.1 Backup Current Data (Safety)
```bash
# Backup current Weaviate data (optional but recommended)
curl -s http://localhost:8080/v1/schema > /tmp/weaviate_schema_backup_$(date +%Y%m%d_%H%M%S).json

# Backup ETL output
cp data/results/etl_v2_results/ontology_terms_v2.json \
   data/results/etl_v2_results/ontology_terms_v2.json.backup_$(date +%Y%m%d_%H%M%S)
```

#### 3.2 Run ETL with Fixes
```bash
cd plugins/bank-advisor-private

# Run ETL v2.0 with deduplication fixes
python archive/scripts/etl_ontology_v2_0.py
```

**Expected Output**:
```
4.7. MERGING SEED TERMS (IMOR/ICOR/ICAP)
----------------------------------------
   Loaded 3 seed terms from ontology_seed_terms.json
   Overriding 'IMOR' with seed term (was: regulatory_concepts)
   Overriding 'ICOR' with seed term (was: regulatory_concepts)
   Overriding 'ICAP' with seed term (was: regulatory_concepts)
   Overridden: 3, Added: 0
   Total unique terms after merge: 581

...

6. LOADING TO WEAVIATE
----------------------------------------
   Connected to Weaviate at http://localhost:8080
   Deleting existing collection: Ontology_Term_V2
   ✅ Verified: Collection Ontology_Term_V2 deleted successfully
   Created collection: Ontology_Term_V2
   ✅ Verified: No duplicates in 581 terms
   Generating embeddings for 581 terms...
   Inserting 581 objects with vectors...
   Inserted 581 objects with embeddings
   Verified: 581 objects in collection
```

#### 3.3 Verify No Duplicates in Weaviate
```python
# Check for duplicates in final Weaviate collection
python3 - <<'PYEOF'
import weaviate
from weaviate.classes.query import Filter

client = weaviate.connect_to_local(host="localhost", port=8080)
collection = client.collections.get("Ontology_Term_V2")

# Get total count
total = collection.aggregate.over_all(total_count=True)
print(f"Total objects in Ontology_Term_V2: {total.total_count}")

# Check for duplicates in critical terms
for term in ["IMOR", "ICOR", "ICAP"]:
    results = collection.query.fetch_objects(
        filters=Filter.by_property("name").equal(term),
        limit=5
    )

    if len(results.objects) > 1:
        print(f"\n⚠️ {term}: {len(results.objects)} objects (DUPLICATE!)")
        for obj in results.objects:
            print(f"  Source: {obj.properties.get('source')}")
    else:
        print(f"✅ {term}: 1 object (source: {results.objects[0].properties.get('source')})")

client.close()
PYEOF
```

**Expected Output**:
```
Total objects in Ontology_Term_V2: 581
✅ IMOR: 1 object (source: ontology_seed_terms)
✅ ICOR: 1 object (source: ontology_seed_terms)
✅ ICAP: 1 object (source: ontology_seed_terms)
```

---

## Phase 4: Validation

**Objective**: Verify CA-02/CA-03 acceptance criteria now PASS

### Steps

#### 4.1 Test Seed Terms via bank-advisor RPC
```bash
# Start bank-advisor if not running
cd plugins/bank-advisor-private
make dev

# Test queries
curl -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{"query": "Que es IMOR?", "user_id": "test", "session_id": "test"}' | jq '.answer'

curl -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{"query": "Que es ICOR?", "user_id": "test", "session_id": "test"}' | jq '.answer'

curl -X POST http://localhost:8002/rpc \
  -H "Content-Type: application/json" \
  -d '{"query": "Que es ICAP?", "user_id": "test", "session_id": "test"}' | jq '.answer'
```

**Expected**: Responses should include correct definitions with formulas

#### 4.2 Direct Weaviate Query Validation
```python
# Validate all seed terms have correct data
python3 - <<'PYEOF'
import weaviate
from weaviate.classes.query import Filter

client = weaviate.connect_to_local(host="localhost", port=8080)
collection = client.collections.get("Ontology_Term_V2")

seed_terms = ["IMOR", "ICOR", "ICAP"]
all_pass = True

for term_name in seed_terms:
    results = collection.query.fetch_objects(
        filters=Filter.by_property("name").equal(term_name),
        limit=5
    )

    if len(results.objects) != 1:
        print(f"❌ {term_name}: Expected 1 object, found {len(results.objects)}")
        all_pass = False
        continue

    obj = results.objects[0]
    props = obj.properties

    # Check required fields
    has_definition = props.get("definition") and len(props["definition"]) > 20
    has_formula = props.get("formula_text") and len(props["formula_text"]) > 10
    correct_source = props.get("source") == "ontology_seed_terms"

    if has_definition and has_formula and correct_source:
        print(f"✅ {term_name}: Definition ✓, Formula ✓, Source ✓")
    else:
        print(f"❌ {term_name}: Definition={has_definition}, Formula={has_formula}, Source={correct_source}")
        all_pass = False

client.close()

if all_pass:
    print("\n🎉 CA-02/CA-03 VALIDATION PASS")
else:
    print("\n❌ CA-02/CA-03 VALIDATION FAIL")
PYEOF
```

**Expected Output**:
```
✅ IMOR: Definition ✓, Formula ✓, Source ✓
✅ ICOR: Definition ✓, Formula ✓, Source ✓
✅ ICAP: Definition ✓, Formula ✓, Source ✓

🎉 CA-02/CA-03 VALIDATION PASS
```

#### 4.3 Update HU4 Validation Results
**File**: `../../docs/kanban/DOING/TASK-2026-01-02-2048__complete-hu4-cas/validate.md`

**Add section**:
```markdown
## Validation: 2026-01-05 17:00 (Post-Cleanup)

**Status:** ✅ **CA-02/CA-03 UNBLOCKED**

### Weaviate Cleanup Results
- Deleted 2 duplicate entries (IMOR/ICOR with source="regulatory_concepts")
- ETL re-run with deduplication fixes
- Final count: 581 objects (no duplicates)

### CA-02/CA-03: Definitions + Formulas
- IMOR: ✅ Correct definition + formula
- ICOR: ✅ Correct definition + formula
- ICAP: ✅ Correct definition + formula
- **Status:** ✅ PASS

### Updated Score: 6/14 PASS (42.8%)
- CA-01: ❌ FAIL (581/3000 terms - 19.4%)
- CA-02/CA-03: ✅ PASS (seed terms now correct)
- CA-04/CA-11: ⚠️ PARTIAL (100% coverage in ETL, needs E2E validation)
- CA-05/CA-06: ⚠️ PARTIAL (36.7% synonyms coverage)
- CA-07: ✅ PASS
- CA-08: ✅ PASS
- CA-09: ✅ PASS
- CA-10: ❌ NOT VALIDATED
- CA-12: ⚠️ UNKNOWN
- CA-13: ❌ NOT IMPLEMENTED
- CA-14: ⚠️ PARTIAL
```

---

## Validation Commands

```bash
# Phase 1 validation
python scripts/cleanup_weaviate_duplicates.py
python3 - <<'PYEOF' # Verify IMOR/ICOR/ICAP (1 object each, correct source)

# Phase 2 validation
# (Code review of ETL changes)

# Phase 3 validation
python archive/scripts/etl_ontology_v2_0.py  # Should show no duplicates
python3 - <<'PYEOF' # Verify total count = 581, no duplicates

# Phase 4 validation
curl -X POST http://localhost:8002/rpc -d '{"query": "Que es IMOR?"}' | jq
python3 - <<'PYEOF' # Final CA-02/CA-03 validation
```

---

## Rollback Plan (if needed)

### If Manual Cleanup Fails
```bash
# Restore from backup
# (Manual cleanup is surgical - unlikely to need rollback)
```

### If ETL Re-run Fails
```bash
# Restore ETL output from backup
cp data/results/etl_v2_results/ontology_terms_v2.json.backup_* \
   data/results/etl_v2_results/ontology_terms_v2.json

# Reload Weaviate from backup
python archive/scripts/etl_ontology_v2_0.py --load-only  # (if flag exists)
# OR: Re-run ETL without code changes
```

---

## Success Criteria (Final Checklist)

- [ ] Phase 1: IMOR/ICOR duplicates deleted from Weaviate
- [ ] Phase 1: Only 1 object per term with source="ontology_seed_terms"
- [ ] Phase 2: ETL `_merge_seed_terms()` uses dict deduplication
- [ ] Phase 2: ETL verifies collection deletion succeeded
- [ ] Phase 2: ETL verifies no duplicates before insert
- [ ] Phase 3: ETL re-run completes successfully
- [ ] Phase 3: Weaviate has exactly 581 objects (no duplicates)
- [ ] Phase 4: IMOR/ICOR/ICAP queries return correct definitions + formulas
- [ ] Phase 4: CA-02/CA-03 validation PASS
- [ ] Phase 4: HU4 validate.md updated with results
- [ ] Cleanup script archived (not needed for future runs)
- [ ] Best practices documented for future reference

---

## Future Improvements (Out of Scope)

- Delete Ontology_Term (4,418 objects) after 2-week V2 stability
- Investigate BankingGlossaryV5 usage
- Add automated duplicate detection in CI/CD
- Implement hybrid search (CA-13)
- Schema versioning automation
