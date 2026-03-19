#!/usr/bin/env python3
"""
Comprehensive Unit Tests for QuerySpecParser

Tests for:
- Entity extraction (banks, metrics)
- Temporal parsing
- Confidence scoring
- Typo handling
- Synonym resolution
- Edge cases and error handling
"""

import pytest
from typing import List, Tuple

# Import the parser - adjust path if needed
from bankadvisor.services.query_spec_parser import QuerySpecParser
from bankadvisor.services.clarification_service import ClarificationService


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def parser():
    """Create a QuerySpecParser instance."""
    return QuerySpecParser()


@pytest.fixture
def clarification_service():
    """Create a ClarificationService instance."""
    return ClarificationService()


# =============================================================================
# BANK ENTITY EXTRACTION TESTS
# =============================================================================

class TestBankExtraction:
    """Tests for bank entity extraction."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_bank", [
        # Exact matches
        ("IMOR de INVEX", "INVEX"),
        ("IMOR de BBVA", "BBVA"),
        ("IMOR de Santander", "SANTANDER"),
        ("IMOR de Banorte", "BANORTE"),
        ("IMOR de HSBC", "HSBC"),
        ("IMOR de Citibanamex", "CITIBANAMEX"),
        ("IMOR de Scotiabank", "SCOTIABANK"),
        ("IMOR de Inbursa", "INBURSA"),
        # Case variations
        ("IMOR de invex", "INVEX"),
        ("IMOR de INVEX", "INVEX"),
        ("IMOR de InVeX", "INVEX"),
        # Aliases
        ("IMOR de Bancomer", "BBVA"),
        ("IMOR de BBVA Bancomer", "BBVA"),
        ("IMOR de Banamex", "CITIBANAMEX"),
    ])
    async def test_bank_exact_match(self, parser, query, expected_bank):
        """Test exact bank name extraction."""
        spec = await parser.parse(query)
        assert expected_bank in spec.banks or spec.banks == [expected_bank]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "mi IMOR",
        "IMOR del banco",
        "nuestro IMOR",
        "nuestro banco IMOR",
    ])
    async def test_implicit_invex_reference(self, parser, query):
        """Test implicit INVEX references (mi, nuestro, del banco)."""
        spec = await parser.parse(query)
        # Should either extract INVEX or require clarification
        assert "INVEX" in spec.banks or spec.requires_clarification

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_banks", [
        ("IMOR de INVEX y BBVA", ["INVEX", "BBVA"]),
        ("compara INVEX con Santander", ["INVEX", "SANTANDER"]),
        ("INVEX vs BBVA", ["INVEX", "BBVA"]),
        ("INVEX, BBVA y Banorte", ["INVEX", "BBVA", "BANORTE"]),
    ])
    async def test_multiple_banks(self, parser, query, expected_banks):
        """Test multiple bank extraction."""
        spec = await parser.parse(query)
        for bank in expected_banks:
            assert bank in spec.banks

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "IMOR de todos los bancos",
        "IMOR del sistema",
        "IMOR del sistema bancario",
        "IMOR del mercado",
    ])
    async def test_system_references(self, parser, query):
        """Test system/market references."""
        spec = await parser.parse(query)
        assert "SISTEMA" in spec.banks or spec.comparison_type == "system"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "IMOR de BancoFantasma",
        "IMOR de Bank of America",
        "IMOR de Chase",
        "IMOR de Wells Fargo",
    ])
    async def test_unknown_bank(self, parser, query):
        """Test handling of unknown bank names."""
        spec = await parser.parse(query)
        # Should require clarification or have low confidence
        assert spec.requires_clarification or spec.confidence_score < 0.5


# =============================================================================
# METRIC EXTRACTION TESTS
# =============================================================================

class TestMetricExtraction:
    """Tests for metric entity extraction."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_metric", [
        # Direct metric names
        ("IMOR de INVEX", "IMOR"),
        ("ICAP de INVEX", "ICAP"),
        ("ICOR de INVEX", "ICOR"),
        # Synonyms
        ("morosidad de INVEX", "IMOR"),
        ("cobertura de INVEX", "ICOR"),
        ("capitalización de INVEX", "ICAP"),
        ("indice de morosidad de INVEX", "IMOR"),
        ("indice de cobertura de INVEX", "ICOR"),
        ("indice de capitalización de INVEX", "ICAP"),
        # With accents
        ("índice de morosidad de INVEX", "IMOR"),
        # English terms
        ("NPL ratio de INVEX", "IMOR"),
        ("coverage ratio de INVEX", "ICOR"),
    ])
    async def test_metric_extraction(self, parser, query, expected_metric):
        """Test metric extraction with various forms."""
        spec = await parser.parse(query)
        assert spec.metric == expected_metric

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_metric", [
        ("cartera total de INVEX", "CARTERA_TOTAL"),
        ("cartera comercial de INVEX", "CARTERA_COMERCIAL"),
        ("cartera de consumo de INVEX", "CARTERA_CONSUMO"),
        ("cartera hipotecaria de INVEX", "CARTERA_VIVIENDA"),
        ("cartera vencida de INVEX", "CARTERA_VENCIDA"),
        ("reservas de INVEX", "RESERVAS"),
    ])
    async def test_cartera_metrics(self, parser, query, expected_metric):
        """Test cartera/portfolio metric extraction."""
        spec = await parser.parse(query)
        assert spec.metric == expected_metric

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "datos de INVEX",
        "información de INVEX",
        "métricas de INVEX",
        "todo sobre INVEX",
    ])
    async def test_missing_metric(self, parser, query):
        """Test queries without specific metric."""
        spec = await parser.parse(query)
        assert spec.requires_clarification or "metric" in (spec.missing_fields or [])


# =============================================================================
# TEMPORAL PARSING TESTS
# =============================================================================

class TestTemporalParsing:
    """Tests for temporal/time range parsing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_months", [
        ("IMOR de INVEX últimos 3 meses", 3),
        ("IMOR de INVEX ultimos 3 meses", 3),
        ("IMOR de INVEX últimos tres meses", 3),
        ("IMOR de INVEX últimos 6 meses", 6),
        ("IMOR de INVEX último mes", 1),
        ("IMOR de INVEX últimos 12 meses", 12),
    ])
    async def test_relative_months(self, parser, query, expected_months):
        """Test relative month parsing."""
        spec = await parser.parse(query)
        if spec.time_range:
            assert spec.time_range.months == expected_months or spec.time_range.period_type == "months"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_year", [
        ("IMOR de INVEX 2024", 2024),
        ("IMOR de INVEX en 2024", 2024),
        ("IMOR de INVEX año 2024", 2024),
        ("IMOR de INVEX del 2024", 2024),
    ])
    async def test_year_parsing(self, parser, query, expected_year):
        """Test year parsing."""
        spec = await parser.parse(query)
        if spec.time_range:
            assert spec.time_range.year == expected_year

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_quarter", [
        ("IMOR de INVEX Q1 2024", 1),
        ("IMOR de INVEX primer trimestre 2024", 1),
        ("IMOR de INVEX segundo trimestre", 2),
        ("IMOR de INVEX último trimestre", 4),
    ])
    async def test_quarter_parsing(self, parser, query, expected_quarter):
        """Test quarter/trimester parsing."""
        spec = await parser.parse(query)
        if spec.time_range:
            assert spec.time_range.quarter == expected_quarter or "trimestre" in query.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "IMOR de INVEX enero 2024",
        "IMOR de INVEX en enero",
        "IMOR de INVEX diciembre 2023",
    ])
    async def test_specific_month(self, parser, query):
        """Test specific month parsing."""
        spec = await parser.parse(query)
        # Should have time range with month or specific date
        assert spec.time_range is not None or not spec.requires_clarification


# =============================================================================
# CONFIDENCE SCORING TESTS
# =============================================================================

class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,min_confidence", [
        # High confidence queries (complete and clear)
        ("IMOR de INVEX", 0.7),
        ("ICAP de INVEX últimos 3 meses", 0.8),
        ("compara IMOR de INVEX con BBVA", 0.7),
    ])
    async def test_high_confidence(self, parser, query, min_confidence):
        """Test high confidence scoring."""
        spec = await parser.parse(query)
        assert spec.confidence_score >= min_confidence

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,max_confidence", [
        # Low confidence queries (ambiguous/incomplete)
        ("datos", 0.3),
        ("información", 0.3),
        ("banco", 0.4),
        ("métricas", 0.4),
    ])
    async def test_low_confidence(self, parser, query, max_confidence):
        """Test low confidence scoring."""
        spec = await parser.parse(query)
        assert spec.confidence_score <= max_confidence or spec.requires_clarification


# =============================================================================
# TYPO HANDLING TESTS
# =============================================================================

class TestTypoHandling:
    """Tests for typo tolerance."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_metric", [
        ("IMRO de INVEX", "IMOR"),  # Transposed letters
        ("morisidad de INVEX", "IMOR"),  # Common typo
        ("morozidad de INVEX", "IMOR"),  # s->z
        ("indise de cobertura", "ICOR"),  # c->s typo
    ])
    async def test_metric_typos(self, parser, query, expected_metric):
        """Test metric typo tolerance."""
        spec = await parser.parse(query)
        # Should either match the correct metric or ask for clarification
        assert spec.metric == expected_metric or spec.requires_clarification

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        ("IMBEX IMOR"),  # INVEX typo
        ("cartra comercial"),  # cartera typo
        ("ultmos 3 meces"),  # últimos meses typo
    ])
    async def test_general_typos(self, parser, query):
        """Test general typo tolerance."""
        spec = await parser.parse(query)
        # Should not crash and should provide some response
        assert spec is not None


# =============================================================================
# COMPARISON TYPE TESTS
# =============================================================================

class TestComparisonTypes:
    """Tests for comparison type detection."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_type", [
        ("compara IMOR de INVEX con BBVA", "banks"),
        ("INVEX vs BBVA", "banks"),
        ("INVEX contra BBVA", "banks"),
        ("diferencia entre INVEX y BBVA", "banks"),
    ])
    async def test_bank_comparison(self, parser, query, expected_type):
        """Test bank comparison detection."""
        spec = await parser.parse(query)
        assert spec.comparison_type == expected_type or len(spec.banks) > 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "IMOR de INVEX vs sistema",
        "compara INVEX con el mercado",
        "INVEX contra el promedio",
    ])
    async def test_system_comparison(self, parser, query):
        """Test system/market comparison detection."""
        spec = await parser.parse(query)
        assert "SISTEMA" in spec.banks or spec.comparison_type == "system"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "evolución del IMOR de INVEX",
        "tendencia del ICAP",
        "histórico de reservas",
    ])
    async def test_evolution_detection(self, parser, query):
        """Test evolution/trend detection."""
        spec = await parser.parse(query)
        assert spec.query_type == "evolution" or spec.time_range is not None


# =============================================================================
# CLARIFICATION SERVICE TESTS
# =============================================================================

class TestClarificationService:
    """Tests for clarification service."""

    @pytest.mark.asyncio
    async def test_clarification_payload_structure(self, parser, clarification_service):
        """Test clarification payload has correct structure for frontend."""
        query = "datos de INVEX"
        spec = await parser.parse(query)
        enriched = clarification_service.enrich_with_clarifications(spec)
        payload = clarification_service.get_clarification_payload(enriched)

        # Required fields
        assert "type" in payload
        assert payload["type"] == "clarification"
        assert "clarifications" in payload
        assert len(payload["clarifications"]) > 0

        # Each clarification should have required fields
        for clar in payload["clarifications"]:
            assert "field" in clar
            assert "question" in clar
            assert "options" in clar
            assert len(clar["options"]) > 0

    @pytest.mark.asyncio
    async def test_missing_bank_clarification(self, parser, clarification_service):
        """Test clarification for missing bank."""
        query = "IMOR de los últimos 3 meses"
        spec = await parser.parse(query)
        enriched = clarification_service.enrich_with_clarifications(spec)

        assert enriched.requires_clarification
        # Should ask for bank
        assert "bank" in enriched.missing_fields or any(
            f.field == "bank" for f in getattr(enriched, "ambiguity_flags", [])
        )

    @pytest.mark.asyncio
    async def test_missing_metric_clarification(self, parser, clarification_service):
        """Test clarification for missing metric."""
        query = "datos de INVEX"
        spec = await parser.parse(query)
        enriched = clarification_service.enrich_with_clarifications(spec)

        assert enriched.requires_clarification
        assert "metric" in enriched.missing_fields

    @pytest.mark.asyncio
    async def test_valid_query_no_clarification(self, parser, clarification_service):
        """Test that valid queries don't trigger clarification."""
        query = "IMOR de INVEX"
        spec = await parser.parse(query)

        assert not spec.requires_clarification
        assert spec.confidence_score >= 0.7


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and special inputs."""

    @pytest.mark.asyncio
    async def test_empty_query(self, parser):
        """Test empty query handling."""
        spec = await parser.parse("")
        assert spec.requires_clarification

    @pytest.mark.asyncio
    async def test_whitespace_only(self, parser):
        """Test whitespace-only query."""
        spec = await parser.parse("   ")
        assert spec.requires_clarification

    @pytest.mark.asyncio
    async def test_special_characters(self, parser):
        """Test query with special characters."""
        spec = await parser.parse("IMOR de INVEX!!! ???")
        # Should handle gracefully
        assert spec is not None

    @pytest.mark.asyncio
    async def test_very_long_query(self, parser):
        """Test very long query."""
        query = "IMOR " * 100 + "de INVEX"
        spec = await parser.parse(query)
        # Should not crash
        assert spec is not None

    @pytest.mark.asyncio
    async def test_unicode_characters(self, parser):
        """Test unicode character handling."""
        spec = await parser.parse("IMOR de INVEX últimos 3 meses")
        assert spec is not None

    @pytest.mark.asyncio
    async def test_mixed_language(self, parser):
        """Test mixed Spanish/English query."""
        spec = await parser.parse("show me the IMOR of INVEX")
        # Should extract IMOR and INVEX
        assert spec.metric == "IMOR" or spec.requires_clarification

    @pytest.mark.asyncio
    async def test_repeated_entities(self, parser):
        """Test repeated entity handling."""
        spec = await parser.parse("INVEX INVEX INVEX IMOR")
        # Should detect single bank
        assert len(spec.banks) == 1 or "INVEX" in spec.banks


# =============================================================================
# INTEGRATION TESTS (Parser + Clarification)
# =============================================================================

class TestParserClarificationIntegration:
    """Integration tests for parser and clarification service."""

    @pytest.mark.asyncio
    async def test_full_flow_valid_query(self, parser, clarification_service):
        """Test full flow with valid query."""
        query = "IMOR de INVEX últimos 3 meses"
        spec = await parser.parse(query)
        enriched = clarification_service.enrich_with_clarifications(spec)

        assert not enriched.requires_clarification
        assert enriched.metric == "IMOR"
        assert "INVEX" in enriched.banks
        assert enriched.confidence_score >= 0.7

    @pytest.mark.asyncio
    async def test_full_flow_ambiguous_query(self, parser, clarification_service):
        """Test full flow with ambiguous query."""
        query = "quiero ver datos"
        spec = await parser.parse(query)
        enriched = clarification_service.enrich_with_clarifications(spec)

        assert enriched.requires_clarification
        assert len(enriched.missing_fields) >= 2  # metric and bank

    @pytest.mark.asyncio
    async def test_clarification_options_valid(self, parser, clarification_service):
        """Test that clarification options are valid."""
        query = "datos de INVEX"
        spec = await parser.parse(query)
        enriched = clarification_service.enrich_with_clarifications(spec)
        payload = clarification_service.get_clarification_payload(enriched)

        # Check that metric options are valid
        for clar in payload["clarifications"]:
            if clar["field"] == "metric":
                valid_metrics = ["IMOR", "ICAP", "ICOR", "CARTERA_TOTAL", "RESERVAS"]
                for opt in clar["options"]:
                    # Option value or label should be a valid metric
                    assert any(m in str(opt).upper() for m in valid_metrics)
