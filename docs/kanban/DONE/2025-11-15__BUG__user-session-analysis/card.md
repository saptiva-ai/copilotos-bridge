# BUG-015: User Session Analysis & Bug Triage

## Status: DONE

## Priority: High

## Created: 2026-01-13

## Closed: 2026-01-20

## Summary

Análisis de conversaciones de usuarios de prueba en producción para identificar y categorizar bugs del sistema bank-advisor.

## Context

Los usuarios de prueba reportaron problemas con el chatbot. Se extrajeron las conversaciones de MongoDB (producción) para análisis de bugs.

## Data Sources

- **MongoDB**: `${PROD_MONGO_HOST}` (container: octavios-chat-bajaware_invex-mongodb)
- **Collections**: `messages`, `chat_sessions`, `users`
- **Period**: 2026-01-06 a 2026-01-13

## Exported Files

| File | Location | Size |
|------|----------|------|
| Full export | `user_conversations_debug.json` | 2.1MB |
| Bug report | `plugins/bank-advisor-private/BUG_REPORT_USER_SESSIONS_2026-01-13.md` | - |

## Bugs Identified

### Fixed

| ID | Bug | Resolution |
|----|-----|------------|
| BUG-CLARIFICATION | Clarification triggered for evolution queries | ClarificationStrategy refactor |
| BUG-SISTEMA | SISTEMA aggregation for hip_cartera_vivienda | Dynamic SUM + GROUP BY |
| BUG-RANKING | TOP N queries fail | Fixed in BUG-CH-006 (bank-advisor v1.4.9) |
| BUG-RESERVAS | RESERVAS metric not mapped | Column exists (`reservas_etapa_todas`) + mapped in synonyms.yaml |
| BUG-HSBC-GAPS | HSBC data missing for 2023-2024 | **NOT A BUG** - Data verified complete (2000-2025) |

### Deferred (Data Limitation)

| ID | Bug | Resolution |
|----|-----|------------|
| BUG-TARJETAS | Tarjetas de crédito metric unavailable | Moved to separate task - CNBV source limitation |

## Acceptance Criteria

- [x] Extract user conversations from production MongoDB
- [x] Identify bug patterns from error responses
- [x] Create detailed bug report with reproduction steps
- [x] Fix critical clarification issues
- [x] Fix HSBC data gaps → Verified NOT A BUG (data complete)
- [x] Map RESERVAS metric → Already mapped
- [x] Implement ranking queries → Fixed in BUG-CH-006

## Related Files

- `plugins/bank-advisor-private/src/bankadvisor/services/clarification_service.py`
- `plugins/bank-advisor-private/src/main.py`
- `plugins/bank-advisor-private/config/columns.yaml`
- `plugins/bank-advisor-private/config/synonyms.yaml`

## Verification (2026-01-20)

### HSBC Data Verification
```sql
SELECT DATE_TRUNC('year', fecha) as year, COUNT(*) as total_rows
FROM monthly_kpis WHERE banco_norm = 'HSBC'
GROUP BY 1 ORDER BY 1;

-- Result: Complete data 2000-2025 (299 rows total)
-- 2023: 12 rows ✅
-- 2024: 12 rows ✅
-- 2025: 10 rows ✅
```

### RESERVAS Mapping
- Column: `reservas_etapa_todas` (exists in schema)
- Synonym: `reservas → reservas_etapa_todas` (synonyms.yaml:215)

### RANKING Queries
- Fixed in BUG-CH-006 (deployed bank-advisor v1.4.9)
- Added typo aliases: `hipetecaria`, `hipetecario`
- Ranking keywords: "por banco", "por año" working

## Labels

`bug`, `investigation`, `user-feedback`, `bank-advisor`, `closed`
