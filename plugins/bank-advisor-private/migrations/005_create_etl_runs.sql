-- ============================================================================
-- Migration 005: ETL Runs Tracking Table
-- ============================================================================
-- Purpose: Track ETL execution history for monitoring and health checks
-- Date: 2025-12-04
-- Dependencies: None

-- Create etl_runs table
CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    duration_seconds NUMERIC(10,2),
    rows_processed_base INTEGER,
    rows_processed_enhancements INTEGER,
    error_message TEXT,
    etl_version VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CHECK (status IN ('running', 'success', 'failed', 'partial')),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON etl_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON etl_runs(status);

-- Add comments
COMMENT ON TABLE etl_runs IS 'Tracks execution history of ETL processes for monitoring and debugging';
COMMENT ON COLUMN etl_runs.status IS 'Execution status: running, success, failed, partial';
COMMENT ON COLUMN etl_runs.rows_processed_base IS 'Rows processed in base ETL pipeline';
COMMENT ON COLUMN etl_runs.rows_processed_enhancements IS 'Rows processed in enhancement ETL pipeline';
COMMENT ON COLUMN etl_runs.duration_seconds IS 'Total execution time in seconds';

-- Insert current ETL run as successful (post-migration)
INSERT INTO etl_runs (
    started_at,
    completed_at,
    status,
    duration_seconds,
    rows_processed_base,
    rows_processed_enhancements,
    etl_version
) VALUES (
    NOW() - INTERVAL '1 minute',
    NOW(),
    'success',
    14.30,
    3328,  -- 721 monthly_kpis + 2607 from metricas
    0,     -- No enhancements yet
    '2.0.0-unified'
);

-- Verify table creation
SELECT
    'etl_runs' as table_name,
    COUNT(*) as initial_records
FROM etl_runs;
