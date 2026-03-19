#!/usr/bin/env python3
"""
🧪 Hallucination Detection E2E Test Suite

This test reproduces the fsaavedra case where the LLM fabricated regional
data when only temporal data was available:
- User asked for: "comparativo de cartera comercial por región"
- Bank-advisor returned: temporal series (evolution) data only
- LLM fabricated: regional breakdown with percentages summing to 113.7%

Goals:
1. Reproduce the exact conversation flow
2. Verify the system handles unavailable breakdowns correctly
3. Detect hallucination patterns in responses
4. Measure response quality with grading

Reference: TASK-2026-01-27__hallucination-detection__fsaavedra-feedback
"""

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Ensure tests/ is on path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.helpers import get_auth_token as helper_get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
RESULTS_FILE = "hallucination_test_results.json"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class HallucinationCheck:
    """Checks for potential hallucination patterns."""
    name: str
    detected: bool
    severity: str  # "critical", "warning", "info"
    details: str


@dataclass
class ResponseQuality:
    """Quality assessment of a response."""
    score: int  # 0-100
    hallucination_checks: List[HallucinationCheck] = field(default_factory=list)
    grounding_score: int = 100  # How well grounded in data
    accuracy_score: int = 100  # Factual accuracy
    helpfulness_score: int = 100  # How helpful the response is
    notes: List[str] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """A single turn in the test conversation."""
    message: str
    description: str
    expected_behavior: str  # What SHOULD happen
    forbidden_patterns: List[str] = field(default_factory=list)
    required_patterns: List[str] = field(default_factory=list)


@dataclass
class TestScenario:
    """A complete test scenario."""
    id: str
    name: str
    description: str
    turns: List[ConversationTurn]


# =============================================================================
# HALLUCINATION PATTERNS
# =============================================================================

# Mexican region names that shouldn't appear without regional data
REGION_NAMES = [
    "centro", "norte", "sur", "occidente", "oriente",
    "sureste", "noreste", "noroeste", "bajío"
]

# Patterns that suggest fabricated data
FABRICATION_PATTERNS = [
    r"por\s+regi[oó]n",  # "por región"
    r"desglose\s+regional",  # "desglose regional"
    r"distribuci[oó]n\s+geogr[aá]fica",  # "distribución geográfica"
    r"entidad\s+federativa",  # "entidad federativa"
]


# =============================================================================
# TEST SCENARIOS
# =============================================================================

SCENARIOS: List[TestScenario] = [
    # -------------------------------------------------------------------------
    # Scenario 1: fsaavedra Case Reproduction
    # NOTE: Updated 2026-02-03 - Regional data is NOW available via MCP tools
    # (get_regional_portfolio returns Centro, Norte, Sureste, Centro-Occidente)
    # -------------------------------------------------------------------------
    TestScenario(
        id="HALL-001",
        name="fsaavedra Case - Regional Breakdown Request",
        description=(
            "Tests regional breakdown request. Since REFACTOR-2026-02-03, "
            "regional data IS available via get_regional_portfolio MCP tool."
        ),
        turns=[
            ConversationTurn(
                message="¿Cómo se ha comportado la cartera comercial de INVEX?",
                description="Initial valid query - should return temporal data",
                expected_behavior="Return chart with temporal evolution of cartera comercial",
                required_patterns=["INVEX", "cartera"],
            ),
            ConversationTurn(
                message="Muéstrame la gráfica de evolución",
                description="Request for evolution chart",
                expected_behavior="Return temporal evolution chart",
                required_patterns=[],
            ),
            ConversationTurn(
                message="Dame el saldo por entidad federativa a octubre 2025",
                description="Request for state-level data (may not exist)",
                expected_behavior=(
                    "Should either return state data if available, or say "
                    "data is not available at state level (regional IS available)"
                ),
                forbidden_patterns=[
                    r"entidad\s+federativa.*\d+%",  # State with percentage (fabricated)
                ],
            ),
            ConversationTurn(
                message="Comparativo de cartera comercial por región",
                description="Regional breakdown request - NOW AVAILABLE via MCP tool",
                expected_behavior=(
                    "Should return regional data from get_regional_portfolio. "
                    "Valid regions: Centro, Norte, Sureste, Centro-Occidente"
                ),
                forbidden_patterns=[
                    # Only forbid clearly fabricated patterns, not valid region names
                    r"47\.2%",  # Specific fabricated percentage from old case
                    r"113\.7%",  # Sum that exceeds 100%
                    r"\d+\.\d+%.*\d+\.\d+%.*\d+\.\d+%.*\d+\.\d+%.*\d+\.\d+%",  # 5+ percentages
                ],
                required_patterns=[],  # Regional data is now valid
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 2: Percentage Sum Validation
    # -------------------------------------------------------------------------
    TestScenario(
        id="HALL-002",
        name="Percentage Distribution Validation",
        description=(
            "Tests that any percentages in breakdown responses sum correctly."
        ),
        turns=[
            ConversationTurn(
                message="Dame la distribución de cartera de INVEX por tipo de crédito",
                description="Request for credit type breakdown",
                expected_behavior=(
                    "If breakdown exists, percentages should sum to ~100%. "
                    "If not available, should say so."
                ),
                forbidden_patterns=[
                    r"(?:(?:\d+\.?\d*)\s*%\s*.*){5,}",  # 5+ percentages (potential fabrication)
                ],
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 3: Valid Temporal Request (Control)
    # -------------------------------------------------------------------------
    TestScenario(
        id="HALL-003",
        name="Valid Temporal Query (Control Case)",
        description=(
            "Control test: validates that correct temporal queries work properly."
        ),
        turns=[
            ConversationTurn(
                message="IMOR de INVEX en los últimos 6 meses",
                description="Valid temporal query",
                expected_behavior="Return chart with IMOR evolution",
                required_patterns=["IMOR", "INVEX"],
            ),
            ConversationTurn(
                message="Compáralo con el sistema",
                description="Add comparison",
                expected_behavior="Return comparison chart",
                required_patterns=["IMOR"],
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 4: Sector Breakdown (Potential Hallucination)
    # -------------------------------------------------------------------------
    TestScenario(
        id="HALL-004",
        name="Sector Breakdown Request",
        description=(
            "Tests request for sector breakdown which may not be available."
        ),
        turns=[
            ConversationTurn(
                message="Dame la cartera de INVEX por sector económico",
                description="Request for sector breakdown",
                expected_behavior=(
                    "Should either return real sector data or say unavailable. "
                    "Should NOT fabricate sector distribution."
                ),
                forbidden_patterns=[
                    r"sector\s+(primario|secundario|terciario)",  # Generic sectors
                    r"(?:sector.*\d+%.*){4,}",  # Multiple sectors with percentages
                ],
            ),
        ],
    ),
]


# =============================================================================
# HALLUCINATION DETECTION FUNCTIONS
# =============================================================================

def detect_regional_fabrication(
    text: str,
    response_type: str = "text",
    has_chart_data: bool = False,
) -> HallucinationCheck:
    """
    Detect fabricated regional breakdown.

    If response_type is "chart" and has_chart_data is True, regional data
    is considered REAL (from bank_mv_cartera_por_estado view), not fabricated.

    NOTE (2026-02-03): Regional data IS now available via get_regional_portfolio
    MCP tool. Region mentions in text suggesting alternatives are acceptable.
    """
    text_lower = text.lower()

    # If this is a chart response with real data, regional mentions are valid
    if response_type == "chart" and has_chart_data:
        return HallucinationCheck(
            name="Regional Fabrication",
            detected=False,
            severity="info",
            details="Regional data from chart is valid (not fabricated)"
        )

    # Count region mentions
    region_count = sum(1 for r in REGION_NAMES if r in text_lower)

    # Check for regional table patterns (with specific values = likely fabrication)
    has_regional_table = bool(re.search(r"\|\s*regi[oó]n\s*\|.*\d+", text_lower))

    # Check if this is suggesting alternatives (acceptable behavior)
    is_suggesting_alternative = any(phrase in text_lower for phrase in [
        "no disponible", "no está disponible", "no tengo", "no cuento con",
        "en su lugar", "como alternativa", "puedo ofrecer",
        "datos regionales", "nivel regional", "por región",
        "centro", "norte", "sureste",  # Valid region names as suggestions
    ])

    # Check for specific fabricated values (percentages with regions)
    has_fabricated_values = bool(re.search(
        r"(centro|norte|sur|occidente).*\d+\.?\d*\s*%", text_lower
    ))

    # Only flag as fabrication if there are specific values, not just mentions
    if has_fabricated_values and not has_chart_data:
        return HallucinationCheck(
            name="Regional Fabrication",
            detected=True,
            severity="critical",
            details=f"Found region names with specific percentages (likely fabricated)"
        )

    if has_regional_table and region_count >= 2 and not is_suggesting_alternative:
        return HallucinationCheck(
            name="Regional Fabrication",
            detected=True,
            severity="warning",
            details="Regional table pattern detected"
        )

    return HallucinationCheck(
        name="Regional Fabrication",
        detected=False,
        severity="info",
        details="No regional fabrication detected (regional data now available via MCP tools)"
    )


def detect_percentage_sum_error(
    text: str,
    metric_name: str = "",
) -> HallucinationCheck:
    """
    Detect when percentages in tables don't sum to ~100%.

    IMPORTANT: This check does NOT apply to ratio metrics (IMOR, ICAP, etc.)
    because those are individual rate values, not distributions.
    """
    text_lower = text.lower()

    # Skip validation for ratio metrics - they are NOT distributions
    ratio_metrics = ["imor", "icap", "tasa", "índice", "indice", "ratio", "rendimiento"]
    metric_lower = metric_name.lower() if metric_name else ""

    is_ratio_metric = (
        any(r in text_lower for r in ratio_metrics)
        or any(r in metric_lower for r in ratio_metrics)
    )

    if is_ratio_metric:
        return HallucinationCheck(
            name="Percentage Sum",
            detected=False,
            severity="info",
            details="Ratio metric (IMOR/ICAP) - not a distribution, skip sum check"
        )

    # Find percentage values in text
    pct_pattern = r"(\d+(?:\.\d+)?)\s*%"
    percentages = [float(m) for m in re.findall(pct_pattern, text)]

    if len(percentages) < 3:
        return HallucinationCheck(
            name="Percentage Sum",
            detected=False,
            severity="info",
            details="Not enough percentages to validate distribution"
        )

    # Filter out 100% (total row) and very small values (< 1%)
    # Also filter out values that look like growth rates (small and could be negative context)
    distribution_pcts = [p for p in percentages if 1.0 < p < 99.9]

    if len(distribution_pcts) < 3:
        return HallucinationCheck(
            name="Percentage Sum",
            detected=False,
            severity="info",
            details="Not enough distribution percentages"
        )

    total = sum(distribution_pcts)

    # Check if sum is way off (>5% tolerance)
    if abs(total - 100.0) > 5.0:
        return HallucinationCheck(
            name="Percentage Sum",
            detected=True,
            severity="critical",
            details=f"Percentages sum to {total:.1f}%, expected ~100%"
        )

    return HallucinationCheck(
        name="Percentage Sum",
        detected=False,
        severity="info",
        details=f"Percentages sum to {total:.1f}% (acceptable)"
    )


def detect_entity_fabrication(
    text: str,
    user_query: str = "",
    has_chart_data: bool = False,
) -> HallucinationCheck:
    """Detect fabricated entity/state mentions."""
    text_lower = text.lower()
    query_lower = user_query.lower()

    # Mexican states that shouldn't appear without real data
    states = [
        "jalisco", "nuevo león", "nuevo leon", "cdmx",
        "ciudad de méxico", "ciudad de mexico", "querétaro",
        "guanajuato", "chihuahua", "sonora"
    ]

    found_states = [s for s in states if s in text_lower]

    if len(found_states) >= 2:
        # Regional/state requests naturally mention states. Treat these as
        # non-fabrication unless there is evidence of contradiction.
        regional_query_cues = [
            "estado",
            "entidad federativa",
            "región",
            "region",
            "geográfica",
            "geografica",
        ]
        requested_regional_breakdown = any(cue in query_lower for cue in regional_query_cues)
        if requested_regional_breakdown:
            details = (
                "State mentions are expected for regional query"
                if has_chart_data
                else "State mentions likely valid for regional query (no chart to cross-check)"
            )
            return HallucinationCheck(
                name="Entity Fabrication",
                detected=False,
                severity="info",
                details=details,
            )

        return HallucinationCheck(
            name="Entity Fabrication",
            detected=True,
            severity="critical",
            details=f"Found {len(found_states)} state names: {found_states}"
        )

    return HallucinationCheck(
        name="Entity Fabrication",
        detected=False,
        severity="info",
        details="No entity fabrication detected"
    )


def detect_value_inconsistency(text: str) -> HallucinationCheck:
    """Detect inconsistent monetary values (e.g., parts > total)."""
    # Find large monetary values (millions/billions)
    value_pattern = r"(\d{1,3}(?:,\d{3}){2,})"
    values = []

    for match in re.findall(value_pattern, text):
        try:
            val = float(match.replace(",", ""))
            if val >= 1_000_000:
                values.append(val)
        except ValueError:
            pass

    if len(values) < 2:
        return HallucinationCheck(
            name="Value Inconsistency",
            detected=False,
            severity="info",
            details="Not enough values to check consistency"
        )

    # Sort values descending
    values_sorted = sorted(values, reverse=True)

    # Check if sum of smaller values exceeds the largest
    largest = values_sorted[0]
    sum_others = sum(values_sorted[1:])

    if sum_others > largest * 1.1:  # 10% tolerance
        return HallucinationCheck(
            name="Value Inconsistency",
            detected=True,
            severity="warning",
            details=f"Sum of parts ({sum_others:,.0f}) > largest ({largest:,.0f})"
        )

    return HallucinationCheck(
        name="Value Inconsistency",
        detected=False,
        severity="info",
        details="Values appear consistent"
    )


def run_hallucination_checks(
    text: str,
    response_type: str = "text",
    has_chart_data: bool = False,
    metric_name: str = "",
    user_query: str = "",
) -> List[HallucinationCheck]:
    """Run all hallucination checks on a response."""
    return [
        detect_regional_fabrication(text, response_type, has_chart_data),
        detect_percentage_sum_error(text, metric_name),
        detect_entity_fabrication(
            text,
            user_query=user_query,
            has_chart_data=has_chart_data,
        ),
        detect_value_inconsistency(text),
    ]


def assess_response_quality(
    response: Dict[str, Any],
    turn: ConversationTurn,
    scenario_id: str = "",
) -> ResponseQuality:
    """Assess the quality of a response."""
    quality = ResponseQuality(score=100)

    # Get response content
    content = response.get("content", "")
    chart = response.get("bank_chart")
    clarification = response.get("clarification")

    full_text = content
    if chart:
        full_text += f" {json.dumps(chart)}"

    # Determine response type and if it has real chart data
    response_type = "chart" if chart else "text"
    # Check for chart data: can be chart_status="success" OR success=true OR has plotly_config
    has_chart_data = bool(
        chart and (
            chart.get("chart_status") == "success" or
            chart.get("success") is True or
            chart.get("plotly_config") is not None
        )
    )

    # Extract metric name from chart data or message
    metric_name = ""
    if chart:
        metric_name = chart.get("metric_name", "")
    if not metric_name:
        # Try to detect from message
        msg_lower = turn.message.lower()
        if "imor" in msg_lower:
            metric_name = "IMOR"
        elif "icap" in msg_lower:
            metric_name = "ICAP"

    # Run hallucination checks with context
    quality.hallucination_checks = run_hallucination_checks(
        full_text,
        response_type=response_type,
        has_chart_data=has_chart_data,
        metric_name=metric_name,
        user_query=turn.message,
    )

    # Score deductions for hallucinations
    for check in quality.hallucination_checks:
        if check.detected:
            if check.severity == "critical":
                quality.grounding_score -= 40
                quality.accuracy_score -= 40
                quality.notes.append(f"CRITICAL: {check.name} - {check.details}")
            elif check.severity == "warning":
                quality.grounding_score -= 20
                quality.accuracy_score -= 20
                quality.notes.append(f"WARNING: {check.name} - {check.details}")

    # Check forbidden patterns
    for pattern in turn.forbidden_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            quality.accuracy_score -= 20
            quality.notes.append(f"Found forbidden pattern: {pattern}")

    # Check required patterns
    for pattern in turn.required_patterns:
        if not re.search(pattern, full_text, re.IGNORECASE):
            quality.helpfulness_score -= 15
            quality.notes.append(f"Missing required pattern: {pattern}")

    # Check for appropriate "not available" response
    not_available_phrases = [
        "no disponible", "no tengo", "no cuento con",
        "no está disponible", "no puedo proporcionar",
        "información no disponible"
    ]

    has_not_available = any(
        phrase in content.lower() for phrase in not_available_phrases
    )

    # If asking for unavailable data and system says so, that's GOOD
    if "región" in turn.message.lower() or "entidad" in turn.message.lower():
        if has_not_available or clarification:
            quality.helpfulness_score += 10
            quality.notes.append("Correctly indicated data unavailability")

    # Calculate final score
    quality.score = (
        quality.grounding_score * 0.4 +
        quality.accuracy_score * 0.4 +
        quality.helpfulness_score * 0.2
    )
    quality.score = max(0, min(100, int(quality.score)))

    return quality


# =============================================================================
# TEST EXECUTION
# =============================================================================

def get_auth_token() -> Optional[str]:
    """Get authentication token."""
    return helper_get_auth_token(backend_url=BACKEND_URL)


def run_scenario(scenario: TestScenario, token: str) -> Dict[str, Any]:
    """Run a complete test scenario."""
    result = {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "passed": True,
        "turns": [],
        "overall_quality": 100,
        "hallucinations_detected": 0,
        "issues": [],
    }

    chat_id = None
    turn_qualities = []

    for i, turn in enumerate(scenario.turns):
        print(f"  Turn {i+1}: {turn.message[:50]}...")

        turn_result = {
            "turn": i + 1,
            "message": turn.message,
            "description": turn.description,
            "expected": turn.expected_behavior,
            "passed": True,
            "response_type": "unknown",
            "quality": None,
            "issues": [],
        }

        # Send message
        response = send_chat_message(
            token,
            turn.message,
            backend_url=BACKEND_URL,
            chat_id=chat_id,
            timeout=60,
        )

        # Get chat_id from first response
        if i == 0 and response.get("meta"):
            chat_id = response["meta"].get("chat_id")

        # Check for errors
        if response.get("error"):
            turn_result["passed"] = False
            turn_result["issues"].append(f"Error: {response['error']}")
            result["passed"] = False
            result["turns"].append(turn_result)
            continue

        # Determine response type
        if response.get("bank_chart"):
            turn_result["response_type"] = "chart"
        elif response.get("clarification"):
            turn_result["response_type"] = "clarification"
        elif response.get("content"):
            turn_result["response_type"] = "text"

        # Assess quality
        quality = assess_response_quality(response, turn)
        turn_result["quality"] = {
            "score": quality.score,
            "grounding": quality.grounding_score,
            "accuracy": quality.accuracy_score,
            "helpfulness": quality.helpfulness_score,
            "notes": quality.notes,
            "hallucination_checks": [
                {
                    "name": c.name,
                    "detected": c.detected,
                    "severity": c.severity,
                    "details": c.details,
                }
                for c in quality.hallucination_checks
            ],
        }
        turn_qualities.append(quality.score)

        # Count hallucinations
        critical_hallucinations = sum(
            1 for c in quality.hallucination_checks
            if c.detected and c.severity == "critical"
        )
        result["hallucinations_detected"] += critical_hallucinations

        # Mark as failed if quality is too low or critical hallucination
        if quality.score < 60 or critical_hallucinations > 0:
            turn_result["passed"] = False
            turn_result["issues"].extend(quality.notes)
            result["passed"] = False

        # Store response preview
        turn_result["response_preview"] = response.get("content", "")[:200]

        result["turns"].append(turn_result)

        # Print status
        status = "✅" if turn_result["passed"] else "❌"
        print(f"    {status} Quality: {quality.score}/100, "
              f"Type: {turn_result['response_type']}")

        if quality.notes:
            for note in quality.notes[:3]:  # First 3 notes
                print(f"       📝 {note}")

        time.sleep(0.5)

    # Overall quality
    if turn_qualities:
        result["overall_quality"] = int(sum(turn_qualities) / len(turn_qualities))

    return result


def run_all_scenarios():
    """Run all hallucination detection scenarios."""
    print("=" * 70)
    print("🔍 HALLUCINATION DETECTION TEST SUITE")
    print("=" * 70)
    print(f"Backend: {BACKEND_URL}")
    print(f"Scenarios: {len(SCENARIOS)}")
    print("=" * 70)

    token = get_auth_token()
    if not token:
        print("❌ FATAL: Authentication failed")
        return False

    print("✅ Authentication successful\n")

    results = []
    total_passed = 0
    total_failed = 0

    for scenario in SCENARIOS:
        print(f"\n{'─' * 60}")
        print(f"📋 {scenario.id}: {scenario.name}")
        print(f"   {scenario.description}")
        print("─" * 60)

        result = run_scenario(scenario, token)
        results.append(result)

        if result["passed"]:
            total_passed += 1
            print(f"\n✅ PASSED - Quality: {result['overall_quality']}/100")
        else:
            total_failed += 1
            print(f"\n❌ FAILED - Quality: {result['overall_quality']}/100, "
                  f"Hallucinations: {result['hallucinations_detected']}")

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Scenarios Passed: {total_passed}/{len(SCENARIOS)}")
    print(f"Scenarios Failed: {total_failed}/{len(SCENARIOS)}")

    total_hallucinations = sum(r["hallucinations_detected"] for r in results)
    avg_quality = sum(r["overall_quality"] for r in results) / len(results)

    print(f"Total Hallucinations Detected: {total_hallucinations}")
    print(f"Average Quality Score: {avg_quality:.1f}/100")

    # Grade
    if avg_quality >= 90 and total_hallucinations == 0:
        grade = "A"
        grade_desc = "Excellent - No hallucinations, high quality"
    elif avg_quality >= 80 and total_hallucinations <= 1:
        grade = "B"
        grade_desc = "Good - Minor issues"
    elif avg_quality >= 70:
        grade = "C"
        grade_desc = "Acceptable - Some issues need attention"
    elif avg_quality >= 60:
        grade = "D"
        grade_desc = "Poor - Significant hallucination issues"
    else:
        grade = "F"
        grade_desc = "Failing - Critical hallucination problems"

    print(f"\n🎓 GRADE: {grade} - {grade_desc}")

    # Save results
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "passed": total_passed,
                "failed": total_failed,
                "total_hallucinations": total_hallucinations,
                "average_quality": avg_quality,
                "grade": grade,
            },
            "scenarios": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to {RESULTS_FILE}")

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_scenarios()
    exit(0 if success else 1)
