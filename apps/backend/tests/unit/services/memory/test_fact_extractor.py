"""
Unit tests for memory/fact_extractor module.

Tests:
- BANKS and BANK_ALIASES constants
- PERIOD_PATTERNS
- METRIC_PATTERNS
- extract_topic_metric function
- extract_bank function
- extract_period function
- extract_metrics function
- extract_all function
"""

import pytest

from src.services.memory.fact_extractor import (
    BANK_ALIASES,
    BANKS,
    METRIC_PATTERNS,
    PERIOD_PATTERNS,
    TOPIC_METRIC_ALIASES,
    extract_all,
    extract_bank,
    extract_metrics,
    extract_period,
    extract_topic_metric,
)

pytestmark = [pytest.mark.unit]


class TestBankConstants:
    """Test bank-related constants."""

    def test_banks_not_empty(self):
        """Test BANKS set is not empty."""
        assert len(BANKS) > 0

    def test_banks_contains_major_banks(self):
        """Test BANKS contains major Mexican banks."""
        assert "invex" in BANKS
        assert "bbva" in BANKS
        assert "banorte" in BANKS
        assert "santander" in BANKS
        assert "hsbc" in BANKS
        assert "citibanamex" in BANKS

    def test_banks_are_lowercase(self):
        """Test all bank names are lowercase."""
        for bank in BANKS:
            assert bank == bank.lower()

    def test_bank_aliases_not_empty(self):
        """Test BANK_ALIASES dict is not empty."""
        assert len(BANK_ALIASES) > 0

    def test_banamex_alias(self):
        """Test banamex aliases to citibanamex."""
        assert BANK_ALIASES["banamex"] == "citibanamex"

    def test_citi_alias(self):
        """Test citi aliases to citibanamex."""
        assert BANK_ALIASES["citi"] == "citibanamex"


class TestPeriodPatterns:
    """Test period pattern definitions."""

    def test_period_patterns_not_empty(self):
        """Test PERIOD_PATTERNS list is not empty."""
        assert len(PERIOD_PATTERNS) > 0

    def test_period_patterns_are_tuples(self):
        """Test each pattern is a tuple of (regex, formatter)."""
        for pattern, formatter in PERIOD_PATTERNS:
            assert isinstance(pattern, str)
            assert callable(formatter)


class TestMetricPatterns:
    """Test metric pattern definitions."""

    def test_metric_patterns_not_empty(self):
        """Test METRIC_PATTERNS dict is not empty."""
        assert len(METRIC_PATTERNS) > 0

    def test_common_metrics_defined(self):
        """Test common banking metrics are defined."""
        assert "imor" in METRIC_PATTERNS
        assert "icor" in METRIC_PATTERNS
        assert "icap" in METRIC_PATTERNS
        assert "roe" in METRIC_PATTERNS
        assert "roa" in METRIC_PATTERNS


class TestTopicMetricAliases:
    """Test topic metric alias definitions."""

    def test_aliases_not_empty(self):
        """Test TOPIC_METRIC_ALIASES list is not empty."""
        assert len(TOPIC_METRIC_ALIASES) > 0

    def test_aliases_are_tuples(self):
        """Test each alias is a tuple of (alias, metric_key)."""
        for alias, metric_key in TOPIC_METRIC_ALIASES:
            assert isinstance(alias, str)
            assert isinstance(metric_key, str)


class TestExtractTopicMetric:
    """Test extract_topic_metric function."""

    def test_extracts_pdm_from_text(self):
        """Test extracts PDM metric."""
        assert extract_topic_metric("¿Cuál es el PDM de INVEX?") == "pdm"

    def test_extracts_market_share(self):
        """Test extracts market share as PDM."""
        assert extract_topic_metric("What is the market share?") == "pdm"

    def test_extracts_participacion_de_mercado(self):
        """Test extracts participación de mercado as PDM."""
        assert extract_topic_metric("La participación de mercado de BBVA") == "pdm"

    def test_extracts_imor(self):
        """Test extracts IMOR metric."""
        assert extract_topic_metric("Dime el IMOR de Banorte") == "imor"

    def test_extracts_icap(self):
        """Test extracts ICAP metric."""
        assert extract_topic_metric("¿Cuál es el ratio de capitalización?") == "icap"

    def test_extracts_roe(self):
        """Test extracts ROE metric."""
        assert extract_topic_metric("El ROE del sistema bancario") == "roe"

    def test_extracts_cartera_vencida(self):
        """Test extracts cartera vencida metric."""
        assert extract_topic_metric("La cartera vencida de Santander") == "cartera_vencida"

    def test_returns_none_for_no_metric(self):
        """Test returns None when no metric found."""
        assert extract_topic_metric("Hola, cómo estás?") is None

    def test_case_insensitive(self):
        """Test extraction is case insensitive."""
        assert extract_topic_metric("EL IMOR ES ALTO") == "imor"
        assert extract_topic_metric("el imor es alto") == "imor"


class TestExtractBank:
    """Test extract_bank function."""

    def test_extracts_invex(self):
        """Test extracts INVEX bank."""
        assert extract_bank("El IMOR de INVEX") == "invex"

    def test_extracts_bbva(self):
        """Test extracts BBVA bank."""
        assert extract_bank("BBVA tiene buen ROE") == "bbva"

    def test_extracts_banorte(self):
        """Test extracts Banorte bank."""
        assert extract_bank("Banorte reportó utilidades") == "banorte"

    def test_extracts_santander(self):
        """Test extracts Santander bank."""
        assert extract_bank("Santander México") == "santander"

    def test_extracts_hsbc(self):
        """Test extracts HSBC bank."""
        assert extract_bank("HSBC tuvo pérdidas") == "hsbc"

    def test_extracts_citibanamex(self):
        """Test extracts Citibanamex bank."""
        assert extract_bank("Citibanamex cerró sucursales") == "citibanamex"

    def test_extracts_sistema(self):
        """Test extracts sistema (aggregate)."""
        assert extract_bank("El sistema bancario mexicano") == "sistema"

    def test_returns_none_for_no_bank(self):
        """Test returns None when no bank found."""
        assert extract_bank("Hola, cómo estás?") is None

    def test_case_insensitive(self):
        """Test extraction is case insensitive."""
        assert extract_bank("INVEX") == "invex"
        assert extract_bank("invex") == "invex"
        assert extract_bank("Invex") == "invex"

    def test_word_boundary_matching(self):
        """Test matches on word boundaries only."""
        # Should not match "investment" even though it contains "inv"
        assert extract_bank("investment banking") is None


class TestExtractPeriod:
    """Test extract_period function."""

    def test_extracts_q_format(self):
        """Test extracts Q3 2025 format."""
        assert extract_period("Q3 2025") == "q3_2025"

    def test_extracts_q_de_format(self):
        """Test extracts Q3 de 2025 format."""
        assert extract_period("Q3 de 2025") == "q3_2025"

    def test_extracts_year_q_format(self):
        """Test extracts 2025 Q3 format."""
        assert extract_period("2025 Q3") == "q3_2025"

    def test_extracts_year_dash_q_format(self):
        """Test extracts 2025-Q3 format."""
        assert extract_period("2025-Q3") == "q3_2025"

    def test_extracts_trimestre_t_format(self):
        """Test extracts T1 2025 format (Spanish trimestre)."""
        assert extract_period("T1 2025") == "q1_2025"

    def test_extracts_number_t_format(self):
        """Test extracts 1T 2025 format."""
        assert extract_period("1T 2025") == "q1_2025"

    def test_extracts_year_only(self):
        """Test extracts year only."""
        assert extract_period("En 2024 el banco") == "2024"

    def test_returns_none_for_no_period(self):
        """Test returns None when no period found."""
        assert extract_period("Hola, cómo estás?") is None

    def test_case_insensitive(self):
        """Test extraction is case insensitive."""
        assert extract_period("q3 2025") == "q3_2025"
        assert extract_period("Q3 2025") == "q3_2025"


class TestExtractMetrics:
    """Test extract_metrics function."""

    def test_extracts_imor_percent(self):
        """Test extracts IMOR with percent."""
        result = extract_metrics("El IMOR es de 2.3%")
        assert "imor" in result
        assert "2.3%" in result["imor"]

    def test_extracts_imor_mdp(self):
        """Test extracts IMOR with MDP."""
        result = extract_metrics("El IMOR de INVEX es de 4 MDP")
        assert "imor" in result
        assert "MDP" in result["imor"]

    def test_extracts_icor(self):
        """Test extracts ICOR metric."""
        result = extract_metrics("ICOR: 1.5%")
        assert "icor" in result

    def test_extracts_icap(self):
        """Test extracts ICAP metric."""
        result = extract_metrics("El ICAP es 15%")
        assert "icap" in result

    def test_extracts_roe(self):
        """Test extracts ROE metric."""
        result = extract_metrics("ROE de 12.5%")
        assert "roe" in result

    def test_extracts_roa(self):
        """Test extracts ROA metric."""
        result = extract_metrics("ROA = 1.2%")
        assert "roa" in result

    def test_extracts_multiple_metrics(self):
        """Test extracts multiple metrics from text."""
        result = extract_metrics("IMOR es 2.3% y ROE es 15%")
        assert "imor" in result
        assert "roe" in result

    def test_returns_empty_for_no_metrics(self):
        """Test returns empty dict when no metrics found."""
        result = extract_metrics("Hola, cómo estás?")
        assert result == {}

    def test_handles_european_decimal_format(self):
        """Test handles European decimal format (2,3 -> 2.3)."""
        result = extract_metrics("IMOR es de 2,3%")
        assert "imor" in result
        # Should convert comma to period
        assert "2.3" in result["imor"]

    def test_default_percent_for_ratio_metrics(self):
        """Test adds % suffix for ratio metrics without unit."""
        result = extract_metrics("El IMOR es de 2.3")
        assert "imor" in result
        assert result["imor"].endswith("%")


class TestExtractAll:
    """Test extract_all function."""

    def test_extracts_bank_period_metric(self):
        """Test extracts all components."""
        # Note: Pattern requires "es/de/fue/:" directly before number
        # So we provide context separately
        facts, context = extract_all("En Q2 2025, IMOR de INVEX es 2.3%")

        # Check facts - pattern matches "IMOR de INVEX es 2.3%"
        assert "invex.q2_2025.imor" in facts
        assert "2.3%" in facts["invex.q2_2025.imor"]

        # Check context
        assert context["bank"] == "invex"
        assert context["period"] == "q2_2025"
        assert context["metric"] == "imor"

    def test_inherits_from_current_context(self):
        """Test inherits missing values from context."""
        current_context = {"bank": "bbva", "period": "q1_2025"}
        facts, context = extract_all("El IMOR es 3%", current_context)

        # Should use context values for key
        assert "bbva.q1_2025.imor" in facts
        assert context["bank"] == "bbva"
        assert context["period"] == "q1_2025"

    def test_overrides_context_with_new_values(self):
        """Test new values override context."""
        current_context = {"bank": "bbva", "period": "q1_2025"}
        facts, context = extract_all(
            "El IMOR de INVEX Q3 2025 es 2%", current_context
        )

        # New values should override
        assert context["bank"] == "invex"
        assert context["period"] == "q3_2025"

    def test_metric_only_key(self):
        """Test creates metric-only key when no bank/period."""
        facts, context = extract_all("El IMOR es 5%")

        assert "imor" in facts
        assert facts["imor"] == "5%"

    def test_bank_and_metric_key(self):
        """Test creates bank.metric key when no period."""
        facts, context = extract_all("El IMOR de INVEX es 3%")

        assert "invex.imor" in facts

    def test_period_and_metric_key(self):
        """Test creates period.metric key when no bank."""
        # Pattern needs "es/de/fue/:" before number, period separate
        facts, context = extract_all("Q2 2025: IMOR es 4%")

        assert "q2_2025.imor" in facts

    def test_updates_metric_context_from_topic(self):
        """Test updates metric context from topic mention."""
        facts, context = extract_all("¿Cuál es el PDM de INVEX?")

        # No facts (no value provided)
        assert len(facts) == 0
        # But context should have metric
        assert context.get("metric") == "pdm"

    def test_empty_context_on_no_match(self):
        """Test returns empty context when nothing found."""
        facts, context = extract_all("Hola")

        assert facts == {}
        assert "bank" not in context
        assert "period" not in context
        assert "metric" not in context

    def test_preserves_existing_context(self):
        """Test preserves existing context when nothing new found."""
        current_context = {"bank": "invex", "period": "q1_2025", "metric": "imor"}
        facts, context = extract_all("Hola", current_context)

        assert context["bank"] == "invex"
        assert context["period"] == "q1_2025"
        assert context["metric"] == "imor"


class TestIntegration:
    """Integration tests for fact extraction scenarios."""

    def test_multi_turn_conversation(self):
        """Test fact extraction across multiple turns."""
        # Turn 1: User mentions bank and metric
        facts1, ctx1 = extract_all("¿Cuál es el IMOR de INVEX?")
        assert ctx1.get("bank") == "invex"
        assert ctx1.get("metric") == "imor"

        # Turn 2: Assistant provides value
        facts2, ctx2 = extract_all("El IMOR es de 2.3%", ctx1)
        assert "invex.imor" in facts2
        assert ctx2.get("bank") == "invex"

        # Turn 3: User asks about different metric, same bank
        facts3, ctx3 = extract_all("¿Y el ROE?", ctx2)
        assert ctx3.get("metric") == "roe"
        assert ctx3.get("bank") == "invex"  # Preserved

    def test_realistic_query(self):
        """Test realistic banking query."""
        # Format that matches the regex pattern: metric + bank + es/fue/de + value
        text = "Q3 2025: El IMOR de Banorte fue de 1.8%"
        facts, ctx = extract_all(text)

        assert "banorte.q3_2025.imor" in facts
        assert "1.8%" in facts["banorte.q3_2025.imor"]
        assert ctx["bank"] == "banorte"
        assert ctx["period"] == "q3_2025"
        assert ctx["metric"] == "imor"
