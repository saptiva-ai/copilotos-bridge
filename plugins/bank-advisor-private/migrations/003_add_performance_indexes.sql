-- Migration 003: Add Performance Indexes for BankAdvisor
-- Date: 2025-11-27
-- Purpose: Optimize query performance for common access patterns
-- Impact: -30-40% latency for multi-banco and time-range queries

-- ============================================================================
-- Index 1: Composite index for banco + fecha queries (most common pattern)
-- ============================================================================
-- Covers queries like:
-- - "IMOR de INVEX en 2024"
-- - "Compara INVEX vs SISTEMA últimos 12 meses"
-- - "Top 5 bancos por ICAP 2024"

CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco_fecha
ON monthly_kpis(banco_norm, fecha DESC)
WHERE fecha > CURRENT_DATE - INTERVAL '2 years';

COMMENT ON INDEX idx_monthly_kpis_banco_fecha IS
'Composite index for banco + fecha. Optimizes most common query pattern. Partial index covers last 2 years only.';

-- ============================================================================
-- Index 2: Single column index for fecha (timeline queries)
-- ============================================================================
-- Covers queries like:
-- - "Todos los bancos en 2024"
-- - "Sistema financiero últimos 12 meses"

CREATE INDEX IF NOT EXISTS idx_monthly_kpis_fecha
ON monthly_kpis(fecha DESC)
WHERE fecha > CURRENT_DATE - INTERVAL '2 years';

COMMENT ON INDEX idx_monthly_kpis_fecha IS
'Date index for timeline queries. Partial index covers last 2 years only.';

-- ============================================================================
-- Index 3: GIN index for full-text search on banco_nombre (future use)
-- ============================================================================
-- Covers queries like:
-- - "Bancos que contengan 'SANTANDER'"
-- - "BBVA*" (wildcard search)
-- Not actively used yet but prepared for advanced search

CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco_gin
ON monthly_kpis USING gin(to_tsvector('spanish', banco_nombre));

COMMENT ON INDEX idx_monthly_kpis_banco_gin IS
'Full-text search index for banco_nombre. Future-proofing for advanced search capabilities.';

-- ============================================================================
-- Index 4: Covering index for common metrics (IMOR, ICOR, ICAP)
-- ============================================================================
-- Optimizes queries that SELECT specific metrics without needing table scan
-- Covers: fecha, banco_norm, imor, icor, icap_total

CREATE INDEX IF NOT EXISTS idx_monthly_kpis_common_metrics
ON monthly_kpis(fecha DESC, banco_norm)
INCLUDE (imor, icor, icap_total, cartera_total)
WHERE fecha > CURRENT_DATE - INTERVAL '2 years';

COMMENT ON INDEX idx_monthly_kpis_common_metrics IS
'Covering index for most common metrics. Index-only scans possible for IMOR/ICOR/ICAP queries.';

-- ============================================================================
-- Analyze table to update statistics after index creation
-- ============================================================================
ANALYZE monthly_kpis;

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================

-- Check index sizes
-- SELECT
--     indexname,
--     pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
-- FROM pg_indexes
-- WHERE tablename = 'monthly_kpis'
-- ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Check index usage (run after some queries)
-- SELECT
--     indexrelname AS index_name,
--     idx_scan AS index_scans,
--     idx_tup_read AS tuples_read,
--     idx_tup_fetch AS tuples_fetched
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public' AND relname = 'monthly_kpis'
-- ORDER BY idx_scan DESC;

-- Test query performance (before/after)
-- EXPLAIN ANALYZE
-- SELECT fecha, banco_norm, imor, icor
-- FROM monthly_kpis
-- WHERE banco_norm = 'INVEX'
--   AND fecha >= '2024-01-01'
-- ORDER BY fecha DESC;
