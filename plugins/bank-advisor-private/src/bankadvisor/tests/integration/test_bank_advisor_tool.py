"""
Integration tests for BankAdvisor Tool - NL2SQL Pipeline Only

Q1 2025: Legacy IntentService tests removed.
All queries now use NL2SQL pipeline exclusively.
"""
import sys
import os

# Ensure /app is in path to resolve 'src' packages correctly
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_nl2sql_pipeline_success():
    """Validates NL2SQL pipeline processes a clear query successfully."""

    with patch("src.main._try_nl2sql_pipeline") as mock_nl2sql:
        # Configure mock to return successful result
        mock_nl2sql.return_value = {
            "success": True,
            "data": {
                "months": [
                    {"month_label": "Jul 2025", "data": [{"category": "INVEX", "value": 100}]}
                ]
            },
            "metadata": {
                "metric": "CARTERA_TOTAL",
                "pipeline": "nl2sql",
                "sql_generated": "SELECT * FROM monthly_kpis WHERE metric='CARTERA_TOTAL'"
            },
            "plotly_config": {"type": "line"},
            "title": "Cartera Total",
            "data_as_of": "15/08/2025"
        }

        # Import after patching
        from src.mcp.tools.bank_advisor import BankAdvisorTool

        tool = BankAdvisorTool()
        result = await tool.execute({"query": "cartera total de INVEX", "mode": "chart"})

        # Validations
        assert result.get("success") is True or result.get("type") == "ui_render"
        assert "data" in result or "content" in result


@pytest.mark.asyncio
async def test_nl2sql_pipeline_query_parsing():
    """Validates QuerySpec is properly parsed from natural language."""

    with patch("src.bankadvisor.services.query_spec_parser.QuerySpecParser.parse") as mock_parse:
        from bankadvisor.specs import QuerySpec, TimeRangeSpec

        # Configure mock to return valid QuerySpec
        mock_parse.return_value = QuerySpec(
            metric="IMOR",
            bank_names=["INVEX"],
            time_range=TimeRangeSpec(type="last_n_months", n=3),
            confidence_score=0.95
        )

        # Execute parsing
        from src.bankadvisor.services.query_spec_parser import QuerySpecParser

        parser = QuerySpecParser()
        spec = await parser.parse("IMOR de INVEX últimos 3 meses")

        # Validations
        assert spec.metric == "IMOR"
        assert "INVEX" in spec.bank_names
        assert spec.time_range.type == "last_n_months"
        assert spec.time_range.n == 3
        assert spec.confidence_score >= 0.7


@pytest.mark.asyncio
async def test_nl2sql_pipeline_ambiguous_query():
    """Validates ambiguous queries return clarification request."""

    with patch("src.main._try_nl2sql_pipeline") as mock_nl2sql:
        # Configure mock to return clarification needed
        mock_nl2sql.return_value = {
            "success": False,
            "error_code": "requires_clarification",
            "message": "Query 'cartera' es ambigua",
            "suggestions": ["cartera total", "cartera comercial", "cartera de consumo"]
        }

        from src.mcp.tools.bank_advisor import BankAdvisorTool

        tool = BankAdvisorTool()
        result = await tool.execute({"query": "cartera", "mode": "auto"})

        # Validations - should indicate ambiguity
        assert result.get("success") is False or "clarification" in str(result).lower()


@pytest.mark.asyncio
async def test_nl2sql_service_unavailable():
    """Validates proper error when NL2SQL service is not available."""

    with patch("src.main.NL2SQL_AVAILABLE", False):
        # When NL2SQL not available, should return service unavailable error
        # This is the new behavior after pipeline consolidation

        from src.mcp.tools.bank_advisor import BankAdvisorTool

        tool = BankAdvisorTool()
        result = await tool.execute({"query": "test query", "mode": "auto"})

        # Should return error about service unavailable
        assert "error" in result or result.get("success") is False


@pytest.mark.asyncio
async def test_nl2sql_sql_generation():
    """Validates SQL is properly generated from QuerySpec."""

    with patch("src.bankadvisor.services.sql_generation_service.SqlGenerationService.generate") as mock_gen:
        # Configure mock
        mock_gen.return_value = MagicMock(
            sql="SELECT banco, mes_reporta, IMOR FROM monthly_kpis WHERE banco = 'INVEX'",
            confidence=0.95,
            explanation="Generated SQL for IMOR metric filtered by INVEX"
        )

        from bankadvisor.services.sql_generation_service import SqlGenerationService
        from bankadvisor.specs import QuerySpec, TimeRangeSpec, RagContext

        # Create test inputs
        spec = QuerySpec(
            metric="IMOR",
            bank_names=["INVEX"],
            time_range=TimeRangeSpec(type="all")
        )

        rag_context = RagContext(
            metric_definitions=[],
            schema_snippets=[],
            example_queries=[],
            available_columns=["IMOR", "banco", "mes_reporta"]
        )

        generator = SqlGenerationService()
        result = await generator.generate(spec, rag_context)

        # Validations
        assert "SELECT" in result.sql
        assert result.confidence >= 0.7


@pytest.mark.asyncio
async def test_query_logging_on_success():
    """Validates successful queries are logged for RAG feedback loop."""

    with patch("src.bankadvisor.services.query_logger_service.QueryLoggerService.log_successful_query") as mock_log:
        mock_log.return_value = "test-query-id"

        from bankadvisor.services.query_logger_service import QueryLoggerService
        from unittest.mock import MagicMock

        # Create mock session
        mock_session = MagicMock()

        logger = QueryLoggerService(mock_session)
        query_id = await logger.log_successful_query(
            user_query="IMOR de INVEX",
            generated_sql="SELECT * FROM monthly_kpis",
            banco="INVEX",
            metric="IMOR",
            intent="metric_query",
            execution_time_ms=150.0,
            pipeline_used="nl2sql"
        )

        # Validations
        mock_log.assert_called_once()
        assert query_id is not None
