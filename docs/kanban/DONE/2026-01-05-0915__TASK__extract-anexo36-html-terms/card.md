---
id: "TASK-2026-01-05-0915__extract-anexo36-html-terms__html-parsing"
title: "Extract Additional Terms from Anexo 36 HTML Pages"
status: "DONE"
phase: "Complete"
priority: "P1"
closed: "2026-01-29"
blocked_by: []
scope_in:
  - "Parse 48 JSON files with HTML text from priority_pages/"
  - "Extract regulatory terms and definitions using NLP/heuristics"
  - "Generate structured term objects with page references"
  - "Target: +1,700-2,000 terms to reach 1,800-2,200 total Anexo 36 terms"
scope_out:
  - "ETL execution (separate from this task)"
  - "Formula/synonym extraction (Phase 2 of HU4)"
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

- **Objective**: Extract 1,700-2,000 additional regulatory terms from Anexo 36 HTML pages to supplement 61 report codes already consolidated.
- **Context**: Phase 1B identified data gap - only 61 structured report codes available, need HTML parsing to reach original target of 1,800-2,200 Anexo 36 terms.
- **Constraints**: HTML is semi-structured (tables + narrative text), requires parsing (BeautifulSoup), extraction heuristics, dedupe, and page refs for source_refs.

## Background

From **TASK-2026-01-02-2048__complete-hu4-cas Phase 1B**:
- ✅ Consolidated 61 report codes from `anexo36_report_codes_clean.json`
- ⚠️ Gap: 48 priority page JSON files contain only HTML text (not structured terms)
- 📊 Original plan expected 1,800-2,200 terms, actual: 61 terms
- 🎯 This task closes the gap by parsing HTML to extract remaining ~1,700-2,000 terms

## Input Data

- **Location**: `plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages/`
- **Files**: 48 JSON files in priority_pages (filenames include page_0001.json..page_0006.json and page_0056.json..page_0097.json)
- **Format**: `{"page_number": N, "section": "...", "text": "<html>...", ...}`
- **Note**: There are 48 files total; page_number values span up to 97 (max), but only those 48 pages are present.

## Expected Output

Append to `anexo36_terms.json`:
```json
{
  "term_id": "hash",
  "name": "Term name",
  "definition": "Definition...",
  "source": "anexo36",
  "category": "regulatory",
  "source_refs": ["doc:Anexo_36_page_N"]
}
```

## Success Criteria

- Extract 1,700+ new terms from 48 HTML pages
- Each term has name, definition, source_refs with page number
- Combined total: 1,800-2,200 Anexo 36 terms
- No duplicates with existing 61 report codes

# Updates
- 2026-01-05 09:20 - Created as scope change from Phase 1B. HTML parsing out of Phase 1B scope. Priority P1 for completing HU4 CA-01 (need 3,000+ total terms).
- 2026-01-05 09:56 - Unblocked after Phase 1B completion. Plan drafted for HTML parsing + dedupe; ready to implement extraction.
- 2026-01-05 10:05 - Verified input set: 48 files in priority_pages, with page_number values up to 97.
- 2026-01-05 17:56 - Parsed additional HTML from `pages/` (10 files). Added 44 new terms; total Anexo 36 terms now 275.
- 2026-01-05 17:56 - Full OCR extraction blocked: `extract_anexo36_saptiva.py` requires `SAPTIVA_API_KEY` not configured.
- 2026-01-05 20:07 - OCR cache expanded: 392 pages total (384 new on 2026-01-05), success 284 / fail 100.
- 2026-01-05 20:07 - HTML extraction on cached pages added 573 new terms; Anexo 36 total now 848.
- 2026-01-29 17:35 - Resumed OCR extraction with SAPTIVA_API_KEY configured.
- 2026-01-29 19:05 - OCR completed: 584/584 pages (186 new pages extracted, 6 failed HTTP 500).
- 2026-01-29 19:06 - Final HTML extraction: 2,136 total terms (767 new). **OBJECTIVE MET: 1,800-2,200 target achieved.**
- 2026-01-30 01:20 - **Weaviate Cloud sync complete**: 4,132 total ontology records loaded (ETL + anexo36 + seeds).

# Final Results

| Metric | Value |
|--------|-------|
| Pages OCR'd | 584 |
| Anexo 36 terms | 2,136 |
| Report codes | 71 |
| Concepts | 2,065 |
| Duplicates removed | 11,711 |
| Tokens used | 391,269 |
| OCR time | 90 min |
| **Weaviate total** | **4,132** |
