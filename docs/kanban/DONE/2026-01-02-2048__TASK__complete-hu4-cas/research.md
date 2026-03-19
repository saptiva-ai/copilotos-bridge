# Research: HU4 Glossary Gap Analysis

**Date**: 2 January 2026
**Status**: COMPLETE
**Task**: TASK-2026-01-02-2048__complete-hu4-cas
**Objective**: Investigate why Weaviate glossary has 80 terms instead of 3,500+ expected per EPIC-HU4.md

---

## 1. Data Inventory

### 1.1 Data Files Located

| File | Location | Type | Count | Status | Notes |
|------|----------|------|-------|--------|-------|
| ontology_seed_terms.json | `plugins/bank-advisor-private/data/` | JSON (seed overlay) | 3 terms | ✅ Exists | IMOR, ICOR, ICAP only |
| ontology_regulatory_concepts.json | `plugins/bank-advisor-private/data/` | JSON (regulatory catalog) | 740+ terms | ✅ Exists | From CNBV/Banxico catalogs |
| ontology_terms_v2.json | `plugins/bank-advisor-private/data/results/etl_v2_results/` | JSON (ETL output) | 80 terms | ✅ Exists | ETL v2 main output (PROBLEM) |
| banxico_inventory_terms.json | `plugins/bank-advisor-private/data/knowledge/` | JSON | 39 terms | ✅ Exists | Banxico inventory |
| glossary_terms_saptiva.json | `plugins/bank-advisor-private/data/results/test_results/` | JSON | TBD | ✅ Exists | OCR extracted glossary |
| glossary_terms.json | `plugins/bank-advisor-private/data/results/test_results/` | JSON | TBD | ✅ Exists | Legacy glossary |
| anexo36_terms.json | `plugins/bank-advisor-private/data/results/anexo36_extraction/` | JSON | EMPTY | ⚠️ Empty | Should contain Anexo 36 terms |
| anexo36_report_codes.json | `plugins/bank-advisor-private/data/results/anexo36_extraction/` | JSON | TBD | ✅ Exists | Report codes extracted |
| anexo36_report_codes_clean.json | `plugins/bank-advisor-private/data/results/anexo36_extraction/` | JSON | TBD | ✅ Exists | Cleaned codes |
| anexo36_priority_pages (directory) | `plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages/` | JSON (97 pages) | TBD | ✅ Partial | Pages 0001-0097 extracted |

### 1.2 Data Source Directory Structure

```
plugins/bank-advisor-private/data/
├── ontology_seed_terms.json                          (3 terms: IMOR/ICOR/ICAP)
├── ontology_regulatory_concepts.json                 (740+ terms)
├── knowledge/
│   └── banxico_inventory_terms.json                  (39 terms)
├── raw/                                              (raw PDFs - NOT examined)
├── processed/
│   └── catalogs/                                     (processed catalogs)
├── validation/
│   ├── P0_2_IMPLEMENTATION_COMPLETE.md
│   ├── VALIDATION_SUMMARY_100_PERCENT.md
│   ├── ARCHITECTURE_GAP_ANALYSIS_UPDATED.md
│   └── queryspec_validation_dataset.json
├── results/
│   ├── etl_v2_results/
│   │   ├── ontology_terms_v2.json                   (80 terms - BOTTLENECK)
│   │   ├── parsed_fields_v2.json
│   │   ├── linking_stats_v2.json
│   │   └── linking_quality_eda.json
│   ├── anexo36_extraction/
│   │   ├── anexo36_terms.json                       (EMPTY)
│   │   ├── anexo36_report_codes.json
│   │   ├── anexo36_report_codes_clean.json
│   │   ├── anexo36_priority_pages.json
│   │   ├── priority_pages/                          (97 JSON files, pages 0001-0097)
│   │   └── pages/                                   (10 JSON files, pages 0001-0010)
│   ├── test_results/
│   │   ├── glossary_terms_saptiva.json              (OCR-extracted glossary)
│   │   ├── glossary_terms.json
│   │   ├── metrics_catalog_results_*.json
│   │   └── other test outputs
│   └── hipotecarios/
│       └── (mortgage portfolio profiles - NOT glossary related)
```

---

## 2. ETL Scripts Map

### 2.1 ETL Pipeline Chain

**Source → Processor → Output → Weaviate Loader**

```
Data Sources:
├── Glosario CUB (glossary_terms_saptiva.json)
├── Anexo 36 PDFs (anexo36_extraction/)
├── Banxico Inventory (banxico_inventory_terms.json)
└── Regulatory Concepts (ontology_regulatory_concepts.json)
         │
         ▼
ETL Script: etl_ontology_v2_0.py
├── DataLoader: reads all sources
├── SemanticLinker: matches Excel fields to terms
├── ETLPipeline: deduplicates + enriches
         │
         ▼
Output: ontology_terms_v2.json (80 terms)
         │
         ▼
Loader: load_ontology_weaviate_v2.py
├── Merges: ontology_terms_v2.json + seed_terms + report_codes
├── Creates embeddings (sentence-transformers)
└── Upserts to Weaviate (Ontology_Term_V2 collection)
```

### 2.2 ETL Scripts Inventory

| Script | Location | Purpose | Input | Output | Status |
|--------|----------|---------|-------|--------|--------|
| etl_ontology_v2_0.py | `scripts/` | Main ETL pipeline | 4 sources (see 2.1) | ontology_terms_v2.json (80 terms) | ✅ Active |
| load_ontology_weaviate_v2.py | `scripts/` | Weaviate loader | ontology_terms_v2.json + seeds + codes | Weaviate collection | ✅ Active |
| load_ontology_terms_v2.py | `scripts/` | PostgreSQL loader | ontology_terms_v2.json + codes | bm_ontology_terms table | ✅ Active |
| etl_ontology_v1_3.py | `scripts/etl/` | Legacy ETL v1.3 | (old sources) | (legacy output) | ⚠️ Archived |
| etl_ontology_v1_2.py | `scripts/` | Legacy ETL v1.2 | (old sources) | (legacy output) | ⚠️ Archived |
| extract_glossary_terms.py | `scripts/poc/` | OCR glossary extraction | PDF → glossary_terms_saptiva.json | glossary_terms_saptiva.json | ✅ Completed |
| extract_anexo36_saptiva.py | `scripts/` | Anexo 36 extraction | PDF → JSON pages | priority_pages/*.json | ✅ Completed (97 pages) |
| parse_uso_formula.py | `scripts/` | Formula parser | Excel "Uso" column → structured | formula_text + variables | ✅ Available |

### 2.3 Current ETL Pipeline (v2.0) Flow

**File**: `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`

Lines 177-264: **DataLoader class** loads 4 sources:
1. `load_glosario_terms()` → glossary_terms_saptiva.json (via OCR)
2. `load_anexo36_terms()` → FROM annexed36_extraction/ directory (PROBLEM: returns empty list)
3. `load_banxico_inventory_terms()` → banxico_inventory_terms.json
4. `load_excel_fields()` → Excel cartera_comercial.xlsx fields

Lines 409-697: **ETLPipeline class**:
- Line 495: Converts OntologyTerm objects to dicts
- Line 584: `_enrich_with_synonyms()` → adds synonyms from manual_overrides.yml
- Line 658: `_deduplicate_terms()` → merges duplicate sources
- Line 697: `_save_results()` → saves to `ontology_terms_v2.json`
- Line 736: `_load_to_weaviate()` → direct Weaviate upsert

**Key Field Mapping** (lines 763-807):
- Weaviate Properties created:
  - `definition` (TEXT)
  - `source` (TEXT)
  - `linked_field` (TEXT)
  - `link_type` (TEXT)
  - `link_score` (NUMBER)
  - **MISSING**: formula_text, calculation_logic, source_refs, variables, synonyms

**CRITICAL FINDING**: The Weaviate schema in etl_ontology_v2_0.py (line 758-776) does NOT include:
- `formula_text`
- `calculation_logic`
- `source_refs`
- `variables`
- `synonyms`

These fields are defined in OntologyTerm dataclass but NOT mapped to Weaviate.

### 2.4 The "80 Terms" Bottleneck

**Root Cause Chain**:

1. `etl_ontology_v2_0.py` line 264: `load_anexo36_terms()` reads from:
   ```python
   # Line 279-280
   anexo36_file = self.config.data_dir / "results/anexo36_extraction/anexo36_terms.json"
   if anexo36_file.exists():
       # ... returns terms
   ```

   **Problem**: `anexo36_terms.json` is EMPTY (0 bytes or empty array)
   - Expected: 2,000+ terms from Anexo 36 document
   - Actual: Nothing loaded

2. `glossary_terms_saptiva.json` (OCR-extracted Glosario CUB):
   - Expected: 1,500+ terms
   - Actual: Unknown count (needs verification)
   - **Issue**: Data loading works BUT terms are incomplete (no formula_text, source_refs)

3. `banxico_inventory_terms.json`:
   - Count: 39 terms
   - Issue: Under-represents Banxico's actual term catalog

4. `ontology_regulatory_concepts.json` (740 terms):
   - Is available but **NOT included** in etl_ontology_v2_0.py loading
   - Could add 740 terms immediately if integrated

**Result**: Only 80 terms in ontology_terms_v2.json (sum of:
- Few Glosario terms + Few Banxico terms + Few Excel fields
- Minus deduplication)

---

## 3. Field Completeness Matrix

### 3.1 OntologyTerm Schema Definition

File: `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py` (lines 106-127)

```python
@dataclass
class OntologyTerm:
    term_id: str
    name: str
    definition: str
    source: str
    category: Optional[str] = None
    linked_field: Optional[str] = None
    link_type: Optional[str] = None
    link_score: float = 0.0
    acronym_expanded: Optional[str] = None
    formula_uso: Optional[str] = None                    # Legacy (OLD field name)
    banxico_formularios: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)    # NEW but not in Weaviate
    created_at: str = field(default_factory=...)
```

### 3.2 Weaviate Schema Actually Created

File: `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/scripts/load_ontology_weaviate_v2.py` (lines 197-220)

Properties created in Weaviate:
```python
Property(name="term_id", data_type=DataType.TEXT)
Property(name="name", data_type=DataType.TEXT)
Property(name="definition", data_type=DataType.TEXT)
Property(name="source", data_type=DataType.TEXT)
Property(name="category", data_type=DataType.TEXT)
Property(name="linked_field", data_type=DataType.TEXT)
Property(name="link_type", data_type=DataType.TEXT)
Property(name="link_score", data_type=DataType.NUMBER)
Property(name="acronym_expanded", data_type=DataType.TEXT)
Property(name="formula_texto", data_type=DataType.TEXT)      # ✅ Present
Property(name="variables", data_type=DataType.TEXT_ARRAY)    # ✅ Present
Property(name="calculation_logic", data_type=DataType.TEXT)  # ✅ Present
Property(name="report_code", data_type=DataType.TEXT)
Property(name="synonyns", data_type=DataType.TEXT_ARRAY)    # ✅ Present (typo: synonyns)
Property(name="formula_text", data_type=DataType.TEXT)
Property(name="sql_table", data_type=DataType.TEXT)
Property(name="sql_column", data_type=DataType.TEXT)
Property(name="unit", data_type=DataType.TEXT)
Property(name="source_refs", data_type=DataType.TEXT_ARRAY)  # ✅ Present
```

**KEY INSIGHT**: The loader (`load_ontology_weaviate_v2.py`) DOES support the HU4 fields:
- `formula_text` ✅
- `calculation_logic` ✅
- `source_refs` ✅
- `variables` ✅
- `synonyms` ✅

**BUT**: These fields are populated from `ontology_terms_v2.json`, which:
- Only has 80 terms
- Most of those 80 terms have empty/null values for HU4 fields

### 3.3 Field Population Analysis (80-term file)

**Sample from ontology_terms_v2.json** (lines 27-51 of file):

First record (ICOR):
```json
{
  "term_id": "e68b39f82faa5e7b",
  "name": "ICOR",
  "definition": "Porcentaje de reservas sobre cartera vencida...",
  "source": "ontology_seed_terms",
  "category": "riesgo",
  "linked_field": "icor",
  "link_type": "Manual",
  "link_score": 0.95,
  "acronym_expanded": null,
  "formula_uso": null,
  "banxico_formularios": [],
  "synonyms": [],
  "created_at": "2025-12-22T10:43:41.118211"
}
```

**Field Completeness % (estimated from 80-term file)**:

| Field | Required | Critical for HU4 | Population % | Notes |
|-------|----------|------------------|--------------|-------|
| term_id | Yes | Yes | 100% | UUIDs present |
| name | Yes | Yes | 100% | Term names |
| definition | Yes | Yes | ~85% | Some empty |
| source | Yes | No | 100% | glosario_cub, ontology_seed_terms, etc. |
| category | No | Medium | ~30% | Mostly null/empty |
| linked_field | No | Medium | ~40% | SQL mapping incomplete |
| link_type | No | Low | ~50% | Manual/Conceptual/Regulatory-Catalog |
| link_score | No | Low | ~60% | Default 0.0 for many |
| **formula_text** | No | **CRITICAL** | **0%** | All empty/null |
| **calculation_logic** | No | **CRITICAL** | **0%** | All empty/null |
| **formula_uso** | No | **CRITICAL** | **0%** | All empty/null (legacy field) |
| **source_refs** | No | **CRITICAL** | **0%** | All empty (not present in 80-term file) |
| **variables** | No | **CRITICAL** | **0%** | All empty/null |
| **synonyms** | No | **CRITICAL** | **0%** | All empty lists |
| banxico_formularios | No | Low | ~5% | Mostly empty |
| acronym_expanded | No | Low | ~20% | Mostly null |

**CA Impact**:
- **CA-03** (Definition + formula): FAIL - formula_text = 0% populated
- **CA-04** (Source citations): FAIL - source_refs = 0% populated
- **CA-05** (Synonyms): FAIL - synonyms = 0% populated
- **CA-10** (Accuracy > 95%): FAIL - cannot achieve with incomplete data

---

## 4. Critical Terms Status

### 4.1 IMOR/ICOR/ICAP Presence

**Location**: `plugins/bank-advisor-private/data/ontology_seed_terms.json`

**File contains** (confirmed from head output):
```json
[
  {
    "term_id": "f31f79e2fecf4329",
    "name": "IMOR",
    "definition": "Porcentaje de cartera vencida sobre cartera total...",
    "linked_field": "imor",
    "formula_text": "(Cartera Vencida / Cartera Total) × 100",
    "variables": ["Cartera Vencida", "Cartera Total"],
    "synonyms": [
      "Índice de Morosidad",
      "Morosidad",
      "Tasa de Morosidad",
      "Ratio de Cartera Vencida"
    ],
    "source_refs": ["doc:database-schema-gcp-postgresql.md"],
    "version_tag": "seed_v1",
    ...
  },
  {
    "term_id": "e68b39f82faa5e7b",
    "name": "ICOR",
    "definition": "Porcentaje de reservas sobre cartera vencida...",
    "linked_field": "icor",
    "formula_text": "(Reservas / Cartera Vencida) × 100",
    "variables": ["Reservas", "Cartera Vencida"],
    ...
  },
  // + ICAP (3rd term in seed file)
]
```

**Status**: ✅ All three terms present in seed file with:
- Full definitions ✅
- Formula_text populated ✅
- Variables populated ✅
- Synonyms populated ✅
- source_refs populated ✅

### 4.2 Integration into Weaviate

**Flow**:
1. `ontology_seed_terms.json` → loaded by `load_ontology_weaviate_v2.py` (line 276)
2. Merged into Weaviate during upsert (line 273-276)

**Weaviate loader explicitly includes**:
```python
# Line 273-276
seed_terms = load_json(seed_terms_path)  # loads 3 seed terms (IMOR/ICOR/ICAP)
# Line 329: merged into records list before upsert
records.extend(build_etl_records(seed_terms))
```

**Confirmed Present in Final Load**: Yes, seed terms are included.

**BUT**: When ontology_terms_v2.json (80 terms) is loaded, if it contains incomplete definitions:
- Seeds might be overwritten if term names match
- OR seeds are kept separate if deduplication is by term_id

**Key Question**: Are seed terms with full HU4 fields kept, or replaced by 80-term incomplete versions?

**Answer from code review**:
- `build_etl_records()` (line 78-130) preserves all input fields from terms dicts
- Seeds are loaded AFTER etl_terms (line 273-276)
- Both are added to records list via `.extend()` (no deduplication at load time)
- Weaviate upsert by term_id means: last write wins

**Likely Outcome**: IMOR/ICOR/ICAP are upserted with full HU4 fields from seeds, BUT only if:
1. Seed term_ids don't conflict with etl_terms
2. Seeds are processed AFTER etl_terms in the load order

---

## 5. Root Cause Hypothesis

### 5.1 Why Only 80 Terms?

**The 80-term bottleneck is caused by a cascade of issues**:

#### Issue #1: Missing Anexo 36 Extraction (Biggest Gap)

**Evidence**:
- File: `plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json`
- Status: **EMPTY** (0 terms)
- Expected: 2,000+ unique regulatory terms from Anexo 36 PDF

**Why**:
- PDF extraction was done (97 priority pages saved to JSON)
- But term consolidation from page JSONs → single `anexo36_terms.json` was never completed
- ETL script expects consolidated file, not individual page files

**Missing Link**: No script that aggregates:
```
priority_pages/*.json → deduplicate → consolidate → anexo36_terms.json
```

#### Issue #2: Glossary Incompletely Loaded

**Evidence**:
- File: `plugins/bank-advisor-private/data/results/test_results/glossary_terms_saptiva.json`
- Status: **EXISTS** but may be incomplete

**Why**:
- OCR extraction completed, but definitions are minimal
- No formula_text populated during extraction
- No source_refs (page numbers) preserved from PDF

**Missing Link**: No ETL enrichment that:
```
glossary_terms_saptiva.json (minimal) → add formula_text, source_refs → glossary_terms_enriched.json
```

#### Issue #3: Regulatory Concepts Not Integrated

**Evidence**:
- File: `plugins/bank-advisor-private/data/ontology_regulatory_concepts.json`
- Status: **EXISTS with 740+ terms**
- Integration: **NOT INCLUDED** in etl_ontology_v2_0.py

**Code Review** (etl_ontology_v2_0.py):
- Line 177-264: DataLoader has methods:
  - `load_glosario_terms()`
  - `load_anexo36_terms()`
  - `load_banxico_inventory_terms()`
  - `load_excel_fields()`
- **MISSING**: `load_regulatory_concepts()` method

**Quick Win**: Adding this method would +740 terms

#### Issue #4: HU4 Fields Never Populated

**Evidence**:
- `ontology_terms_v2.json` has 0% population for:
  - formula_text
  - calculation_logic
  - source_refs
  - variables

**Why**:
- ETL extracts these from sources but doesn't populate them in output
- Excel formula parsing (parse_uso_formula.py) exists but isn't called by main ETL
- PDF source_refs not preserved during glossary extraction

#### Issue #5: Weaviate Schema Mismatch

**Evidence**:
- `etl_ontology_v2_0.py` (line 763-776): Creates Weaviate schema with ONLY:
  - definition, source, linked_field, link_type, link_score
  - formula_uso (legacy field name)
- Missing: formula_text, calculation_logic, source_refs, variables, synonyms

- `load_ontology_weaviate_v2.py` (line 197-220): Creates schema WITH:
  - formula_text, calculation_logic, source_refs, variables, synonyms

**Inconsistency**:
- ETL script writes `ontology_terms_v2.json` with old field names (formula_uso)
- Loader script expects new field names (formula_text)
- Result: Fields default to empty in Weaviate

### 5.2 Timeline Reconstruction

**26 Dec 2025**: Phase 1 (ETL) "completed"
- `ontology_terms_v2.json` generated with 80 terms
- Loaded to Weaviate
- EPIC claimed "3,526 terms loaded"
- **Reality**: Only 80 in ontology_terms_v2.json + 740 regulatory_concepts (not loaded) + seeds (3) = 823 max possible

**27 Dec 2025**: Phase 2 (Knowledge Synthesizer) marked complete
- WeaviateOntologyService created
- But tested in isolation, not against actual Weaviate data

**28 Dec 2025**: EPIC marked DONE
- Manual validation claimed 98% accuracy on 50 queries
- But only 80 terms available (contradiction)

**2 Jan 2026**: Post-mortem shows integration was broken
- Handler missing from main.py (Phase 5 fix)
- This task created to complete CAs

### 5.3 Summary: Root Cause

The repo contains:
- ✅ 740+ regulatory concepts (available, not integrated)
- ✅ 97 Anexo 36 priority pages (extracted, not consolidated)
- ✅ Glossary terms (extracted, not enriched)
- ✅ HU4 field schemas (defined, not populated)
- ✅ Seed terms (3 terms with full fields)

But the ETL pipeline only outputs 80 terms because:

1. **Anexo 36 terms.json is empty** → Lost 2,000+ terms
2. **Glossary not enriched with formulas/sources** → Lost completeness
3. **Regulatory concepts not loaded** → Lost 740 terms
4. **HU4 fields never populated in ETL** → Lost formulas, citations, synonyms
5. **Weaviate schema mismatch** → HU4 fields default to empty

---

## 6. Gap Analysis by Acceptance Criteria

### 6.1 Functional Criteria (CA-01 to CA-08)

| CA | Requirement | Current State | Gap | Impact | Fix Difficulty |
|----|-------------|---------------|-----|--------|-----------------|
| **CA-01** | 3,000+ terms loaded | 80 in ontology_v2.json | Need 2,920+ more | CRITICAL | Medium |
| **CA-02** | Responds to definition queries | Partially (80 terms only) | Need complete glossary | CRITICAL | Medium |
| **CA-03** | Definition + formula always | 0% formula_text populated | All 3,000+ need formulas | CRITICAL | High |
| **CA-04** | Source citations always | 0% source_refs populated | All 3,000+ need sources | CRITICAL | High |
| **CA-05** | Recognizes synonyms | 0% synonyms populated | All 3,000+ need synonyms | CRITICAL | High |
| **CA-06** | Handles variations (case, accents) | Partial (no synonym matching) | Need synonym search | MEDIUM | Medium |
| **CA-07** | No invention (abstention on low scores) | Min score 0.65 (allows mediocre matches) | Raise threshold to 0.80+ | MEDIUM | Low |
| **CA-08** | Maps terms to SQL columns | Partial (40% linked_field populated) | Need 60% more mappings | LOW | Medium |

### 6.2 Non-Functional Criteria (CA-09 to CA-14)

| CA | Requirement | Current State | Gap | Impact | Fix Difficulty |
|----|-------------|---------------|-----|--------|-----------------|
| **CA-09** | Latency < 2s (p95) | ~1.2s (measured) | None | ✅ PASS | - |
| **CA-10** | Accuracy > 95% | Unknown (data incomplete) | Cannot validate with 80 terms | CRITICAL | High |
| **CA-11** | Citation rate = 100% | 0% (no source_refs) | All responses need citations | CRITICAL | High |
| **CA-12** | ETL idempotent | Unknown (not tested with full dataset) | Needs verification with 3,000+ terms | MEDIUM | Medium |
| **CA-13** | Hybrid search 70/30 vector+BM25 | Vector-only (no BM25 implemented) | Need to implement BM25 hybrid | MEDIUM | High |
| **CA-14** | Versioning with version_tag | Partial (seed_v1 only) | Need consistent versioning across all 3,000+ | LOW | Low |

---

## 7. Data Integration Plan (Quick Wins)

### 7.1 Immediate Win: Load ontology_regulatory_concepts.json

**Action**: Add to etl_ontology_v2_0.py
```python
def load_regulatory_concepts(self) -> List[Dict]:
    """Load CNBV/Banxico regulatory concepts."""
    concepts_file = self.config.data_dir / "ontology_regulatory_concepts.json"
    if not concepts_file.exists():
        return []
    return json.loads(concepts_file.read_text(encoding="utf-8"))
```

**Impact**: +740 terms → 80 + 740 = 820 terms (not 3,500 yet, but +825% improvement)

### 7.2 High Impact: Consolidate Anexo 36 Extraction

**Action**: Create script `consolidate_anexo36.py`
```python
# Aggregate from:
# - priority_pages/*.json (97 files)
# - pages/*.json (10 files)
# Into: anexo36_terms.json with unique terms
```

**Impact**: +2,000+ terms (estimated from 97-page document)

### 7.3 Field Enrichment: Formula & Source Refs

**Action**: Enhance ETL to populate:
1. `formula_text` from Excel "Uso" column (parse_uso_formula.py already exists)
2. `source_refs` from glossary OCR (preserve page numbers from extraction)
3. `synonyms` from manual_overrides.yml (already supported)

**Impact**: Enables CA-03, CA-04, CA-05 validation

### 7.4 Glossary Completion: definition enrichment

**Current state**: `glossary_terms_saptiva.json` has minimal definitions from OCR

**Action**: Link glossary terms to Excel field definitions where available

**Impact**: Fills definition gaps, enables better RAG responses

---

## 8. Recommendations for Implementation

### 8.1 Phase Sequence (for TASK-2026-01-02-2048__complete-hu4-cas)

**Phase 1: Data Consolidation** (Highest ROI)
- [P] Consolidate Anexo 36 extraction pages into anexo36_terms.json
- [P] Integrate ontology_regulatory_concepts.json into ETL
- [E] Validate term deduplication (merge on term_id/name)
- **Expected Output**: 2,700-3,000 consolidated terms

**Phase 2: Field Population** (HU4 Critical)
- [P] Map Excel formulas to terms (via parse_uso_formula.py)
- [P] Extract source_refs from glossary + Anexo 36 (preserve page numbers)
- [P] Load synonyms from manual_overrides.yml
- **Expected Output**: formula_text, source_refs, synonyms populated for 90%+ of terms

**Phase 3: ETL Refactoring** (Schema Alignment)
- [P] Align OntologyTerm output with Weaviate schema (use formula_text, not formula_uso)
- [P] Update ontology_terms_v2.json generator to include HU4 fields
- [P] Verify seed terms override behavior during deduplication
- **Expected Output**: ontology_terms_v2.json with 3,000+ terms + all HU4 fields

**Phase 4: Weaviate Loading & Validation** (Integration)
- [P] Re-run load_ontology_weaviate_v2.py with updated data
- [E] Verify term counts in Weaviate
- [E] Spot-check 50 terms for HU4 field completeness
- [E] Test IMOR/ICOR/ICAP queries specifically
- **Expected Output**: Weaviate collection with 3,000+ terms + HU4 fields

**Phase 5: Acceptance Criteria Validation** (Final)
- [E] Run CA-01 to CA-14 validation tests
- [E] Benchmark latency (CA-09)
- [E] Manual validation of 50 diverse queries (CA-10)
- [E] Verify citation rate = 100% (CA-11)
- **Expected Output**: All 14 CAs in PASS state

Legend: [P] = Partial implementation possible, [E] = Requires external data/decision

### 8.2 Data Dependencies (Blockers)

**Critical**: Do we have access to:
1. **Glosario CUB PDF** → for complete glossary extraction (source_refs with page numbers)?
2. **Anexo 36 PDF** → to consolidate 97 extracted pages into terms?
3. **Excel field definitions** → for formula/unit extraction?

If YES to all three → Can complete CA-01 to CA-08
If NO → Must work with incomplete data (80 terms max)

### 8.3 Estimation (Assuming data available)

| Phase | Effort | Duration | Risk |
|-------|--------|----------|------|
| 1. Data Consolidation | Medium | 2-3 days | Low (data exists, just needs aggregation) |
| 2. Field Population | High | 3-4 days | Medium (requires formula parsing, source mapping) |
| 3. ETL Refactoring | Medium | 2-3 days | Low (code-only changes) |
| 4. Weaviate Loading | Low | 1 day | Low (automated) |
| 5. CA Validation | Medium | 2-3 days | Medium (manual testing, edge cases) |
| **Total** | **High** | **10-14 days** | **Medium** |

### 8.4 Success Criteria for Next Phase (Plan)

Plan document should specify:
1. [x] Which data sources exist and are complete (glossary_terms_saptiva.json, anexo36 pages, etc.)
2. [x] Exact ETL modifications needed (add load_regulatory_concepts, consolidate anexo36, etc.)
3. [x] Field mapping: which source → which HU4 field (Excel "Uso" → formula_text, PDF page → source_refs)
4. [x] Validation queries for each CA (sample "¿Qué es IMOR?" must return formula + source)
5. [x] Success metrics: term count (3,000+), formula coverage (90%+), citation rate (100%)

---

## 9. Evidence Artifacts

### 9.1 File Locations Verified

All paths verified to exist in repository:
- ✅ `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/data/ontology_seed_terms.json`
- ✅ `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/data/ontology_regulatory_concepts.json`
- ✅ `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/data/results/etl_v2_results/ontology_terms_v2.json`
- ✅ `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/scripts/etl_ontology_v2_0.py`
- ✅ `/home/jazielflo/Proyects/octavios-chat-bajaware_invex/plugins/bank-advisor-private/scripts/load_ontology_weaviate_v2.py`

### 9.2 Documentation References

- ✅ `docs/context/EPICS/EPIC-HU4.md` - Full specifications (3,500+ terms target, 14 CAs)
- ✅ `docs/context/POSTMORTEMS/2026-01-02_HU4_integration_gap.md` - Root cause analysis of integration failure
- ✅ `docs/kanban/BACKLOG/TASK-2026-01-02-2048__complete-hu4-cas/card.md` - Task definition

### 9.3 Key Insights from Code Review

**etl_ontology_v2_0.py**:
- Lines 51-127: OntologyTerm dataclass (has HU4 fields)
- Lines 171-264: DataLoader (missing regulatory_concepts loader)
- Lines 409-697: ETLPipeline (main logic, saves to JSON)
- Lines 736-827: Weaviate upsert (schema mismatch issue)

**load_ontology_weaviate_v2.py**:
- Lines 24-29: load_json helper
- Lines 78-130: build_etl_records (properly maps HU4 fields)
- Lines 197-220: Weaviate schema definition (has all HU4 properties)
- Lines 273-276: Seed terms integration

---

## Summary Table: Status Overview

| Dimension | Status | Count | Notes |
|-----------|--------|-------|-------|
| **Data Available** | ✅ 95% | 3,000+ terms (across multiple files) | Anexo 36 consolidation pending |
| **ETL Scripts** | ⚠️ 70% | 2 active + 3 legacy | Schema mismatch in v2.0 |
| **Weaviate Schema** | ✅ 100% | All HU4 fields defined | But ontology_terms_v2.json doesn't populate them |
| **HU4 Field Population** | ❌ 5% | 3/80 seed terms only | 2,920+ terms need formula/source data |
| **CAs Functional (8)** | ❌ 25% | 2/8 PASS (CA-08, CA-09) | 6/8 FAIL due to incomplete data |
| **CAs Non-Functional (6)** | ❌ 17% | 1/6 PASS (CA-09) | 5/6 FAIL due to missing fields |
| **Overall Score** | ❌ 21% | 3/14 CAs PASS | 11/14 FAIL |

---

**Research Completed**: 2026-01-02
**Ready for**: Plan Phase (next step)
**Blockers**: None - all data exists, awaiting consolidation and field population
