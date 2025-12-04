"""
Tests for Simple Memory Service

Tests the regex-based fact extraction and memory service functionality.
"""

import pytest
from src.services.memory.fact_extractor import (
    extract_all,
    extract_bank,
    extract_period,
    extract_metrics,
)


class TestExtractBank:
    """Test bank name extraction."""

    def test_extract_invex(self):
        assert extract_bank("El IMOR de INVEX es 2.3%") == "invex"

    def test_extract_bbva(self):
        assert extract_bank("Analiza BBVA por favor") == "bbva"

    def test_extract_banorte(self):
        assert extract_bank("Datos de Banorte Q3") == "banorte"

    def test_extract_lowercase(self):
        assert extract_bank("santander tiene mejor ratio") == "santander"

    def test_no_bank_found(self):
        assert extract_bank("Random text without bank") is None

    def test_partial_match_rejected(self):
        # Should not match partial words
        assert extract_bank("investment bank analysis") is None


class TestExtractPeriod:
    """Test period extraction."""

    def test_q_format(self):
        assert extract_period("Q3 2025") == "q3_2025"

    def test_q_with_de(self):
        assert extract_period("Q1 de 2024") == "q1_2024"

    def test_year_q_format(self):
        assert extract_period("2025 Q2") == "q2_2025"

    def test_trimestre_format(self):
        assert extract_period("T4 2025") == "q4_2025"

    def test_just_year(self):
        assert extract_period("en 2024") == "2024"

    def test_no_period_found(self):
        assert extract_period("sin periodo especificado") is None


class TestExtractMetrics:
    """Test metric extraction."""

    def test_imor_basic(self):
        metrics = extract_metrics("IMOR es 2.3%")
        assert "imor" in metrics
        assert metrics["imor"] == "2.3%"

    def test_imor_with_de(self):
        metrics = extract_metrics("IMOR de 3.8%")
        assert metrics["imor"] == "3.8%"

    def test_icor(self):
        metrics = extract_metrics("ICOR: 145%")
        assert metrics["icor"] == "145%"

    def test_dscr_no_percent(self):
        metrics = extract_metrics("DSCR es 1.25")
        assert metrics["dscr"] == "1.25"

    def test_tasa_interes(self):
        metrics = extract_metrics("tasa de interés 11.2%")
        assert "tasa_interes" in metrics
        assert metrics["tasa_interes"] == "11.2%"

    def test_cartera_vencida(self):
        metrics = extract_metrics("cartera vencida de 450,000,000")
        assert "cartera_vencida" in metrics

    def test_multiple_metrics(self):
        metrics = extract_metrics("IMOR 3.8%, ICOR 145%, tasa 11%")
        assert "imor" in metrics
        assert "icor" in metrics

    def test_european_decimal_format(self):
        """Handle European decimal format (comma as decimal separator)."""
        metrics = extract_metrics("IMOR es 2,3%")
        assert metrics["imor"] == "2.3%"

    def test_thousand_separator(self):
        """Handle thousand separators correctly."""
        metrics = extract_metrics("cartera vencida de 1,000,000")
        assert "cartera_vencida" in metrics
        # Should remove thousand separators
        assert "," not in metrics["cartera_vencida"]


class TestExtractAll:
    """Test complete fact extraction."""

    def test_basic_extraction(self):
        """Extract bank, period, and metric from text."""
        facts, ctx = extract_all("El IMOR de INVEX Q2 2025 es 2.3%")

        assert "invex.q2_2025.imor" in facts
        assert facts["invex.q2_2025.imor"] == "2.3%"
        assert ctx["bank"] == "invex"
        assert ctx["period"] == "q2_2025"
        assert ctx["metric"] == "imor"

    def test_context_inheritance(self):
        """Use existing context when bank/period not in message."""
        facts, ctx = extract_all(
            "Ahora el DSCR es 1.25",
            current_context={"bank": "invex", "period": "q2_2025"}
        )

        assert "invex.q2_2025.dscr" in facts
        assert facts["invex.q2_2025.dscr"] == "1.25"

    def test_context_override(self):
        """New bank/period overrides existing context."""
        facts, ctx = extract_all(
            "BBVA Q3 2026 tiene IMOR de 2.1%",
            current_context={"bank": "invex", "period": "q2_2025"}
        )

        assert ctx["bank"] == "bbva"
        assert ctx["period"] == "q3_2026"
        assert "bbva.q3_2026.imor" in facts

    def test_no_context_only_metric(self):
        """Metric without bank/period uses simple key."""
        facts, ctx = extract_all("El IMOR es 2.3%")

        assert "imor" in facts
        assert facts["imor"] == "2.3%"

    def test_bank_only_no_period(self):
        """Bank without period uses bank.metric format."""
        facts, ctx = extract_all("INVEX tiene IMOR de 2.3%")

        # Should be invex.imor since no period specified
        assert any("invex" in k and "imor" in k for k in facts)

    def test_empty_string(self):
        """Empty string returns empty results."""
        facts, ctx = extract_all("")
        assert facts == {}
        assert ctx == {}

    def test_no_facts_preserves_context(self):
        """Message without facts preserves existing context."""
        facts, ctx = extract_all(
            "¿Cuál era el dato?",
            current_context={"bank": "invex", "period": "q2_2025"}
        )

        assert facts == {}
        assert ctx["bank"] == "invex"
        assert ctx["period"] == "q2_2025"


class TestFormattingForLLM:
    """Test the format of extracted facts for LLM consumption."""

    def test_multiple_scopes(self):
        """Multiple banks/periods should extract correctly."""
        # First message
        facts1, ctx1 = extract_all("INVEX 2025 tiene IMOR 2.3%")

        # Second message with different bank
        facts2, ctx2 = extract_all(
            "BBVA Q3 2026 tiene IMOR 2.1%",
            current_context=ctx1
        )

        # Both facts should be scoped correctly
        assert "invex.2025.imor" in facts1
        assert "bbva.q3_2026.imor" in facts2

    def test_accumulation_scenario(self):
        """Simulate accumulating facts over conversation."""
        all_facts = {}
        ctx = {}

        # Turn 1
        facts, ctx = extract_all("Dame el IMOR de INVEX en 2025", ctx)
        all_facts.update(facts)  # No facts yet, just context

        # Turn 2
        facts, ctx = extract_all("El IMOR es 2.3% y la cartera vencida 450 millones", ctx)
        all_facts.update(facts)

        # Turn 3
        facts, ctx = extract_all("Ahora Q3 2026, el IMOR subió a 3.8%", ctx)
        all_facts.update(facts)

        # Verify accumulated facts
        assert "invex.2025.imor" in all_facts or "invex.imor" in all_facts
        assert any("q3_2026" in k and "imor" in k for k in all_facts)


# Async tests for MemoryService would go here
# Requires pytest-asyncio and database mocking

# @pytest.mark.asyncio
# async def test_process_message():
#     """Test processing a message through memory service."""
#     pass

# @pytest.mark.asyncio
# async def test_get_context_for_llm():
#     """Test building LLM context with memory."""
#     pass
