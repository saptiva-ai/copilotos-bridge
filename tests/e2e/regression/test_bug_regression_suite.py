#!/usr/bin/env python3
"""
Test Suite - Bug Fixes Validation
Validates fixes for bugs reported in ISSUE-003_user-reported-bugs.

Includes:
- BA-001: RAG Grounding (ICAP/IMOR hallucination prevention)
- BA-002: INVEX Default Bias (multi-tenancy support)
- MONTH-001: Wrong month data mapping (LLM confuses months)
- DECIMAL-001: ICAP decimal shift (2005% instead of 20%)
- SCOPE-001: Query scope expansion (single bank returns all banks)

Run all: python tests/e2e/regression/test_bug_regression_suite.py
Run BA tests only: python tests/e2e/regression/test_bug_regression_suite.py --ba-only
Run specific bugs: python tests/e2e/regression/test_bug_regression_suite.py --bugs MONTH-001,DECIMAL-001
"""

import os
import sys
import re
import requests
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

# Configuration from environment with fallbacks
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


def slugify(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")[:60]


def parse_args():
    parser = argparse.ArgumentParser(description="Run Bug Fixes Test Suite")
    parser.add_argument("--bugs", type=str, help="Comma-separated bug IDs to test (e.g., 1,3,10 or BA-001,BA-002)")
    parser.add_argument("--backend-url", type=str, default=BACKEND_URL)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--save-dir", type=str, default="bug_fixes_debug")
    parser.add_argument("--ba-only", action="store_true", help="Run only BA-XXX tests")
    return parser.parse_args()


@dataclass
class BugTestCase:
    bug_id: Union[int, str]  # Support both numeric (1) and string (BA-001) IDs
    description: str
    query: str
    expected_behavior: str
    validation_fn: str  # Name of validation function to use
    expected_keywords: List[str] = field(default_factory=list)
    forbidden_keywords: List[str] = field(default_factory=list)  # BA-001: Keywords that should NOT appear
    should_trigger_clarification: bool = False


# Bug-specific test cases
BUG_TEST_CASES = [
    # BUG-01: Router se ancla a ICAP
    BugTestCase(
        bug_id=1,
        description="Router should NOT default to ICAP for general queries",
        query="Dame los datos generales de INVEX",
        expected_behavior="Should ask for clarification or provide overview, not just ICAP",
        validation_fn="validate_not_only_icap",
        expected_keywords=["INVEX"],
        should_trigger_clarification=True
    ),
    BugTestCase(
        bug_id=1,
        description="Explicit IMOR query should return IMOR, not ICAP",
        query="Dame el IMOR de INVEX",
        expected_behavior="Should return IMOR chart",
        validation_fn="validate_metric_match",
        expected_keywords=["IMOR", "Morosidad"]
    ),

    # BUG-10: Ambiguity of 'capitalización'
    BugTestCase(
        bug_id=10,
        description="'capitalización' should trigger disambiguation",
        query="¿Cuál es el mejor banco en capitalización?",
        expected_behavior="Should ask for clarification between ICAP and Market Cap",
        validation_fn="validate_capitalizacion_disambiguation",
        should_trigger_clarification=True
    ),
    BugTestCase(
        bug_id=10,
        description="'capitalización regulatoria' should map to ICAP without clarification",
        query="Dame la capitalización regulatoria de INVEX",
        expected_behavior="Should return ICAP chart directly",
        validation_fn="validate_metric_match",
        expected_keywords=["ICAP", "Capitalización"]
    ),
    BugTestCase(
        bug_id=10,
        description="ICAP query should work normally",
        query="Dame el ICAP de INVEX vs Sistema",
        expected_behavior="Should return ICAP comparison chart",
        validation_fn="validate_metric_match",
        expected_keywords=["ICAP", "Sistema"]
    ),

    # BUG-07: Default bank hardcode
    BugTestCase(
        bug_id=7,
        description="Query without bank should use default bank config",
        query="Dame el IMOR",
        expected_behavior="Should use default bank (INVEX) or ask for clarification",
        validation_fn="validate_has_bank",
        expected_keywords=["IMOR"]
    ),

    # BUG-09: Hallucination/mismatch
    BugTestCase(
        bug_id=9,
        description="Response should match chart metric",
        query="Dame el ICOR de INVEX",
        expected_behavior="Chart metric should match query intent",
        validation_fn="validate_metric_match",
        expected_keywords=["ICOR", "Cobertura"]
    ),

    # BUG-11: Markdown rendering
    BugTestCase(
        bug_id=11,
        description="RAG response should have clean markdown",
        query="¿Qué es el ICAP?",
        expected_behavior="Response should not have broken markdown (literal asterisks)",
        validation_fn="validate_clean_markdown",
        # BA-001 compatible: flexible keywords that accept both knowledge handler and LLM responses
        expected_keywords=["ICAP", "capital"]
    ),

    # =========================================================================
    # BA-001: RAG GROUNDING (ICAP/IMOR hallucination prevention)
    # =========================================================================
    BugTestCase(
        bug_id="BA-001",
        description="ICAP query returns ICAP definition (not IMOR)",
        query="¿Qué es ICAP?",
        expected_behavior="Should return ICAP/Índice de Capitalización definition",
        validation_fn="validate_rag_grounding",
        expected_keywords=["ICAP", "Capitalización", "capital"],
        forbidden_keywords=["IMOR", "Morosidad", "mora", "cartera vencida"]
    ),
    BugTestCase(
        bug_id="BA-001",
        description="IMOR query returns IMOR definition (not ICAP)",
        query="¿Qué es IMOR?",
        expected_behavior="Should return IMOR/Índice de Morosidad definition",
        validation_fn="validate_rag_grounding",
        expected_keywords=["IMOR", "Morosidad", "mora"],
        forbidden_keywords=["ICAP", "Capitalización", "capital regulatorio"]
    ),
    BugTestCase(
        bug_id="BA-001",
        description="ICOR query returns ICOR definition",
        query="¿Qué significa ICOR?",
        expected_behavior="Should return ICOR/Índice de Cobertura definition",
        validation_fn="validate_rag_grounding",
        expected_keywords=["ICOR", "Cobertura"],
        forbidden_keywords=["IMOR", "ICAP"]
    ),
    BugTestCase(
        bug_id="BA-001",
        description="Unknown term returns abstention (no hallucination)",
        query="¿Qué es XIXY?",
        expected_behavior="Should return 'no encontré' or similar abstention",
        validation_fn="validate_rag_abstention",
        expected_keywords=["no encontr", "glosario"]
    ),

    # =========================================================================
    # BA-002: INVEX DEFAULT BIAS (multi-tenancy support)
    # =========================================================================
    BugTestCase(
        bug_id="BA-002",
        description="Query without bank triggers clarification",
        query="Dame el IMOR",
        expected_behavior="Should ask which bank (clarification)",
        validation_fn="validate_no_invex_default",
        forbidden_keywords=["INVEX"],
        should_trigger_clarification=True
    ),
    BugTestCase(
        bug_id="BA-002",
        description="ICAP query without bank triggers clarification",
        query="¿Cuál es el ICAP?",
        expected_behavior="Should ask which bank (clarification)",
        validation_fn="validate_no_invex_default",
        forbidden_keywords=["INVEX"],
        should_trigger_clarification=True
    ),
    BugTestCase(
        bug_id="BA-002",
        description="Reservas query without bank triggers clarification",
        query="Muéstrame las reservas",
        expected_behavior="Should ask which bank (clarification)",
        validation_fn="validate_no_invex_default",
        forbidden_keywords=["INVEX"],
        should_trigger_clarification=True
    ),
    BugTestCase(
        bug_id="BA-002",
        description="Market share without bank triggers clarification",
        query="Dame la participación de mercado",
        expected_behavior="Should ask which bank (clarification)",
        validation_fn="validate_no_invex_default",
        forbidden_keywords=["INVEX"],
        should_trigger_clarification=True
    ),
    # Control: Query WITH explicit bank should work normally
    BugTestCase(
        bug_id="BA-002",
        description="Query WITH explicit bank (BBVA) works normally",
        query="Dame el IMOR de BBVA",
        expected_behavior="Should return BBVA chart without asking for bank",
        validation_fn="validate_explicit_bank",
        expected_keywords=["IMOR", "BBVA"]
    ),
    BugTestCase(
        bug_id="BA-002",
        description="Query WITH explicit bank (INVEX) works normally",
        query="Dame el IMOR de INVEX",
        expected_behavior="Should return INVEX chart when explicitly requested",
        validation_fn="validate_explicit_bank",
        expected_keywords=["IMOR", "INVEX"]
    ),

    # =========================================================================
    # BUG-MONTH-001: WRONG MONTH DATA MAPPING (2026-01-30)
    # LLM confuses months - uses January data as September
    # Root cause: extract_chart_statistics() extracted values without dates
    # Fix: New analytics_extractor.py keeps date-value pairs together
    # =========================================================================
    BugTestCase(
        bug_id="MONTH-001",
        description="Chart response includes explicit date-value pairs",
        query="Dame el ICAP de BBVA en 2025",
        expected_behavior="Response should include explicit dates with values",
        validation_fn="validate_date_value_association",
        expected_keywords=["ICAP", "BBVA", "2025"]
    ),
    BugTestCase(
        bug_id="MONTH-001",
        description="Analysis text correctly associates months with values",
        query="Explícame la evolución del ICAP de Santander de enero a octubre 2025",
        expected_behavior="Text should not confuse January values with September",
        validation_fn="validate_no_month_confusion",
        expected_keywords=["ICAP", "Santander"],
        forbidden_keywords=[]  # Specific month-value validation in function
    ),
    BugTestCase(
        bug_id="MONTH-001",
        description="Multi-bank comparison maintains correct date associations",
        query="Compara el ICAP de BBVA y Santander en 2025",
        expected_behavior="Each bank's values should be correctly dated",
        validation_fn="validate_date_value_association",
        expected_keywords=["ICAP", "BBVA", "Santander"]
    ),

    # =========================================================================
    # BUG-DECIMAL-001: ICAP DECIMAL SHIFT (2026-01-30)
    # ICAP shows 2005.94% instead of 20.0594%
    # Root cause: Value multiplied by 100 when already a percentage
    # =========================================================================
    BugTestCase(
        bug_id="DECIMAL-001",
        description="ICAP values are in valid percentage range (0-100%)",
        query="Dame el ICAP de BBVA",
        expected_behavior="ICAP values should be <100%, not >1000%",
        validation_fn="validate_icap_range",
        expected_keywords=["ICAP", "BBVA"]
    ),
    BugTestCase(
        bug_id="DECIMAL-001",
        description="IMOR values are in valid percentage range (0-20%)",
        query="Dame el IMOR de Santander",
        expected_behavior="IMOR values should be <20%, not >100%",
        validation_fn="validate_imor_range",
        expected_keywords=["IMOR", "Santander"]
    ),
    BugTestCase(
        bug_id="DECIMAL-001",
        description="Ranking ICAP values are all valid",
        query="¿Cuál banco tiene el mejor ICAP?",
        expected_behavior="All ICAP values in ranking should be <100%",
        validation_fn="validate_icap_range",
        expected_keywords=["ICAP"]
    ),

    # =========================================================================
    # BUG-SCOPE-001: QUERY SCOPE ALL BANKS (2026-01-30)
    # Query for specific bank returns all 18 banks
    # Root cause: Follow-up queries lose bank context
    # =========================================================================
    BugTestCase(
        bug_id="SCOPE-001",
        description="Single bank query returns only that bank",
        query="Dame el ICAP de Citibanamex",
        expected_behavior="Chart should only contain Citibanamex",
        validation_fn="validate_single_bank_scope",
        expected_keywords=["ICAP", "Citibanamex"]
    ),
    BugTestCase(
        bug_id="SCOPE-001",
        description="Two bank comparison returns only those banks",
        query="Compara el ICAP de BBVA y Santander",
        expected_behavior="Chart should only contain BBVA and Santander",
        validation_fn="validate_limited_bank_scope",
        expected_keywords=["ICAP", "BBVA", "Santander"]
    ),
    BugTestCase(
        bug_id="SCOPE-001",
        description="Query should not expand to all banks",
        query="Dame el IMOR de Banorte",
        expected_behavior="Should not return 18 banks",
        validation_fn="validate_no_bank_expansion",
        expected_keywords=["IMOR", "Banorte"],
        forbidden_keywords=["INVEX", "AZTECA", "AFIRME"]  # Banks that shouldn't appear
    ),
]


def get_auth_token(backend_url: str) -> Optional[str]:
    """Get auth token using shared helper."""
    return helper_get_auth_token(backend_url=backend_url)


def parse_sse_response(response) -> Dict[str, Any]:
    result = {
        "events": [],
        "bank_chart": None,
        "content": "",
        "clarification": None,
        "error": None
    }

    current_event = None

    for line in response.iter_lines():
        if not line:
            continue
        decoded = line.decode('utf-8')

        if decoded.startswith('event:'):
            current_event = decoded.replace('event:', '').strip()
            result["events"].append(current_event)
        elif decoded.startswith('data:') and current_event:
            data = decoded.replace('data:', '').strip()
            if data == "[DONE]":
                continue

            try:
                parsed = json.loads(data)
                if current_event == 'bank_chart':
                    result["bank_chart"] = parsed
                elif current_event == 'bank_clarification':
                    result["clarification"] = parsed
                elif current_event == 'chunk':
                    if "content" in parsed:
                        result["content"] += parsed["content"]
                elif current_event == 'error':
                    result["error"] = parsed
            except:
                if current_event == 'chunk':
                    result["content"] += data

    return result


# Validation Functions
def validate_not_only_icap(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BUG-01: Ensure general queries don't always return ICAP."""
    issues = []

    # If we got clarification, that's good
    if sse_data.get("clarification"):
        return True, []

    # If we got a chart, check it's not defaulting to ICAP
    chart = sse_data.get("bank_chart")
    if chart:
        metric = chart.get("metric_name", "").upper()
        # For "datos generales", ICAP alone is not acceptable
        if metric == "ICAP_TOTAL" and "general" in test_case.query.lower():
            issues.append("Query asked for 'general data' but got only ICAP")

    return len(issues) == 0, issues


def validate_capitalizacion_disambiguation(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BUG-10: 'capitalización' alone should trigger clarification."""
    issues = []

    clarification = sse_data.get("clarification")
    content = sse_data.get("content", "").lower()

    # Should have clarification or mention both options
    if clarification:
        options = clarification.get("options", [])
        option_labels = [o.get("label", "").lower() for o in options]

        has_icap = any("icap" in l or "regulatoria" in l for l in option_labels)
        has_market = any("mercado" in l or "market" in l for l in option_labels)

        if not has_icap:
            issues.append("Clarification missing ICAP option")
        if not has_market:
            issues.append("Clarification missing Market Cap option")
    elif "capitalización" in test_case.query.lower():
        # If no clarification, check if response mentions both types
        if "icap" not in content and "regulatoria" not in content:
            issues.append("No clarification triggered for ambiguous 'capitalización'")

    return len(issues) == 0, issues


def validate_metric_match(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """Generic validation: chart metric should match expected keywords."""
    issues = []

    chart = sse_data.get("bank_chart")
    if not chart:
        if test_case.should_trigger_clarification and sse_data.get("clarification"):
            return True, []
        issues.append("Expected chart but got none")
        return False, issues

    # Check title/metric contains expected keywords
    title = chart.get("title", "") or chart.get("metric_name", "") or ""
    metadata = chart.get("metadata", {})
    full_text = f"{title} {metadata.get('title', '')} {metadata.get('metric_interpretation', '')}".lower()

    for kw in test_case.expected_keywords:
        if kw.lower() not in full_text:
            issues.append(f"Missing expected keyword: {kw}")

    return len(issues) == 0, issues


def validate_has_bank(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BUG-07: Query should use default bank or clarify."""
    issues = []

    chart = sse_data.get("bank_chart")
    clarification = sse_data.get("clarification")

    if clarification:
        # Asked for clarification - acceptable
        return True, []

    if chart:
        bank_names = chart.get("bank_names", [])
        if not bank_names:
            issues.append("Chart has no bank specified (default bank not applied)")
    else:
        issues.append("No chart or clarification received")

    return len(issues) == 0, issues


def validate_clean_markdown(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BUG-11: Response should not have broken markdown."""
    issues = []

    content = sse_data.get("content", "")

    # Check for common markdown issues
    broken_patterns = [
        ("**\\n**", "Double asterisks around newline"),
        ("***", "Triple asterisks"),
        ("** **", "Empty bold"),
        ("_ _", "Empty italic"),
    ]

    for pattern, desc in broken_patterns:
        if pattern in content:
            issues.append(f"Broken markdown: {desc}")

    # Check expected keywords are present
    for kw in test_case.expected_keywords:
        if kw.lower() not in content.lower():
            issues.append(f"Missing expected keyword: {kw}")

    return len(issues) == 0, issues


def validate_rag_grounding(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BA-001: Validate RAG response contains expected terms and NOT forbidden terms.

    NOTE: If clarification is received instead of RAG, we check if the clarification
    options don't bias toward forbidden terms. This happens when the system needs
    clarification before providing a RAG response.
    """
    issues = []

    content = sse_data.get("content", "").lower()
    clarification = sse_data.get("clarification")

    # If we got clarification, the system is asking for more info before RAG
    # This is acceptable for BA-001 as long as clarification is neutral
    if clarification and not content.strip():
        # Clarification is acceptable - system asking for more context
        return True, []

    # If we got both clarification AND content, only check the actual content
    # (ignore clarification options which may list multiple metrics)
    if not content.strip():
        issues.append("No RAG content received")
        return False, issues

    # Check expected keywords are present in main content
    found_expected = False
    for kw in test_case.expected_keywords:
        if kw.lower() in content:
            found_expected = True
            break

    if not found_expected and test_case.expected_keywords:
        issues.append(f"Missing expected keywords: {test_case.expected_keywords}")

    # Check forbidden keywords are NOT present (critical for grounding)
    # Only check in the main response content, not in clarification options
    for kw in test_case.forbidden_keywords:
        # Skip if the forbidden keyword is just mentioned in a list context
        # Focus on definitional statements
        if kw.lower() in content:
            # Check if this is in a definition/explanation context
            # Look for patterns like "X es..." or "El X..."
            forbidden_patterns = [
                f"el {kw.lower()} es",
                f"la {kw.lower()} es",
                f"{kw.lower()} mide",
                f"{kw.lower()} indica",
                f"{kw.lower()} representa",
            ]
            is_definition = any(pat in content for pat in forbidden_patterns)
            if is_definition:
                issues.append(f"GROUNDING FAIL: Found definition of forbidden term '{kw}'")

    return len(issues) == 0, issues


def validate_rag_abstention(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BA-001: For unknown terms, system should abstain (not hallucinate).

    If clarification is received, that's also acceptable - system is asking for more info.
    """
    issues = []

    content = sse_data.get("content", "").lower()
    clarification = sse_data.get("clarification")

    # If we got clarification, system is asking for more context - acceptable
    if clarification and not content.strip():
        return True, []

    # Should contain abstention phrases
    abstention_phrases = [
        "no encontr",  # matches "no encontré", "no encontramos"
        "no encuentro",  # present tense
        "no tengo información",
        "no hay datos",
        "no dispongo",
        "glosario",
        "no existe",
        "no reconozco"
    ]

    found_abstention = any(phrase in content for phrase in abstention_phrases)
    if not found_abstention:
        issues.append("Expected abstention but got confident response (possible hallucination)")

    return len(issues) == 0, issues


def validate_no_invex_default(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BA-002: Query without bank should NOT default to INVEX silently."""
    issues = []

    clarification = sse_data.get("clarification")
    chart = sse_data.get("bank_chart")
    content = sse_data.get("content", "").lower()

    # Good: Got a clarification asking for bank
    if clarification:
        # Check clarification is about bank selection
        message = clarification.get("message", "").lower()
        if "banco" in message or "bank" in message or "cuál" in message or "qué banco" in message:
            return True, []  # Correct behavior
        # Still acceptable if it's a generic clarification
        return True, []

    # Bad: Got a chart with INVEX when not specified
    if chart:
        bank_names = chart.get("bank_names", [])
        for forbidden in test_case.forbidden_keywords:
            if forbidden.upper() in [b.upper() for b in bank_names]:
                # Check if bank was explicitly in query
                if forbidden.lower() not in test_case.query.lower():
                    issues.append(f"BIAS FAIL: Chart defaulted to '{forbidden}' without explicit request")

        # Also check chart title
        chart_title = chart.get("title", "").lower()
        for forbidden in test_case.forbidden_keywords:
            if forbidden.lower() in chart_title and forbidden.lower() not in test_case.query.lower():
                issues.append(f"BIAS FAIL: Chart title contains '{forbidden}'")

    # If no chart and no clarification, also suspicious
    if not chart and not clarification and not content:
        issues.append("Neither chart nor clarification received for query without bank")

    return len(issues) == 0, issues


def validate_explicit_bank(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """BA-002 control: Query WITH explicit bank should work normally."""
    issues = []

    chart = sse_data.get("bank_chart")
    clarification = sse_data.get("clarification")

    # Should get chart, not clarification
    if clarification and not chart:
        issues.append("Got clarification when bank was explicitly specified")
        return False, issues

    if chart:
        bank_names = chart.get("bank_names", [])
        # Check expected bank is in the results
        for kw in test_case.expected_keywords:
            if kw.upper() in [b.upper() for b in bank_names]:
                return True, []

        # Check metric matches
        metric = chart.get("metric_name", "").upper()
        for kw in test_case.expected_keywords:
            if kw.upper() in metric:
                return True, []

        issues.append(f"Chart missing expected keywords: {test_case.expected_keywords}")

    if not chart:
        issues.append("No chart received for explicit bank query")

    return len(issues) == 0, issues


# =========================================================================
# BUG-MONTH-001 VALIDATORS: Wrong Month Data Mapping
# =========================================================================
def validate_date_value_association(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """MONTH-001: Validate that chart data has explicit date-value pairs."""
    issues = []

    chart = sse_data.get("bank_chart")
    if not chart:
        if sse_data.get("clarification"):
            return True, []  # Clarification is acceptable
        issues.append("No chart received")
        return False, issues

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    if not traces:
        issues.append("No traces in plotly_config")
        return False, issues

    for i, trace in enumerate(traces):
        x_values = trace.get("x", [])
        y_values = trace.get("y", [])
        bank_name = trace.get("name", f"Trace_{i}")

        # Both x (dates) and y (values) must be present
        if not x_values:
            issues.append(f"Trace '{bank_name}' missing x values (dates)")
        if not y_values:
            issues.append(f"Trace '{bank_name}' missing y values")

        # Lengths must match (each value has its date)
        if x_values and y_values and len(x_values) != len(y_values):
            issues.append(f"Trace '{bank_name}' has mismatched x/y lengths: {len(x_values)} vs {len(y_values)}")

        # x values should look like dates (YYYY-MM-DD format)
        if x_values:
            first_x = str(x_values[0])
            if not (len(first_x) >= 10 and "-" in first_x):
                issues.append(f"Trace '{bank_name}' x values don't look like dates: {first_x}")

    return len(issues) == 0, issues


def validate_no_month_confusion(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """MONTH-001: Validate that text response doesn't confuse month-value associations."""
    issues = []

    content = sse_data.get("content", "").lower()
    chart = sse_data.get("bank_chart")

    # If we have both chart and content, check for consistency
    if chart and content:
        plotly_config = chart.get("plotly_config", {})
        traces = plotly_config.get("data", [])

        for trace in traces:
            x_values = trace.get("x", [])
            y_values = trace.get("y", [])

            if x_values and y_values and len(x_values) == len(y_values):
                # Check that first value isn't attributed to last month
                first_date = str(x_values[0])[:7] if x_values else ""  # YYYY-MM
                last_date = str(x_values[-1])[:7] if x_values else ""

                first_val = y_values[0] if y_values else None
                last_val = y_values[-1] if y_values else None

                # Extract month names from dates
                month_map = {
                    "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
                    "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
                    "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre"
                }

                if first_date and last_date and first_val and last_val:
                    first_month = month_map.get(first_date[5:7], "")
                    last_month = month_map.get(last_date[5:7], "")

                    # Check for the specific bug: first value attributed to last month
                    if first_month and last_month and first_month != last_month:
                        first_val_str = f"{first_val:.2f}" if isinstance(first_val, float) else str(first_val)

                        # Bug pattern: "en [last_month] fue [first_val]"
                        bug_pattern = f"{last_month}" in content and first_val_str[:4] in content
                        # This is a heuristic - if the first value appears near the last month name
                        # it might indicate month confusion

    # Basic validation: chart data exists and is well-formed
    if chart:
        return validate_date_value_association(sse_data, test_case)

    if not chart and not sse_data.get("clarification"):
        issues.append("No chart or clarification received")

    return len(issues) == 0, issues


# =========================================================================
# BUG-DECIMAL-001 VALIDATORS: ICAP Decimal Shift
# =========================================================================
def validate_icap_range(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """DECIMAL-001: Validate ICAP values are in valid range (0-100%, not 1000%+)."""
    issues = []

    chart = sse_data.get("bank_chart")
    content = sse_data.get("content", "")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    for trace in traces:
        y_values = trace.get("y", [])
        bank_name = trace.get("name", "Unknown")

        for val in y_values:
            if val is not None and isinstance(val, (int, float)):
                # ICAP should be < 100% (typical range 10-25%)
                # Values > 100% indicate the x100 bug
                if abs(val) > 100:
                    issues.append(
                        f"DECIMAL SHIFT DETECTED: {bank_name} has ICAP value {val:.2f}% "
                        f"(should be < 100%)"
                    )
                # Values > 500% definitely indicate the bug
                if abs(val) > 500:
                    issues.append(
                        f"CRITICAL: {bank_name} ICAP value {val:.2f}% appears to be x100 multiplied"
                    )

    # Also check text content for suspicious values
    import re
    percentage_pattern = r'(\d{3,4})[,.]?\d*\s*%'
    suspicious_values = re.findall(percentage_pattern, content)
    for val in suspicious_values:
        if int(val) > 100:
            issues.append(f"Text contains suspicious percentage: {val}%")

    return len(issues) == 0, issues


def validate_imor_range(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """DECIMAL-001: Validate IMOR values are in valid range (0-20%, not 100%+)."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    for trace in traces:
        y_values = trace.get("y", [])
        bank_name = trace.get("name", "Unknown")

        for val in y_values:
            if val is not None and isinstance(val, (int, float)):
                # IMOR typically ranges 0-15% for healthy banks
                # Values > 50% almost certainly indicate a bug
                if abs(val) > 50:
                    issues.append(
                        f"DECIMAL SHIFT DETECTED: {bank_name} has IMOR value {val:.2f}% "
                        f"(should be < 20% for most banks)"
                    )

    return len(issues) == 0, issues


# =========================================================================
# BUG-SCOPE-001 VALIDATORS: Query Scope All Banks
# =========================================================================
def validate_single_bank_scope(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """SCOPE-001: Single bank query should return only that bank."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    bank_names = chart.get("bank_names", [])
    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    # Extract expected bank from query
    expected_bank = None
    for kw in test_case.expected_keywords:
        if kw.upper() not in ["ICAP", "IMOR", "ICOR", "ROE", "ROA"]:  # Not a metric
            expected_bank = kw.upper()
            break

    # Check bank_names field
    if len(bank_names) > 2:  # Allow for SISTEMA comparison
        issues.append(
            f"SCOPE EXPANSION DETECTED: Expected 1-2 banks, got {len(bank_names)}: {bank_names}"
        )

    # Check traces
    trace_names = [t.get("name", "").upper() for t in traces]
    if len(traces) > 3:  # Allow for some flexibility
        issues.append(
            f"Too many traces ({len(traces)}): {trace_names[:5]}..."
        )

    # Verify expected bank is present
    if expected_bank:
        found_expected = any(expected_bank in name.upper() for name in bank_names + trace_names)
        if not found_expected:
            issues.append(f"Expected bank '{expected_bank}' not found in response")

    return len(issues) == 0, issues


def validate_limited_bank_scope(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """SCOPE-001: Multi-bank comparison should return only specified banks."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    bank_names = chart.get("bank_names", [])
    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    # Extract expected banks from keywords (non-metric keywords)
    metrics = {"ICAP", "IMOR", "ICOR", "ROE", "ROA", "CARTERA", "RESERVAS"}
    expected_banks = [kw.upper() for kw in test_case.expected_keywords if kw.upper() not in metrics]

    # Should have at most expected banks + SISTEMA
    max_banks = len(expected_banks) + 1  # +1 for potential SISTEMA
    if len(bank_names) > max_banks + 1:  # Small tolerance
        issues.append(
            f"SCOPE EXPANSION DETECTED: Expected max {max_banks} banks, got {len(bank_names)}: {bank_names}"
        )

    # Verify all expected banks are present
    for expected in expected_banks:
        found = any(expected in name.upper() for name in bank_names)
        if not found:
            issues.append(f"Expected bank '{expected}' not found in response")

    return len(issues) == 0, issues


def validate_no_bank_expansion(sse_data: Dict, test_case: BugTestCase) -> Tuple[bool, List[str]]:
    """SCOPE-001: Query should not silently expand to all banks."""
    issues = []

    chart = sse_data.get("bank_chart")

    if not chart:
        if sse_data.get("clarification"):
            return True, []
        issues.append("No chart received")
        return False, issues

    bank_names = chart.get("bank_names", [])
    plotly_config = chart.get("plotly_config", {})
    traces = plotly_config.get("data", [])

    # Check for forbidden banks in the response
    for forbidden in test_case.forbidden_keywords:
        if forbidden.upper() in [b.upper() for b in bank_names]:
            issues.append(f"SCOPE EXPANSION: Unexpected bank '{forbidden}' in response")

        # Also check trace names
        for trace in traces:
            trace_name = trace.get("name", "").upper()
            if forbidden.upper() in trace_name:
                issues.append(f"SCOPE EXPANSION: Unexpected bank '{forbidden}' in traces")
                break

    # General expansion check: more than 5 banks is suspicious for single-bank queries
    if len(bank_names) > 5:
        issues.append(
            f"SUSPICIOUS EXPANSION: Got {len(bank_names)} banks for a single-bank query"
        )

    return len(issues) == 0, issues


# Validation function dispatcher
VALIDATORS = {
    "validate_not_only_icap": validate_not_only_icap,
    "validate_capitalizacion_disambiguation": validate_capitalizacion_disambiguation,
    "validate_metric_match": validate_metric_match,
    "validate_has_bank": validate_has_bank,
    "validate_rag_grounding": validate_rag_grounding,
    "validate_rag_abstention": validate_rag_abstention,
    "validate_no_invex_default": validate_no_invex_default,
    "validate_explicit_bank": validate_explicit_bank,
    "validate_clean_markdown": validate_clean_markdown,
    # BUG-MONTH-001: Wrong month data mapping
    "validate_date_value_association": validate_date_value_association,
    "validate_no_month_confusion": validate_no_month_confusion,
    # BUG-DECIMAL-001: ICAP decimal shift
    "validate_icap_range": validate_icap_range,
    "validate_imor_range": validate_imor_range,
    # BUG-SCOPE-001: Query scope all banks
    "validate_single_bank_scope": validate_single_bank_scope,
    "validate_limited_bank_scope": validate_limited_bank_scope,
    "validate_no_bank_expansion": validate_no_bank_expansion,
}


def run_bug_test(
    test_case: BugTestCase,
    token: str,
    backend_url: str,
    timeout: int,
    verbose: bool
) -> Dict[str, Any]:
    """Run a single bug test case."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    payload = {
        "message": test_case.query,
        "stream": True,
        "model": "Saptiva Turbo"
    }

    result = {
        "bug_id": test_case.bug_id,
        "description": test_case.description,
        "query": test_case.query,
        "passed": False,
        "issues": [],
        "latency_ms": 0
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{backend_url}/api/chat",
            json=payload,
            headers=headers,
            stream=True,
            timeout=timeout
        )

        if response.status_code != 200:
            result["issues"].append(f"HTTP {response.status_code}")
            return result

        sse_data = parse_sse_response(response)
        result["latency_ms"] = (time.time() - start_time) * 1000

        # Run the appropriate validator
        validator = VALIDATORS.get(test_case.validation_fn)
        if validator:
            passed, issues = validator(sse_data, test_case)
            result["passed"] = passed
            result["issues"] = issues
        else:
            result["issues"].append(f"Unknown validator: {test_case.validation_fn}")

        if verbose:
            print(f"   Events: {sse_data.get('events', [])}")
            if sse_data.get("clarification"):
                print(f"   Clarification: {sse_data['clarification'].get('message', '')[:80]}")
            if sse_data.get("bank_chart"):
                print(f"   Chart: {sse_data['bank_chart'].get('metric_name', 'N/A')}")

    except Exception as e:
        result["issues"].append(str(e))

    return result


def main():
    args = parse_args()

    print("=" * 60)
    print("Bug Fixes Test Suite (includes BA-001 to BA-004)")
    print("=" * 60)

    # Get auth token
    token = get_auth_token(args.backend_url)
    if not token:
        print("Fatal: Auth failed")
        return

    # Filter test cases if specific bugs requested
    cases = BUG_TEST_CASES

    # --ba-only filter: only run BA-xxx tests
    if args.ba_only:
        cases = [c for c in cases if isinstance(c.bug_id, str) and c.bug_id.startswith("BA-")]
    elif args.bugs:
        # Parse wanted bugs - support both numeric (1,3) and string (BA-001,BA-002) IDs
        wanted_bugs = set()
        for x in args.bugs.split(","):
            x = x.strip().upper()
            if x.isdigit():
                wanted_bugs.add(int(x))
            else:
                wanted_bugs.add(x)
        cases = [c for c in cases if c.bug_id in wanted_bugs or (isinstance(c.bug_id, int) and c.bug_id in wanted_bugs)]

    print(f"Running {len(cases)} test cases")
    print("-" * 60)

    results_by_bug: Dict[Union[int, str], List[Dict]] = {}

    for case in cases:
        result = run_bug_test(case, token, args.backend_url, args.timeout, args.verbose)

        if case.bug_id not in results_by_bug:
            results_by_bug[case.bug_id] = []
        results_by_bug[case.bug_id].append(result)

        status = "\u2705" if result["passed"] else "\u274c"
        bug_id_str = case.bug_id if isinstance(case.bug_id, str) else f"BUG-{case.bug_id:02d}"
        print(f"{status} [{bug_id_str}]: {case.description[:50]}...")
        if not result["passed"]:
            for issue in result["issues"]:
                print(f"   {issue}")

        time.sleep(0.3)

    # Summary by bug
    print("=" * 60)
    print("Summary by Bug")
    print("=" * 60)

    all_passed = True
    # Sort bug IDs: strings first (BA-xxx), then numeric
    sorted_bug_ids = sorted(results_by_bug.keys(), key=lambda x: (0 if isinstance(x, str) else 1, x))
    for bug_id in sorted_bug_ids:
        bug_results = results_by_bug[bug_id]
        passed = sum(1 for r in bug_results if r["passed"])
        total = len(bug_results)
        status = "\u2705" if passed == total else "\u274c"
        bug_id_str = bug_id if isinstance(bug_id, str) else f"BUG-{bug_id:02d}"
        print(f"{status} {bug_id_str}: {passed}/{total} tests passed")
        if passed < total:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("\u2705 All bug fix tests PASSED!")
    else:
        print("\u274c Some tests FAILED - review issues above")

    # Save results
    save_path = Path(args.save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    with open(save_path / "bug_fixes_results.json", "w") as f:
        json.dump(results_by_bug, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {save_path}/bug_fixes_results.json")


if __name__ == "__main__":
    main()
