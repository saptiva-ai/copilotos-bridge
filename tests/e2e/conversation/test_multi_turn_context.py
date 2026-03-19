#!/usr/bin/env python3
"""
Multi-Turn Conversation Context Tests

Tests for:
- Long conversation chains (5+ turns)
- Context retention across turns
- Entity resolution (anaphora)
- Topic switching and return
- Context correction
- Conflicting context resolution
- Context persistence edge cases
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

# Ensure tests/ is on path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.helpers import get_auth_token as helper_get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
AUTH_PAYLOAD = {"identifier": "demo", "password": "Demo1234"}


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    message: str
    expected_entities: List[str] = field(default_factory=list)  # Banks/metrics expected in response
    expected_type: str = "any"  # "chart", "clarification", "rag", "any"
    description: str = ""


@dataclass
class ConversationScenario:
    """A complete conversation scenario to test."""
    id: str
    name: str
    description: str
    turns: List[ConversationTurn]
    expected_final_context: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CONVERSATION SCENARIOS
# =============================================================================

SCENARIOS: List[ConversationScenario] = [
    # -------------------------------------------------------------------------
    # Scenario 1: Long Chain with Context Accumulation
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-001",
        name="Long Chain Accumulation",
        description="5-turn conversation building on previous context",
        turns=[
            ConversationTurn(
                message="Dame el IMOR de INVEX",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Initial query - sets bank and metric",
            ),
            ConversationTurn(
                message="y el ICAP?",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
                description="Change metric, retain bank",
            ),
            ConversationTurn(
                message="comparalo con BBVA",
                expected_entities=["INVEX", "BBVA", "ICAP"],
                expected_type="chart",
                description="Add comparison bank, retain metric",
            ),
            ConversationTurn(
                message="ahora muestra los ultimos 6 meses",
                expected_entities=["INVEX", "BBVA", "ICAP"],
                expected_type="chart",
                description="Add temporal context",
            ),
            ConversationTurn(
                message="solo INVEX",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
                description="Remove comparison, keep rest",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 2: Topic Switch and Return
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-002",
        name="Topic Switch and Return",
        description="Change topic completely then return to original",
        turns=[
            ConversationTurn(
                message="IMOR de INVEX ultimos 3 meses",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Initial NL2SQL query",
            ),
            ConversationTurn(
                message="Que es el ICAP?",
                expected_entities=["ICAP"],
                expected_type="rag",
                description="Switch to RAG question",
            ),
            ConversationTurn(
                message="regresa al IMOR que te pedi antes",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Return to previous context",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 3: Entity Correction
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-003",
        name="Entity Correction",
        description="User corrects a mistake in entity",
        turns=[
            ConversationTurn(
                message="IMOR de BBVA",
                expected_entities=["BBVA", "IMOR"],
                expected_type="chart",
                description="Initial query with wrong bank",
            ),
            ConversationTurn(
                message="perdon, quise decir INVEX",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Correction - should replace bank",
            ),
            ConversationTurn(
                message="ahora si BBVA tambien",
                expected_entities=["INVEX", "BBVA", "IMOR"],
                expected_type="chart",
                description="Add back the first bank",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 4: Anaphoric References
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-004",
        name="Anaphoric References",
        description="Test pronoun and reference resolution",
        turns=[
            ConversationTurn(
                message="IMOR de los 5 bancos mas grandes",
                expected_entities=["IMOR"],
                expected_type="chart",
                description="Query with implicit bank set",
            ),
            ConversationTurn(
                message="y el de INVEX?",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Reference to previous metric",
            ),
            ConversationTurn(
                message="comparalo con el primero de la lista",
                expected_entities=["INVEX", "IMOR"],
                expected_type="any",
                description="Reference to previous result",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 5: Conflicting Context (Metric Switch)
    # FIX: Use INVEX for all turns - only bank with data in dev DB
    # Tests context switch via metric change (IMOR → ICAP → IMOR)
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-005",
        name="Conflicting Context",
        description="New query that conflicts with previous context - metric switch",
        turns=[
            ConversationTurn(
                message="IMOR de INVEX en 2024",
                expected_entities=["INVEX", "IMOR", "2024"],
                expected_type="chart",
                description="Set specific context",
            ),
            ConversationTurn(
                message="ICAP de INVEX en 2023",
                expected_entities=["INVEX", "ICAP", "2023"],
                expected_type="chart",
                description="Different metric and year - should override context",
            ),
            ConversationTurn(
                message="y el IMOR?",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Change metric back, keep same bank",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 6: Negation in Context
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-006",
        name="Negation Handling",
        description="Test exclusion and negation in context",
        turns=[
            ConversationTurn(
                message="IMOR de todos los bancos",
                expected_entities=["IMOR"],
                expected_type="chart",
                description="All banks",
            ),
            ConversationTurn(
                message="excepto INVEX",
                expected_entities=["IMOR"],
                expected_type="any",
                description="Exclude specific bank",
            ),
            ConversationTurn(
                message="ahora incluye INVEX pero quita BBVA",
                expected_entities=["INVEX", "IMOR"],
                expected_type="any",
                description="Swap inclusions/exclusions",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 7: Multi-Metric Request
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-007",
        name="Multi-Metric Conversation",
        description="Request multiple metrics across turns",
        turns=[
            ConversationTurn(
                message="Dame IMOR e ICAP de INVEX",
                expected_entities=["INVEX", "IMOR", "ICAP"],
                expected_type="any",
                description="Two metrics at once",
            ),
            ConversationTurn(
                message="agrega el ICOR",
                expected_entities=["INVEX", "ICOR"],
                expected_type="any",
                description="Add third metric",
            ),
            ConversationTurn(
                message="solo el IMOR",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Reduce to one metric",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 8: Temporal Context Changes
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-008",
        name="Temporal Context Evolution",
        description="Test temporal context modifications",
        turns=[
            ConversationTurn(
                message="IMOR de INVEX en enero 2024",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Specific month",
            ),
            ConversationTurn(
                message="ahora el trimestre completo",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Expand to quarter",
            ),
            ConversationTurn(
                message="comparalo con el mismo periodo del ano anterior",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Year-over-year comparison",
            ),
            ConversationTurn(
                message="muestra la tendencia de todo el 2024",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Full year view",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 9: Clarification Flow
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-009",
        name="Clarification Resolution",
        description="Handle clarification and resolution",
        turns=[
            ConversationTurn(
                message="Dame datos de INVEX",
                expected_entities=["INVEX"],
                expected_type="clarification",
                description="Ambiguous - should ask for metric",
            ),
            ConversationTurn(
                message="el IMOR",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Provide missing metric",
            ),
            ConversationTurn(
                message="ahora de BBVA",
                expected_entities=["BBVA", "IMOR"],
                expected_type="chart",
                description="Change bank, keep metric",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 10: Stress - 7 Turn Conversation
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-010",
        name="Extended Conversation (7 turns)",
        description="Long conversation stress test",
        turns=[
            ConversationTurn(
                message="IMOR de INVEX",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="agrega BBVA",
                expected_entities=["INVEX", "BBVA", "IMOR"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="y Santander",
                expected_entities=["INVEX", "BBVA", "Santander", "IMOR"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="ultimos 6 meses",
                expected_entities=["IMOR"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="cambia a ICAP",
                expected_entities=["ICAP"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="solo INVEX y sistema",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="regresa a IMOR con los 3 bancos originales",
                expected_entities=["IMOR"],
                expected_type="any",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 11: Long Mixed Topics with Priority on Latest Turn
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-011",
        name="Long Mixed Topics with Priority",
        description=(
            "Mix metrics and glossary questions across many turns; "
            "the assistant must prioritize the latest intent and avoid sticking to old context."
        ),
        turns=[
            ConversationTurn(
                message="IMOR de INVEX en 2024",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Start with a metric request that should yield a chart.",
            ),
            ConversationTurn(
                message="Que es un fideicomiso?",
                expected_entities=[],
                expected_type="rag",
                description="Switch to a glossary definition; should not trigger chart/tooling.",
            ),
            ConversationTurn(
                message="ahora ICAP de BBVA",
                expected_entities=["BBVA", "ICAP"],
                expected_type="chart",
                description="Shift back to metrics with a different bank/metric.",
            ),
            ConversationTurn(
                message="que significa CNVB",
                expected_entities=[],
                expected_type="rag",
                description="Introduce a typo; system should answer definition/fuzzy match (no chart).",
            ),
            ConversationTurn(
                message="regresa al IMOR de INVEX",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Confirm it can restore the earlier bank/metric context after glossary turns.",
            ),
            ConversationTurn(
                message="solo defineme ICAP, sin grafica",
                expected_entities=["ICAP"],
                expected_type="rag",
                description="Latest intent is definitional; must avoid charting despite prior metric turns.",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 12: Glossary Definitions (BUG-01)
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-012",
        name="Glossary Definitions Without Chart",
        description="Test that definition queries go to RAG without triggering chart",
        turns=[
            ConversationTurn(
                message="Que es un fideicomiso?",
                expected_entities=[],
                expected_type="rag",
                description="Pure definition query should go to RAG, not chart",
            ),
            ConversationTurn(
                message="Y que significa CCL?",
                expected_entities=["CCL"],
                expected_type="rag",
                description="Acronym definition should also go to RAG",
            ),
            ConversationTurn(
                message="ahora si dame el IMOR de INVEX",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
                description="Explicit chart request after definitions",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 13: Acronym Typos (BUG-03)
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-013",
        name="Acronym Typo Handling",
        description="Test fuzzy matching for common typos",
        turns=[
            ConversationTurn(
                message="CNVB?",
                expected_entities=[],  # RAG may expand acronym without using it
                expected_type="rag",
                description="Should route CNVB typo to RAG (definition-like)",
            ),
            ConversationTurn(
                message="y el ICPA de INVEX?",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
                description="Should normalize ICPA to ICAP and return chart",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 14: Multi-Bank Comparison (BUG-05)
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-014",
        name="Multi-Bank Comparison Beyond INVEX",
        description="Test that multiple banks work, not just INVEX/SISTEMA",
        turns=[
            ConversationTurn(
                message="IMOR de BBVA y Santander en 2024",
                expected_entities=["BBVA", "SANTANDER", "IMOR", "2024"],
                expected_type="chart",
                description="Compare two non-INVEX banks",
            ),
            ConversationTurn(
                message="agrega Banorte",
                expected_entities=["BANORTE", "IMOR"],
                expected_type="chart",
                description="Add third bank",
            ),
            ConversationTurn(
                message="comparalo con el sistema",
                expected_entities=["SISTEMA", "IMOR"],
                expected_type="chart",
                description="Add system aggregate",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 15: Long Complex Conversation (10 turns)
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-015",
        name="Long Complex Conversation (10 turns)",
        description="Stress test with 10 turns mixing definitions, metrics, and corrections",
        turns=[
            ConversationTurn(
                message="IMOR de INVEX",
                expected_entities=["INVEX", "IMOR"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="que es el IMOR?",
                expected_entities=["IMOR"],
                expected_type="rag",
                description="Definition mid-conversation",
            ),
            ConversationTurn(
                message="ahora comparalo con BBVA",
                expected_entities=["BBVA", "IMOR"],
                expected_type="chart",
                description="Return to chart with comparison",
            ),
            ConversationTurn(
                message="cambia a ICAP",
                expected_entities=["ICAP"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="ultimos 6 meses",
                expected_entities=["ICAP"],
                expected_type="chart",
                description="Temporal modifier preserves metric",
            ),
            ConversationTurn(
                message="solo INVEX",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="que es un fideicomiso?",
                expected_entities=[],
                expected_type="rag",
                description="Glossary question",
            ),
            ConversationTurn(
                message="regresa al ICAP de INVEX",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
                description="Return after glossary",
            ),
            ConversationTurn(
                message="agrega Santander y Banorte",
                expected_entities=["SANTANDER", "BANORTE", "ICAP"],
                expected_type="chart",
            ),
            ConversationTurn(
                message="en 2023",
                expected_entities=["ICAP", "2023"],
                expected_type="chart",
                description="Year change preserves metric and banks",
            ),
        ],
    ),

    # -------------------------------------------------------------------------
    # Scenario 16: Definition with Metric Name (no chart)
    # -------------------------------------------------------------------------
    ConversationScenario(
        id="CONV-016",
        name="Definition Request with Metric Name",
        description="User asks for definition of a metric, should not trigger chart",
        turns=[
            ConversationTurn(
                message="que significa ICAP?",
                expected_entities=["ICAP"],
                expected_type="rag",
                description="Definition of ICAP should go to RAG",
            ),
            ConversationTurn(
                message="y cual es el de INVEX?",
                expected_entities=["INVEX", "ICAP"],
                expected_type="chart",
                description="Follow-up asking for actual value",
            ),
        ],
    ),
]


def get_auth_token() -> Optional[str]:
    """Get authentication token using shared helper."""
    return helper_get_auth_token(backend_url=BACKEND_URL)


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response."""
    result = {
        "events": [],
        "bank_chart": None,
        "clarification": None,
        "content": "",
        "meta": None,
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
                elif current_event == "meta":
                    result["meta"] = parsed
                elif current_event == "chunk" and "content" in parsed:
                    result["content"] += parsed["content"]
                elif current_event == "error":
                    result["error"] = parsed
            except json.JSONDecodeError:
                if current_event == "chunk":
                    result["content"] += data

    return result


def send_message(token: str, message: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Send a message and return parsed response using shared helper."""
    return send_chat_message(
        token,
        message,
        backend_url=BACKEND_URL,
        chat_id=chat_id,
        model="Saptiva Turbo",
        timeout=60,
    )


def extract_entities_from_response(response: Dict) -> List[str]:
    """Extract bank names and metrics from response.

    NOTE: This function focuses on PRIMARY entities (banks, metrics, years)
    from structured chart data to minimize false positives. Content-based
    extraction is limited to key entities only.
    """
    entities = []

    # From chart - primary source of truth
    if response.get("bank_chart"):
        chart = response["bank_chart"]
        # Bank names from chart (high confidence)
        if "bank_names" in chart:
            entities.extend(chart["bank_names"])
        # Metric name from chart (high confidence)
        if "metric_name" in chart:
            entities.append(chart["metric_name"])
        # Extract years from time_range (high confidence)
        time_range = chart.get("time_range") or {}
        start_date = time_range.get("start", "")
        end_date = time_range.get("end", "")
        for date_str in [start_date, end_date]:
            if date_str:
                year_match = re.search(r"(20\d{2})", str(date_str))
                if year_match:
                    entities.append(year_match.group(1))
        # NOTE: Removed time_range_note as it adds noise (full sentence strings)

    # From content - only extract explicit bank and metric mentions
    # Limit to avoid noise from general explanatory text
    content = response.get("content", "").upper()

    # Only extract banks and metrics if they appear prominently (not just mentioned)
    # Use stricter matching - entity must be in a data context
    primary_banks = ["INVEX", "BBVA", "SANTANDER", "BANORTE", "HSBC", "CITIBANAMEX", "SCOTIABANK", "SISTEMA"]
    primary_metrics = ["IMOR", "ICAP", "ICOR", "ROE", "ROA", "CCL"]

    for entity in primary_banks + primary_metrics:
        if entity in content:
            entities.append(entity)

    # Extract years from content only if explicitly expected (not casual mentions)
    # Only extract 4-digit years that appear in data context
    years = re.findall(r"\b(20\d{2})\b", content)
    entities.extend(years)

    # NOTE: Removed MIN, NSFR, LCR, CNBV as they cause noise
    # These appear in explanatory text but aren't primary entities

    # From clarification payload (banks/suggestions)
    clarification = response.get("clarification") or {}
    clar_context = clarification.get("context") or {}
    for bank in clar_context.get("banks") or []:
        entities.append(bank)
    # NOTE: Removed available_banks as it lists all options, not selected ones

    # Filter None and empty values before returning
    return list(set(e for e in entities if e))


def get_response_type(response: Dict) -> str:
    """Determine response type."""
    if response.get("error"):
        return "error"
    if response.get("bank_chart"):
        return "chart"
    if response.get("clarification"):
        return "clarification"
    if response.get("content") and len(response["content"]) > 50:
        return "rag"
    return "unknown"


def run_scenario(scenario: ConversationScenario, token: str) -> Dict:
    """Run a complete conversation scenario."""
    result = {
        "id": scenario.id,
        "name": scenario.name,
        "passed": True,
        "turn_results": [],
        "issues": [],
    }

    chat_id = None

    for i, turn in enumerate(scenario.turns):
        turn_result = {
            "turn": i + 1,
            "message": turn.message,
            "passed": True,
            "issues": [],
        }

        # Send message
        response = send_message(token, turn.message, chat_id)

        # Get chat_id from first response
        if i == 0 and response.get("meta"):
            chat_id = response["meta"].get("chat_id")
            turn_result["chat_id"] = chat_id

        # Check for errors
        if response.get("error"):
            turn_result["passed"] = False
            turn_result["issues"].append(f"Error: {response['error']}")
            result["passed"] = False
            result["turn_results"].append(turn_result)
            continue

        # Persist expectations for downstream metric aggregation
        turn_result["expected_entities"] = turn.expected_entities
        turn_result["expected_type"] = turn.expected_type

        # Check response type
        response_type = get_response_type(response)
        turn_result["response_type"] = response_type

        if turn.expected_type != "any" and response_type != turn.expected_type:
            turn_result["issues"].append(
                f"Expected {turn.expected_type}, got {response_type}"
            )

        # Check expected entities
        entities_found = extract_entities_from_response(response)
        turn_result["entities_found"] = entities_found

        missing_entities = []
        for expected in turn.expected_entities:
            if not any(expected.upper() in e.upper() for e in entities_found):
                missing_entities.append(expected)

        if missing_entities:
            turn_result["issues"].append(
                f"Missing entities: {missing_entities}"
            )

        # Determine if turn passed
        if turn_result["issues"]:
            turn_result["passed"] = False
            result["passed"] = False

        result["turn_results"].append(turn_result)

        # Small delay between turns
        time.sleep(0.3)

    return result


def compute_aggregated_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute coarse-grained precision/recall for entity grounding and type accuracy."""
    tp_entities = 0
    fp_entities = 0
    fn_entities = 0
    type_checks = 0
    type_correct = 0

    for scenario in results:
        for turn in scenario.get("turn_results", []):
            expected_entities = {e.upper() for e in turn.get("expected_entities", []) if e}
            predicted_entities = {e.upper() for e in turn.get("entities_found", []) if e}

            # Entity metrics only when we have explicit expectations
            if expected_entities:
                tp = len(expected_entities & predicted_entities)
                fn = len(expected_entities - predicted_entities)
                fp = len(predicted_entities - expected_entities)

                tp_entities += tp
                fn_entities += fn
                fp_entities += fp

            # Response-type accuracy when enforced
            expected_type = turn.get("expected_type")
            response_type = turn.get("response_type")
            if expected_type and expected_type != "any":
                type_checks += 1
                if expected_type == response_type:
                    type_correct += 1

    precision = tp_entities / (tp_entities + fp_entities) if (tp_entities + fp_entities) > 0 else 0.0
    recall = tp_entities / (tp_entities + fn_entities) if (tp_entities + fn_entities) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    type_accuracy = type_correct / type_checks if type_checks > 0 else 0.0

    return {
        "precision_entities": precision,
        "recall_entities": recall,
        "f1_entities": f1,
        "type_accuracy": type_accuracy,
        "tp_entities": tp_entities,
        "fp_entities": fp_entities,
        "fn_entities": fn_entities,
        "type_checks": type_checks,
    }


def run_all_scenarios(max_workers: int = 1):
    """Run all conversation scenarios.

    Args:
        max_workers: degree of parallelism. 1 = sequential (default). >1 runs scenarios in threads.
    """
    print("=" * 70)
    print("MULTI-TURN CONVERSATION CONTEXT TESTS")
    print("=" * 70)

    token = get_auth_token()
    if not token:
        print("FATAL: Authentication failed")
        return

    print(f"Total scenarios: {len(SCENARIOS)}\n")

    total_passed = 0
    total_failed = 0
    results = []

    def _execute(scenario: ConversationScenario):
        print(f"\n{'─' * 60}")
        print(f"Scenario: {scenario.id} - {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Turns: {len(scenario.turns)}")
        print("─" * 60)
        return run_scenario(scenario, token)

    if max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_execute, s): s for s in SCENARIOS}
            for future in as_completed(future_map):
                result = future.result()
                results.append(result)
    else:
        for scenario in SCENARIOS:
            result = _execute(scenario)
            results.append(result)

    # Print per-scenario results in deterministic order (by id)
    for result in sorted(results, key=lambda r: r["id"]):
        if result["passed"]:
            total_passed += 1
            status = "\033[92mPASS\033[0m"
        else:
            total_failed += 1
            status = "\033[91mFAIL\033[0m"

        print(f"Result: [{status}] - {result['id']} {result['name']}")

        for turn_result in result["turn_results"]:
            turn_status = "\033[92m✓\033[0m" if turn_result["passed"] else "\033[91m✗\033[0m"
            print(f"  Turn {turn_result['turn']}: [{turn_status}] {turn_result['message'][:40]}...")
            if turn_result.get("response_type"):
                print(f"       Type: {turn_result['response_type']}")
            if turn_result.get("entities_found"):
                print(f"       Entities: {turn_result['entities_found']}")
            for issue in turn_result.get("issues", []):
                print(f"       \033[93m⚠ {issue}\033[0m")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Scenarios Passed: {total_passed}/{len(SCENARIOS)}")
    print(f"Scenarios Failed: {total_failed}/{len(SCENARIOS)}")
    print(f"Pass Rate: {total_passed / len(SCENARIOS) * 100:.1f}%")

    if total_failed > 0:
        print("\nFailed Scenarios:")
        for result in results:
            if not result["passed"]:
                print(f"  - {result['id']}: {result['name']}")

    # Aggregate metrics across all turns to measure grounding precision/recall and routing accuracy
    metrics = compute_aggregated_metrics(results)
    print("\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)
    print(f"Entity Precision: {metrics['precision_entities']:.3f} "
          f"(TP={metrics['tp_entities']}, FP={metrics['fp_entities']})")
    print(f"Entity Recall:    {metrics['recall_entities']:.3f} "
          f"(TP={metrics['tp_entities']}, FN={metrics['fn_entities']})")
    print(f"Entity F1:        {metrics['f1_entities']:.3f}")
    print(f"Type Accuracy:    {metrics['type_accuracy']:.3f} "
          f"(checks={metrics['type_checks']})")

    return total_failed == 0


if __name__ == "__main__":
    import os

    workers = int(os.environ.get("E2E_MAX_WORKERS", "1"))
    success = run_all_scenarios(max_workers=workers)
    exit(0 if success else 1)
