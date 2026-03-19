# TASK-2026-01-22: Database Normalization 3NF

## Status: DONE ✅

## Summary
Normalize database schema to 3NF, consolidate duplicate catalogs, and standardize table naming with `bank_dim_*`, `bank_fact_*`, `bank_mv_*` convention.

## Acceptance Criteria
- [x] All dimension tables created (`bank_dim_*`)
- [x] All fact tables renamed (`bank_fact_*`)
- [x] Foreign keys added to fact tables
- [x] Materialized views created (`bank_mv_*`)
- [x] Application code updated (METRIC_TABLE_ROUTING, models)
- [x] Compatibility views created for legacy support
- [x] Verified: FK joins, NL2SQL config, backward compatibility

## Implementation Progress

### Phase 1: Create Dimensions ✅
- [x] `020_bank_dim_institucion.sql` - Consolidated institution catalog
- [x] `021_bank_dim_periodo.sql` - Time dimension (2000-2030)
- [x] `022_bank_dim_estado.sql` - Geographic dimension (32 states)
- [x] `023_bank_dim_auxiliares.sql` - Sector, currency, loan type, etc.

### Phase 2: Rename Fact Tables ✅
- [x] `024_rename_monthly_kpis.sql` - monthly_kpis → bank_fact_kpis_mensual
- [x] `025_rename_hip_cartera_comercial.sql` - 11 cartera comercial tables
- [x] `026_rename_remaining_fact_tables.sql` - vivienda, financieras, operativa

### Phase 3: Update Application Code ✅
- [x] `template_sql_generator.py` - METRIC_TABLE_ROUTING updated
- [x] `kpi.py` - SQLAlchemy models updated
- [x] `synonyms.yaml` - data_source references updated

### Phase 4: Materialized Views ✅
- [x] `030_bank_mv_ranking_cartera.sql` - Pre-computed rankings
- [x] `031_bank_mv_evolucion_cartera.sql` - YoY/MoM calculations

### Phase 5: Cleanup ✅
- [x] MV refresh functions created (`032_bank_mv_refresh_functions.sql`)
- [x] `bank_mv_refresh_all()` - Refresh all MVs with monitoring
- [x] `bank_mv_check_freshness()` - Monitor MV staleness
- [x] Unique index added for CONCURRENTLY refresh support
- [~] Legacy `hip_cat_*` tables - **KEPT** (used by CarteraComercial feature)
- [~] Deprecated columns - deferred (no immediate impact)

### Phase 6: Migration Execution & Testing ✅
- [x] Execute migrations in production database
- [x] Verify schema: 10 dimensions, 12 fact tables, 2 materialized views
- [x] Verify FK population: 5,537 KPI records with institucion_id + periodo_id
- [x] Verify MVs: ranking (17 banks), evolution (5,371 records, 19 banks, 299 periods)
- [x] Verify NL2SQL configuration (METRIC_TABLE_ROUTING uses bank_fact_*)
- [x] Verify FK joins work (bank_fact_kpis_mensual + dimensions)
- [x] Verify backward compatibility (monthly_kpis view works)

## Files Created/Modified

### New Files (10)
```
plugins/bank-advisor-private/migrations/
├── 020_bank_dim_institucion.sql
├── 021_bank_dim_periodo.sql
├── 022_bank_dim_estado.sql
├── 023_bank_dim_auxiliares.sql
├── 024_rename_monthly_kpis.sql
├── 025_rename_hip_cartera_comercial.sql
├── 026_rename_remaining_fact_tables.sql
├── 030_bank_mv_ranking_cartera.sql
├── 031_bank_mv_evolucion_cartera.sql
└── 032_bank_mv_refresh_functions.sql
```

### Modified Files (3)
```
plugins/bank-advisor-private/
├── src/bankadvisor/services/template_sql_generator.py
├── src/bankadvisor/models/kpi.py
└── config/synonyms.yaml
```

## Table Mapping Reference

| Old Name | New Name |
|----------|----------|
| monthly_kpis | bank_fact_kpis_mensual |
| hip_cat_institucion | bank_dim_institucion |
| hip_cartera_comercial_base_total | bank_fact_cartera_comercial |
| hip_cartera_total_mensual | bank_fact_cartera_total_mensual |
| metricas_financieras_ext | bank_fact_metricas_financieras |
| hip_info_operativa_consolidada | bank_fact_info_operativa |

## Migration Execution Summary

**Executed on:** 2026-01-22 (Production DB: ${BANK_ADVISOR_DB_HOST})

| Migration | Status | Result |
|-----------|--------|--------|
| 020_bank_dim_institucion | ✅ | 93 institutions |
| 021_bank_dim_periodo | ✅ | 372 periods (2000-2030) |
| 022_bank_dim_estado | ✅ | 34 states |
| 023_bank_dim_auxiliares | ✅ | 7 auxiliary dimensions |
| 024_rename_monthly_kpis | ✅ | 5,537 records with FKs |
| 025_rename_hip_cartera_comercial | ✅ | 11 tables + compatibility views |
| 026_rename_remaining_fact_tables | ✅ | 22 bank_fact_* tables |
| 030_bank_mv_ranking_cartera | ✅ | 17 banks ranked |
| 031_bank_mv_evolucion_cartera | ✅ | 5,371 records with YoY/MoM |
| 032_bank_mv_refresh_functions | ✅ | 4 functions for cron scheduling |

**Known Issues:**
- Some `bank_fact_*` are views (not tables) pointing to original hip_* tables
- Deadlock occurred during 025 but recovered

## MV Refresh Scheduling (Cron)

The following functions are available for scheduling:

```sql
-- Refresh all MVs (recommended: daily at 6 AM after ETL)
SELECT * FROM bank_mv_refresh_all();

-- Check freshness (for monitoring alerts)
SELECT * FROM bank_mv_check_freshness();
```

**Cron example (external):**
```bash
# Daily at 6:00 AM
0 6 * * * PGPASSWORD='...' psql -h HOST -U USER -d DB -c "SELECT bank_mv_refresh_all();"
```

**pg_cron example:**
```sql
SELECT cron.schedule('refresh-bank-mvs', '0 6 * * *', 'SELECT bank_mv_refresh_all();');
```

## Decisions Made

1. **Legacy `hip_cat_*` tables KEPT**: These are used by the CarteraComercial (Commercial Loan Portfolio) feature and are separate from the Monthly KPIs domain.

2. **Deprecated columns deferred**: The `banco_norm` and `fecha` columns in fact tables can be removed after extended validation, but they don't cause issues and provide backward compatibility.

---
*Created: 2026-01-22*
*Last Updated: 2026-01-22*
