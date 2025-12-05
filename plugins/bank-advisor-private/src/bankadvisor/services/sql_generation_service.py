"""
SQL Generation Service for NL2SQL Pipeline

Generates safe SQL queries from QuerySpec + RagContext using:
1. Template-based generation (preferred for common patterns)
2. LLM-based generation (fallback for novel queries)

All generated SQL is validated through SqlValidator before returning.

Architecture:
    QuerySpec + RagContext → Template match → SQL → Validation → SqlGenerationResult
                           ↓ (no template)
                           LLM prompt → SQL → Validation → SqlGenerationResult
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog

from ..specs import QuerySpec, RagContext, SqlGenerationResult
from ..services.sql_validator import SqlValidator
from ..services.analytics_service import AnalyticsService

logger = structlog.get_logger(__name__)


class SqlGenerationService:
    """
    Generates SQL queries from structured QuerySpec and RAG context.

    Responsibilities:
    - Match QuerySpec to pre-defined templates (80% of queries)
    - Generate SQL using LLM for novel patterns (20% of queries)
    - Always validate SQL through SqlValidator before returning
    - Map metrics to database columns using RagContext
    - Build WHERE clauses for banks and time ranges

    Thread-safety: Stateless service, safe for concurrent use.
    """

    # Maximum rows to return (security limit)
    MAX_LIMIT = 1000

    def __init__(
        self,
        validator: Optional[SqlValidator] = None,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize SQL generation service.

        Args:
            validator: SqlValidator instance (defaults to new instance)
            llm_client: Optional LLM client for complex queries (SAPTIVA, OpenAI, etc.)
        """
        self.validator = validator or SqlValidator()
        self.llm_client = llm_client

        logger.info(
            "sql_generation.initialized",
            llm_enabled=llm_client is not None,
            validator_enabled=True
        )

    async def build_sql_from_spec(
        self,
        spec: QuerySpec,
        ctx: RagContext
    ) -> SqlGenerationResult:
        """
        Generate SQL from QuerySpec and RagContext.

        Process:
        1. Check if spec is complete and valid
        2. Try template-based generation first
        3. Fall back to LLM if no template matches
        4. Validate generated SQL
        5. Return SqlGenerationResult

        Args:
            spec: Structured query specification
            ctx: RAG-retrieved context (schema, metrics, examples)

        Returns:
            SqlGenerationResult with success flag and SQL or error details
        """
        logger.info(
            "sql_generation.start",
            metric=spec.metric,
            bank_names=spec.bank_names,
            time_range_type=spec.time_range.type,
            requires_clarification=spec.requires_clarification
        )

        # Step 1: Validate spec is complete
        if not spec.is_complete():
            logger.warning(
                "sql_generation.incomplete_spec",
                metric=spec.metric,
                missing_fields=spec.missing_fields,
                confidence=spec.confidence_score
            )
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="ambiguous_spec",
                error_message=f"QuerySpec is incomplete. Missing: {', '.join(spec.missing_fields)}",
                metadata={
                    "missing_fields": spec.missing_fields,
                    "confidence_score": spec.confidence_score
                }
            )

        # Step 2: Check if metric columns exist
        metric_column = self._resolve_metric_column(spec.metric, ctx)
        if not metric_column:
            logger.error(
                "sql_generation.unsupported_metric",
                metric=spec.metric,
                available_columns=ctx.available_columns
            )
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="unsupported_metric",
                error_message=f"Metric '{spec.metric}' is not supported or column doesn't exist",
                metadata={
                    "available_metrics": ctx.available_columns[:10]  # Show first 10
                }
            )

        # Step 3: Try template-based generation
        template_result = self._try_template_generation(spec, ctx, metric_column)
        if template_result:
            logger.info(
                "sql_generation.template_success",
                template=template_result.metadata.get("template"),
                metric=spec.metric
            )
            return template_result

        # Step 4: Fall back to LLM generation
        if self.llm_client:
            llm_result = await self._try_llm_generation(spec, ctx, metric_column)
            if llm_result:
                logger.info(
                    "sql_generation.llm_success",
                    metric=spec.metric,
                    tokens_used=llm_result.metadata.get("tokens_used")
                )
                return llm_result
        else:
            logger.warning(
                "sql_generation.llm_unavailable",
                metric=spec.metric,
                message="No LLM client configured and no template matched"
            )

        # Step 5: Generation failed
        logger.error(
            "sql_generation.failed",
            metric=spec.metric,
            reason="No template matched and LLM unavailable or failed"
        )
        return SqlGenerationResult(
            success=False,
            sql=None,
            error_code="generation_failed",
            error_message="Could not generate SQL: no template matched and LLM unavailable",
            metadata={
                "metric": spec.metric,
                "templates_tried": ["metric_timeseries", "metric_comparison", "metric_aggregate"]
            }
        )

    # Extended metric mappings for multi-table queries
    EXTENDED_METRIC_MAP = {
        # Market Share
        "market_share": {"table": "monthly_kpis", "column": "market_share_pct"},
        # Activos Totales (from metricas_financieras_ext)
        "activo_total": {"table": "metricas_financieras_ext", "column": "activo_total"},
        # Segmented IMOR (from metricas_cartera_segmentada)
        "imor_automotriz": {"table": "metricas_cartera_segmentada", "column": "imor", "segment": "Credito Automotriz"},
        "imor_nomina": {"table": "metricas_cartera_segmentada", "column": "imor", "segment": "Credito de Nomina"},
        "imor_tdc": {"table": "metricas_cartera_segmentada", "column": "imor", "segment": "Tarjeta de Credito"},
        # Segmented Cartera (from metricas_cartera_segmentada)
        "cartera_automotriz": {"table": "metricas_cartera_segmentada", "column": "cartera_total", "segment": "Credito Automotriz"},
        "cartera_nomina": {"table": "metricas_cartera_segmentada", "column": "cartera_total", "segment": "Credito de Nomina"},
        "cartera_tdc": {"table": "metricas_cartera_segmentada", "column": "cartera_total", "segment": "Tarjeta de Credito"},
        "cartera_personales": {"table": "metricas_cartera_segmentada", "column": "cartera_total", "segment": "Prestamos Personales"},
    }

    def _resolve_metric_column(self, metric: str, ctx: RagContext) -> Optional[str]:
        """
        Resolve metric name to database column.

        Args:
            metric: Canonical metric name (e.g., "IMOR", "CARTERA_COMERCIAL")
            ctx: RagContext with available_columns

        Returns:
            Column name or None if not found

        Mapping Strategy:
        1. Check extended metric map (for multi-table queries)
        2. Direct match: "IMOR" → "imor"
        3. Prefix match: "CARTERA_COMERCIAL" → "cartera_comercial_total"
        4. RAG metric definition: Check ctx.metric_definitions for "preferred_columns"
        """
        metric_lower = metric.lower()

        # Check extended metric map first (multi-table metrics)
        if metric_lower in self.EXTENDED_METRIC_MAP:
            return metric_lower  # Will be handled specially in template generation

        # Direct match
        if metric_lower in ctx.available_columns:
            return metric_lower

        # Prefix match for CARTERA_* metrics
        for col in ctx.available_columns:
            if col.startswith(metric_lower):
                return col

        # Check RAG metric definitions
        metric_def = ctx.get_metric_definition(metric)
        if metric_def and metric_def.get("preferred_columns"):
            preferred = metric_def["preferred_columns"][0]
            if preferred in ctx.available_columns:
                return preferred

        return None

    def _try_template_generation(
        self,
        spec: QuerySpec,
        ctx: RagContext,
        metric_column: str
    ) -> Optional[SqlGenerationResult]:
        """
        Try to generate SQL using pre-defined templates.

        Templates (by pattern):
        1. metric_timeseries: Single metric, time series
        2. metric_comparison: Compare INVEX vs SISTEMA
        3. metric_aggregate: Single aggregate value (no time dimension)
        4. metric_ranking: TOP N banks by metric
        5. segmented_metric: Metrics from metricas_cartera_segmentada
        6. extended_metric: Metrics from metricas_financieras_ext (activos)

        Args:
            spec: QuerySpec
            ctx: RagContext
            metric_column: Resolved database column name

        Returns:
            SqlGenerationResult or None if no template matches
        """
        # Check for extended metrics (multi-table queries)
        metric_lower = metric_column.lower()
        if metric_lower in self.EXTENDED_METRIC_MAP:
            extended_config = self.EXTENDED_METRIC_MAP[metric_lower]

            # Template 5: Segmented metric (metricas_cartera_segmentada)
            if extended_config.get("segment"):
                return self._generate_segmented_sql(spec, extended_config)

            # Template 6: Extended metric (metricas_financieras_ext)
            if extended_config["table"] == "metricas_financieras_ext":
                return self._generate_extended_financieras_sql(spec, extended_config)

            # Market share from monthly_kpis (use standard template)
            if extended_config["table"] == "monthly_kpis":
                metric_column = extended_config["column"]

        # Template 4: Ranking (TOP N banks) - NEW
        if hasattr(spec, 'ranking_mode') and spec.ranking_mode:
            return self._generate_ranking_sql(spec, metric_column)

        # Template 1: Comparison (INVEX vs SISTEMA) - check before timeseries
        # Comparison mode takes priority over simple timeseries
        if spec.comparison_mode and len(spec.bank_names) > 1:
            return self._generate_comparison_sql(spec, metric_column)

        # Template 2: Time series (most common)
        if spec.time_range.type in ["last_n_months", "last_n_quarters", "year", "between_dates"]:
            return self._generate_timeseries_sql(spec, metric_column)

        # Template 3: Aggregate (single value, no time breakdown)
        if spec.time_range.type == "all" and not spec.comparison_mode:
            return self._generate_aggregate_sql(spec, metric_column)

        # No template matched
        logger.debug(
            "sql_generation.no_template_match",
            metric=spec.metric,
            time_range_type=spec.time_range.type,
            comparison_mode=spec.comparison_mode
        )
        return None

    def _generate_timeseries_sql(
        self,
        spec: QuerySpec,
        metric_column: str
    ) -> SqlGenerationResult:
        """
        Generate SQL for time series queries.

        Pattern:
            SELECT fecha, {metric}
            FROM monthly_kpis
            WHERE banco_norm = 'INVEX'
              AND fecha >= {start_date}
            ORDER BY fecha ASC
            LIMIT 1000

        Args:
            spec: QuerySpec
            metric_column: Database column name

        Returns:
            SqlGenerationResult with generated SQL
        """
        # Build SELECT clause (include banco_norm for proper data transformation)
        select_clause = f"banco_norm, fecha, {metric_column}"

        # Build WHERE clauses
        where_clauses = []

        # Bank filter
        if spec.bank_names:
            if len(spec.bank_names) == 1:
                where_clauses.append(f"banco_norm = '{spec.bank_names[0]}'")
            else:
                banks_str = "', '".join(spec.bank_names)
                where_clauses.append(f"banco_norm IN ('{banks_str}')")

        # Time range filter
        time_clause = self._build_time_filter(spec.time_range)
        if time_clause:
            where_clauses.append(time_clause)

        # Filter NULL values for the metric column
        where_clauses.append(f"{metric_column} IS NOT NULL")

        # Combine WHERE clauses
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build final SQL
        sql = f"""
SELECT {select_clause}
FROM monthly_kpis
WHERE {where_sql}
ORDER BY fecha ASC
LIMIT {self.MAX_LIMIT}
        """.strip()

        # Validate SQL
        validation = self.validator.validate(sql)
        if not validation.valid:
            logger.error(
                "sql_generation.validation_failed",
                metric=spec.metric,
                error=validation.error_message
            )
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="validation_failed",
                error_message=validation.error_message,
                metadata={"template": "metric_timeseries"}
            )

        return SqlGenerationResult(
            success=True,
            sql=validation.sanitized_sql or sql,
            used_template=True,
            metadata={
                "template": "metric_timeseries",
                "metric_column": metric_column,
                "time_range_type": spec.time_range.type
            }
        )

    def _generate_comparison_sql(
        self,
        spec: QuerySpec,
        metric_column: str
    ) -> SqlGenerationResult:
        """
        Generate SQL for comparison queries (INVEX vs SISTEMA).

        Pattern:
            SELECT fecha, banco_norm, {metric}
            FROM monthly_kpis
            WHERE banco_norm IN ('INVEX', 'SISTEMA')
              AND fecha >= {start_date}
            ORDER BY fecha ASC, banco_norm
            LIMIT 1000

        Args:
            spec: QuerySpec
            metric_column: Database column name

        Returns:
            SqlGenerationResult with generated SQL
        """
        # Build SELECT clause (include banco_norm for comparison)
        select_clause = f"fecha, banco_norm, {metric_column}"

        # Build WHERE clauses
        where_clauses = []

        # Bank filter (required for comparison)
        banks_str = "', '".join(spec.bank_names)
        where_clauses.append(f"banco_norm IN ('{banks_str}')")

        # Time range filter
        time_clause = self._build_time_filter(spec.time_range)
        if time_clause:
            where_clauses.append(time_clause)

        # Filter NULL values for the metric column
        where_clauses.append(f"{metric_column} IS NOT NULL")

        where_sql = " AND ".join(where_clauses)

        # Build final SQL
        sql = f"""
SELECT {select_clause}
FROM monthly_kpis
WHERE {where_sql}
ORDER BY fecha ASC, banco_norm
LIMIT {self.MAX_LIMIT}
        """.strip()

        # Validate SQL
        validation = self.validator.validate(sql)
        if not validation.valid:
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="validation_failed",
                error_message=validation.error_message,
                metadata={"template": "metric_comparison"}
            )

        return SqlGenerationResult(
            success=True,
            sql=validation.sanitized_sql or sql,
            used_template=True,
            metadata={
                "template": "metric_comparison",
                "metric_column": metric_column,
                "banks": spec.bank_names
            }
        )

    def _generate_aggregate_sql(
        self,
        spec: QuerySpec,
        metric_column: str
    ) -> SqlGenerationResult:
        """
        Generate SQL for aggregate queries (single value).

        Pattern:
            SELECT AVG({metric}) as promedio
            FROM monthly_kpis
            WHERE banco_norm = 'INVEX'

        Args:
            spec: QuerySpec
            metric_column: Database column name

        Returns:
            SqlGenerationResult with generated SQL
        """
        # Build WHERE clause
        where_clauses = []

        if spec.bank_names:
            if len(spec.bank_names) == 1:
                where_clauses.append(f"banco_norm = '{spec.bank_names[0]}'")
            else:
                banks_str = "', '".join(spec.bank_names)
                where_clauses.append(f"banco_norm IN ('{banks_str}')")

        # Filter NULL values for the metric column
        where_clauses.append(f"{metric_column} IS NOT NULL")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build SQL with aggregate
        sql = f"""
SELECT AVG({metric_column}) as promedio,
       MIN({metric_column}) as minimo,
       MAX({metric_column}) as maximo,
       COUNT(*) as meses
FROM monthly_kpis
WHERE {where_sql}
        """.strip()

        # Validate SQL
        validation = self.validator.validate(sql)
        if not validation.valid:
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="validation_failed",
                error_message=validation.error_message,
                metadata={"template": "metric_aggregate"}
            )

        return SqlGenerationResult(
            success=True,
            sql=validation.sanitized_sql or sql,
            used_template=True,
            metadata={
                "template": "metric_aggregate",
                "metric_column": metric_column
            }
        )

    def _build_time_filter(self, time_range) -> Optional[str]:
        """
        Build SQL time filter clause.

        Args:
            time_range: TimeRangeSpec

        Returns:
            SQL WHERE clause fragment or None
        """
        if time_range.type == "all":
            return None

        if time_range.type == "last_n_months":
            # PostgreSQL: CURRENT_DATE - INTERVAL 'N months'
            return f"fecha >= (CURRENT_DATE - INTERVAL '{time_range.n} months')"

        if time_range.type == "last_n_quarters":
            months = time_range.n * 3
            return f"fecha >= (CURRENT_DATE - INTERVAL '{months} months')"

        if time_range.type == "year":
            return f"fecha >= '{time_range.start_date}' AND fecha <= '{time_range.end_date}'"

        if time_range.type == "between_dates":
            return f"fecha >= '{time_range.start_date}' AND fecha <= '{time_range.end_date}'"

        return None

    def _generate_ranking_sql(
        self,
        spec: QuerySpec,
        metric_column: str
    ) -> SqlGenerationResult:
        """
        Generate SQL for TOP N ranking queries.

        Pattern:
            SELECT banco_norm, AVG({metric}) as promedio
            FROM monthly_kpis
            WHERE fecha >= {start_date}
            GROUP BY banco_norm
            ORDER BY promedio DESC
            LIMIT {top_n}

        Args:
            spec: QuerySpec with ranking_mode=True and top_n
            metric_column: Database column name

        Returns:
            SqlGenerationResult with generated SQL
        """
        # Get top_n (default 5)
        top_n = getattr(spec, 'top_n', 5)

        # Build WHERE clause for time filter
        where_clauses = []
        time_clause = self._build_time_filter(spec.time_range)
        if time_clause:
            where_clauses.append(time_clause)

        # Add filter to exclude null values
        where_clauses.append(f"{metric_column} IS NOT NULL")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build SQL
        sql = f"""
SELECT banco_norm,
       AVG({metric_column}) as promedio,
       MAX({metric_column}) as maximo,
       MIN({metric_column}) as minimo,
       COUNT(*) as meses
FROM monthly_kpis
WHERE {where_sql}
GROUP BY banco_norm
ORDER BY promedio DESC
LIMIT {min(top_n, self.MAX_LIMIT)}
        """.strip()

        # Validate SQL
        validation = self.validator.validate(sql)
        if not validation.valid:
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="validation_failed",
                error_message=validation.error_message,
                metadata={"template": "metric_ranking"}
            )

        return SqlGenerationResult(
            success=True,
            sql=validation.sanitized_sql or sql,
            used_template=True,
            metadata={
                "template": "metric_ranking",
                "metric_column": metric_column,
                "top_n": top_n
            }
        )

    def _generate_segmented_sql(
        self,
        spec: QuerySpec,
        config: Dict[str, Any]
    ) -> SqlGenerationResult:
        """
        Generate SQL for segmented metrics (metricas_cartera_segmentada).

        Queries metrics like IMOR automotriz, cartera by segment, etc.

        Pattern:
            SELECT institucion, fecha_corte, {column}
            FROM metricas_cartera_segmentada
            WHERE segmento_nombre = 'Credito Automotriz'
              AND institucion ILIKE '%invex%'
            ORDER BY fecha_corte ASC

        Args:
            spec: QuerySpec
            config: Extended metric config with segment info

        Returns:
            SqlGenerationResult with generated SQL
        """
        column = config["column"]
        segment = config["segment"]

        # Build WHERE clauses
        where_clauses = [f"segmento_nombre = '{segment}'"]

        # Bank filter - use ILIKE for partial match
        if spec.bank_names:
            bank_conditions = []
            for bank in spec.bank_names:
                if bank.upper() == "SISTEMA":
                    bank_conditions.append("institucion ILIKE '%Sistema%'")
                else:
                    bank_conditions.append(f"institucion ILIKE '%{bank}%'")
            where_clauses.append(f"({' OR '.join(bank_conditions)})")

        # Time range filter (uses fecha_corte string format YYYY-MM-DD)
        if spec.time_range.type == "last_n_months":
            where_clauses.append(
                f"fecha_corte::date >= (CURRENT_DATE - INTERVAL '{spec.time_range.n} months')"
            )
        elif spec.time_range.type == "year":
            where_clauses.append(
                f"fecha_corte::date >= '{spec.time_range.start_date}' AND fecha_corte::date <= '{spec.time_range.end_date}'"
            )

        where_sql = " AND ".join(where_clauses)

        # Build SQL
        sql = f"""
SELECT institucion as banco_norm, fecha_corte::date as fecha, {column}
FROM metricas_cartera_segmentada
WHERE {where_sql}
ORDER BY fecha_corte ASC
LIMIT {self.MAX_LIMIT}
        """.strip()

        # Validate SQL
        validation = self.validator.validate(sql)
        if not validation.valid:
            logger.error(
                "sql_generation.segmented_validation_failed",
                segment=segment,
                error=validation.error_message
            )
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="validation_failed",
                error_message=validation.error_message,
                metadata={"template": "segmented_metric", "segment": segment}
            )

        return SqlGenerationResult(
            success=True,
            sql=validation.sanitized_sql or sql,
            used_template=True,
            metadata={
                "template": "segmented_metric",
                "segment": segment,
                "column": column,
                "table": "metricas_cartera_segmentada"
            }
        )

    def _generate_extended_financieras_sql(
        self,
        spec: QuerySpec,
        config: Dict[str, Any]
    ) -> SqlGenerationResult:
        """
        Generate SQL for extended financial metrics (metricas_financieras_ext).

        Used for activo_total, roa, roe, etc. - bank-level financial data.

        Pattern for ranking/comparison:
            SELECT banco_norm, activo_total,
                   activo_total * 100.0 / SUM(activo_total) OVER () as pct_total
            FROM metricas_financieras_ext
            WHERE fecha_corte = (SELECT MAX(fecha_corte) FROM metricas_financieras_ext)
              AND banco_norm != 'SISTEMA'
            ORDER BY activo_total DESC
            LIMIT 20

        Args:
            spec: QuerySpec
            config: Extended metric config

        Returns:
            SqlGenerationResult with generated SQL
        """
        column = config["column"]

        # Build WHERE clauses - exclude SISTEMA for rankings
        where_clauses = [
            "fecha_corte = (SELECT MAX(fecha_corte) FROM metricas_financieras_ext)",
            "banco_norm IS NOT NULL",
            "banco_norm != 'SISTEMA'",
            "banco_norm != 'N.D. NO DISPONIBLE'"
        ]

        # Bank filter if specific banks requested
        if spec.bank_names and "SISTEMA" not in spec.bank_names:
            bank_conditions = []
            for bank in spec.bank_names:
                bank_conditions.append(f"banco_norm ILIKE '%{bank}%'")
            if bank_conditions:
                where_clauses.append(f"({' OR '.join(bank_conditions)})")

        where_sql = " AND ".join(where_clauses)

        # Build SQL with percentage calculation
        sql = f"""
SELECT banco_norm,
       {column},
       {column} * 100.0 / SUM({column}) OVER () as pct_total
FROM metricas_financieras_ext
WHERE {where_sql}
  AND {column} IS NOT NULL
ORDER BY {column} DESC
LIMIT 20
        """.strip()

        # Validate SQL
        validation = self.validator.validate(sql)
        if not validation.valid:
            logger.error(
                "sql_generation.extended_validation_failed",
                column=column,
                error=validation.error_message
            )
            return SqlGenerationResult(
                success=False,
                sql=None,
                error_code="validation_failed",
                error_message=validation.error_message,
                metadata={"template": "extended_financieras", "column": column}
            )

        return SqlGenerationResult(
            success=True,
            sql=validation.sanitized_sql or sql,
            used_template=True,
            metadata={
                "template": "extended_financieras",
                "column": column,
                "table": "metricas_financieras_ext"
            }
        )

    async def _try_llm_generation(
        self,
        spec: QuerySpec,
        ctx: RagContext,
        metric_column: str
    ) -> Optional[SqlGenerationResult]:
        """
        Generate SQL using LLM for complex queries.

        This is a fallback for queries that don't match any template.

        Args:
            spec: QuerySpec
            ctx: RagContext
            metric_column: Resolved database column

        Returns:
            SqlGenerationResult or None if LLM generation fails
        """
        if not self.llm_client:
            logger.debug(
                "sql_generation.llm_unavailable",
                metric=spec.metric,
                message="No LLM client configured"
            )
            return None

        try:
            logger.info(
                "sql_generation.llm_calling",
                metric=spec.metric,
                llm_type=type(self.llm_client).__name__
            )

            # Call LLM to generate SQL
            sql = await self.llm_client.generate_sql(
                user_query=f"{spec.metric} {' '.join(spec.bank_names)}",
                query_spec=spec.dict(),
                rag_context={
                    "metric_definitions": ctx.metric_definitions,
                    "schema_snippets": ctx.schema_snippets,
                    "example_queries": ctx.example_queries,
                    "available_columns": ctx.available_columns
                }
            )

            if not sql:
                logger.warning(
                    "sql_generation.llm_no_output",
                    metric=spec.metric
                )
                return None

            # Validate generated SQL
            validation = self.validator.validate(sql)

            if not validation.valid:
                logger.warning(
                    "sql_generation.llm_validation_failed",
                    metric=spec.metric,
                    error=validation.error_message,
                    sql_preview=sql[:100]
                )
                return SqlGenerationResult(
                    success=False,
                    sql=None,
                    error_code="llm_validation_failed",
                    error_message=validation.error_message,
                    metadata={
                        "llm_generated": sql[:200],
                        "llm_type": type(self.llm_client).__name__
                    }
                )

            logger.info(
                "sql_generation.llm_success",
                metric=spec.metric,
                sql_length=len(sql)
            )

            return SqlGenerationResult(
                success=True,
                sql=validation.sanitized_sql or sql,
                used_template=False,
                metadata={
                    "llm_type": type(self.llm_client).__name__,
                    "sql_length": len(sql)
                }
            )

        except Exception as e:
            logger.error(
                "sql_generation.llm_error",
                metric=spec.metric,
                error=str(e),
                exc_info=True
            )
            return None


# Singleton instance (optional)
_sql_generation_service: Optional[SqlGenerationService] = None


def get_sql_generation_service(
    validator: Optional[SqlValidator] = None,
    llm_client: Optional[Any] = None
) -> SqlGenerationService:
    """
    Get or create SQL generation service instance.

    Args:
        validator: SqlValidator instance
        llm_client: Optional LLM client for complex queries

    Returns:
        SqlGenerationService instance
    """
    global _sql_generation_service

    if _sql_generation_service is None:
        _sql_generation_service = SqlGenerationService(
            validator=validator,
            llm_client=llm_client
        )

    return _sql_generation_service
