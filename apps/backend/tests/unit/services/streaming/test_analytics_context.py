"""
Unit tests for analytics_context module.

Tests:
- BankAnalyticsContextService.build_llm_context
- BankAnalyticsContextService context builder methods
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.streaming.analytics_context import BankAnalyticsContextService

pytestmark = [pytest.mark.unit]


class TestBuildLlmContextBasic:
    """Test build_llm_context basic behavior."""

    def test_returns_none_for_empty_data(self):
        """Test returns empty for None/empty data."""
        context, ctx_type = BankAnalyticsContextService.build_llm_context(None)
        assert context == ""
        assert ctx_type == "none"

        context, ctx_type = BankAnalyticsContextService.build_llm_context({})
        assert context == ""
        assert ctx_type == "none"

    def test_handles_pydantic_model(self):
        """Test handles Pydantic model with model_dump."""
        mock_data = MagicMock()
        mock_data.model_dump.return_value = {
            "type": "knowledge",
            "metric_name": "IMOR",
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(mock_data)

        assert ctx_type == "knowledge"
        mock_data.model_dump.assert_called_once()


class TestBuildClarificationContext:
    """Test clarification context building."""

    def test_builds_clarification_context(self):
        """Test builds context for clarification type."""
        data = {
            "type": "clarification",
            "message": "¿A cuál banco te refieres?",
            "options": [
                {"label": "INVEX", "id": "invex", "description": "Banco INVEX"},
                {"label": "BBVA", "id": "bbva", "description": "Banco BBVA"},
            ],
            "context": {
                "banks": ["INVEX", "BBVA"],
                "original_query": "muéstrame el IMOR",
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "clarification"
        assert "ACLARACIÓN REQUERIDA" in context
        assert "INVEX" in context
        assert "BBVA" in context
        assert "muéstrame el IMOR" in context

    def test_clarification_includes_message(self):
        """Test clarification includes the message."""
        data = {
            "type": "clarification",
            "message": "Selecciona una opción",
            "options": [],
            "context": {},
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert "Selecciona una opción" in context


class TestBuildInvalidBankContext:
    """Test invalid bank context building."""

    def test_builds_invalid_bank_context(self):
        """Test builds context for invalid_bank type."""
        data = {
            "type": "invalid_bank",
            "invalid_bank": "BancoFalso",
            "refusal_context": "El banco BancoFalso no está en nuestra base CNBV.",
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "invalid_bank"
        assert "BancoFalso" in context

    def test_adds_repeat_refusal_alert(self):
        """Test adds alert for repeat refusals."""
        data = {
            "type": "invalid_bank",
            "invalid_bank": "BancoFalso",
            "refusal_context": "No disponible.",
            "previous_refusal": {
                "timestamp": "2024-01-15T10:30:00",
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert "ALERTA" in context
        assert "INTENTO DE NEGOCIACIÓN" in context


class TestBuildKnowledgeContext:
    """Test knowledge context building."""

    def test_builds_knowledge_context(self):
        """Test builds context for knowledge type."""
        data = {
            "type": "knowledge",
            "metric_name": "IMOR",
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "knowledge"
        assert "IMOR" in context
        assert "glosario" in context.lower()


class TestBuildChartContext:
    """Test chart context building."""

    def test_builds_success_context(self):
        """Test builds context for successful chart."""
        data = {
            "type": "chart",
            "chart_status": "success",
            "metric_name": "IMOR",
            "bank_names": ["INVEX"],
            "time_range": {"start": "2023-01", "end": "2024-01"},
            "data_as_of": "2024-01-15",
            "plotly_config": {
                "data": [
                    {"name": "INVEX", "y": [1.5, 1.8, 1.6, 1.4]}
                ]
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "chart"
        assert "IMOR" in context
        assert "INVEX" in context
        assert "2023-01" in context

    def test_builds_empty_context(self):
        """Test builds context for empty chart."""
        data = {
            "type": "chart",
            "chart_status": "empty",
            "metric_name": "IMOR",
            "bank_names": ["INVEX"],
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "empty"
        assert "SIN DATOS" in context
        assert "NO HAY GRÁFICA" in context

    def test_builds_error_context(self):
        """Test builds context for chart with error."""
        data = {
            "type": "chart",
            "chart_status": "error",
            "metric_name": "IMOR",
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "error"
        assert "ERROR" in context
        assert "problema técnico" in context

    def test_handles_enum_chart_status(self):
        """Test handles enum chart_status."""
        mock_status = MagicMock()
        mock_status.value = "empty"

        data = {
            "type": "chart",
            "chart_status": mock_status,
            "metric_name": "IMOR",
            "bank_names": [],
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert ctx_type == "empty"


class TestResolveBankNames:
    """Test _resolve_bank_names method."""

    def test_returns_bank_names_list(self):
        """Test returns comma-joined bank names."""
        data = {}
        bank_names, is_ranking = BankAnalyticsContextService._resolve_bank_names(
            data, ["INVEX", "BBVA"], False
        )

        assert bank_names == "INVEX, BBVA"
        assert is_ranking is False

    def test_extracts_from_traces_when_empty(self):
        """Test extracts from traces when bank_names is empty."""
        data = {
            "plotly_config": {
                "data": [
                    {"name": "INVEX"},
                    {"name": "BBVA"},
                ]
            }
        }

        bank_names, is_ranking = BankAnalyticsContextService._resolve_bank_names(
            data, [], False
        )

        assert "INVEX" in bank_names
        assert "BBVA" in bank_names
        assert is_ranking is True

    def test_returns_system_default_when_no_traces(self):
        """Test returns default when no bank names and no traces."""
        data = {}

        bank_names, is_ranking = BankAnalyticsContextService._resolve_bank_names(
            data, [], False
        )

        assert bank_names == "todos los bancos del sistema"
        assert is_ranking is True


class TestBuildSuccessContext:
    """Test _build_success_context method."""

    def test_includes_critical_instructions(self):
        """Test includes critical instructions first."""
        context = BankAnalyticsContextService._build_success_context(
            metric_name="IMOR",
            bank_names="INVEX",
            time_range={"start": "2023-01", "end": "2024-01"},
            data_as_of="2024-01-15",
            chart_stats={"INVEX": {
                "min": 1.0, "max": 2.0, "avg": 1.5,
                "current": 1.8, "first": 1.0,
                "trend": "creciente", "change_pct": 80.0
            }},
            is_ratio=True,
            unit_label="%",
            is_ranking=False,
            include_ranking_context=True,
        )

        assert "INSTRUCCIONES CRÍTICAS" in context
        assert "FRASES ABSOLUTAMENTE PROHIBIDAS" in context

    def test_includes_statistics(self):
        """Test includes bank statistics."""
        context = BankAnalyticsContextService._build_success_context(
            metric_name="IMOR",
            bank_names="INVEX",
            time_range={},
            data_as_of="2024-01-15",
            chart_stats={"INVEX": {
                "min": 1.0, "max": 2.0, "avg": 1.5,
                "current": 1.8, "first": 1.0,
                "trend": "creciente", "change_pct": 80.0
            }},
            is_ratio=True,
            unit_label="%",
            is_ranking=False,
            include_ranking_context=True,
        )

        assert "INVEX" in context
        assert "1.80%" in context or "1.8%" in context
        assert "creciente" in context

    def test_includes_ranking_context(self):
        """Test includes ranking context when applicable."""
        context = BankAnalyticsContextService._build_success_context(
            metric_name="IMOR",
            bank_names="INVEX, BBVA",
            time_range={},
            data_as_of="2024-01-15",
            chart_stats={},
            is_ratio=False,
            unit_label="MDP",
            is_ranking=True,
            include_ranking_context=True,
        )

        assert "RANKING" in context
        assert "ranking" in context.lower()

    def test_excludes_ranking_when_disabled(self):
        """Test excludes ranking context when disabled."""
        context = BankAnalyticsContextService._build_success_context(
            metric_name="IMOR",
            bank_names="INVEX",
            time_range={},
            data_as_of="2024-01-15",
            chart_stats={},
            is_ratio=False,
            unit_label="MDP",
            is_ranking=True,
            include_ranking_context=False,
        )

        # Should not have RANKING header
        assert "TIPO DE CONSULTA: RANKING" not in context


class TestBuildEmptyContext:
    """Test _build_empty_context method."""

    def test_includes_truth_rules(self):
        """Test includes truth rules."""
        context = BankAnalyticsContextService._build_empty_context(
            "IMOR", "INVEX"
        )

        assert "REGLAS DE VERDAD" in context
        assert "NO HAY GRÁFICA" in context

    def test_includes_example(self):
        """Test includes example response."""
        context = BankAnalyticsContextService._build_empty_context(
            "IMOR", "INVEX"
        )

        assert "Ejemplo" in context


class TestBuildErrorContext:
    """Test _build_error_context method."""

    def test_includes_error_info(self):
        """Test includes error information."""
        context = BankAnalyticsContextService._build_error_context("IMOR")

        assert "ERROR" in context
        assert "IMOR" in context

    def test_includes_truth_rules(self):
        """Test includes truth rules for error."""
        context = BankAnalyticsContextService._build_error_context("IMOR")

        assert "REGLAS DE VERDAD" in context
        assert "LA GRÁFICA FALLÓ" in context


class TestBuildFallbackContext:
    """Test _build_fallback_context method."""

    def test_builds_basic_context(self):
        """Test builds basic fallback context."""
        context = BankAnalyticsContextService._build_fallback_context(
            metric_name="IMOR",
            bank_names="INVEX",
            time_range={"start": "2023-01", "end": "2024-01"},
            data_as_of="2024-01-15",
            chart_stats={},
            is_ratio=False,
            unit_label="MDP",
        )

        assert "IMOR" in context
        assert "INVEX" in context

    def test_includes_stats_when_available(self):
        """Test includes statistics when available."""
        context = BankAnalyticsContextService._build_fallback_context(
            metric_name="IMOR",
            bank_names="INVEX",
            time_range={},
            data_as_of="2024-01-15",
            chart_stats={"INVEX": {
                "min": 1.0, "max": 2.0, "avg": 1.5,
                "current": 1.8, "first": 1.0,
                "trend": "creciente", "change_pct": 80.0
            }},
            is_ratio=True,
            unit_label="%",
        )

        assert "Estadísticas" in context
        assert "INVEX" in context


class TestIntentDetection:
    """Test intent/ranking detection in chart context."""

    def test_detects_ranking_intent_from_metadata(self):
        """Test detects ranking intent from metadata."""
        data = {
            "type": "chart",
            "chart_status": "success",
            "metric_name": "IMOR",
            "bank_names": [],
            "metadata": {"intent": "ranking"},
            "time_range": {},
            "data_as_of": "2024-01-15",
            "plotly_config": {
                "data": [{"name": "INVEX", "y": [1.5]}]
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert "RANKING" in context

    def test_detects_ranking_intent_from_top_level(self):
        """Test detects ranking intent from top level."""
        data = {
            "type": "chart",
            "chart_status": "success",
            "metric_name": "IMOR",
            "intent": "ranking",
            "bank_names": [],
            "time_range": {},
            "data_as_of": "2024-01-15",
            "plotly_config": {
                "data": [{"name": "INVEX", "y": [1.5]}]
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        # Should still be chart type
        assert ctx_type == "chart"


class TestUnitLabels:
    """Test unit label handling."""

    def test_uses_percent_for_ratio(self):
        """Test uses % for ratio metrics."""
        data = {
            "type": "chart",
            "chart_status": "success",
            "metric_name": "IMOR",
            "bank_names": ["INVEX"],
            "metadata": {"type": "ratio"},
            "time_range": {},
            "data_as_of": "2024-01-15",
            "plotly_config": {
                "data": [{"name": "INVEX", "y": [1.5, 1.8]}]
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert "%" in context

    def test_uses_mdp_for_non_ratio(self):
        """Test uses MDP for non-ratio metrics."""
        data = {
            "type": "chart",
            "chart_status": "success",
            "metric_name": "CARTERA",
            "bank_names": ["INVEX"],
            "metadata": {"type": "amount"},
            "time_range": {},
            "data_as_of": "2024-01-15",
            "plotly_config": {
                "data": [{"name": "INVEX", "y": [1000000, 1500000]}]
            },
        }

        context, ctx_type = BankAnalyticsContextService.build_llm_context(data)

        assert "MDP" in context
