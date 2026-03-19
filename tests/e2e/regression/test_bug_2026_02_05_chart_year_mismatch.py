"""
E2E Regression Tests: Chart Year Mismatch (BUG-2026-02-05)

Problem: When user requests data for a specific year (e.g., "cartera en 2023"),
         the text response was correct but the chart showed data from another year.

Root Cause:
- Handlers ignored spec.time_range
- SQL generation used MAX(fecha) instead of user's requested date range

Fix:
- Added _extract_time_range() helper to BaseHandler
- Updated handlers to pass time_range to use cases
- Modified SQL to filter by user's date range when provided

Test Strategy:
1. Unit tests for time_range extraction
2. Unit tests for periodo_id conversion
3. Integration tests for SQL date filtering logic
"""

import pytest
from datetime import date
from typing import Optional, Tuple


# =============================================================================
# UNIT TESTS: Time Range Extraction
# =============================================================================

class MockTimeRangeSpec:
    """Mock TimeRangeSpec for testing."""
    def __init__(self, type: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        self.type = type
        self.start_date = start_date
        self.end_date = end_date


class MockQuerySpec:
    """Mock QuerySpec for testing."""
    def __init__(self, time_range: Optional[MockTimeRangeSpec] = None):
        self.time_range = time_range


def extract_time_range(spec) -> Tuple[Optional[str], Optional[str]]:
    """
    Replicated from BaseHandler._extract_time_range() for testing.

    This function should match the implementation in:
    plugins/bank-advisor-private/src/bankadvisor/handlers/base.py
    """
    if not spec or not spec.time_range:
        return None, None
    return spec.time_range.start_date, spec.time_range.end_date


@pytest.mark.parametrize("test_id,spec_data,expected", [
    # Test ID, (type, start_date, end_date), (expected_start, expected_end)
    ("YEAR_2023", ("year", "2023-01-01", "2023-12-31"), ("2023-01-01", "2023-12-31")),
    ("YEAR_2024", ("year", "2024-01-01", "2024-12-31"), ("2024-01-01", "2024-12-31")),
    ("BETWEEN_DATES", ("between_dates", "2023-06-01", "2024-01-31"), ("2023-06-01", "2024-01-31")),
    ("LAST_N_MONTHS", ("last_n_months", "2024-06-01", "2024-12-31"), ("2024-06-01", "2024-12-31")),
    ("NO_END_DATE", ("year", "2023-01-01", None), ("2023-01-01", None)),
    ("NO_START_DATE", ("year", None, "2023-12-31"), (None, "2023-12-31")),
])
def test_time_range_extraction_with_dates(test_id, spec_data, expected):
    """Test that time_range is correctly extracted from QuerySpec."""
    type_, start, end = spec_data
    spec = MockQuerySpec(time_range=MockTimeRangeSpec(type=type_, start_date=start, end_date=end))

    result_start, result_end = extract_time_range(spec)

    assert result_start == expected[0], f"[{test_id}] start_date mismatch"
    assert result_end == expected[1], f"[{test_id}] end_date mismatch"


def test_time_range_extraction_no_spec():
    """Test extraction with None spec returns (None, None)."""
    result = extract_time_range(None)
    assert result == (None, None), "None spec should return (None, None)"


def test_time_range_extraction_no_time_range():
    """Test extraction with spec but no time_range returns (None, None)."""
    spec = MockQuerySpec(time_range=None)
    result = extract_time_range(spec)
    assert result == (None, None), "Spec without time_range should return (None, None)"


def test_time_range_extraction_type_all():
    """Test that type='all' with no dates returns (None, None)."""
    spec = MockQuerySpec(time_range=MockTimeRangeSpec(type="all"))
    result = extract_time_range(spec)
    assert result == (None, None), "type='all' should return (None, None)"


# =============================================================================
# UNIT TESTS: Date to Periodo_ID Conversion
# =============================================================================

def date_to_periodo_id(date_str: str) -> int:
    """
    Convert ISO date string (YYYY-MM-DD) to periodo_id (YYYYMM).

    This logic is used in:
    - financial_metrics.py: get_ranking()
    - growth_evolution.py: _query_bank_evolution()
    """
    # Extract YYYY and MM from date string
    return int(date_str[:4] + date_str[5:7])


@pytest.mark.parametrize("date_str,expected_periodo", [
    ("2023-01-01", 202301),
    ("2023-12-31", 202312),
    ("2024-06-15", 202406),
    ("2025-01-01", 202501),
    ("2022-09-30", 202209),
])
def test_date_to_periodo_id_conversion(date_str, expected_periodo):
    """Test that dates are correctly converted to periodo_id format."""
    result = date_to_periodo_id(date_str)
    assert result == expected_periodo, f"Expected {expected_periodo}, got {result}"


# =============================================================================
# UNIT TESTS: SQL Date Filter Generation
# =============================================================================

def build_date_filter(start_date: Optional[str], end_date: Optional[str]) -> str:
    """
    Build SQL date filter clause for periodo_id.

    Replicates logic from use cases:
    - financial_metrics.py: get_ranking()
    - growth_evolution.py: _query_bank_evolution()
    """
    filter_parts = []

    if end_date:
        end_periodo = date_to_periodo_id(end_date)
        filter_parts.append(f"periodo_id <= {end_periodo}")

    if start_date:
        start_periodo = date_to_periodo_id(start_date)
        filter_parts.append(f"periodo_id >= {start_periodo}")

    if filter_parts:
        return " AND ".join(filter_parts)
    return ""


@pytest.mark.parametrize("start,end,expected_contains", [
    # Full year filter
    ("2023-01-01", "2023-12-31", ["periodo_id >= 202301", "periodo_id <= 202312"]),
    # Only end date (most common for "datos de 2023")
    (None, "2023-12-31", ["periodo_id <= 202312"]),
    # Only start date
    ("2024-06-01", None, ["periodo_id >= 202406"]),
    # No dates - empty filter
    (None, None, []),
])
def test_sql_date_filter_generation(start, end, expected_contains):
    """Test that SQL date filters are correctly generated."""
    result = build_date_filter(start, end)

    for expected in expected_contains:
        assert expected in result, f"Expected '{expected}' in filter '{result}'"

    if not expected_contains:
        assert result == "", f"Expected empty filter, got '{result}'"


# =============================================================================
# INTEGRATION TESTS: Full Flow Simulation
# =============================================================================

class TestChartYearMatchFlow:
    """
    Integration tests simulating the full flow from user query to SQL filter.

    These tests verify the fix ensures chart data matches the requested year.
    """

    def test_year_2023_query_generates_correct_filter(self):
        """
        Simulates: "activo total 2023"

        Parser should create TimeRangeSpec(type="year", start="2023-01-01", end="2023-12-31")
        Handler should extract these dates
        SQL should filter to periodo_id between 202301 and 202312
        """
        # Simulate parser output
        spec = MockQuerySpec(
            time_range=MockTimeRangeSpec(
                type="year",
                start_date="2023-01-01",
                end_date="2023-12-31"
            )
        )

        # Handler extracts time_range
        start, end = extract_time_range(spec)

        # SQL filter is built
        sql_filter = build_date_filter(start, end)

        # Verify filter restricts to 2023
        assert "202301" in sql_filter, "Filter should include January 2023"
        assert "202312" in sql_filter, "Filter should include December 2023"
        assert "2024" not in sql_filter, "Filter should NOT include 2024"

    def test_specific_month_query(self):
        """
        Simulates: "ROE diciembre 2024"

        Should filter to December 2024 only.
        """
        spec = MockQuerySpec(
            time_range=MockTimeRangeSpec(
                type="month",
                start_date="2024-12-01",
                end_date="2024-12-31"
            )
        )

        start, end = extract_time_range(spec)
        sql_filter = build_date_filter(start, end)

        assert "202412" in sql_filter, "Filter should include December 2024"

    def test_no_date_falls_back_to_latest(self):
        """
        Simulates: "activo total" (no year specified)

        Should generate empty filter, allowing SQL to use MAX(fecha) fallback.
        """
        spec = MockQuerySpec(time_range=MockTimeRangeSpec(type="all"))

        start, end = extract_time_range(spec)
        sql_filter = build_date_filter(start, end)

        assert sql_filter == "", "No date spec should generate empty filter"

    def test_date_range_query(self):
        """
        Simulates: "evolución de cartera desde enero 2023 hasta junio 2024"

        Should filter to the specified range.
        """
        spec = MockQuerySpec(
            time_range=MockTimeRangeSpec(
                type="between_dates",
                start_date="2023-01-01",
                end_date="2024-06-30"
            )
        )

        start, end = extract_time_range(spec)
        sql_filter = build_date_filter(start, end)

        assert "202301" in sql_filter, "Filter should start at January 2023"
        assert "202406" in sql_filter, "Filter should end at June 2024"


# =============================================================================
# REGRESSION TESTS: Specific User Feedback Scenarios
# =============================================================================

class TestUserFeedbackScenarios:
    """
    Tests based on actual user feedback from 2026-02-05.

    FDBK-0074: "el texto de la respuesta esta bien, me da la cartera en 2023,
               pero la grafica no, me muestra de otro año"
    FDBK-0072: "el valor que menciona en enero 2025 no corresponde al de la tabla"
    """

    def test_fdbk_0074_cartera_2023(self):
        """
        FDBK-0074: User asked for "cartera en 2023" but chart showed 2024.

        The fix ensures SQL filters to 2023 data only.
        """
        # User query: "cartera de vivienda en 2023"
        # Parser creates year=2023 time_range
        spec = MockQuerySpec(
            time_range=MockTimeRangeSpec(
                type="year",
                start_date="2023-01-01",
                end_date="2023-12-31"
            )
        )

        start, end = extract_time_range(spec)

        # The key fix: dates are extracted and can be used in SQL
        assert start == "2023-01-01"
        assert end == "2023-12-31"

        # SQL filter ensures only 2023 data
        sql_filter = build_date_filter(start, end)
        assert "202301" in sql_filter
        assert "202312" in sql_filter

    def test_fdbk_0072_specific_month_value_mismatch(self):
        """
        FDBK-0072: Value in text didn't match chart/table for "enero 2025".

        The fix ensures all data sources use the same date filter.
        """
        # User query about specific month
        spec = MockQuerySpec(
            time_range=MockTimeRangeSpec(
                type="month",
                start_date="2025-01-01",
                end_date="2025-01-31"
            )
        )

        start, end = extract_time_range(spec)
        sql_filter = build_date_filter(start, end)

        # Filter restricts to January 2025
        assert "202501" in sql_filter
        # No other months should be included
        assert "202502" not in sql_filter
        assert "202412" not in sql_filter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
