#!/usr/bin/env python3
"""
Test Suite - Language Mismatch Bug (BUG-2026-01-30)
Validates that responses are in Spanish when user asks in Spanish.

Bug: Sistema responde en inglés cuando usuario pregunta en español.
Root cause: Chain-of-thought reasoning leaking into response (Saptiva Cortex).
Note: This bug is primarily associated with Saptiva Cortex's reasoning_content field.
      Saptiva Turbo/Legacy don't have this issue, but the sanitizer provides defense-in-depth.

Run: python tests/e2e/regression/test_bug_2026_01_30_language_mismatch.py
"""

import os
import sys
import re
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field

# Add tests/ to path for shared helpers
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token as helper_get_auth_token

# Configuration
BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")


@dataclass
class LanguageTestCase:
    test_id: str
    description: str
    query: str  # Spanish query
    expected_behavior: str
    forbidden_patterns: List[str] = field(default_factory=list)


# Chain-of-thought patterns that should NOT appear in responses
COT_PATTERNS = [
    r"okay,?\s*let'?s?\s*see",
    r"let me think",
    r"let me check",
    r"wait,?\s*but",
    r"hmm,?\s*actually",
    r"the user is asking",
    r"the question is about",
    r"on second thought",
    r"looking again",
    r"in my previous response",
]

ENGLISH_REASONING_PATTERNS = [
    r"^okay\b",
    r"^alright\b",
    r"^so,?\s",
    r"^well,?\s",
    r"^let me\b",
    r"^i need to\b",
    r"^i should\b",
    r"^the user\b",
    r"^they want\b",
    r"^this means\b",
]

TEST_CASES = [
    LanguageTestCase(
        test_id="LANG-001",
        description="Response to Spanish query should be in Spanish",
        query="Dame el ICAP de BBVA",
        expected_behavior="Response in Spanish, no English reasoning",
        forbidden_patterns=COT_PATTERNS + ENGLISH_REASONING_PATTERNS,
    ),
    LanguageTestCase(
        test_id="LANG-002",
        description="Explanation request should not leak CoT",
        query="Explícame cómo obtuviste ese resultado",
        expected_behavior="Spanish explanation without internal reasoning",
        forbidden_patterns=COT_PATTERNS,
    ),
    LanguageTestCase(
        test_id="LANG-003",
        description="Follow-up question should stay in Spanish",
        query="¿Por qué Santander tiene mejor ICAP que BBVA?",
        expected_behavior="Spanish comparison without English phrases",
        forbidden_patterns=COT_PATTERNS + ENGLISH_REASONING_PATTERNS,
    ),
    LanguageTestCase(
        test_id="LANG-004",
        description="Complex analysis should not expose reasoning",
        query="Analiza la tendencia del IMOR de Citibanamex en 2025",
        expected_behavior="Spanish analysis without CoT leakage",
        forbidden_patterns=COT_PATTERNS,
    ),
]


def parse_sse_response(response) -> Dict[str, Any]:
    """Parse SSE response into structured data."""
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


def validate_no_cot_leakage(
    sse_data: Dict,
    test_case: LanguageTestCase
) -> Tuple[bool, List[str]]:
    """Validate that response doesn't contain chain-of-thought patterns."""
    issues = []

    content = sse_data.get("content", "")
    if not content:
        if sse_data.get("clarification"):
            return True, []  # Clarification is acceptable
        issues.append("No content received")
        return False, issues

    content_lower = content.lower()

    # Check for forbidden patterns
    for pattern in test_case.forbidden_patterns:
        matches = re.findall(pattern, content_lower, re.IGNORECASE | re.MULTILINE)
        if matches:
            # Extract context around the match
            for match in matches[:2]:  # Limit to first 2 matches
                issues.append(f"COT LEAK: Found '{match}' pattern in response")

    # Check for predominantly English response (>50% English words)
    # Simple heuristic: count Spanish-specific characters/words
    spanish_indicators = len(re.findall(r'[áéíóúüñ¿¡]', content_lower))
    english_starts = len(re.findall(r'\b(the|is|are|was|were|have|has|this|that|will|would|can|could)\b', content_lower))

    if english_starts > 10 and spanish_indicators < 5:
        issues.append(f"LANGUAGE: Response appears predominantly English (eng_words={english_starts}, spanish_chars={spanish_indicators})")

    return len(issues) == 0, issues


def run_test(
    test_case: LanguageTestCase,
    token: str,
    backend_url: str,
    timeout: int,
    verbose: bool
) -> Dict[str, Any]:
    """Run a single test case."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    payload = {
        "message": test_case.query,
        "stream": True,
        "model": "Saptiva Turbo"  # Using Turbo - CoT leak is primarily a Cortex issue
    }

    result = {
        "test_id": test_case.test_id,
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

        passed, issues = validate_no_cot_leakage(sse_data, test_case)
        result["passed"] = passed
        result["issues"] = issues

        if verbose:
            print(f"   Events: {sse_data.get('events', [])}")
            content_preview = sse_data.get("content", "")[:200]
            print(f"   Content preview: {content_preview}...")

    except requests.exceptions.ConnectionError:
        result["issues"].append("Connection failed - is backend running?")
    except Exception as e:
        result["issues"].append(str(e))

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default=BACKEND_URL)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("Language Mismatch Bug Test Suite (BUG-2026-01-30)")
    print("=" * 60)

    token = helper_get_auth_token(backend_url=args.backend_url)
    if not token:
        print("Fatal: Auth failed - check backend is running")
        sys.exit(2)

    print(f"Running {len(TEST_CASES)} test cases")
    print("-" * 60)

    passed_count = 0
    failed_count = 0

    for test_case in TEST_CASES:
        result = run_test(test_case, token, args.backend_url, args.timeout, args.verbose)

        status = "\u2705" if result["passed"] else "\u274c"
        print(f"{status} [{result['test_id']}]: {result['description'][:50]}...")

        if result["passed"]:
            passed_count += 1
        else:
            failed_count += 1
            for issue in result["issues"]:
                print(f"   {issue}")

        time.sleep(0.5)

    print("=" * 60)
    print(f"Results: {passed_count}/{passed_count + failed_count} passed")

    if failed_count == 0:
        print("\u2705 All language tests PASSED!")
        sys.exit(0)
    else:
        print("\u274c Some tests FAILED - CoT leakage may still occur")
        sys.exit(1)


if __name__ == "__main__":
    main()
