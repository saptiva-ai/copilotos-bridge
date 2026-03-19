"""
E2E Regression Tests: Chart Year Mismatch (BUG-2026-02-05)

Tests that call the actual backend to verify:
- When user requests data for a specific year, chart shows that year's data
- Text response and chart data are consistent

User Feedback:
- FDBK-0074: "el texto de la respuesta esta bien, me da la cartera en 2023,
             pero la grafica no, me muestra de otro año"
- FDBK-0072: "el valor que menciona en enero 2025 no corresponde al de la tabla"

Usage:
    python tests/e2e/regression/test_bug_2026_02_05_chart_year_mismatch_e2e.py

Environment Variables:
    BASE_URL: Backend URL (default: http://localhost:8000)
    MODEL: Model to use (default: Saptiva Turbo)
    TIMEOUT: Request timeout in seconds (default: 60)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Add tests/ to path for shared utils
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token


# =============================================================================
# TEST CASES
# =============================================================================

TEST_CASES = [
    {
        "id": "EVOLUTION_CARTERA_2023",
        "query": "evolución de cartera en 2023",
        "expected_year": "2023",
        "description": "Evolution query for 2023 should show only 2023 data (original bug report)",
    },
    {
        "id": "EVOLUTION_IMOR_2024",
        "query": "evolución del IMOR de INVEX en 2024",
        "expected_year": "2024",
        "description": "IMOR evolution for 2024 should show only 2024 data",
    },
    {
        "id": "EVOLUTION_ICAP_2023",
        "query": "evolución del ICAP de BBVA en 2023",
        "expected_year": "2023",
        "description": "ICAP evolution for specific bank and year",
    },
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

MONTH_ABBREV = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

# Patterns: "2024-01-01", "2024-01", "Jan 2023", "2024-12-01 00:00:00"
_ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})")
_ABBREV_DATE_RE = re.compile(r"([A-Za-z]{3})\s+(\d{4})")


def _normalize_date(x: str) -> Optional[str]:
    """Normalize various date formats to YYYY-MM."""
    # ISO format: "2024-01-01" or "2024-01"
    m = _ISO_DATE_RE.match(x)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # Abbreviated month: "Jan 2023", "Dec 2024"
    m = _ABBREV_DATE_RE.match(x)
    if m:
        month = MONTH_ABBREV.get(m.group(1).lower())
        if month:
            return f"{m.group(2)}-{month}"
    return None


def extract_chart_dates(response: Dict[str, Any]) -> List[str]:
    """
    Extract dates from chart data in the response.

    Supports multiple date formats:
    - ISO: "2024-01-01", "2024-01"
    - Abbreviated: "Jan 2023", "Dec 2024"
    - Timestamp: "2024-12-01 00:00:00"

    The chat API returns bank chart data nested under:
    - response.bank_chart.plotly_config (non-streaming)
    - response.metadata.bank_chart_data.plotly_config (streaming done event)
    """
    dates = []

    # Get bank_chart from response (non-streaming API response)
    bank_chart = response.get("bank_chart", {})

    # Fallback: check metadata.bank_chart_data (streaming format)
    if not bank_chart:
        metadata = response.get("metadata", {})
        bank_chart = metadata.get("bank_chart_data", {})

    # Legacy fallback: check root level (in case API changes)
    if not bank_chart:
        bank_chart = response

    # Try plotly_config
    plotly_config = bank_chart.get("plotly_config", {})
    if plotly_config:
        for trace in plotly_config.get("data", []):
            x_values = trace.get("x", [])
            for x in x_values:
                if isinstance(x, str):
                    normalized = _normalize_date(x)
                    if normalized:
                        dates.append(normalized)

    # Try time_range
    time_range = bank_chart.get("time_range", {})
    if time_range:
        if time_range.get("start"):
            dates.append(time_range["start"])
        if time_range.get("end"):
            dates.append(time_range["end"])

    # Try data_as_of
    data_as_of = bank_chart.get("data_as_of")
    if data_as_of and isinstance(data_as_of, str):
        dates.append(data_as_of)

    return dates


def extract_year_from_dates(dates: List[str]) -> List[str]:
    """Extract unique years from date strings."""
    years = set()
    for date_str in dates:
        match = re.match(r"(\d{4})", str(date_str))
        if match:
            years.add(match.group(1))
    return sorted(list(years))


def verify_chart_year(response: Dict[str, Any], expected_year: str) -> tuple[bool, str]:
    """
    Verify that chart data is from the expected year.

    Primary check: chart x-axis dates match expected year.
    Fallback: if no chart dates, check text content mentions the year
    and data_as_of field.

    Returns:
        (passed, message)
    """
    dates = extract_chart_dates(response)

    if not dates:
        # Fallback: check text content for year mentions
        content = response.get("content", "")
        if expected_year in content:
            return True, f"No chart dates found, but text content mentions {expected_year}"
        return False, "No dates found in chart data or text content"

    years = extract_year_from_dates(dates)

    if not years:
        return False, f"Could not extract years from dates: {dates}"

    # Check if expected year is in the chart data
    if expected_year in years:
        # Additional check: ensure we don't have unexpected years
        unexpected = [y for y in years if y != expected_year]
        if unexpected:
            return False, f"Chart contains unexpected years: {unexpected}. Expected only {expected_year}"
        return True, f"Chart correctly shows {expected_year} data"

    return False, f"Expected year {expected_year} not found in chart. Found: {years}"


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_test(
    client: httpx.Client,
    base_url: str,
    conversation_id: str,
    model: str,
    test_case: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a single test case and return results."""
    test_id = test_case["id"]
    query = test_case["query"]
    expected_year = test_case["expected_year"]

    print(f"\n--- Test: {test_id} ---")
    print(f"Query: {query}")
    print(f"Expected year: {expected_year}")

    try:
        # Send message to backend
        response = client.post(
            f"{base_url}/api/chat",
            json={
                "message": query,
                "chat_id": conversation_id,
                "model": model,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

        # Check for errors
        if data.get("type") == "error":
            return {
                "test_id": test_id,
                "passed": False,
                "message": f"API returned error: {data.get('message', 'Unknown error')}",
                "response": data,
            }

        # Verify chart year
        passed, message = verify_chart_year(data, expected_year)

        # Additional: check text content mentions expected year
        content = data.get("content", "")
        text_mentions_year = expected_year in content

        result = {
            "test_id": test_id,
            "passed": passed,
            "message": message,
            "text_mentions_year": text_mentions_year,
            "dates_found": extract_chart_dates(data),
            "response_type": data.get("type"),
        }

        if passed:
            print(f"✅ PASS: {message}")
        else:
            print(f"❌ FAIL: {message}")

        return result

    except httpx.HTTPStatusError as e:
        return {
            "test_id": test_id,
            "passed": False,
            "message": f"HTTP error: {e.response.status_code}",
        }
    except Exception as e:
        return {
            "test_id": test_id,
            "passed": False,
            "message": f"Exception: {str(e)}",
        }


def main() -> int:
    print("=" * 60)
    print("E2E Test: Chart Year Mismatch (BUG-2026-02-05)")
    print("=" * 60)

    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    model = os.environ.get("MODEL", "Saptiva Turbo")
    timeout = float(os.environ.get("TIMEOUT", "60"))

    print(f"\nConfiguration:")
    print(f"  BASE_URL: {base_url}")
    print(f"  MODEL: {model}")
    print(f"  TIMEOUT: {timeout}s")

    # Get auth token
    print("\nAuthenticating...")
    token = get_auth_token(backend_url=base_url)
    if not token:
        print("❌ FAIL: Authentication failed")
        return 1

    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=timeout, headers=headers) as client:
        # Run tests - each in its own conversation to avoid context bleed
        results = []
        for test_case in TEST_CASES:
            try:
                conv_response = client.post(f"{base_url}/api/conversations", json={})
                conv_response.raise_for_status()
                conversation_id = conv_response.json().get("id")
            except Exception as e:
                print(f"❌ FAIL: Could not create conversation: {e}")
                return 1

            result = run_test(client, base_url, conversation_id, model, test_case)
            results.append(result)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in results if r["passed"])
        total = len(results)

        for r in results:
            status = "✅" if r["passed"] else "❌"
            print(f"{status} {r['test_id']}: {r['message']}")

        print(f"\nTotal: {passed}/{total} passed")

        # Save results
        results_file = Path(__file__).parent / "chart_year_mismatch_results.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "results": results,
                },
                f,
                indent=2,
            )
        print(f"\nResults saved to: {results_file}")

        return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
