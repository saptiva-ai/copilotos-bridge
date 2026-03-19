"""
Unit tests for ResponseValidator - Hallucination detection.

Tests verify:
1. Correct codes from tools pass validation
2. Hallucinated codes (not from tools) are detected
3. No hardcoded bank names - uses tool_results only
4. Code-bank consistency checks work
"""

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from services.response_validator import ResponseValidator, ValidationResult


@pytest.fixture
def validator():
    """Create fresh validator for each test."""
    return ResponseValidator()


class TestValidBankCodes:
    """Test that correct codes from tools pass validation."""

    def test_single_code_matches_tool(self, validator):
        """Code in response matches tool result."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "SCOTIABANK", "clave_cnbv": "0000040044"},
            }
        ]
        response = "La clave de SCOTIABANK es 040044"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True
        assert result.severity == "none"
        assert len(result.mismatched_codes) == 0

    def test_multiple_codes_match_tools(self, validator):
        """Multiple codes in response all match tool results."""
        tool_results = [
            {
                "banks": [
                    {"nombre_corto": "BBVA", "clave_cnbv": "0000040012"},
                    {"nombre_corto": "BANORTE", "clave_cnbv": "0000040072"},
                ]
            }
        ]
        response = "BBVA tiene la clave 040012 y BANORTE es 040072"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True
        assert len(result.mismatched_codes) == 0

    def test_code_with_leading_zeros_matches(self, validator):
        """0000040044 should match 40044."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "SCOTIABANK", "clave_cnbv": "0000040044"},
            }
        ]
        response = "La clave es 40044"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True


class TestHallucinationDetection:
    """Test that hallucinated codes are detected."""

    def test_detects_wrong_code(self, validator):
        """Tool returns 040044, LLM says 040021 - should detect."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "SCOTIABANK", "clave_cnbv": "0000040044"},
            }
        ]
        response = "La clave de Scotiabank es 040021"  # Wrong!

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is False
        assert result.severity == "error"
        assert "40021" in result.mismatched_codes

    def test_detects_invented_code(self, validator):
        """Response mentions code that no tool returned."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "BBVA", "clave_cnbv": "0000040012"},
            }
        ]
        response = "La clave de BBVA es 040012 y Santander es 040014"

        result = validator.validate_bank_codes(response, tool_results)

        # 040014 was not in tool results
        assert result.valid is False
        assert "40014" in result.mismatched_codes

    def test_detects_multiple_hallucinations(self, validator):
        """Multiple wrong codes in response."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "CIBANCO", "clave_cnbv": "0000040143"},
            }
        ]
        response = "CIBANCO: 040012, también 040021, y 040072"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is False
        # All three are wrong
        assert len(result.mismatched_codes) >= 2


class TestNoHardcodedBanks:
    """Test that validator uses tool_results only, no hardcoded banks."""

    def test_extracts_banks_from_tool_results_only(self, validator):
        """Banks should only come from tool_results, not hardcoded."""
        # Custom bank that wouldn't be hardcoded
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "BANCO_FICTICIO", "clave_cnbv": "0000099999"},
            }
        ]
        response = "La clave de BANCO_FICTICIO es 099999"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True
        assert "banco_ficticio" in result.tool_banks
        assert "banco_ficticio" in result.response_banks

    def test_unknown_bank_not_extracted_without_tool_data(self, validator):
        """Banks NOT in tool_results should NOT be extracted from response."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "BBVA", "clave_cnbv": "0000040012"},
            }
        ]
        response = "BBVA es 040012, pero BANORTE no aparece en tools"

        result = validator.validate_bank_codes(response, tool_results)

        # BANORTE is in response but NOT in tool_results
        # So it should NOT be in response_banks
        assert "banorte" not in result.response_banks
        assert "bbva" in result.response_banks

    def test_institutions_list_provides_valid_banks(self, validator):
        """list_institutions response provides valid bank names."""
        tool_results = [
            {
                "institutions": [
                    {"nombre_corto": "BBVA", "clave_cnbv": "0000040012"},
                    {"nombre_corto": "BANORTE", "clave_cnbv": "0000040072"},
                    {"nombre_corto": "SCOTIABANK", "clave_cnbv": "0000040044"},
                ]
            }
        ]
        response = "Los bancos son: BBVA (040012), BANORTE (040072), SCOTIABANK (040044)"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True
        assert len(result.tool_banks) == 3


class TestNoToolData:
    """Test behavior when no tool data is available."""

    def test_passes_when_no_tool_data(self, validator):
        """If no tools returned bank data, validation passes."""
        tool_results = []
        response = "La clave de BBVA es 040012"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True  # Can't validate, so pass through

    def test_passes_when_tool_failed(self, validator):
        """If tool returned success=false, no data to validate against."""
        tool_results = [
            {"success": False, "error": "Bank not found"}
        ]
        response = "No encontré información"

        result = validator.validate_bank_codes(response, tool_results)

        assert result.valid is True


class TestCodeBankConsistency:
    """Test that code-bank pairings are validated."""

    def test_correct_pairing_passes(self, validator):
        """BBVA=040012 in response matches BBVA=040012 from tools."""
        tool_results = [
            {
                "success": True,
                "bank": {"nombre_corto": "BBVA", "clave_cnbv": "0000040012"},
            }
        ]
        response = "BBVA tiene la clave 040012"

        result = validator.validate_code_bank_consistency(response, tool_results)

        assert result.valid is True

    def test_wrong_pairing_detected(self, validator):
        """Tool says SANTANDER=040014, LLM says CIBANCO=040014 - detect."""
        tool_results = [
            {
                "banks": [
                    {"nombre_corto": "SANTANDER", "clave_cnbv": "0000040014"},
                    {"nombre_corto": "CIBANCO", "clave_cnbv": "0000040143"},
                ]
            }
        ]
        response = "CIBANCO tiene la clave 040014"  # Wrong! Should be SANTANDER

        result = validator.validate_code_bank_consistency(response, tool_results)

        assert result.valid is False
        assert result.severity == "error"


class TestCodeNormalization:
    """Test code normalization for comparison."""

    def test_strips_leading_zeros(self, validator):
        """0000040012 and 40012 should match."""
        assert validator._normalize_code("0000040012") == "40012"
        assert validator._normalize_code("40012") == "40012"

    def test_preserves_significant_digits(self, validator):
        """Should keep meaningful part of code."""
        assert validator._normalize_code("040044") == "40044"
        assert validator._normalize_code("040012") == "40012"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
