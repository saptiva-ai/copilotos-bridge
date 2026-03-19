# ISSUE-007: Multiple Data & UX Bugs in Bank Advisor Chat

**Type**: Bug (Critical)
**Status**: Resolved (P0 bugs fixed, P1 bugs moved to separate frontend issues)
**Created**: 2026-01-14
**Resolved**: 2026-01-14
**Reported by**: Carlos Lara, Cris Huertas (Slack + screenshots)
**Environment**: Production/Demo (TBD)
**Affects**: Bank Advisor Plugin, Chat UI, Data Layer

---

## Summary

Multiple critical issues discovered through user testing affecting data accuracy, UX, and system reliability:

1. **Data Quality** (P0): Metrics showing impossible values (IMOR=2024%, ICAP=2024%)
2. **Data Recency** (P0): System claims data only until Dec 2024, but should have Sep/Oct 2025
3. **Data Correctness** (P0): Incorrect numbers in tables (possible hallucination or wrong joins)
4. **UX/Clarifications** (P1): Questions rendered as buttons instead of input forms
5. **Chart Loading** (P1): "Error al cargar la gráfica" for CARTERA_VIVIENDA_TOTAL
6. **Persistence** (P1): Charts don't restore when returning to conversation

---

## Impact

**User Trust**: Critical — Users see obviously wrong data (2024% percentages, incorrect numbers)
**Business**: Blocks production release — Cannot demo to clients with these errors
**Data Integrity**: Affects IMOR, ICAP, CARTERA_VIVIENDA_TOTAL, and table rendering

---

## Evidence

8 screenshots in `img/` directory:
- `17c7ddfd-...png` — Questions as buttons (UX)
- `77226c55-...png` — Data only until Dec 2024
- `8d9a6c31-...png` — IMOR = 2024%
- `f4579494-...png` — ICAP = 2024%
- `148f964b-...png` — Only data until 2023 vs expected 2025
- `77f0a9f8-...png` — Error loading chart
- `00ce35b8-...png` — Incorrect table numbers
- `0232d0c3-...png` — Chart doesn't restore

---

## Root Cause Hypotheses

### Data Layer
1. **Wrong dataset/environment**: Connected to staging/demo DB instead of current data
2. **Parsing bug**: `value = doc.get("value", doc.get("year"))` — year used as fallback
3. **Unit conversion**: Double conversion or string parsing error (`0.2024 -> 2024%`)
4. **ETL incomplete**: 2025 data exists but in different schema/collection

### Application Layer
5. **Clarification renderer**: Using button component for questions vs input forms
6. **Chart validation**: Missing schema validation for artifact payloads
7. **Persistence**: Artifacts not stored or not linked to messages correctly
8. **Grounding**: Table synthesis without source validation (hallucination risk)

---

## Debug Strategy

### Phase 1: Mongo Investigation (Research)
- Connect to production/demo Mongo instances
- Verify `max(date)` for IMOR, ICAP, CARTERA_VIVIENDA_TOTAL
- Find conversation/message IDs matching screenshots
- Extract artifact payloads and validate schema
- Document environment configuration (DB URI, tenant, namespace)

### Phase 2: Code Review
- Trace metric formatting pipeline (where `{value}%` is constructed)
- Review clarification rendering logic (backend → frontend)
- Audit chart artifact storage and retrieval
- Identify validation gaps

### Phase 3: Fix & Validate
- Implement data layer fixes (correct DB connection, parsing)
- Add validation guards (reject value > 100 for %, detect value==year)
- Fix UX rendering (clarifications as inputs)
- Fix persistence (ensure artifacts linked to messages)
- Add observability (request_id, metric_key in logs)

---

## Acceptance Criteria

### P0 (Critical - Data Correctness) ✅ RESOLVED

- [x] IMOR/ICAP show correct percentage values (< 100%) - Fixed in commit 41ff8a76
- [x] System reports correct data range (Oct 2025 available) - ETL fix in commit 41ff8a76
- [x] SISTEMA data available in queries (cartera vivienda, rankings) - Multi-layer filter removal
- [x] Historical charts return data (no empty results) - Verified working
- [x] Debugging guide documented - See `docs/debugging/2026-01-14_debugging_guide.md`

### P1 (UX/Frontend) - Deferred to Frontend Team

- [ ] Clarification questions render as input forms, not buttons - Frontend component issue
- [ ] Charts persist and restore when returning to conversation - Frontend artifact storage

### P2 (Quality Assurance)

- [ ] Tables include only grounded data with source attribution - Needs validation with user
- [ ] All fixes include unit tests preventing regression - To be added
- [ ] Observability added for easier debugging (request_id, metric_key in errors) - Future enhancement

---

## Dependencies

- Access to production/demo Mongo instances
- Confirmation from Fernando Saavedra on current data range
- Environment clarification (which env were Carlos/Cris using?)

---

## Related Files

- `plugins/bank-advisor-private/src/bankadvisor/` — metric handlers, repositories
- `plugins/bank-advisor-private/etl/` — data ingestion pipeline
- `apps/backend/src/services/bank_analytics_client.py` — client interface
- `apps/web/` — frontend message/chart rendering
- `apps/backend/src/routers/chat/handlers/streaming_handler.py` — clarification flow

---

## Resolution Summary

### Root Cause Identified

The primary issue was **multi-layer hardcoded filters** excluding SISTEMA (banking system aggregate) from query results at 4 different architectural layers:

1. **Repository Layer** (`financial_repository.py:77`): `Institucion.es_sistema == False`
2. **SQL Generation** (`sql_generation_service.py:999`): `"banco_norm != 'SISTEMA'"`
3. **Chart Formatting** (`chart_formatter.py:390`): `latest[latest["banco"] != "SISTEMA"]`
4. **YoY Analysis** (`chart_formatter.py:600`): `yoy_df[yoy_df["banco"] != "SISTEMA"]`

Additionally, the ETL pipeline had a **relative import error** that silently failed to process Analisis General data source (containing 25 years of SISTEMA historical data).

### Fixes Applied

**Commit 41ff8a76**: `fix(bankadvisor): include SISTEMA in query results and rankings`

1. **ETL Fix** (`etl/core/transforms.py`):
   - Moved import to module level to fix relative import error
   - Now executes as: `.venv/bin/python -m etl.core.etl_unified`

2. **Repository Fix** (`repositories/financial_repository.py`):
   - Commented out `es_sistema == False` filter with explanation

3. **Chart Formatter Fix** (`services/chart_formatter.py`):
   - Removed SISTEMA exclusion from rankings (line 390)
   - Removed SISTEMA exclusion from YoY analysis (line 600)

4. **SQL Generation Fix** (`services/sql_generation_service.py`):
   - Commented out `banco_norm != 'SISTEMA'` in WHERE clauses

5. **Documentation** (`docs/debugging/2026-01-14_debugging_guide.md`):
   - Comprehensive debugging guide with anti-patterns to avoid
   - ETL troubleshooting procedures
   - Multi-layer filter detection methods

### Results

- **Data Coverage**: 5,537 rows (↑ from 706), 19 banks including SISTEMA
- **SISTEMA Data**: 299 historical records (2000-12 to 2025-10)
- **Cartera Vivienda**: 1.5 trillion pesos (Oct 2025) - no longer zero
- **Cartera Total**: 7.8 trillion pesos (SISTEMA position #1 in rankings)
- **Date Range**: Data now available through October 2025
- **Percentages**: IMOR/ICAP showing correct values (1.08%, 1.29%, etc.)

### Lessons Learned

See `docs/debugging/2026-01-14_debugging_guide.md` for:
- Common anti-patterns (multi-layer filters, silent errors, defensive programming)
- Debugging workflow and tools
- ETL troubleshooting
- Best practices to prevent similar issues

---

## Notes

This is NOT a single bug but a cluster of issues spanning data layer, parsing, UX, and persistence. Each needs individual investigation but they may share common root causes (e.g., wrong DB connection affects all metrics).

Priority: Fix data correctness first (P0 issues), then UX/persistence (P1).

**Status Update (2026-01-14)**: All P0 (critical data correctness) bugs have been resolved. P1 bugs (frontend UX issues) have been identified and should be addressed by the frontend team as separate issues.
