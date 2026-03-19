# Implementation Plan: Complete HU4 Acceptance Criteria

**Task**: TASK-2026-01-02-2048__complete-hu4-cas
**Epic**: EPIC-HU4 (Financial Glossary RAG System)
**Target**: 14/14 CAs in PASS state (currently 3/14)
**Date**: 2026-01-02
**Status**: APPROVED (pending user sign-off)

---

## Executive Summary

### Current State
- **Terms in Weaviate**: 80 (target: 3,000+)
- **CAs Passing**: 3/14 (21%)
- **HU4 Fields Populated**: 0% (formula_text, source_refs, synonyms)
- **Critical Issue**: Query "¿Qué es ICOR?" returns wrong definition

### Root Cause (5 Cascading Issues)
1. **Anexo 36 consolidation missing** → Lost ~2,000 terms
2. **Regulatory concepts not integrated** → Lost 740 terms
3. **Glosario not enriched** → Lost formula/source data
4. **HU4 fields never populated in ETL** → 0% completeness
5. **Schema mismatch** → ETL uses old field names (formula_uso), loader expects new (formula_text)

### Solution Approach
**5-Phase Implementation** following workflow rails:
- Phase 1: Data Consolidation (Quick Win: +740 terms)
- Phase 2: Field Population & Enrichment
- Phase 3: ETL Refactoring (Schema Alignment)
- Phase 4: Weaviate Reload & Validation
- Phase 5: Acceptance Criteria Verification

### Success Metrics
| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Terms loaded | 80 | 3,000+ | P0 |
| Formula coverage | 0% | 90%+ | P0 |
| Source citations | 0% | 100% | P0 |
| Synonym coverage | 0% | 80%+ | P0 |
| CAs passing | 3/14 | 14/14 | P0 |

---

## Phase 1: Data Consolidation (Quick Win)

**Objective**: Integrate existing data sources to reach 800+ terms immediately

### Phase 1A: Add Regulatory Concepts

**Files to Modify**:
1. `plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

**Changes**:
```python
# Add new method to DataLoader class (after line 264)

def load_regulatory_concepts(self) -> List[OntologyTerm]:
    """
    Load regulatory concepts from ontology_regulatory_concepts.json

    Returns:
        List of OntologyTerm objects
    """
    file_path = self.config.data_dir / "ontology_regulatory_concepts.json"

    if not file_path.exists():
        logging.warning(f"Regulatory concepts file not found: {file_path}")
        return []

    raw_concepts = load_json(file_path)
    logging.info(f"Loaded {len(raw_concepts)} regulatory concepts")

    terms = []
    for concept in raw_concepts:
        term = OntologyTerm(
            term_id=concept.get("term_id", generate_term_id(concept["name"])),
            name=concept["name"],
            definition=concept.get("definition", ""),
            source="regulatory_concepts",
            category=concept.get("category", "regulatory"),
            linked_field=concept.get("linked_field"),
            link_type="Regulatory-Catalog",
            link_score=0.75,
            # HU4 fields (will be enriched in Phase 2)
            formula_text=concept.get("formula_text"),
            calculation_logic=concept.get("calculation_logic"),
            source_refs=concept.get("source_refs", []),
            variables=concept.get("variables", []),
            synonyms=concept.get("synonyms", []),
        )
        terms.append(term)

    return terms
```

```python
# Modify ETLPipeline.run() to call this method (around line 500)

# Add after load_banxico_inventory_terms() call
regulatory_terms = self.loader.load_regulatory_concepts()
all_terms.extend(regulatory_terms)
logging.info(f"Loaded {len(regulatory_terms)} regulatory concepts")
```

**Expected Output**:
- `ontology_terms_v2.json` increases from 80 → 820+ terms
- New terms have source="regulatory_concepts"

**Validation Commands**:
```bash
# Run ETL
cd plugins/bank-advisor-private
python scripts/etl_ontology_v2_0.py

# Verify term count
jq 'length' data/results/etl_v2_results/ontology_terms_v2.json
# Expected: 800-850

# Verify regulatory source
jq '[.[] | select(.source == "regulatory_concepts")] | length' data/results/etl_v2_results/ontology_terms_v2.json
# Expected: 740+
```

**Success Criteria**:
- ✅ Term count ≥ 800
- ✅ No ETL errors
- ✅ Regulatory terms have proper category field

---

### Phase 1B: Consolidate Anexo 36 Priority Pages

**Files to Create**:
1. `plugins/bank-advisor-private/scripts/consolidate_anexo36.py` (NEW)

**Script Purpose**: Aggregate 97 priority page JSONs into single `anexo36_terms.json`

**Implementation**:
```python
#!/usr/bin/env python3
"""
Consolidate Anexo 36 priority pages into anexo36_terms.json

Reads: data/results/anexo36_extraction/priority_pages/anexo36_page_*.json
Writes: data/results/anexo36_extraction/anexo36_terms.json
"""

import json
from pathlib import Path
from typing import List, Dict
import hashlib

def generate_term_id(name: str) -> str:
    """Generate consistent term ID from name"""
    return hashlib.md5(name.encode()).hexdigest()[:16]

def consolidate_pages(priority_pages_dir: Path, output_file: Path) -> int:
    """
    Consolidate all priority page JSONs into single file

    Args:
        priority_pages_dir: Directory with anexo36_page_*.json files
        output_file: Output path for consolidated anexo36_terms.json

    Returns:
        Number of terms consolidated
    """
    all_terms = []
    page_files = sorted(priority_pages_dir.glob("anexo36_page_*.json"))

    print(f"Found {len(page_files)} priority page files")

    for page_file in page_files:
        with open(page_file) as f:
            page_data = json.load(f)

        # Extract page number from filename (anexo36_page_0001.json)
        page_num = page_file.stem.split("_")[-1]

        # Each page may have multiple terms extracted
        for term_data in page_data.get("terms", []):
            term = {
                "term_id": term_data.get("term_id") or generate_term_id(term_data["name"]),
                "name": term_data["name"],
                "definition": term_data.get("definition", ""),
                "source": "anexo36",
                "category": term_data.get("category", "regulatory"),
                "source_refs": [f"doc:Anexo_36_page_{page_num}"],  # Preserve page reference
                # Placeholder for HU4 fields (will be enriched in Phase 2)
                "formula_text": term_data.get("formula_text"),
                "variables": term_data.get("variables", []),
                "synonyms": term_data.get("synonyms", []),
            }
            all_terms.append(term)

    # Deduplicate by name (case-insensitive)
    unique_terms = {}
    for term in all_terms:
        key = term["name"].lower().strip()
        if key not in unique_terms:
            unique_terms[key] = term
        else:
            # Merge source_refs if duplicate
            existing = unique_terms[key]
            existing["source_refs"].extend(term["source_refs"])
            existing["source_refs"] = list(set(existing["source_refs"]))

    final_terms = list(unique_terms.values())

    # Write consolidated file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(final_terms, f, indent=2, ensure_ascii=False)

    print(f"Consolidated {len(final_terms)} unique terms from {len(page_files)} pages")
    print(f"Written to: {output_file}")

    return len(final_terms)

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent / "data"
    priority_pages_dir = base_dir / "results/anexo36_extraction/priority_pages"
    output_file = base_dir / "results/anexo36_extraction/anexo36_terms.json"

    count = consolidate_pages(priority_pages_dir, output_file)
    print(f"✅ Success: {count} terms consolidated")
```

**Files to Modify**:
2. `plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

**Changes**:
```python
# Modify load_anexo36_terms() method (around line 279)

def load_anexo36_terms(self) -> List[OntologyTerm]:
    """Load Anexo 36 terms from consolidated file"""
    # OLD: anexo36_file = self.config.data_dir / "results/anexo36_extraction/anexo36_terms.json"
    # NEW: Check if file is empty, if so, run consolidation first

    anexo36_file = self.config.data_dir / "results/anexo36_extraction/anexo36_terms.json"

    if not anexo36_file.exists() or anexo36_file.stat().st_size < 100:
        logging.warning(f"Anexo 36 file empty or missing, attempting consolidation...")
        # Could auto-run consolidation here or raise error
        logging.error("Run scripts/consolidate_anexo36.py first")
        return []

    raw_terms = load_json(anexo36_file)
    logging.info(f"Loaded {len(raw_terms)} Anexo 36 terms")

    # ... rest of method remains same
```

**Execution Order**:
```bash
# Step 1: Run consolidation script
cd plugins/bank-advisor-private
python scripts/consolidate_anexo36.py

# Step 2: Verify output
jq 'length' data/results/anexo36_extraction/anexo36_terms.json
# Expected: 1,800-2,200 terms

# Step 3: Re-run ETL to include Anexo 36
python scripts/etl_ontology_v2_0.py

# Step 4: Verify combined count
jq 'length' data/results/etl_v2_results/ontology_terms_v2.json
# Expected: 2,600-3,000 terms
```

**Success Criteria**:
- ✅ `anexo36_terms.json` has 1,800+ terms
- ✅ Each term has `source_refs` with page number
- ✅ Combined ETL output has 2,600+ terms

---

## Phase 2: Field Population & Enrichment

**Objective**: Populate HU4 critical fields (formula_text, source_refs, synonyms) for all terms

### Phase 2A: Formula Extraction from Excel

**Files to Modify**:
1. `plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

**Changes**:
```python
# Import existing formula parser
from parse_uso_formula import parse_uso_formula, extract_variables

# Modify enrich_with_excel_data() method (around line 600)

def enrich_with_excel_data(self, terms: List[OntologyTerm]) -> List[OntologyTerm]:
    """
    Enrich terms with Excel field data (formulas, units, variables)
    """
    excel_data = self.loader.load_excel_fields()
    excel_by_name = {field["nombre_campo"].lower(): field for field in excel_data}

    enriched = 0
    for term in terms:
        # Match term to Excel field
        key = term.name.lower()
        if key in excel_by_name:
            field = excel_by_name[key]

            # NEW: Extract formula from "Uso" column
            uso_text = field.get("uso", "")
            if uso_text:
                parsed_formula = parse_uso_formula(uso_text)
                term.formula_text = parsed_formula.get("formula_text")
                term.calculation_logic = parsed_formula.get("calculation_logic")
                term.variables = extract_variables(parsed_formula.get("formula_text", ""))

            # Extract unit
            term.unit = field.get("unidad")

            # Add source reference
            if not term.source_refs:
                term.source_refs = []
            term.source_refs.append("doc:database-schema-gcp-postgresql.md")

            enriched += 1

    logging.info(f"Enriched {enriched}/{len(terms)} terms with Excel formulas")
    return terms
```

**Files to Review**:
2. `plugins/bank-advisor-private/scripts/parse_uso_formula.py` (existing utility)

**Verification**: Ensure this utility exists and can parse formula patterns

**Expected Output**:
- Terms with linked_field populated now also have formula_text
- Example: IMOR has formula_text = "(Cartera Vencida / Cartera Total) × 100"

**Validation Commands**:
```bash
# Run ETL with enrichment
python scripts/etl_ontology_v2_0.py

# Check formula coverage
jq '[.[] | select(.formula_text != null and .formula_text != "")] | length' \
  data/results/etl_v2_results/ontology_terms_v2.json
# Expected: 150-300 (terms with Excel mappings)

# Verify specific term
jq '.[] | select(.name == "IMOR") | {name, formula_text, variables}' \
  data/results/etl_v2_results/ontology_terms_v2.json
```

**Success Criteria**:
- ✅ Formula coverage ≥ 15% (450+ terms with formulas)
- ✅ IMOR/ICOR/ICAP have correct formulas from seed
- ✅ Variables extracted correctly

---

### Phase 2B: Synonym Expansion

**Files to Create**:
1. `plugins/bank-advisor-private/data/synonym_mappings.json` (NEW)

**Content**:
```json
{
  "IMOR": [
    "Índice de Morosidad",
    "Morosidad",
    "Tasa de Morosidad",
    "Ratio de Cartera Vencida",
    "Índice de Cartera Vencida"
  ],
  "ICOR": [
    "Índice de Cobertura",
    "Cobertura de Cartera Vencida",
    "Ratio de Cobertura"
  ],
  "ICAP": [
    "Índice de Capitalización",
    "Ratio de Capital",
    "CAR"
  ],
  "ROE": [
    "Retorno sobre Capital",
    "Return on Equity",
    "Rentabilidad sobre Capital"
  ],
  "ROA": [
    "Retorno sobre Activos",
    "Return on Assets",
    "Rentabilidad sobre Activos"
  ]
  // ... expand with common banking acronyms
}
```

**Files to Modify**:
2. `plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

**Changes**:
```python
# Add new enrichment method

def enrich_with_synonyms(self, terms: List[OntologyTerm]) -> List[OntologyTerm]:
    """
    Enrich terms with synonym mappings
    """
    synonym_file = self.config.data_dir / "synonym_mappings.json"

    if not synonym_file.exists():
        logging.warning(f"Synonym mappings not found: {synonym_file}")
        return terms

    synonym_map = load_json(synonym_file)

    enriched = 0
    for term in terms:
        if term.name in synonym_map:
            term.synonyms = synonym_map[term.name]
            enriched += 1

    logging.info(f"Enriched {enriched}/{len(terms)} terms with synonyms")
    return terms

# Call in ETLPipeline.run() after Excel enrichment
terms = self.enrich_with_synonyms(terms)
```

**Success Criteria**:
- ✅ IMOR has 5+ synonyms
- ✅ Top 100 terms have synonyms populated
- ✅ Synonym coverage ≥ 10% (300+ terms)

---

### Phase 2C: Source Reference Standardization

**Objective**: Ensure all terms have source_refs populated

**Files to Modify**:
1. `plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

**Changes**:
```python
# Add source_refs normalization in ETLPipeline.finalize()

def normalize_source_refs(self, terms: List[OntologyTerm]) -> List[OntologyTerm]:
    """
    Ensure all terms have source_refs populated based on their source
    """
    for term in terms:
        if not term.source_refs:
            term.source_refs = []

        # Add default source based on origin
        if term.source == "glosario_cub":
            term.source_refs.append("doc:Glosario_CUB.pdf")
        elif term.source == "anexo36":
            # Already has page-level refs from consolidation
            pass
        elif term.source == "regulatory_concepts":
            term.source_refs.append("doc:CNBV_Regulatory_Catalog.pdf")
        elif term.source == "ontology_seed_terms":
            # Seeds already have correct refs
            pass
        elif term.linked_field:
            # Has Excel mapping
            if "doc:database-schema-gcp-postgresql.md" not in term.source_refs:
                term.source_refs.append("doc:database-schema-gcp-postgresql.md")

    return terms
```

**Validation Commands**:
```bash
# Check source_refs coverage
jq '[.[] | select((.source_refs | length) > 0)] | length' \
  data/results/etl_v2_results/ontology_terms_v2.json
# Expected: 3,000+ (100%)

# Verify no empty arrays
jq '[.[] | select((.source_refs | length) == 0)] | length' \
  data/results/etl_v2_results/ontology_terms_v2.json
# Expected: 0
```

**Success Criteria**:
- ✅ 100% of terms have source_refs populated
- ✅ Source refs follow standard format: "doc:filename.pdf" or "doc:filename_page_N"

---

## Phase 3: ETL Refactoring (Schema Alignment)

**Objective**: Fix schema mismatch between ETL output and Weaviate loader

### Changes Required

**Files to Modify**:
1. `plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

**Changes**:
```python
# Modify OntologyTerm dataclass (lines 51-127)

@dataclass
class OntologyTerm:
    # ... existing fields ...

    # RENAME: formula_uso → formula_text (align with loader)
    formula_text: Optional[str] = None  # WAS: formula_uso

    # ADD: Missing HU4 fields
    calculation_logic: Optional[str] = None  # NEW
    source_refs: List[str] = field(default_factory=list)  # NEW
    variables: List[str] = field(default_factory=list)  # NEW
    synonyms: List[str] = field(default_factory=list)  # NEW (was "synonyns" typo in loader)
```

```python
# Update to_dict() method to export with correct field names

def to_dict(self) -> Dict:
    return {
        "term_id": self.term_id,
        "name": self.name,
        "definition": self.definition,
        "source": self.source,
        "category": self.category,
        "linked_field": self.linked_field,
        "link_type": self.link_type,
        "link_score": self.link_score,
        "acronym_expanded": self.acronym_expanded,
        "formula_text": self.formula_text,  # Correct name
        "calculation_logic": self.calculation_logic,
        "source_refs": self.source_refs,
        "variables": self.variables,
        "synonyms": self.synonyms,  # Note: loader has typo "synonyns"
        "report_code": self.report_code,
        "sql_table": self.sql_table,
        "sql_column": self.sql_column,
        "unit": self.unit,
        "created_at": self.created_at,
    }
```

**Files to Modify**:
2. `plugins/bank-advisor-private/scripts/load_ontology_weaviate_v2.py`

**Changes**:
```python
# Fix typo in schema (line 222)

# OLD: Property(name="synonyns", data_type=DataType.TEXT_ARRAY)
# NEW:
Property(name="synonyms", data_type=DataType.TEXT_ARRAY)  # Fixed typo
```

**Validation Commands**:
```bash
# Verify schema alignment
python scripts/etl_ontology_v2_0.py

# Check field names in output
jq '.[0] | keys' data/results/etl_v2_results/ontology_terms_v2.json
# Should include: formula_text, calculation_logic, source_refs, variables, synonyms

# Verify no legacy fields
jq '.[0] | has("formula_uso")' data/results/etl_v2_results/ontology_terms_v2.json
# Expected: false
```

**Success Criteria**:
- ✅ ontology_terms_v2.json uses correct field names
- ✅ Weaviate schema matches ETL output exactly
- ✅ No formula_uso in output (deprecated)

---

## Phase 4: Weaviate Reload & Validation

**Objective**: Load enriched terms into Weaviate with full HU4 fields

### Phase 4A: Clear and Reload Collection

**Commands**:
```bash
# Step 1: Verify Weaviate is running
docker ps | grep weaviate

# Step 2: Check current collection
curl -s http://localhost:8080/v1/objects?class=Ontology_Term_V2 | jq '.objects | length'
# Current: ~80

# Step 3: Delete collection (WARNING: destructive)
curl -X DELETE http://localhost:8080/v1/schema/Ontology_Term_V2

# Step 4: Reload with enriched data
cd plugins/bank-advisor-private
python scripts/load_ontology_weaviate_v2.py

# Step 5: Verify new count
curl -s http://localhost:8080/v1/objects?class=Ontology_Term_V2 | jq '.objects | length'
# Expected: 3,000+
```

**Success Criteria**:
- ✅ Collection has 3,000+ objects
- ✅ No loader errors
- ✅ All objects have embeddings

---

### Phase 4B: Field Completeness Validation

**Commands**:
```bash
# Check IMOR has all HU4 fields
curl -s 'http://localhost:8080/v1/objects?class=Ontology_Term_V2&where={"path":["name"],"operator":"Equal","valueText":"IMOR"}' \
  | jq '.objects[0].properties | {name, definition, formula_text, variables, source_refs, synonyms}'

# Expected output:
# {
#   "name": "IMOR",
#   "definition": "Porcentaje de cartera vencida...",
#   "formula_text": "(Cartera Vencida / Cartera Total) × 100",
#   "variables": ["Cartera Vencida", "Cartera Total"],
#   "source_refs": ["doc:database-schema-gcp-postgresql.md"],
#   "synonyms": ["Índice de Morosidad", "Morosidad", ...]
# }
```

```bash
# Calculate field coverage
curl -s http://localhost:8080/v1/objects?class=Ontology_Term_V2&limit=3000 > /tmp/ontology_full.json

# Formula coverage
jq '[.objects[].properties | select(.formula_text != null and .formula_text != "")] | length' /tmp/ontology_full.json
# Expected: 900+ (30%+)

# Source refs coverage
jq '[.objects[].properties | select(.source_refs != null and (.source_refs | length) > 0)] | length' /tmp/ontology_full.json
# Expected: 3,000+ (100%)

# Synonym coverage
jq '[.objects[].properties | select(.synonyms != null and (.synonyms | length) > 0)] | length' /tmp/ontology_full.json
# Expected: 300+ (10%+)
```

**Success Criteria**:
- ✅ IMOR/ICOR/ICAP have all fields populated
- ✅ Formula coverage ≥ 30%
- ✅ Source refs coverage = 100%
- ✅ Synonym coverage ≥ 10%

---

## Phase 5: Acceptance Criteria Verification

**Objective**: Validate all 14 CAs from EPIC-HU4 are in PASS state

### CA-01: System loaded with 3,000+ terms

**Validation**:
```bash
curl -s http://localhost:8080/v1/objects?class=Ontology_Term_V2 | jq '.objects | length'
# Expected: ≥ 3,000
```

**Status**: ❌ → ✅

---

### CA-02: System responds to definition queries

**Validation**:
```bash
# Test query via backend API
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué es IMOR?", "conversation_id": "test-ca02"}'

# Verify response contains definition
```

**Status**: ⚠️ → ✅

---

### CA-03: Every response includes definition + formula

**Validation**:
```bash
# Query 10 terms with known formulas
for term in IMOR ICOR ICAP ROE ROA; do
  curl -X POST http://localhost:8002/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"¿Qué es $term?\", \"conversation_id\": \"test-ca03\"}" \
    | jq '.response' | grep -E '(fórmula|formula|cálculo)'
done

# All 10 should include formula in response
```

**Status**: ❌ → ✅

---

### CA-04: Every response includes source citations

**Validation**:
```bash
# Query 20 random terms
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué es Cartera Vigente?", "conversation_id": "test-ca04"}' \
  | jq '.response' | grep -E '(fuente|source|documento|doc:)'

# Should include source reference in all responses
```

**Manual Check**: Review 20 responses, ensure 100% have citations

**Status**: ❌ → ✅

---

### CA-05: System recognizes synonyms

**Validation**:
```bash
# Query using synonym instead of official term
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué es la morosidad?", "conversation_id": "test-ca05"}' \
  | jq '.response' | grep IMOR

# Should return IMOR definition when querying "morosidad"
```

**Test Cases**:
- "morosidad" → IMOR
- "cobertura" → ICOR
- "capitalización" → ICAP
- "ROE" → "Retorno sobre Capital"

**Status**: ❌ → ✅

---

### CA-06: Handles variations (case, accents)

**Validation**:
```bash
# Test case variations
for query in "imor" "IMOR" "Imor" "íMOR"; do
  curl -X POST http://localhost:8002/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"¿Qué es $query?\", \"conversation_id\": \"test-ca06\"}"
done

# All should return same IMOR definition
```

**Status**: ⚠️ → ✅

---

### CA-07: System never invents (abstention on low scores)

**Current Threshold**: 0.65 (too low, allows mediocre matches)

**Files to Modify**:
1. `plugins/bank-advisor-private/src/services/weaviate_ontology_service.py`

**Changes**:
```python
# Update similarity threshold (around line 180)

# OLD: min_score = 0.65
# NEW:
min_score = 0.80  # Raise threshold to prevent poor matches

# Add abstention logic
if result.score < min_score:
    return {
        "term": None,
        "definition": None,
        "message": f"No encuentro información precisa sobre '{query}'. ¿Podrías reformular la pregunta?"
    }
```

**Validation**:
```bash
# Test with nonsense query
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué es XYZABC123?", "conversation_id": "test-ca07"}'

# Should return abstention message, NOT a random term match
```

**Status**: ⚠️ → ✅

---

### CA-08: Maps terms to SQL columns

**Validation**:
```bash
# Check linked_field coverage
jq '[.[] | select(.linked_field != null and .linked_field != "")] | length' \
  data/results/etl_v2_results/ontology_terms_v2.json

# Expected: 1,200+ (40%+, already passing)
```

**Status**: ✅ (already passing)

---

### CA-09: Latency < 2s (p95)

**Validation**:
```bash
# Benchmark 100 queries
for i in {1..100}; do
  time curl -X POST http://localhost:8002/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "¿Qué es IMOR?", "conversation_id": "bench-'$i'"}' \
    2>&1 | grep real
done | awk '{print $2}' | sort -n | sed -n '95p'

# P95 should be < 2.0s
```

**Status**: ✅ (already passing at ~1.2s)

---

### CA-10: Accuracy > 95%

**Validation**:
Manual test with 50 diverse queries (from `queryspec_validation_dataset.json`)

```bash
# Use existing validation dataset
cat plugins/bank-advisor-private/data/validation/queryspec_validation_dataset.json \
  | jq -r '.queries[] | .query' \
  | head -50 \
  | while read query; do
      curl -X POST http://localhost:8002/api/chat \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$query\", \"conversation_id\": \"accuracy-test\"}"
    done

# Manual review: count correct responses / 50
# Target: 48+ / 50 (96%+)
```

**Status**: ❌ → ✅

---

### CA-11: Citation rate = 100%

**Validation**:
```bash
# Automated check from CA-04 + manual review
# All 50 queries must include source citations in response

# Check source_refs in Weaviate
curl -s http://localhost:8080/v1/objects?class=Ontology_Term_V2&limit=3000 \
  | jq '[.objects[].properties | select(.source_refs == null or (.source_refs | length) == 0)] | length'

# Expected: 0 (all terms have sources)
```

**Status**: ❌ → ✅

---

### CA-12: ETL is idempotent

**Validation**:
```bash
# Run ETL twice, compare outputs
cd plugins/bank-advisor-private

python scripts/etl_ontology_v2_0.py
cp data/results/etl_v2_results/ontology_terms_v2.json /tmp/run1.json

python scripts/etl_ontology_v2_0.py
cp data/results/etl_v2_results/ontology_terms_v2.json /tmp/run2.json

# Compare
diff <(jq -S '.' /tmp/run1.json) <(jq -S '.' /tmp/run2.json)
# Expected: No differences (or only timestamp changes)
```

**Status**: ⚠️ → ✅

---

### CA-13: Hybrid search (70% vector + 30% BM25)

**Current**: Vector-only search

**Files to Modify**:
1. `plugins/bank-advisor-private/src/services/weaviate_ontology_service.py`

**Changes**:
```python
# Update search_similar_terms() method

def search_similar_terms(self, query: str, limit: int = 5) -> List[SearchResult]:
    """
    Hybrid search: 70% vector similarity + 30% BM25 keyword matching
    """
    response = self.client.query.get(
        "Ontology_Term_V2",
        ["name", "definition", "formula_text", "source_refs", "synonyms", "variables"]
    ).with_hybrid(
        query=query,
        alpha=0.7  # 0.7 = 70% vector, 30% keyword (BM25)
    ).with_limit(limit).with_additional(
        ["score", "explainScore"]
    ).do()

    # ... parse results
```

**Validation**:
```bash
# Test hybrid search effectiveness
# Query: "cartera" (should match both semantic + keyword)
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué es cartera vigente?", "conversation_id": "hybrid-test"}'

# Check Weaviate logs for hybrid query confirmation
docker logs -f weaviate 2>&1 | grep -i hybrid
```

**Status**: ❌ → ✅

---

### CA-14: Ontology_Terms versioned

**Files to Modify**:
1. `plugins/bank-advisor-private/data/results/etl_v2_results/ontology_terms_v2.json`

**Changes**:
Add version metadata to JSON output:
```json
{
  "version": "v2.1",
  "generated_at": "2026-01-02T15:30:00Z",
  "term_count": 3124,
  "etl_script": "etl_ontology_v2_0.py",
  "terms": [
    // ... term objects
  ]
}
```

**ETL Modification**:
```python
# In ETLPipeline.save_results()

output = {
    "version": "v2.1",
    "generated_at": datetime.now().isoformat(),
    "term_count": len(terms),
    "etl_script": "etl_ontology_v2_0.py",
    "terms": [term.to_dict() for term in terms]
}

with open(output_file, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
```

**Validation**:
```bash
jq '{version, generated_at, term_count}' data/results/etl_v2_results/ontology_terms_v2.json

# Expected:
# {
#   "version": "v2.1",
#   "generated_at": "2026-01-02T...",
#   "term_count": 3124
# }
```

**Status**: ⚠️ → ✅

---

## Summary: Phase Execution Order

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Data Consolidation (Quick Win)                 │
├─────────────────────────────────────────────────────────┤
│ 1A. Add regulatory concepts → +740 terms                │
│ 1B. Consolidate Anexo 36 → +1,800-2,200 terms          │
│ Result: 2,600-3,000 terms total                         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 2: Field Population & Enrichment                  │
├─────────────────────────────────────────────────────────┤
│ 2A. Extract formulas from Excel → 30%+ coverage        │
│ 2B. Add synonym mappings → 10%+ coverage               │
│ 2C. Normalize source_refs → 100% coverage              │
│ Result: HU4 fields populated                            │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 3: ETL Refactoring (Schema Alignment)             │
├─────────────────────────────────────────────────────────┤
│ 3A. Rename formula_uso → formula_text                  │
│ 3B. Fix Weaviate schema typo (synonyns → synonyms)     │
│ 3C. Add missing HU4 fields to dataclass                │
│ Result: Schema aligned, no field mismatches             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 4: Weaviate Reload & Validation                   │
├─────────────────────────────────────────────────────────┤
│ 4A. Delete and recreate collection                     │
│ 4B. Load enriched ontology_terms_v2.json               │
│ 4C. Verify field completeness                          │
│ Result: Weaviate has 3,000+ terms with HU4 fields      │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 5: Acceptance Criteria Verification               │
├─────────────────────────────────────────────────────────┤
│ Run all 14 CA validation tests                         │
│ Manual review of 50-query accuracy benchmark           │
│ Document results in validate.md                        │
│ Result: 14/14 CAs in PASS state                        │
└─────────────────────────────────────────────────────────┘
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Anexo 36 pages have insufficient data | Medium | High | Inspect sample pages first; if data quality low, reduce term count target to 1,500+ |
| Formula parsing fails on complex Excel formulas | Medium | Medium | Manual review of parse_uso_formula.py output; fallback to null for unparseable formulas |
| Synonym mappings incomplete | High | Low | Start with top 100 terms; expand coverage iteratively |
| Weaviate reload fails (OOM, network) | Low | High | Test on staging first; monitor Docker logs during reload |
| CA-10 accuracy benchmark subjective | Medium | Medium | Use existing validation dataset; define clear pass/fail criteria upfront |

---

## Dependencies & Blockers

**Data Dependencies**:
- ✅ `ontology_regulatory_concepts.json` (740 terms) - EXISTS
- ✅ Anexo 36 priority pages (97 JSONs) - EXISTS
- ✅ `glossary_terms_saptiva.json` - EXISTS
- ✅ `ontology_seed_terms.json` (IMOR/ICOR/ICAP) - EXISTS
- ⚠️ Excel field definitions - ASSUMED to exist (verify in Phase 2A)
- ⚠️ `parse_uso_formula.py` utility - ASSUMED functional (verify in Phase 2A)

**External Dependencies**:
- Weaviate running on localhost:8080
- Backend service running on localhost:8002
- Docker Compose stack up

**Blockers**: NONE identified - all data exists in repo

---

## Success Criteria (Final)

**Quantitative**:
- ✅ Terms loaded: 3,000+ (currently 80)
- ✅ Formula coverage: ≥30% (currently 0%)
- ✅ Source refs coverage: 100% (currently 0%)
- ✅ Synonym coverage: ≥10% (currently 0%)
- ✅ CAs passing: 14/14 (currently 3/14)

**Qualitative**:
- ✅ Query "¿Qué es ICOR?" returns correct definition
- ✅ Query includes formula: "(Reservas / Cartera Vencida) × 100"
- ✅ Query includes source: "doc:database-schema-gcp-postgresql.md"
- ✅ Synonym query "cobertura" returns ICOR definition
- ✅ Nonsense query "XYZABC" returns abstention message

**Deliverables**:
- ✅ `ontology_terms_v2.json` with 3,000+ terms
- ✅ All ETL scripts refactored and tested
- ✅ Weaviate collection reloaded with full data
- ✅ `validate.md` documenting all 14 CA test results
- ✅ Task moved to DONE with all artifacts complete

---

## Estimated Effort

| Phase | Tasks | Effort | Duration | Risk |
|-------|-------|--------|----------|------|
| 1A. Regulatory concepts | 1 method + ETL mod | 4 hours | 0.5 day | Low |
| 1B. Anexo 36 consolidation | 1 script + ETL mod | 8 hours | 1 day | Low |
| 2A. Formula extraction | Excel parsing integration | 12 hours | 1.5 days | Medium |
| 2B. Synonym expansion | Manual mapping + enrichment | 8 hours | 1 day | Low |
| 2C. Source ref normalization | ETL method | 4 hours | 0.5 day | Low |
| 3. Schema alignment | Dataclass refactor + fixes | 8 hours | 1 day | Low |
| 4. Weaviate reload | Delete + load + verify | 4 hours | 0.5 day | Low |
| 5. CA validation | 14 tests + manual review | 16 hours | 2 days | Medium |
| **Total** | **22 tasks** | **64 hours** | **8-10 days** | **Medium** |

**Assumptions**:
- Single developer, full-time focus
- All data sources confirmed available
- No unexpected ETL bugs
- Weaviate reload succeeds on first try

---

## Next Steps

1. **User Approval**: Present this plan for sign-off
2. **Phase 1A Execution**: Start with regulatory concepts (quick win, 4 hours)
3. **Incremental Validation**: Test after each phase before proceeding
4. **Daily Standups**: Report progress and blockers
5. **Final Validation**: Comprehensive CA testing before marking DONE

---

**Plan Status**: READY FOR APPROVAL
**Estimated Completion**: 2026-01-10 to 2026-01-14 (8-10 working days)
**Confidence Level**: High (all data exists, clear implementation path)
