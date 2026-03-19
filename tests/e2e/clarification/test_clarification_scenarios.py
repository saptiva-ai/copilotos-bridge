#!/usr/bin/env python3
"""
Clarification Scenarios Test
Combines ambiguous queries and edge cases to verify the clarification logic.

Scenarios:
1. Ambiguous queries (e.g., "Dame informacion de INVEX") -> Should trigger clarification.
2. Edge queries (broad, vague) -> Should trigger clarification, not empty charts or errors.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure tests/ is on path for shared utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
DEFAULT_MODEL = os.environ.get("TEST_MODEL", "Saptiva Turbo")

AMBIGUOUS_QUERIES = [
    "Dame informacion de INVEX",
    "Quiero datos del banco",
    "Muestrame las metricas",
]

EDGE_QUERIES = [
    "Cuéntame todo lo que sabes de la banca mexicana",
    "Necesito datos sobre bancos",
    "Dame un reporte global de finanzas",
    "Háblame de los bancos que más crecieron",
    "¿Qué información tienes de INVEX?",
    "Comparame todo el sistema bancario",
    "Necesito un resumen financiero de los bancos",
    "¿Qué pasa con la banca?",
    "¿Qué bancos están creciendo en cartera digital?",
    "Dame todos los índices de riesgo del sistema",
    "Cuáles son las tendencias en créditos corporativos",
    "Necesito una panorámica de las métricas regulatorias",
    "Explícame cómo va la banca en general",
]

def test_clarification_scenarios():
    print("=" * 70)
    print("CLARIFICATION SCENARIOS TEST")
    print("=" * 70)

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("❌ Fatal: Auth failed")
        return False

    all_passed = True

    # Test 1: Ambiguous Queries
    print("\n[1/2] Testing Ambiguous Queries...")
    for q in AMBIGUOUS_QUERIES:
        print(f"  Testing: '{q}'")
        res = send_chat_message(token, q, backend_url=BACKEND_URL, model=DEFAULT_MODEL)
        
        if _validate_clarification_response(res):
            print("    ✅ Passed")
        else:
            print(f"    ❌ Failed: {res.get('error') or 'No clarification triggered'}")
            all_passed = False

    # Test 2: Edge Case Queries
    print("\n[2/2] Testing Edge Case Queries...")
    for q in EDGE_QUERIES:
        print(f"  Testing: '{q}'")
        res = send_chat_message(token, q, backend_url=BACKEND_URL, model=DEFAULT_MODEL)
        
        # Edge cases should EITHER return clarification OR a text response (RAG/Knowledge), 
        # but NOT an empty chart or error.
        if res.get("error"):
            print(f"    ❌ Failed: Error received: {res['error']}")
            all_passed = False
            continue

        events = res.get("events", [])
        if "bank_clarification" in events or "clarification" in events:
             print("    ✅ Passed (Clarification triggered)")
        elif res.get("content") and len(res["content"]) > 10:
             print("    ✅ Passed (Text response received)")
        else:
             print(f"    ❌ Failed: No useful response. Events: {events}")
             all_passed = False

    return all_passed

def _validate_clarification_response(res: Dict[str, Any]) -> bool:
    """Helper to validate that a response contains a clarification request.

    Accepts two forms of clarification:
    1. Formal clarification: bank_clarification event with options
    2. Conversational clarification: Text response asking for more specifics
    """
    if res.get("error"):
        return False

    events = res.get("events", [])

    # Option 1: Formal clarification with options
    has_clarification = "bank_clarification" in events or "clarification" in events
    has_options = False

    clarification = res.get("clarification")
    if clarification and clarification.get("options"):
        has_options = True

    if has_clarification and has_options:
        return True

    # Option 2: Conversational clarification - text asking for specifics
    content = res.get("content", "").lower()
    clarification_phrases = [
        "especifica",
        "especifique",
        "qué tipo de datos",
        "qué métrica",
        "qué información",
        "puedes indicar",
        "podrías indicar",
        "más detalles",
        "ser más específico",
        "qué deseas",
        "qué te gustaría",
        "cuál métrica",
    ]

    if content and any(phrase in content for phrase in clarification_phrases):
        return True

    return False

if __name__ == "__main__":
    success = test_clarification_scenarios()
    if success:
        print("\n✅ All clarification scenarios passed.")
        sys.exit(0)
    else:
        print("\n❌ Some scenarios failed.")
        sys.exit(1)
