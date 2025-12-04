"""
Query Logger Service for RAG Feedback Loop

Logs successful query executions to enable automatic RAG seeding.
Part of Q1 2025 RAG Feedback Loop implementation.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class QueryLog:
    """Logged successful query for RAG feedback."""
    query_id: uuid.UUID
    user_query: str
    generated_sql: str
    banco: Optional[str]
    metric: str
    intent: str
    execution_time_ms: float
    success: bool
    error_message: Optional[str]
    pipeline_used: str
    timestamp: datetime
    seeded_to_rag: bool
    rag_confidence: float


class QueryLoggerService:
    """
    Service for logging queries to feed RAG feedback loop.

    Logs all query executions (successful and failed) to enable:
    1. RAG auto-seeding from successful queries
    2. Analytics on query patterns
    3. Pipeline performance monitoring
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_successful_query(
        self,
        user_query: str,
        generated_sql: str,
        banco: Optional[str],
        metric: str,
        intent: str,
        execution_time_ms: float,
        pipeline_used: str = "nl2sql",
        mode: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        result_row_count: Optional[int] = None
    ) -> uuid.UUID:
        """
        Log successful query execution for future RAG seeding.

        Args:
            user_query: Original NL query (e.g., "IMOR de INVEX en 2024")
            generated_sql: Generated SQL that succeeded
            banco: Bank name if query is bank-specific
            metric: Primary metric queried (e.g., "IMOR", "ICOR")
            intent: Query intent classification
            execution_time_ms: Query execution time
            pipeline_used: "nl2sql" or "legacy"
            mode: Visualization mode ("dashboard" or "timeline")
            filters: Parsed query filters as dict
            result_row_count: Number of rows returned

        Returns:
            UUID of inserted query log
        """
        try:
            # Use raw SQL to leverage trigger for rag_confidence calculation
            result = await self.session.execute(
                text("""
                    INSERT INTO query_logs (
                        user_query, generated_sql, banco, metric, intent,
                        execution_time_ms, success, pipeline_used,
                        mode, filters, result_row_count
                    )
                    VALUES (
                        :user_query, :generated_sql, :banco, :metric, :intent,
                        :execution_time_ms, :success, :pipeline_used,
                        :mode, :filters::jsonb, :result_row_count
                    )
                    RETURNING query_id
                """),
                {
                    "user_query": user_query,
                    "generated_sql": generated_sql,
                    "banco": banco,
                    "metric": metric,
                    "intent": intent,
                    "execution_time_ms": execution_time_ms,
                    "success": True,
                    "pipeline_used": pipeline_used,
                    "mode": mode,
                    "filters": str(filters) if filters else None,
                    "result_row_count": result_row_count
                }
            )

            await self.session.commit()

            query_id = result.scalar_one()

            logger.info(
                "query_logged.success",
                query_id=str(query_id),
                user_query=user_query[:50],
                metric=metric,
                execution_time_ms=execution_time_ms,
                pipeline=pipeline_used
            )

            return query_id

        except Exception as e:
            logger.error(
                "query_logged.failed",
                error=str(e),
                user_query=user_query[:50]
            )
            await self.session.rollback()
            raise

    async def log_failed_query(
        self,
        user_query: str,
        error_message: str,
        generated_sql: Optional[str] = None,
        banco: Optional[str] = None,
        metric: Optional[str] = "unknown",
        intent: Optional[str] = "unknown",
        execution_time_ms: float = 0.0,
        pipeline_used: str = "nl2sql"
    ) -> uuid.UUID:
        """
        Log failed query execution for debugging.

        Args:
            user_query: Original NL query
            error_message: Error that occurred
            generated_sql: SQL that was attempted (if any)
            banco: Bank name if detected
            metric: Metric if detected
            intent: Intent if detected
            execution_time_ms: Time before failure
            pipeline_used: Pipeline that failed

        Returns:
            UUID of inserted query log
        """
        try:
            result = await self.session.execute(
                text("""
                    INSERT INTO query_logs (
                        user_query, generated_sql, banco, metric, intent,
                        execution_time_ms, success, error_message, pipeline_used
                    )
                    VALUES (
                        :user_query, :generated_sql, :banco, :metric, :intent,
                        :execution_time_ms, :success, :error_message, :pipeline_used
                    )
                    RETURNING query_id
                """),
                {
                    "user_query": user_query,
                    "generated_sql": generated_sql,
                    "banco": banco,
                    "metric": metric,
                    "intent": intent,
                    "execution_time_ms": execution_time_ms,
                    "success": False,
                    "error_message": error_message,
                    "pipeline_used": pipeline_used
                }
            )

            await self.session.commit()

            query_id = result.scalar_one()

            logger.warning(
                "query_logged.failure",
                query_id=str(query_id),
                user_query=user_query[:50],
                error=error_message[:100]
            )

            return query_id

        except Exception as e:
            logger.error(
                "query_log_failed.error",
                error=str(e),
                user_query=user_query[:50]
            )
            await self.session.rollback()
            raise

    async def get_recent_successful_queries(
        self,
        limit: int = 100,
        min_confidence: float = 0.7,
        min_age_hours: int = 1,
        max_age_days: int = 90,
        not_seeded: bool = True
    ) -> List[QueryLog]:
        """
        Retrieve recent high-confidence queries for RAG seeding.

        Args:
            limit: Maximum number of queries to return
            min_confidence: Minimum RAG confidence threshold
            min_age_hours: Minimum age (avoid seeding too fresh queries)
            max_age_days: Maximum age (decay old patterns)
            not_seeded: Only return queries not yet seeded

        Returns:
            List of QueryLog objects ready for RAG seeding
        """
        query = text("""
            SELECT
                query_id, user_query, generated_sql, banco, metric, intent,
                execution_time_ms, success, error_message, pipeline_used,
                timestamp, seeded_to_rag, rag_confidence
            FROM query_logs
            WHERE success = TRUE
              AND rag_confidence >= :min_confidence
              AND timestamp < NOW() - INTERVAL ':min_age_hours hours'
              AND timestamp > NOW() - INTERVAL ':max_age_days days'
              AND (:not_seeded = FALSE OR seeded_to_rag = FALSE)
            ORDER BY rag_confidence DESC, timestamp DESC
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "min_confidence": min_confidence,
                "min_age_hours": min_age_hours,
                "max_age_days": max_age_days,
                "not_seeded": not_seeded,
                "limit": limit
            }
        )

        rows = result.fetchall()

        return [
            QueryLog(
                query_id=row.query_id,
                user_query=row.user_query,
                generated_sql=row.generated_sql,
                banco=row.banco,
                metric=row.metric,
                intent=row.intent,
                execution_time_ms=row.execution_time_ms,
                success=row.success,
                error_message=row.error_message,
                pipeline_used=row.pipeline_used,
                timestamp=row.timestamp,
                seeded_to_rag=row.seeded_to_rag,
                rag_confidence=row.rag_confidence
            )
            for row in rows
        ]

    async def mark_as_seeded(self, query_ids: List[uuid.UUID]) -> int:
        """
        Mark queries as seeded to RAG.

        Args:
            query_ids: List of query IDs to mark

        Returns:
            Number of queries marked
        """
        if not query_ids:
            return 0

        result = await self.session.execute(
            text("""
                UPDATE query_logs
                SET seeded_to_rag = TRUE,
                    seed_timestamp = NOW()
                WHERE query_id = ANY(:query_ids)
            """),
            {"query_ids": query_ids}
        )

        await self.session.commit()

        count = result.rowcount

        logger.info(
            "queries_marked_seeded",
            count=count,
            query_ids=[str(qid) for qid in query_ids[:5]]  # Log first 5
        )

        return count

    async def get_analytics_summary(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get analytics summary for last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with analytics metrics
        """
        result = await self.session.execute(
            text("""
                SELECT
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE success = TRUE) as successful_queries,
                    COUNT(*) FILTER (WHERE success = FALSE) as failed_queries,
                    AVG(execution_time_ms) as avg_execution_time,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms) as p50_execution_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time,
                    COUNT(DISTINCT metric) as unique_metrics,
                    COUNT(DISTINCT banco) as unique_bancos,
                    COUNT(*) FILTER (WHERE seeded_to_rag = TRUE) as seeded_count,
                    COUNT(*) FILTER (WHERE pipeline_used = 'nl2sql') as nl2sql_count,
                    COUNT(*) FILTER (WHERE pipeline_used = 'legacy') as legacy_count
                FROM query_logs
                WHERE timestamp > NOW() - INTERVAL ':days days'
            """),
            {"days": days}
        )

        row = result.fetchone()

        return {
            "period_days": days,
            "total_queries": row.total_queries,
            "successful_queries": row.successful_queries,
            "failed_queries": row.failed_queries,
            "success_rate": row.successful_queries / row.total_queries if row.total_queries > 0 else 0,
            "avg_execution_time_ms": float(row.avg_execution_time) if row.avg_execution_time else 0,
            "p50_execution_time_ms": float(row.p50_execution_time) if row.p50_execution_time else 0,
            "p95_execution_time_ms": float(row.p95_execution_time) if row.p95_execution_time else 0,
            "unique_metrics": row.unique_metrics,
            "unique_bancos": row.unique_bancos,
            "seeded_count": row.seeded_count,
            "nl2sql_count": row.nl2sql_count,
            "legacy_count": row.legacy_count,
            "nl2sql_percentage": (row.nl2sql_count / row.total_queries * 100) if row.total_queries > 0 else 0
        }
