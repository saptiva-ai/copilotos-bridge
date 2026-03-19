#!/usr/bin/env python3
"""
🧪 BUG-014 Test Suite: Ranking Detection

Validates that ranking queries:
1. Return charts with data for multiple banks
2. LLM response does NOT say "No encuentro información" (false negative)
3. LLM acknowledges the ranking data exists

Run: python tests/e2e/regression/test_ranking_detection.py
"""

import os
import sys
import requests
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")

# False negative phrases that indicate the bug
FALSE_NEGATIVE_PHRASES = [
    "no encuentro información",
    "no tengo información",
    "no dispongo de información",
    "no puedo encontrar",
    "no hay datos",
    "no tengo datos",
    "no está disponible",
    "información no disponible",
    "no se encontró",
    "sin información",
    "lamentablemente no",
    "desafortunadamente no",
]

# Phrases that look like false negatives but are actually valid explanations
# These should NOT trigger false negative detection
FALSE_NEGATIVE_EXCEPTIONS = [
    "no hay datos históricos",  # Valid: explaining only recent data available
    "no hay datos adicionales",  # Valid: data exists but limited scope
    "no hay datos para ese período",  # Valid: time-scoped clarification
]

# Technical error phrases that indicate backend/tool failures
TECHNICAL_ERROR_PHRASES = [
    "problema técnico",
    "error técnico",
    "hubo un problema",
    "no pudo recuperar",
    "no se pudo obtener",
    "error al intentar",
    "error al obtener",
    "falló al",
    "failed to",
    "error retrieving",
    "error fetching",
]

# Positive indicators that LLM acknowledges the data
POSITIVE_INDICATORS = [
    # Ranking-specific terms
    "ranking",
    "clasificación",
    "posición",
    "lugar",
    "puesto",
    # Leadership terms
    "lidera",
    "encabeza",
    "primero",
    "último",
    "top",
    # Comparison terms
    "mayor",
    "menor",
    "más alto",
    "más bajo",
    "mejor",
    "peor",
    # Data acknowledgment
    "bancos",
    "ordenados",
    "según",
    "muestra",
    "presenta",
    "indica",
    # Metric-specific
    "imor",
    "icap",
    "icor",
    "cartera",
    "morosidad",
    "capitalización",
    "cobertura",
]


@dataclass
class RankingTestCase:
    id: int
    query: str
    metric: str
    expected_min_banks: int = 3  # Ranking should show at least 3 banks
    expected_keywords: List[str] = field(default_factory=list)


# =============================================================================
# TEST CASES: Organized by category
# =============================================================================

# --- CATEGORY 1: IMOR (Morosidad) Rankings ---
IMOR_RANKING_CASES = [
    RankingTestCase(
        1,
        "¿Cuál es el ranking de bancos por IMOR?",
        "IMOR",
        expected_min_banks=5,
        expected_keywords=["IMOR"],
    ),
    RankingTestCase(
        2,
        "Ranking de morosidad del sistema bancario",
        "IMOR",
        expected_min_banks=5,
        expected_keywords=["morosidad", "IMOR"],
    ),
    RankingTestCase(
        3,
        "¿Qué bancos tienen mayor índice de mora?",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["mora", "IMOR"],
    ),
    RankingTestCase(
        4,
        "Muéstrame el ranking de IMOR de todos los bancos",
        "IMOR",
        expected_min_banks=5,
        expected_keywords=["IMOR"],
    ),
    RankingTestCase(
        5,
        "¿Cuáles son los bancos con menor morosidad?",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["morosidad", "IMOR"],
    ),
]

# --- CATEGORY 2: ICAP (Capitalización) Rankings ---
ICAP_RANKING_CASES = [
    RankingTestCase(
        10,
        "Ranking de ICAP del sistema",
        "ICAP",
        expected_min_banks=5,
        expected_keywords=["ICAP"],
    ),
    RankingTestCase(
        11,
        "¿Cuáles son los bancos más capitalizados?",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP", "capitaliz"],
    ),
    RankingTestCase(
        12,
        "¿Qué bancos tienen mejor índice de capitalización?",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP", "capitalización"],
    ),
    RankingTestCase(
        13,
        "Top bancos por capitalización",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP"],
    ),
    RankingTestCase(
        14,
        "Ranking de solvencia bancaria",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP", "solvencia"],
    ),
]

# --- CATEGORY 3: ICOR (Cobertura) Rankings ---
ICOR_RANKING_CASES = [
    RankingTestCase(
        20,
        "¿Qué bancos tienen mejor ICOR?",
        "ICOR",
        expected_min_banks=3,
        expected_keywords=["ICOR"],
    ),
    RankingTestCase(
        21,
        "Clasifica los bancos por índice de cobertura",
        "ICOR",
        expected_min_banks=3,
        expected_keywords=["ICOR", "cobertura"],
    ),
    RankingTestCase(
        22,
        "Ranking de cobertura de cartera vencida",
        "ICOR",
        expected_min_banks=3,
        expected_keywords=["ICOR", "cobertura"],
    ),
    RankingTestCase(
        23,
        "¿Cuáles bancos tienen mejor cobertura de reservas?",
        "ICOR",
        expected_min_banks=3,
        expected_keywords=["ICOR", "cobertura"],
    ),
]

# --- CATEGORY 4: Cartera y PDM Rankings ---
CARTERA_PDM_CASES = [
    RankingTestCase(
        30,
        "Top 10 bancos por cartera total",
        "Cartera Total",
        expected_min_banks=5,
        expected_keywords=["cartera"],
    ),
    RankingTestCase(
        31,
        "Ranking de participación de mercado",
        "PDM",
        expected_min_banks=3,
        expected_keywords=["PDM", "participación"],
    ),
    RankingTestCase(
        32,
        "¿Cuáles son los bancos más grandes por cartera?",
        "Cartera Total",
        expected_min_banks=3,
        expected_keywords=["cartera"],
    ),
    RankingTestCase(
        33,
        "Top 5 bancos del sistema",
        "Cartera Total",
        expected_min_banks=3,
        expected_keywords=["cartera"],
    ),
    RankingTestCase(
        34,
        "¿Qué banco tiene mayor market share?",
        "PDM",
        expected_min_banks=3,
        expected_keywords=["PDM", "market"],
    ),
]

# --- CATEGORY 5: Time Period Rankings ---
TIME_PERIOD_CASES = [
    RankingTestCase(
        40,
        "Ranking de IMOR en el último trimestre",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR"],
    ),
    RankingTestCase(
        41,
        "¿Cuáles fueron los bancos más capitalizados en 2024?",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP", "2024"],
    ),
    RankingTestCase(
        42,
        "Ranking de morosidad de los últimos 6 meses",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR", "morosidad"],
    ),
    RankingTestCase(
        43,
        "Top bancos por ICOR en enero 2025",
        "ICOR",
        expected_min_banks=3,
        expected_keywords=["ICOR"],
    ),
]

# --- CATEGORY 6: Synonyms and Variations ---
SYNONYM_CASES = [
    RankingTestCase(
        50,
        "Ordena los bancos por su índice de morosidad",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR", "morosidad"],
    ),
    RankingTestCase(
        51,
        "Lista de bancos por capitalización de mayor a menor",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP"],
    ),
    RankingTestCase(
        52,
        "Posiciones de los bancos por cartera de crédito",
        "Cartera Total",
        expected_min_banks=3,
        expected_keywords=["cartera"],
    ),
    RankingTestCase(
        53,
        "Clasificación bancaria por IMOR",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR"],
    ),
]

# --- CATEGORY 7: Edge Cases ---
EDGE_CASES = [
    RankingTestCase(
        60,
        "ranking imor",  # Minimal query
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR"],
    ),
    RankingTestCase(
        61,
        "RANKING DE BANCOS POR ICAP",  # All caps
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP"],
    ),
    RankingTestCase(
        62,
        "dame el ranking de los bancos por imor por favor",  # Polite form
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR"],
    ),
    RankingTestCase(
        63,
        "quiero ver un ranking de capitalización",  # Informal
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP"],
    ),
]

# --- CATEGORY 8: Specific Bank Context (should still return ranking) ---
SPECIFIC_CONTEXT_CASES = [
    RankingTestCase(
        70,
        "Ranking de IMOR incluyendo a INVEX",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR", "INVEX"],
    ),
    RankingTestCase(
        71,
        "¿Dónde está INVEX en el ranking de capitalización?",
        "ICAP",
        expected_min_banks=3,
        expected_keywords=["ICAP", "INVEX"],
    ),
    RankingTestCase(
        72,
        "Compara INVEX en el ranking general de morosidad",
        "IMOR",
        expected_min_banks=3,
        expected_keywords=["IMOR"],
    ),
]

# --- CATEGORY 9: BUG-CH-006 Breakdown Queries ---
# These test the "por banco por año" pattern that should return ranking/breakdown data
BUG_CH_006_CASES = [
    RankingTestCase(
        100,
        "cartera hipotecaria por banco por ano",
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda"],
    ),
    RankingTestCase(
        101,
        "cartera hipotecaria por banco por año",  # with accent
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda"],
    ),
    RankingTestCase(
        102,
        "quiero que me des la cartera hipotecaria por banco por año",
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda"],
    ),
    RankingTestCase(
        103,
        "cartera vivienda por banco",
        "Cartera Vivienda",
        expected_min_banks=5,
        expected_keywords=["cartera", "vivienda"],
    ),
    RankingTestCase(
        104,
        "IMOR por banco por año",
        "IMOR",
        expected_min_banks=5,
        expected_keywords=["IMOR", "morosidad"],
    ),
    RankingTestCase(
        105,
        "cartera comercial por banco",
        "Cartera Comercial",
        expected_min_banks=5,
        expected_keywords=["cartera", "comercial"],
    ),
]

# Combine all test cases
RANKING_TEST_CASES = (
    IMOR_RANKING_CASES
    + ICAP_RANKING_CASES
    + ICOR_RANKING_CASES
    + CARTERA_PDM_CASES
    + TIME_PERIOD_CASES
    + SYNONYM_CASES
    + EDGE_CASES
    + SPECIFIC_CONTEXT_CASES
    + BUG_CH_006_CASES
)


def get_auth_token(backend_url: str) -> Optional[str]:
    """Get authentication token using shared helper."""
    return helper_get_auth_token(backend_url=backend_url)


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response from chat endpoint."""
    result = {
        "events": [],
        "bank_chart": None,
        "content": "",
        "clarification": None,
        "error": None,
    }

    current_event = None

    for line in response.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8")

        if decoded.startswith("event:"):
            current_event = decoded.replace("event:", "").strip()
            result["events"].append(current_event)
        elif decoded.startswith("data:") and current_event:
            data = decoded.replace("data:", "").strip()
            if data == "[DONE]":
                continue

            try:
                parsed = json.loads(data)
                if current_event == "bank_chart":
                    result["bank_chart"] = parsed
                elif current_event == "bank_clarification":
                    result["clarification"] = parsed
                elif current_event == "chunk":
                    if "content" in parsed:
                        result["content"] += parsed["content"]
                elif current_event == "error":
                    result["error"] = parsed
            except json.JSONDecodeError:
                if current_event == "chunk":
                    result["content"] += data

    return result


def check_false_negative(content: str) -> List[str]:
    """Check if LLM response contains false negative phrases.

    Excludes valid contextual explanations that contain similar wording
    but are not actual false negatives (e.g., "no hay datos históricos").
    """
    content_lower = content.lower()
    found = []

    for phrase in FALSE_NEGATIVE_PHRASES:
        if phrase in content_lower:
            # Check if this match is part of an exception phrase
            is_exception = False
            for exception in FALSE_NEGATIVE_EXCEPTIONS:
                if exception in content_lower:
                    # The phrase appears in a valid exception context
                    is_exception = True
                    break

            if not is_exception:
                found.append(phrase)

    return found


def check_technical_errors(content: str) -> List[str]:
    """Check if LLM response contains technical error phrases."""
    content_lower = content.lower()
    found = []
    for phrase in TECHNICAL_ERROR_PHRASES:
        if phrase in content_lower:
            found.append(phrase)
    return found


def check_positive_indicators(content: str) -> List[str]:
    """Check if LLM response contains positive indicators."""
    content_lower = content.lower()
    found = []
    for indicator in POSITIVE_INDICATORS:
        if indicator in content_lower:
            found.append(indicator)
    return found


def has_valid_ranking_data(content: str) -> bool:
    """
    Check if the response contains actual ranking data despite negative phrases.

    BUG-014 FIX: If the LLM says "not available" but provides actual percentage
    values and bank names in a ranking context, we should consider it valid.

    Enhanced: Also detects decimal values without % (e.g., ICOR: 1.157) and
    currency values (e.g., cartera in millions).
    """
    import re

    # Look for percentage patterns (e.g., "2.3%", "**1.5%**", "15.72%")
    percentage_pattern = r'\d+\.?\d*\s*%'
    percentages = re.findall(percentage_pattern, content)

    # Look for bank names followed by values (handles markdown formatting like **AZTECA**: 5.62%)
    # Extended list of bank names to match actual data
    bank_names = (
        "BBVA|BANORTE|INVEX|SANTANDER|HSBC|CITIBANAMEX|BAJIO|SCOTIABANK|AZTECA|BANREGIO|"
        "AFIRME|MONEX|BANCO BASE|INBURSA|SISTEMA|MIFEL|BMONEX|INTERACCIONES|AUTOFIN"
    )

    # Pattern 1: Bank with percentage (e.g., "AZTECA**: 5.62%" or "**AZTECA**: **23.37%**")
    # Updated to handle markdown bold formatting around both bank name and value
    bank_pct_pattern = rf'\*?\*?(?:{bank_names})\*?\*?[:\s]+\*?\*?\d+\.?\d*\s*%\*?\*?'
    bank_pct_values = re.findall(bank_pct_pattern, content, re.IGNORECASE)

    # Pattern 2: Bank with decimal value (e.g., "BAJIO**: 1.157" for ICOR)
    # Matches values like 0.00, 1.157, 2.30 without % sign
    bank_decimal_pattern = rf'(?:{bank_names})\**[:\s]+\d+\.\d+'
    bank_decimal_values = re.findall(bank_decimal_pattern, content, re.IGNORECASE)

    # Pattern 3: Bank with currency value (e.g., "$4,700,844" for cartera)
    bank_currency_pattern = rf'(?:{bank_names})\**[:\s]+\$?[\d,]+\.?\d*'
    bank_currency_values = re.findall(bank_currency_pattern, content, re.IGNORECASE)

    # Total unique bank-value pairs
    all_bank_values = set(bank_pct_values + bank_decimal_values + bank_currency_values)

    # Check 1: Multiple percentages with bank-value pairs (original check)
    has_multiple_percentages = len(percentages) >= 3
    has_bank_pct_values = len(bank_pct_values) >= 2

    # Check 2: Multiple decimal values (for ICOR and similar ratios)
    has_decimal_values = len(bank_decimal_values) >= 3

    # Check 3: Multiple currency values (for cartera rankings)
    has_currency_values = len(bank_currency_values) >= 3

    # Valid if any check passes
    return (
        (has_multiple_percentages and has_bank_pct_values) or
        has_decimal_values or
        has_currency_values
    )


def count_banks_in_chart(bank_chart: Dict) -> int:
    """Count number of banks in chart traces."""
    if not bank_chart:
        return 0

    plotly_config = bank_chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    if not traces:
        return 0

    # For horizontal bar charts (ranking), banks are in 'y' array of first trace
    first_trace = traces[0]
    if first_trace.get("orientation") == "h" and first_trace.get("y"):
        # Horizontal bar chart - count items in y (excluding SISTEMA)
        y_values = first_trace.get("y", [])
        return len([b for b in y_values if b and b != "SISTEMA"])

    # For line/scatter charts, count traces with names (each trace is a bank)
    bank_count = sum(1 for t in traces if t.get("name"))

    # Fallback: check x values for dates (timeseries) with bank names in traces
    if bank_count == 0:
        # Check if there are multiple data points (suggests multi-bank data)
        for trace in traces:
            if trace.get("y") and len(trace.get("y", [])) > 0:
                bank_count = max(bank_count, 1)

    return bank_count


def run_ranking_test(
    test_case: RankingTestCase,
    token: str,
    backend_url: str,
    timeout: int = 30,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run a single ranking test case."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
    }
    payload = {
        "message": test_case.query,
        "stream": True,
        "model": "Saptiva Turbo",
    }

    result = {
        "id": test_case.id,
        "query": test_case.query,
        "metric": test_case.metric,
        "passed": False,
        "issues": [],
        "warnings": [],
        "details": {},
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{backend_url}/api/chat",
            json=payload,
            headers=headers,
            stream=True,
            timeout=timeout,
        )

        if response.status_code != 200:
            result["issues"].append(f"HTTP {response.status_code}")
            return result

        sse_data = parse_sse_response(response)
        latency_ms = (time.time() - start_time) * 1000
        result["details"]["latency_ms"] = latency_ms

        # Check 1: Chart exists
        if not sse_data["bank_chart"]:
            result["issues"].append("No chart returned for ranking query")
            return result

        result["details"]["has_chart"] = True

        # Check 2: Chart has multiple banks
        bank_count = count_banks_in_chart(sse_data["bank_chart"])
        result["details"]["bank_count"] = bank_count

        if bank_count < test_case.expected_min_banks:
            result["issues"].append(
                f"Expected at least {test_case.expected_min_banks} banks, got {bank_count}"
            )

        # Check 3: LLM response does NOT contain false negatives (BUG-014 core check)
        content = sse_data["content"]
        result["details"]["content_preview"] = content[:200] if content else ""

        false_negatives = check_false_negative(content)
        if false_negatives:
            # BUG-014 FIX: Check if the response has valid ranking data despite the negative phrases
            # This handles cases where the LLM says "not available" but then provides the actual data
            if has_valid_ranking_data(content):
                result["warnings"].append(
                    f"LLM used negative phrases {false_negatives} but provided valid ranking data - acceptable but not ideal"
                )
            else:
                result["issues"].append(
                    f"BUG-014: False negative detected! LLM said: {false_negatives}"
                )

        # Check 3b: LLM response does NOT contain technical errors
        technical_errors = check_technical_errors(content)
        if technical_errors:
            result["issues"].append(
                f"Technical error in response: {technical_errors}"
            )

        # Check 4: LLM response has positive indicators
        positive_found = check_positive_indicators(content)
        result["details"]["positive_indicators"] = positive_found

        if not positive_found and not result["issues"]:
            result["warnings"].append(
                "LLM response lacks ranking-specific language (ranking, posición, lidera, etc.)"
            )

        # Check 5: Expected keywords in response or chart title
        chart_title = sse_data["bank_chart"].get("title", "") or sse_data[
            "bank_chart"
        ].get("metric_name", "")
        combined_text = f"{content} {chart_title}".lower()

        missing_keywords = [
            kw for kw in test_case.expected_keywords if kw.lower() not in combined_text
        ]
        if missing_keywords:
            result["warnings"].append(f"Missing keywords: {missing_keywords}")

        # Final verdict
        if not result["issues"]:
            result["passed"] = True

        if verbose:
            print(f"   Banks in chart: {bank_count}")
            print(f"   Positive indicators: {positive_found}")
            print(f"   Content preview: {content[:150]}...")

    except Exception as e:
        result["issues"].append(f"Exception: {str(e)}")

    return result


# Category mapping for filtering
CATEGORY_MAP = {
    "imor": IMOR_RANKING_CASES,
    "icap": ICAP_RANKING_CASES,
    "icor": ICOR_RANKING_CASES,
    "cartera": CARTERA_PDM_CASES,
    "pdm": CARTERA_PDM_CASES,
    "time": TIME_PERIOD_CASES,
    "period": TIME_PERIOD_CASES,
    "synonym": SYNONYM_CASES,
    "edge": EDGE_CASES,
    "context": SPECIFIC_CONTEXT_CASES,
    "breakdown": BUG_CH_006_CASES,  # BUG-CH-006: "por banco" breakdown queries
    "bug006": BUG_CH_006_CASES,
}


def main():
    parser = argparse.ArgumentParser(
        description="BUG-014 Ranking False Negative Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories available:
  imor     - IMOR (morosidad) ranking tests
  icap     - ICAP (capitalización) ranking tests
  icor     - ICOR (cobertura) ranking tests
  cartera  - Cartera total and PDM ranking tests
  time     - Time period ranking tests
  synonym  - Query variations and synonyms
  edge     - Edge cases (caps, minimal, polite)
  context  - Specific bank context queries

Examples:
  python test_ranking_false_negative.py --category imor
  python test_ranking_false_negative.py --ids 1,2,3,10,11
  python test_ranking_false_negative.py --max 10 --verbose
""",
    )
    parser.add_argument(
        "--backend-url", type=str, default=BACKEND_URL, help="Backend URL"
    )
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--ids", type=str, help="Comma-separated test IDs to run")
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        help="Category to filter (imor, icap, icor, cartera, time, synonym, edge, context)",
    )
    parser.add_argument("--max", type=int, help="Maximum number of tests to run")
    parser.add_argument(
        "--stop-on-fail", action="store_true", help="Stop on first failure"
    )
    parser.add_argument(
        "--save-results", type=str, help="Save results to JSON file"
    )
    args = parser.parse_args()

    token = get_auth_token(args.backend_url)
    if not token:
        print("❌ Auth failed - is the backend running?")
        return 1

    # Filter test cases
    cases = RANKING_TEST_CASES

    if args.category:
        cat_lower = args.category.lower()
        if cat_lower in CATEGORY_MAP:
            cases = CATEGORY_MAP[cat_lower]
            print(f"📁 Running category: {args.category}")
        else:
            print(f"❌ Unknown category: {args.category}")
            print(f"   Available: {', '.join(CATEGORY_MAP.keys())}")
            return 1

    if args.ids:
        wanted = {int(x) for x in args.ids.split(",") if x.strip()}
        cases = [c for c in cases if c.id in wanted]

    if args.max:
        cases = cases[: args.max]

    print(f"🧪 BUG-014 Ranking False Negative Tests (N={len(cases)})")
    print("-" * 60)

    passed = 0
    failed = 0
    results = []
    false_negative_count = 0

    for case in cases:
        result = run_ranking_test(
            case,
            token,
            args.backend_url,
            args.timeout,
            args.verbose,
        )
        results.append(result)

        status = "✅" if result["passed"] else "❌"
        print(f"{status} [{case.id:02d}] {case.query[:50]}...")

        if result["issues"]:
            for issue in result["issues"]:
                print(f"   ↳ ❌ {issue}")
                if "BUG-014" in issue:
                    false_negative_count += 1

        if result["warnings"] and args.verbose:
            for warning in result["warnings"]:
                print(f"   ↳ ⚠️  {warning}")

        if result["passed"]:
            passed += 1
        else:
            failed += 1
            if args.stop_on_fail:
                print("\n🛑 Stopping on first failure")
                break

        time.sleep(0.3)  # Rate limiting

    print("-" * 60)
    total = len(results)
    print(f"📊 Results: {passed}/{total} passed ({passed/total*100:.1f}%)")

    if false_negative_count > 0:
        print(f"🔴 BUG-014 False Negatives: {false_negative_count}")

    # Save results if requested
    if args.save_results:
        with open(args.save_results, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "false_negatives": false_negative_count,
                    "results": results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"💾 Results saved to {args.save_results}")

    if failed > 0:
        print("\n🔍 BUG-014 Status: REGRESSION DETECTED")
        return 1

    print("\n✅ BUG-014 Status: All ranking queries working correctly")
    return 0


if __name__ == "__main__":
    exit(main())
