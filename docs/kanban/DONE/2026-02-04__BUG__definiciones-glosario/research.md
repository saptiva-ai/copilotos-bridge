# Research: Definition & Glossary Queries Bug

## Investigation Date: 2026-02-05

---

## Root Cause Analysis

### 1. Weaviate IS Connected and Working
- **URL**: `https://101180puqcmpaidr4kkaia.c0.us-east1.gcp.weaviate.cloud`
- **Collection**: `Ontology_Term_V2` with 4,132 → 4,144 terms
- **Status**: CONNECTED and operational

### 2. Data Quality Was the Problem
The Weaviate collection contained mostly **OCR-extracted field labels**, not actual definitions:

**Before Fix (low quality):**
```
Name: "ROE"
Definition: "ROE - Detalle del reporte regulatorio"  ← NOT a definition!
```

### 3. Handler EXISTS - KnowledgeHandler
- File: `handlers/knowledge_handler.py`
- Intent: `BANK_KNOWLEDGE`
- Uses `WeaviateOntologyService` for semantic search
- Falls back to `LOCAL_GLOSSARY` (only ~12 terms)

---

## Fix Applied: 2026-02-05

### Step 1: Created Enrichment Script
```
tools/seeding/enrich_ontology_with_glosario.py
```

Extracts official CNBV definitions from `glosario_extracted_text.txt` (regulatory PDF OCR).

### Step 2: Added 12 Official Definitions
Terms added to `ontology_seed_terms.json`:

| Term | Source | Has Formula |
|------|--------|-------------|
| Cartera Comercial | CUB Art.1 XXIX-c | No |
| Cartera de Consumo | CUB Art.1 XXIX-a | No |
| Cartera Hipotecaria de Vivienda | CUB Art.1 XXIX-b | No |
| Índice de Capitalización | CUB Art.1 LXXX | Yes |
| ROE | Financial Metrics | Yes |
| ROA | Financial Metrics | Yes |
| Activo Total | Financial Metrics | No |
| Capital Neto | CUB Art.1 XXVIII | No |
| Cartera Crediticia | CUB Art.1 XXIX | No |
| Microcréditos | CUB Art.1 XXIX-a | No |
| Activos Ponderados Sujetos a Riesgo | CUB Art.1 IV | No |
| Utilidad Neta | Financial Metrics | No |

### Step 3: Reloaded Weaviate Cloud
```bash
python tools/seeding/load_ontology_weaviate_v2.py
```
- Total records: 4,144
- Seed terms: 41 (29 existing + 12 new)

---

## Verification

**After Fix (high quality):**
```
Name: "Cartera Comercial"
Definition: "Créditos directos o contingentes, incluyendo créditos puente 
denominados en moneda nacional, extranjera, en UDIs o en UMA, así como 
los intereses que generen, otorgados a personas morales o personas físicas 
con actividad empresarial..."
Source: glosario_cub_art1_XXIX_c
Synonyms: ['Cartera de Crédito Comercial', 'Créditos Comerciales', 
           'Commercial Loans', 'Commercial Portfolio']
```

```
Name: "Índice de Capitalización"
Definition: "Resultado de dividir el Capital Neto entre los Activos Ponderados 
Sujetos a Riesgo Totales, expresado en porcentaje..."
Formula: (Capital Neto / Activos Ponderados Sujetos a Riesgo Totales) × 100
```

---

## Remaining Work

### Must Deploy to Production
The fix requires:
1. ✅ `ontology_seed_terms.json` updated (committed)
2. ✅ Weaviate Cloud reloaded with new data
3. ⬜ Deploy backend with updated code (if any handler changes needed)
4. ⬜ E2E test to verify in staging/prod

### KnowledgeHandler May Need Priority Adjustment
Currently, semantic search returns BOTH high-quality and low-quality results.
The handler should prefer results with longer definitions.

---

## Files Changed

```
plugins/bank-advisor-private/
├── data/ontology_seed_terms.json          # +12 official definitions
└── tools/seeding/
    └── enrich_ontology_with_glosario.py   # NEW - enrichment script
```

---

## Commands for Future Reference

```bash
# Enrich seed terms with new definitions
python tools/seeding/enrich_ontology_with_glosario.py

# Reload Weaviate Cloud
python tools/seeding/load_ontology_weaviate_v2.py

# Verify definitions in Weaviate
# (see verification script in research notes)
```
