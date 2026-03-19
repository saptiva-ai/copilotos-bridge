---
status: REVIEW
---
# BUG: TDA date format bug drops 99.8% of data in merge_tda()

**Prioridad:** P0
**Fecha:** 2026-02-09
**Status:** BACKLOG

---

## Resumen

## Problem

`load_tda()` at `loaders_unified.py:555` parses TDA.xlsx dates using `%d/%m/%Y` (European) but the actual format is `%m/%d/%Y` (US). This causes `12/01/2021` (December 1) to be parsed as January 12, shifting ALL months to incorrect values.

The downstream `merge_tda()` joins on `["fecha_month", "institucion"]` — since dates are wrong, the left-join produces NULL for >99% of rows. Only January dates survive (where day=01 happens to equal month=01).

**Impact**: `bank_fact_kpis_mensual.tda_cartera_total` has 23 non-null rows in prod out of 5,537 total (0.4%). With the fix, coverage jumps to 7,296/12,097 (60%). INVEX gets 107/107 (100%).

## Research

- TDA.xlsx column `Fecha` contains US-format dates: `12/01/2021` = Dec 1, confirmed by `cve_periodo=202112`
- `normalize_institution_code()` produces matching 6-digit codes (040xxx) on both sides
- CNBV dates parse correctly with `%Y-%m-%d` (ISO format in source)
- The 23 surviving prod rows are exactly the January periods where the month/day swap is harmless
- TDA covers 300 periods (200012-202511) but CNBV only covers 107 (201701-202511), so max theoretical coverage is ~60%

## Plan

1. Fix `loaders_unified.py:555`: change `%d/%m/%Y` → `%m/%d/%Y`
2. Add empty-schema guard to `merge_tda()` (like `merge_te()` already has)
3. Add diagnostic logging: `logger.info(f"TDA merge: {matched}/{total} rows matched")`
4. Dry-run verification with incoming data before any prod deployment

## Testing

```bash
# Verify fix in isolation
cd plugins/bank-advisor-private
.venv/bin/python3 -c "
from etl.core.loaders_unified import load_tda, DataPaths
from pathlib import Path
paths = DataPaths(Path('data/raw/incoming/drive-download-20260209T193355Z-1-001'))
tda = load_tda(paths)
sample = tda.head(5).collect()
print(sample)
# Verify Dec 2021 date parses correctly
assert sample['fecha'][0].month == 12, 'Date format still wrong'
"
```

## Status

**FIX ALREADY APPLIED** in `loaders_unified.py` and `transforms.py`. Awaiting prod deployment verification.

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
