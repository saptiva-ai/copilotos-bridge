#!/usr/bin/env python3
"""
Unit tests for production bug validators.
Run without backend to verify validators work correctly.

Run: python tests/e2e/regression/test_production_bugs_validators_unit.py
"""

import sys
from pathlib import Path

# Import validators from main test file
sys.path.insert(0, str(Path(__file__).parent))
from test_bug_2026_01_30_month_decimal_scope import (
    validate_date_value_association,
    validate_icap_range,
    validate_imor_range,
    validate_single_bank_scope,
    validate_limited_bank_scope,
    validate_no_bank_expansion,
    BugTestCase,
)


def test_month_001_good_data():
    """MONTH-001: Good data with dates should pass."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {
                        'name': 'BBVA',
                        'x': ['2025-01-01', '2025-02-01', '2025-03-01'],
                        'y': [19.19, 20.45, 20.18]
                    }
                ]
            },
            'bank_names': ['BBVA']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="MONTH-001",
        description="test",
        query="test",
        expected_behavior="test",
        validation_fn="validate_date_value_association",
        expected_keywords=['ICAP', 'BBVA']
    )

    passed, issues = validate_date_value_association(sse_data, tc)
    assert passed, f"Should pass with good data: {issues}"
    print("✅ MONTH-001: Good data passes")


def test_month_001_missing_dates():
    """MONTH-001: Missing dates should fail."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {
                        'name': 'BBVA',
                        'x': [],  # Missing dates!
                        'y': [19.19, 20.45, 20.18]
                    }
                ]
            },
            'bank_names': ['BBVA']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="MONTH-001",
        description="test",
        query="test",
        expected_behavior="test",
        validation_fn="validate_date_value_association"
    )

    passed, issues = validate_date_value_association(sse_data, tc)
    assert not passed, "Should fail with missing dates"
    assert any("missing x values" in i for i in issues)
    print("✅ MONTH-001: Missing dates detected")


def test_decimal_001_good_range():
    """DECIMAL-001: ICAP values in valid range should pass."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {'name': 'BBVA', 'x': ['2025-01-01'], 'y': [20.05]}
                ]
            },
            'bank_names': ['BBVA']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="DECIMAL-001",
        description="test",
        query="test",
        expected_behavior="test",
        validation_fn="validate_icap_range"
    )

    passed, issues = validate_icap_range(sse_data, tc)
    assert passed, f"Should pass with valid ICAP: {issues}"
    print("✅ DECIMAL-001: Valid ICAP range passes")


def test_decimal_001_x100_bug():
    """DECIMAL-001: ICAP value >100% should fail (x100 bug)."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {'name': 'BBVA', 'x': ['2025-01-01'], 'y': [2005.94]}  # x100 bug!
                ]
            },
            'bank_names': ['BBVA']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="DECIMAL-001",
        description="test",
        query="test",
        expected_behavior="test",
        validation_fn="validate_icap_range"
    )

    passed, issues = validate_icap_range(sse_data, tc)
    assert not passed, "Should fail with x100 bug"
    assert any("DECIMAL SHIFT" in i or "CRITICAL" in i for i in issues)
    print("✅ DECIMAL-001: x100 bug detected")


def test_scope_001_single_bank():
    """SCOPE-001: Single bank query should pass with 1-2 banks."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {'name': 'Citibanamex', 'x': ['2025-01-01'], 'y': [18.5]}
                ]
            },
            'bank_names': ['Citibanamex']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="SCOPE-001",
        description="test",
        query="Dame el ICAP de Citibanamex",
        expected_behavior="test",
        validation_fn="validate_single_bank_scope",
        expected_keywords=['ICAP', 'Citibanamex']
    )

    passed, issues = validate_single_bank_scope(sse_data, tc)
    assert passed, f"Should pass with single bank: {issues}"
    print("✅ SCOPE-001: Single bank passes")


def test_scope_001_expansion_bug():
    """SCOPE-001: Single bank query returning many banks should fail."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {'name': 'BBVA', 'x': ['2025-01-01'], 'y': [20.05]},
                    {'name': 'INVEX', 'x': ['2025-01-01'], 'y': [18.5]},
                    {'name': 'AZTECA', 'x': ['2025-01-01'], 'y': [15.2]},
                    {'name': 'AFIRME', 'x': ['2025-01-01'], 'y': [16.1]},
                ]
            },
            'bank_names': ['BBVA', 'INVEX', 'AZTECA', 'AFIRME', 'BANORTE', 'HSBC']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="SCOPE-001",
        description="test",
        query="Dame el ICAP de Citibanamex",
        expected_behavior="test",
        validation_fn="validate_single_bank_scope",
        expected_keywords=['ICAP', 'Citibanamex']
    )

    passed, issues = validate_single_bank_scope(sse_data, tc)
    assert not passed, "Should fail with scope expansion"
    assert any("SCOPE EXPANSION" in i for i in issues)
    print("✅ SCOPE-001: Scope expansion detected")


def test_scope_001_forbidden_banks():
    """SCOPE-001: Forbidden banks appearing should fail."""
    sse_data = {
        'bank_chart': {
            'plotly_config': {
                'data': [
                    {'name': 'Banorte', 'x': ['2025-01-01'], 'y': [17.5]},
                    {'name': 'INVEX', 'x': ['2025-01-01'], 'y': [18.5]},
                ]
            },
            'bank_names': ['Banorte', 'INVEX']
        },
        'content': ''
    }
    tc = BugTestCase(
        bug_id="SCOPE-001",
        description="test",
        query="Dame el IMOR de Banorte",
        expected_behavior="test",
        validation_fn="validate_no_bank_expansion",
        expected_keywords=['IMOR', 'Banorte'],
        forbidden_keywords=['INVEX', 'AZTECA']
    )

    passed, issues = validate_no_bank_expansion(sse_data, tc)
    assert not passed, "Should fail with forbidden bank"
    assert any("INVEX" in i for i in issues)
    print("✅ SCOPE-001: Forbidden bank detected")


def main():
    print("=" * 60)
    print("Validator Unit Tests - Production Bugs 2026-01-30")
    print("=" * 60)

    tests = [
        test_month_001_good_data,
        test_month_001_missing_dates,
        test_decimal_001_good_range,
        test_decimal_001_x100_bug,
        test_scope_001_single_bank,
        test_scope_001_expansion_bug,
        test_scope_001_forbidden_banks,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Error - {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed}/{passed + failed} passed")

    if failed == 0:
        print("✅ All validator unit tests PASSED!")
        return 0
    else:
        print("❌ Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
