# Validation

## Latest Validation: 2026-01-05 20:07

### Commands
- .venv/bin/python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter
pages_dir = Path("plugins/bank-advisor-private/data/results/anexo36_extraction/pages")
counts = Counter()
status = Counter()
for path in pages_dir.glob("page_*.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    ts = data.get("timestamp") or ""
    date = ts.split("T")[0] if ts else "unknown"
    counts[date] += 1
    status[(date, bool(data.get("success")))] += 1
print("pages_total", sum(counts.values()))
print("by_date", dict(counts))
print("by_date_success", dict(status))
PY
- .venv/bin/python plugins/bank-advisor-private/scripts/extract_anexo36_html_terms.py --input plugins/bank-advisor-private/data/results/anexo36_extraction/pages --output plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json --stats --keep-noncodes
- .venv/bin/python3 - <<'PY'
import json
from pathlib import Path
terms = json.loads(Path("plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json").read_text())
print("total", len(terms))
print("missing_defs", sum(1 for t in terms if not t.get("definition")))
PY

### Results
- PASS/FAIL: **FAIL** (target 1,700+ not reached)
- Pages cached: 392 total (384 new on 2026-01-05), success 284 / fail 100
- Extracted: 573 new terms from HTML (392 pages), 7,109 duplicates removed
- Final Anexo 36 total: 848 terms in `anexo36_terms.json`

### Notes
- Validate >= 1,700 new terms and no duplicates with report codes.
- Spot-check 10 random terms for correct definitions + source_refs.
- Full extraction still incomplete: OCR cache covers pages 1-392; remaining 192 pages pending and 100 failed pages need retry.

---

## Previous Validation: 2026-01-05 17:20

### Commands
- .venv/bin/python plugins/bank-advisor-private/scripts/extract_anexo36_html_terms.py --input plugins/bank-advisor-private/data/results/anexo36_extraction/priority_pages --output plugins/bank-advisor-private/data/results/anexo36_extraction/anexo36_terms.json --stats

### Results
- PASS/FAIL: **FAIL** (target 1,700+ not reached)
- Extracted: 160 new terms from HTML (48 pages), 1,043 duplicates removed
- Final Anexo 36 total: 231 terms in `anexo36_terms.json`

### Notes
- HTML priority pages appear insufficient for the 1,700-2,000 target; next step likely needs full Anexo 36 extraction or a richer field-level parsing strategy.
