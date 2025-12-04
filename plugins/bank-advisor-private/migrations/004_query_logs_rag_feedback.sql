-- Migration: Query Logs for RAG Feedback Loop
-- Purpose: Log successful queries to enable auto-seeding to RAG
-- Date: 2025-12-03
-- Related: Q1 2025 - RAG Feedback Loop implementation

-- Enable pgvector extension for embeddings storage (optional - uncomment if available)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Create query_logs table
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),

    -- Query details
    user_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    banco VARCHAR(50),
    metric VARCHAR(100) NOT NULL,
    intent VARCHAR(50) NOT NULL,

    -- Execution metadata
    execution_time_ms FLOAT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    pipeline_used VARCHAR(20) DEFAULT 'nl2sql',  -- 'nl2sql' or 'legacy'
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- RAG seeding metadata
    seeded_to_rag BOOLEAN DEFAULT FALSE,
    seed_timestamp TIMESTAMPTZ,
    rag_confidence FLOAT,  -- Calculated confidence for RAG seeding

    -- Optional: Store embedding for faster similarity search
    -- query_embedding VECTOR(1536),  -- OpenAI ada-002 dimension (uncomment if using pgvector)

    -- Additional context
    mode VARCHAR(20),  -- 'dashboard' or 'timeline'
    filters JSONB,  -- Parsed query filters as JSON
    result_row_count INTEGER,

    CONSTRAINT query_logs_confidence_check CHECK (rag_confidence >= 0 AND rag_confidence <= 1)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_success ON query_logs(success) WHERE success = TRUE;
CREATE INDEX IF NOT EXISTS idx_query_logs_metric ON query_logs(metric);
CREATE INDEX IF NOT EXISTS idx_query_logs_banco ON query_logs(banco);
CREATE INDEX IF NOT EXISTS idx_query_logs_seeded ON query_logs(seeded_to_rag) WHERE seeded_to_rag = FALSE;
CREATE INDEX IF NOT EXISTS idx_query_logs_pipeline ON query_logs(pipeline_used);

-- Create partial index for successful unseeded queries (main use case for feedback loop)
CREATE INDEX IF NOT EXISTS idx_query_logs_feedback_candidates
ON query_logs(timestamp DESC, rag_confidence DESC)
WHERE success = TRUE
  AND seeded_to_rag = FALSE;

-- Uncomment if using pgvector for embedding-based similarity
-- CREATE INDEX IF NOT EXISTS idx_query_logs_embedding
-- ON query_logs USING ivfflat (query_embedding vector_cosine_ops)
-- WITH (lists = 100);

-- Create view for RAG feedback candidates
CREATE OR REPLACE VIEW rag_feedback_candidates AS
SELECT
    query_id,
    user_query,
    generated_sql,
    banco,
    metric,
    intent,
    execution_time_ms,
    rag_confidence,
    timestamp,
    AGE(NOW(), timestamp) as query_age
FROM query_logs
WHERE success = TRUE
  AND seeded_to_rag = FALSE
  AND timestamp > NOW() - INTERVAL '90 days'
  AND timestamp < NOW() - INTERVAL '1 hour'  -- Wait 1 hour before seeding
  AND rag_confidence > 0.7  -- Only high-confidence queries
ORDER BY rag_confidence DESC, timestamp DESC
LIMIT 100;

-- Create function to calculate RAG confidence
CREATE OR REPLACE FUNCTION calculate_rag_confidence(
    p_execution_time_ms FLOAT,
    p_query_age_days INTEGER
) RETURNS FLOAT AS $$
DECLARE
    confidence FLOAT := 1.0;
    time_factor FLOAT;
    age_factor FLOAT;
BEGIN
    -- Execution time factor (faster = higher confidence)
    IF p_execution_time_ms < 200 THEN
        time_factor := 1.0;
    ELSIF p_execution_time_ms < 500 THEN
        time_factor := 0.9;
    ELSIF p_execution_time_ms < 1000 THEN
        time_factor := 0.7;
    ELSE
        time_factor := 0.5;
    END IF;

    -- Age decay factor (linear over 90 days)
    age_factor := GREATEST(0.5, 1.0 - (p_query_age_days::FLOAT / 90.0) * 0.5);

    confidence := time_factor * age_factor;

    RETURN LEAST(1.0, GREATEST(0.0, confidence));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to auto-calculate RAG confidence on insert
CREATE OR REPLACE FUNCTION trigger_calculate_rag_confidence()
RETURNS TRIGGER AS $$
BEGIN
    NEW.rag_confidence := calculate_rag_confidence(
        NEW.execution_time_ms,
        EXTRACT(DAYS FROM NOW() - NEW.timestamp)::INTEGER
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER query_logs_confidence_trigger
BEFORE INSERT ON query_logs
FOR EACH ROW
EXECUTE FUNCTION trigger_calculate_rag_confidence();

-- Create materialized view for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS query_logs_analytics AS
SELECT
    DATE_TRUNC('day', timestamp) as day,
    pipeline_used,
    COUNT(*) as total_queries,
    COUNT(*) FILTER (WHERE success = TRUE) as successful_queries,
    AVG(execution_time_ms) as avg_execution_time,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms) as p50_execution_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time,
    COUNT(DISTINCT metric) as unique_metrics,
    COUNT(DISTINCT banco) as unique_bancos,
    COUNT(*) FILTER (WHERE seeded_to_rag = TRUE) as seeded_count
FROM query_logs
WHERE timestamp > NOW() - INTERVAL '90 days'
GROUP BY day, pipeline_used
ORDER BY day DESC;

CREATE UNIQUE INDEX ON query_logs_analytics (day, pipeline_used);

-- Function to refresh analytics (call daily)
CREATE OR REPLACE FUNCTION refresh_query_logs_analytics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY query_logs_analytics;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE query_logs IS 'Logs all queries for RAG feedback loop and analytics';
COMMENT ON COLUMN query_logs.rag_confidence IS 'Auto-calculated confidence for RAG seeding (0-1), based on execution time and age';
COMMENT ON COLUMN query_logs.seeded_to_rag IS 'Whether this query has been seeded to Qdrant RAG';
COMMENT ON VIEW rag_feedback_candidates IS 'High-confidence unseeded queries ready for RAG feedback';
COMMENT ON FUNCTION calculate_rag_confidence IS 'Calculate confidence score for RAG seeding based on query performance and age';
