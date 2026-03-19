---
status: REVIEW
---
# TASK: Extract TE_Invex_Sistema.xlsx from Tableau package into promotion pipeline

**Prioridad:** P2
**Fecha:** 2026-02-09
**Status:** BACKLOG

---

## Resumen

## Problem

`TE_Invex_Sistema.xlsx` (9KB, 19 rows) populates `bank_fact_kpis_mensual.tasa_sistema` and `tasa_invex_consumo`. The existing `load_te_invex()` loader works correctly, but the file is **missing from the incoming drop folder**. It only exists embedded inside `Invex_Tablero_202406_v2021.4.twbx` (at `Data/INVEX ANALITICS/TE_Invex_Sistema.xlsx`).

Prod currently has 220 rows with `tasa_sistema` data — this comes from historical loads. New drops won't include TE data unless we extract it from the Tableau package or request it separately from Bajaware.

## Research

### File content
- Sheet: "Tasa efectiva considerando prom"
- Columns: `Fecha1` (bimonthly dates), `Sistema` (system avg rate %), `Invex Consumo` (Invex consumer rate %)
- Range: 2019-10 to 2024-06 (19 data points, bimonthly)
- Very small file — only 9,423 bytes

### Tableau usage
- Datasource: "Tasa efectiva considerando prom (TE_Invex_Sistema)"
- Used in worksheet: "Tasa Int Efectiva" — compares Invex consumer rate vs system average
- Connection: `Data/INVEX ANALITICS/TE_Invex_Sistema.xlsx`

### Existing loader
- `loaders_unified.py:load_te_invex()` reads the file, renames columns, parses dates
- `merge_te()` joins on `fecha_month` only (no institution — it's system-wide data)
- Already has empty-schema guard (returns NULL columns if file missing)

## Plan

1. Add `.twbx` extraction logic to `data_promotion.py`: if `TE_Invex_Sistema.xlsx` not found in incoming or fallback, check for `.twbx` files and extract from within
2. Alternatively (simpler): copy the file from the extracted `.twbx` to `data/raw/` as a stable source — it's only 9KB and changes infrequently
3. Add to promotion specs (already done in current session)
4. Ask Fernando/Bajaware to include TE_Invex_Sistema.xlsx in future data drops

## Testing

```bash
# Verify file exists in twbx
unzip -l plugins/.../Invex_Tablero_202406_v2021.4.twbx | grep TE_Invex
# Extract and verify loader
cp /tmp/twbx_extract/Data/INVEX\ ANALITICS/TE_Invex_Sistema.xlsx data/raw/current/
.venv/bin/python3 -c "from etl.core.loaders_unified import load_te_invex, DataPaths; ..."
```

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
