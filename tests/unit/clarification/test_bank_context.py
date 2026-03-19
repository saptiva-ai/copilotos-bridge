"""
Unit tests for BankContext and bank detection (BUG-07 fix).

These tests verify that:
1. Explicit bank mentions are correctly detected
2. Queries without bank trigger clarification (not default to INVEX)
3. Possessive pronouns no longer default to INVEX
4. System prompts don't contain INVEX hardcodes

Related documentation: docs/bugfixes/bankadvisor-generalization.md
"""

import pytest
import re
from typing import List, Optional


class TestBankDetection:
    """Tests for bank detection in queries."""

    @pytest.fixture
    def parser(self):
        """Create a QuerySpecParser instance for testing."""
        import sys
        import os
        # Add bank-advisor-private to path if not already
        plugin_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "plugins", "bank-advisor-private", "src"
        )
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        from bankadvisor.services.query_spec_parser import QuerySpecParser
        return QuerySpecParser()

    def test_explicit_bank_detection(self, parser):
        """Test that explicit bank mentions are detected."""
        test_cases = [
            ("IMOR de INVEX", ["INVEX"]),
            ("IMOR de BBVA últimos 3 meses", ["BBVA"]),
            ("compara ICAP de Santander vs HSBC", ["SANTANDER", "HSBC"]),
            ("cartera total del sistema bancario", ["SISTEMA"]),
            ("IMOR de Banorte 2024", ["BANORTE"]),
        ]

        for query, expected_banks in test_cases:
            banks = parser._extract_banks_heuristic(query)
            # Normalize to uppercase for comparison
            banks_upper = [b.upper() for b in banks if b]
            for expected in expected_banks:
                assert expected in banks_upper, f"Expected {expected} in {banks_upper} for query: {query}"

    def test_no_bank_triggers_clarification(self, parser):
        """Test that queries without bank don't silently default to INVEX."""
        queries_without_bank = [
            "¿Cuál es el IMOR?",
            "Muéstrame la morosidad",
            "Dame el ICAP últimos 3 meses",
            "Cartera comercial 2024",
        ]

        for query in queries_without_bank:
            banks = parser._extract_banks_heuristic(query)
            # Should NOT default to INVEX
            assert "INVEX" not in [b.upper() for b in banks if b], \
                f"Query '{query}' should not default to INVEX, got: {banks}"

    def test_possessive_pronouns_no_longer_default_invex(self, parser):
        """Test that 'mi', 'nuestro' don't automatically mean INVEX (BUG-07 fix)."""
        possessive_queries = [
            "mi IMOR",
            "mi cartera",
            "nuestro ICAP",
            "del banco",
            "mi banco",
        ]

        for query in possessive_queries:
            banks = parser._extract_banks_heuristic(query)
            # Possessive pronouns should NOT default to INVEX anymore
            assert "INVEX" not in [b.upper() for b in banks if b], \
                f"Possessive query '{query}' should NOT default to INVEX, got: {banks}"

    def test_bank_aliases_still_work(self, parser):
        """Test that explicit bank aliases still work correctly."""
        alias_tests = [
            ("IMOR del sistema", ["SISTEMA"]),
            ("morosidad sistema bancario", ["SISTEMA"]),
            ("cartera del mercado", ["SISTEMA"]),
        ]

        for query, expected_banks in alias_tests:
            banks = parser._extract_banks_heuristic(query)
            banks_upper = [b.upper() for b in banks if b]
            for expected in expected_banks:
                assert expected in banks_upper, \
                    f"Expected {expected} in {banks_upper} for query: {query}"


class TestInvexHardcodeRemoval:
    """Tests to verify INVEX hardcodes have been removed."""

    def test_default_questions_no_invex_hardcode(self):
        """Test that DEFAULT_BANK_ADVISOR_QUESTIONS don't hardcode INVEX."""
        import sys
        import os
        # This test works by checking the file content directly
        hints_file = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "apps", "web", "src", "components", "chat", "BankAdvisorHints.tsx"
        )

        if not os.path.exists(hints_file):
            pytest.skip("BankAdvisorHints.tsx not found")

        with open(hints_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Find DEFAULT_BANK_ADVISOR_QUESTIONS array
        match = re.search(
            r'export const DEFAULT_BANK_ADVISOR_QUESTIONS\s*=\s*\[(.*?)\];',
            content,
            re.DOTALL
        )

        if match:
            questions_block = match.group(1)
            # Count INVEX mentions in the default questions
            invex_count = questions_block.lower().count("invex")
            assert invex_count == 0, \
                f"DEFAULT_BANK_ADVISOR_QUESTIONS contains {invex_count} INVEX mentions (should be 0)"

    def test_bank_aliases_no_possessive_invex_mapping(self):
        """Test that BANK_ALIASES doesn't map possessives to INVEX."""
        import sys
        import os
        plugin_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "plugins", "bank-advisor-private", "src"
        )
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        from bankadvisor.services.query_spec_parser import QuerySpecParser

        possessive_aliases = ["mi banco", "del banco", "nuestro banco", "nuestro"]

        for alias in possessive_aliases:
            # These should NOT be in BANK_ALIASES anymore
            assert alias not in QuerySpecParser.BANK_ALIASES, \
                f"Possessive alias '{alias}' should not be in BANK_ALIASES"


class TestRuntimeConfigDefaults:
    """Tests for runtime config default behavior."""

    def test_apply_bank_default_is_false(self):
        """Test that apply_bank_default defaults to False for multi-tenant."""
        import sys
        import os
        plugin_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "plugins", "bank-advisor-private", "src"
        )
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        # Clear any cached instance
        from bankadvisor.runtime_config import RuntimeConfig
        RuntimeConfig._instance = None
        RuntimeConfig._config = {}

        from bankadvisor.runtime_config import get_runtime_config
        config = get_runtime_config()

        # With empty config, apply_bank_default should default to False
        # (for multi-tenant support)
        assert config.apply_bank_default == False, \
            "apply_bank_default should default to False for multi-tenant support"


class TestSistemaNote:
    """Tests for SISTEMA aggregation note (BUG-10 fix)."""

    def test_icap_has_sistema_note(self):
        """Test that ICAP metric has a SISTEMA aggregation note."""
        import sys
        import os
        plugin_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "plugins", "bank-advisor-private", "src"
        )
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        from bankadvisor.config_service import get_config
        config = get_config()

        # ICAP should have a sistema_note explaining it's a mean, not sum
        note = config.get_sistema_note("icap_total")
        assert note is not None, "ICAP should have a sistema_note"
        assert "promedio" in note.lower() or "mean" in note.lower(), \
            "ICAP sistema_note should mention it's an average"

    def test_tda_has_sistema_note(self):
        """Test that TDA metric has a SISTEMA aggregation note."""
        import sys
        import os
        plugin_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "plugins", "bank-advisor-private", "src"
        )
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)

        from bankadvisor.config_service import get_config
        config = get_config()

        # TDA should have a sistema_note explaining it's weighted average
        note = config.get_sistema_note("tda_cartera_total")
        assert note is not None, "TDA should have a sistema_note"
        assert "ponderado" in note.lower() or "weighted" in note.lower(), \
            "TDA sistema_note should mention it's a weighted average"
