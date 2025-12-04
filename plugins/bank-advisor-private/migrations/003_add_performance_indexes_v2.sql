-- Migration 003: Add Performance Indexes for BankAdvisor (v2 - Simplified)
-- Date: 2025-11-27
-- Purpose: Optimize query performance for common access patterns
-- Impact: -30-40% latency for multi-banco and time-range queries

-- ============================================================================
-- Index 1: Composite index for banco + fecha queries (most common pattern)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco_fecha
ON monthly_kpis(banco_norm, fecha DESC);

COMMENT ON INDEX idx_monthly_kpis_banco_fecha IS
'Composite index for banco + fecha. Optimizes most common query pattern.';

-- ============================================================================
-- Index 2: Single column index for fecha (timeline queries)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_fecha
ON monthly_kpis(fecha DESC);

COMMENT ON INDEX idx_monthly_kpis_fecha IS
'Date index for timeline queries.';

-- ============================================================================
-- Index 3: Index for banco_norm alone (banco-specific queries)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco
ON monthly_kpis(banco_norm);

COMMENT ON INDEX idx_monthly_kpis_banco IS
'Banco index for bank-specific queries.';

-- ============================================================================
-- Analyze table to update statistics after index creation
-- ============================================================================
ANALYZE monthly_kpis;

-- ============================================================================
-- Verification: Check index sizes
-- ============================================================================
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size,
    idx_scan AS scans,
    idx_tup_read AS tuples_read
FROM pg_indexes
LEFT JOIN pg_stat_user_indexes ON indexrelname = indexname
WHERE tablename = 'monthly_kpis'
ORDER BY pg_relation_size(indexname::regclass) DESC;
