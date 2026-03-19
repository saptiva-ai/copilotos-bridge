# Plan

## Objective
- Extract additional Anexo 36 terms from HTML pages and append to anexo36_terms.json with page refs and dedupe.

## Scope
### In
- Parse HTML from priority_pages/*.json.
- Extract term/definition pairs from tables and narrative text (bold/italic, colon patterns, definicion phrases).
- Normalize and deduplicate against existing report codes in anexo36_terms.json.
- Emit stats and QA samples for manual review.

### Out
- ETL execution or Weaviate load.
- Formula/synonym extraction (Phase 2 of HU4).
- Manual labeling beyond targeted QA samples.

## Phases
### Phase 1: Discovery + parser scaffolding
- [ ] Build a manifest for the 48 priority_pages files (page_number values span up to 97).
- [ ] Inspect representative pages (index tables, instructions, narrative) to catalog HTML patterns.
- [ ] Implement parser with BeautifulSoup:
  - Table rows -> term + definition (skip empty/header rows).
  - Paragraphs/list items with <b>/<strong> and report code pattern [A-Z]-\d{4}.
  - Definition sentences using regex (":", "Se entiende por", "Para efectos de", "Se considerara").
- [ ] Normalize text (strip, collapse whitespace, remove header/footer noise).

#### Phase 1 Files
- plugins/bank-advisor-private/scripts/extract_anexo36_html_terms.py (new)
- docs/kanban/BACKLOG/TASK-2026-01-05-0915__extract-anexo36-html-terms__html-parsing/research.md

### Phase 2: Dedupe + output
- [ ] Load existing anexo36_terms.json and build normalized name/code sets.
- [ ] Generate term_id (md5 of name for non-code terms; keep code-based hash for report codes).
- [ ] Write merged output to anexo36_terms.json (or anexo36_terms_html.json as intermediate).
- [ ] Emit stats: total extracted, per-page counts, duplicates removed, missing definitions.

#### Phase 2 Files
- plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json
- plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms_html.json (optional)

## Validation Commands
- python plugins/bank-advisor-private/scripts/extract_anexo36_html_terms.py --input plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages --output plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms_html.json --stats
- python - <<'PY'
import json
from pathlib import Path
terms = json.loads(Path("plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json").read_text())
print("total", len(terms))
print("missing_defs", sum(1 for t in terms if not t.get("definition")))
PY

## Success Criteria
- >= 1,700 new terms extracted from HTML pages (post-dedupe).
- Each term has name, definition (or explicit placeholder), and source_refs with page number.
- No duplicates with existing 61 report codes.
- Output schema matches consolidate_anexo36.py format.
