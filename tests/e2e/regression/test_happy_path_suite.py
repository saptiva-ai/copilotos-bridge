#!/usr/bin/env python3
"""
🧪 Happy Path Test Suite - Bank Advisor
Comprehensive validation of 40+ queries covering RAG, NL2SQL, Comparisons, and more.

Includes BA-001 (RAG grounding) and BA-002 (INVEX default bias) validation.
"""

import os
import sys
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
    parser = argparse.ArgumentParser(description="Run Happy Path Suite with debug helpers")
    parser.add_argument("--ids", type=str, help="Comma-separated case IDs to run (e.g., 1,2,5)")
    parser.add_argument("--category", type=str, help="Filter by category (e.g., NL2SQL)")
    parser.add_argument("--max", type=int, help="Max number of cases to run")
    parser.add_argument("--backend-url", type=str, default=BACKEND_URL, help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between cases (seconds)")
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop after first failure")
    parser.add_argument("--save-dir", type=str, default="happy_path_debug", help="Directory to store per-case debug dumps")
    parser.add_argument("--save-all", action="store_true", help="Save debug dumps for passing cases too (default only failures)")
    parser.add_argument("--no-save", action="store_true", help="Disable debug dumps")
    parser.add_argument("--verbose", action="store_true", help="Print extra debug info per case")
    return parser.parse_args()

@dataclass
class TestCase:
    id: int
    category: str
    query: str
    tier: int  # 1, 2, or 3
    expected_type: str  # "rag", "chart", "clarification"
    expected_keywords: List[str] = field(default_factory=list)  # Text keywords for RAG/Chart titles
    forbidden_keywords: List[str] = field(default_factory=list)  # BA-001: Keywords that should NOT appear
    value_range: Optional[Tuple[float, float]] = None
    min_confidence: float = 0.0

# Define the 40 Happy Path queries
TEST_CASES = [
    # --- 1️⃣ RAG - Definiciones y Conocimiento Regulatorio (Tier 3) ---
    TestCase(1, "RAG", "¿Qué es ICAP?", 3, "rag", ["Índice de Capitalización", "ICAP"]),
    TestCase(2, "RAG", "Define IMOR", 3, "rag", ["Índice de Morosidad", "IMOR"]),
    TestCase(3, "RAG", "¿Qué significa ICOR?", 3, "rag", ["Índice de Cobertura", "ICOR"]),
    TestCase(4, "RAG", "Explícame qué es la cartera vencida", 3, "rag", ["cartera vencida", "créditos"]),
    TestCase(5, "RAG", "¿Qué son las provisiones preventivas?", 3, "rag", ["provisiones", "reservas", "riesgo"]),

    # --- 2️⃣ NL2SQL - Métricas Simples de INVEX (Tier 1) ---
    TestCase(6, "NL2SQL", "Dame el IMOR de INVEX", 1, "chart", ["IMOR", "INVEX"], value_range=(0, 10)),
    TestCase(7, "NL2SQL", "¿Cuál es el ICAP de INVEX?", 1, "chart", ["ICAP", "INVEX"], value_range=(10, 30)),
    TestCase(8, "NL2SQL", "Muéstrame el ICOR de INVEX", 1, "chart", ["ICOR", "INVEX"], value_range=(0, 500)),
    TestCase(9, "NL2SQL", "Dame las reservas de INVEX", 1, "chart", ["Reservas", "INVEX"]),
    TestCase(10, "NL2SQL", "¿Cuál es la cartera total de INVEX?", 1, "chart", ["Cartera Total", "INVEX"]),

    # --- 3️⃣ Comparaciones INVEX vs Sistema (Tier 2) ---
    TestCase(11, "Comparison", "Compara el IMOR de INVEX contra el sistema", 2, "chart", ["IMOR", "Sistema"]),
    TestCase(12, "Comparison", "¿Cómo está mi ICAP vs el sistema?", 2, "chart", ["ICAP", "Sistema"]),
    TestCase(13, "Comparison", "ICOR de INVEX comparado con el promedio del sistema", 2, "chart", ["ICOR", "Sistema"]),
    # BA-002: Queries with "mi" but no explicit bank should trigger clarification
    TestCase(14, "Comparison", "Mi PDM medido por cartera total", 2, "clarification", ["PDM", "Market Share"]),

    # --- 4️⃣ Análisis Temporal (Tier 2) ---
    TestCase(15, "Temporal", "IMOR de INVEX en los últimos 3 meses", 2, "chart", ["IMOR", "INVEX"]),
    TestCase(16, "Temporal", "Evolución del ICAP de INVEX en los últimos 6 meses", 2, "chart", ["ICAP", "Evolución"]),
    TestCase(17, "Temporal", "Dame las reservas totales de INVEX al cierre del mes", 2, "chart", ["Reservas"]),
    TestCase(18, "Temporal", "Cartera vencida de INVEX en el último trimestre", 2, "chart", ["Cartera", "Vencida", "CARTERA_VENCIDA"]),
    TestCase(19, "Temporal", "ICOR de INVEX durante 2024", 2, "chart", ["ICOR", "2024"]),

    # --- 5️⃣ Multi-Banco (Tier 2) ---
    TestCase(20, "Multi-Bank", "Compara IMOR entre INVEX, BBVA y Santander", 2, "chart", ["IMOR", "BBVA", "Santander"]),
    TestCase(21, "Multi-Bank", "Top 5 bancos por cartera total", 2, "chart", ["Top", "Cartera"]),
    TestCase(22, "Multi-Bank", "¿Qué bancos tienen mejor ICAP?", 2, "chart", ["ICAP", "Ranking"]),
    TestCase(23, "Multi-Bank", "Ranking de ICOR del sistema", 2, "chart", ["ICOR", "Ranking"]),
    TestCase(24, "Multi-Bank", "IMOR de los principales bancos del sistema", 2, "chart", ["IMOR"]),

    # --- 6️⃣ Segmentación de Cartera (Tier 1) ---
    TestCase(25, "Segmentation", "Cartera comercial de INVEX", 1, "chart", ["Cartera Comercial", "INVEX"]),
    # BA-002: "mi" indicates data request but no explicit bank → should clarify
    # Options should include: INVEX, BBVA, Santander, etc.
    TestCase(26, "Segmentation", "¿Cuál es mi cartera de consumo?", 1, "clarification", ["banco", "INVEX"]),
    TestCase(27, "Segmentation", "Dame la cartera hipotecaria de INVEX", 1, "chart", ["Cartera Hipotecaria", "INVEX"]),
    TestCase(28, "Segmentation", "Cartera de crédito corporativo de INVEX", 1, "chart", ["Crédito Corporativo"]),
    TestCase(29, "Segmentation", "Distribución de cartera por segmento de INVEX", 1, "chart", ["Distribución", "Cartera"]),

    # --- 7️⃣ Queries Complejos (Tier 2) ---
    # BA-002: "mi" without explicit bank triggers clarification
    TestCase(30, "Complex", "Cómo está mi PDM medido por cartera total en los últimos 6 meses", 2, "clarification", ["PDM", "Cartera"]),
    TestCase(31, "Complex", "Evolución de reservas preventivas de INVEX vs sistema en 2024", 2, "chart", ["Reservas", "Sistema", "2024"]),
    TestCase(32, "Complex", "Tendencia del IMOR de INVEX comparado con BBVA último año", 2, "chart", ["IMOR", "BBVA"]),
    # BA-002: No bank specified triggers clarification
    TestCase(33, "Complex", "¿Cuál es la tasa de crédito corporativo en moneda nacional?", 2, "clarification", ["Tasa", "Corporativo"]),
    # SMART BEHAVIOR: "capitalización" is ambiguous (ICAP vs Market Cap)
    # System correctly asks for clarification with options
    TestCase(34, "Complex", "Dame el ratio de capitalización de INVEX con desglose por tipo", 2, "clarification", ["ICAP", "Mercado"]),

    # --- 8️⃣ Edge Cases & Variaciones (Tier 2/1) ---
    TestCase(35, "Edge Case", "Cuánto es el índice de mora de INVEX", 1, "chart", ["IMOR", "INVEX"]),
    TestCase(36, "Edge Case", "Provisiones de INVEX", 1, "chart", ["Reservas", "INVEX"]),
    TestCase(37, "Edge Case", "Cobertura de INVEX", 1, "chart", ["ICOR", "INVEX"]),
    # BA-002: "Mi" without explicit bank triggers clarification
    TestCase(38, "Edge Case", "Mi market share", 2, "clarification", ["PDM", "Market Share"]),
    TestCase(39, "Edge Case", "¿Qué tan capitalizado está INVEX?", 2, "chart", ["ICAP"]),
    # BA-002: "del banco" is ambiguous, triggers clarification
    TestCase(40, "Edge Case", "Cartera total del banco", 1, "clarification", ["Cartera Total"]),

    # --- 9️⃣ BA-001: RAG Grounding Tests (ICAP/IMOR cross-contamination) ---
    TestCase(41, "BA-001", "¿Qué es ICAP?", 3, "rag",
             ["ICAP", "Capitalización", "capital"], ["IMOR", "Morosidad", "mora", "cartera vencida"]),
    TestCase(42, "BA-001", "¿Qué es IMOR?", 3, "rag",
             ["IMOR", "Morosidad", "mora"], ["ICAP", "Capitalización", "capital regulatorio"]),
    TestCase(43, "BA-001", "Define ICOR", 3, "rag",
             ["ICOR", "Cobertura"], ["IMOR", "ICAP"]),
    TestCase(44, "BA-001", "¿Qué significa PDM?", 3, "rag",
             ["PDM", "incumplimiento", "default"], ["IMOR", "ICAP", "ICOR"]),

    # --- 🔟 BA-002: INVEX Default Bias Tests (queries without bank) ---
    # These queries should trigger clarification, NOT default to INVEX
    # Note: No forbidden_keywords here because INVEX can appear in clarification options
    TestCase(45, "BA-002", "Dame el IMOR", 2, "clarification", []),
    TestCase(46, "BA-002", "¿Cuál es el ICAP?", 2, "clarification", []),
    TestCase(47, "BA-002", "Muéstrame las reservas", 2, "clarification", []),
]

def get_auth_token(backend_url: str = BACKEND_URL) -> Optional[str]:
    """Get auth token using shared helper."""
    return helper_get_auth_token(backend_url=backend_url)

def parse_sse_response(response, raw_log: Optional[List[str]] = None) -> Dict[str, Any]:
    result = {
        "events": [],
        "bank_chart": None,
        "content": "",
        "clarification": None,
        "error": None
    }
    
    current_event = None
    
    for line in response.iter_lines():
        if not line: continue
        decoded = line.decode('utf-8')
        if raw_log is not None:
            raw_log.append(decoded)
        
        if decoded.startswith('event:'):
            current_event = decoded.replace('event:', '').strip()
            result["events"].append(current_event)
        elif decoded.startswith('data:') and current_event:
            data = decoded.replace('data:', '').strip()
            if data == "[DONE]": continue
            
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

def run_test_case(
    test_case: TestCase,
    token: str,
    *,
    backend_url: str,
    timeout: int,
    save_dir: Optional[Path],
    save_all: bool,
    verbose: bool
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    payload = {
        "message": test_case.query,
        "stream": True,
        "model": "Saptiva Turbo"
    }

    start_time = time.time()
    result = {
        "id": test_case.id,
        "query": test_case.query,
        "passed": False,
        "latency_ms": 0,
        "issues": [],
        "type_received": "unknown",
        "details": {}
    }

    try:
        raw_log: Optional[List[str]] = [] if (save_dir or verbose) else None

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

        sse_data = parse_sse_response(response, raw_log=raw_log)
        end_time = time.time()
        result["latency_ms"] = (end_time - start_time) * 1000

        # Validate Response Type
        if sse_data["bank_chart"]:
            result["type_received"] = "chart"
            chart = sse_data["bank_chart"]
            
            # DEBUG: Print chart data for failed tests
            sql_prev = chart.get('metadata', {}).get('sql_generated', '')[:50].replace('\n', ' ')
            chart_data = chart.get('plotly_config', {}).get('data', [])
            trace_preview = "No data traces"
            if chart_data:
                trace_preview = str(chart_data[0].get('y', []))[:100]
            print(f"DEBUG [{test_case.id}]: Type={chart.get('type')}, Plotly Data Len={len(chart_data)}, SQL={sql_prev}..., Y-Preview={trace_preview}")
            
            # Title Validation
            title = chart.get("title", "") or chart.get("metric_name", "") or ""
            metadata = chart.get("metadata", {})
            full_title = f"{title} {metadata.get('title', '')}"
            
            matches = [kw for kw in test_case.expected_keywords if kw.lower() in full_title.lower()]
            if not matches and test_case.expected_keywords:
                result["issues"].append(f"Title missing keywords {test_case.expected_keywords}. Got: '{full_title}'")

            # Data Validation
            has_data = False
            for trace in chart.get("plotly_config", {}).get("data", []):
                if any(y is not None for y in trace.get("y", [])):
                    has_data = True
                    break
            
            if not has_data:
                result["issues"].append("Chart has no data points")

            # BA-002: Check forbidden keywords in chart (e.g., INVEX when not requested)
            chart_text = f"{full_title} {' '.join(chart.get('bank_names', []))}".lower()
            for forbidden in test_case.forbidden_keywords:
                if forbidden.lower() in chart_text:
                    result["issues"].append(f"BIAS FAIL: Chart contains '{forbidden}' when not requested")

        # FIX 2026-01-14: Check clarification BEFORE RAG to avoid false detection
        # when clarification responses contain text that looks like RAG content
        elif sse_data["clarification"]:
            result["type_received"] = "clarification"
            if test_case.expected_type != "clarification":
                result["issues"].append("Got clarification but expected data/rag")

            # BA-002: Check that clarification doesn't mention INVEX as default
            clarif_text = json.dumps(sse_data["clarification"]).lower()
            for forbidden in test_case.forbidden_keywords:
                if forbidden.lower() in clarif_text:
                    result["issues"].append(f"BIAS FAIL: Clarification mentions '{forbidden}' when it shouldn't")

        elif "Índice" in sse_data["content"] or "definic" in sse_data["content"] or len(sse_data["content"]) > 50:
            # Simple heuristic for RAG content detection
            result["type_received"] = "rag"
            content = sse_data["content"]

            # Check expected keywords
            matches = [kw for kw in test_case.expected_keywords if kw.lower() in content.lower()]
            if not matches and test_case.expected_keywords:
                result["issues"].append(f"RAG content missing keywords {test_case.expected_keywords}")

            # BA-001: Check forbidden keywords (grounding validation)
            for forbidden in test_case.forbidden_keywords:
                if forbidden.lower() in content.lower():
                    result["issues"].append(f"GROUNDING FAIL: Found forbidden term '{forbidden}' in response")

        else:
            result["issues"].append("Empty response or unknown type")

        # Type mismatch check
        if test_case.expected_type == "chart" and result["type_received"] != "chart":
             result["issues"].append(f"Expected chart, got {result['type_received']}")
        elif test_case.expected_type == "rag" and result["type_received"] != "rag":
             result["issues"].append(f"Expected RAG text, got {result['type_received']}")
        elif test_case.expected_type == "clarification" and result["type_received"] != "clarification":
             # BA-002: Queries without bank should trigger clarification
             result["issues"].append(f"Expected clarification, got {result['type_received']}")

        # Latency check (Soft fail)
        # Tier 1 < 1s (relaxed from 500ms due to network), Tier 2 < 5s, Tier 3 < 3s
        thresholds = {1: 2000, 2: 8000, 3: 5000}  # Relaxed for local test
        limit = thresholds.get(test_case.tier, 5000)
        if result["latency_ms"] > limit:
            result["details"]["latency_warning"] = f"Exceeded Tier {test_case.tier} limit ({limit}ms)"

        if not result["issues"]:
            result["passed"] = True

    except Exception as e:
        result["issues"].append(str(e))

    if verbose:
        print(f"   Events: {sse_data.get('events', []) if 'sse_data' in locals() else 'N/A'}")
        print(f"   Type: {result['type_received']} | Latency: {result['latency_ms']:.0f}ms")
        if 'sse_data' in locals():
            print(f"   Content preview: {sse_data.get('content','')[:120]}...")

    should_save = save_dir and ((not result["passed"]) or save_all)
    if should_save:
        save_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{test_case.id:02d}__{slugify(test_case.query)}.json"
        debug_dump = {
            "payload": payload,
            "status_code": response.status_code if 'response' in locals() else None,
            "type_received": result["type_received"],
            "latency_ms": result["latency_ms"],
            "issues": result["issues"],
            "sse": {
                "events": sse_data.get("events") if 'sse_data' in locals() else None,
                "raw": raw_log if 'raw_log' in locals() else None,
                "parsed": sse_data if 'sse_data' in locals() else None,
            },
            "result": result,
        }
        with open(save_dir / fname, "w", encoding="utf-8") as f:
            json.dump(debug_dump, f, indent=2, ensure_ascii=False)

    return result

def main():
    args = parse_args()
    token = get_auth_token(args.backend_url)
    if not token:
        print(f"❌ Fatal: Auth failed (user={AUTH_USER}, backend={args.backend_url})")
        return

    cases = TEST_CASES
    if args.ids:
        wanted_ids = {int(x) for x in args.ids.split(",") if x.strip()}
        cases = [c for c in cases if c.id in wanted_ids]
    if args.category:
        cases = [c for c in cases if c.category.lower() == args.category.lower()]
    if args.max:
        cases = cases[:args.max]

    save_dir = None if args.no_save else Path(args.save_dir)

    print(f"🚀 Starting Happy Path Suite (N={len(cases)})")
    if args.backend_url != BACKEND_URL:
        print(f"   Backend: {args.backend_url}")
    if args.ids or args.category or args.max:
        print(f"   Filters -> ids:{args.ids} category:{args.category} max:{args.max}")
    print("-" * 60)
    
    stats = {"pass": 0, "fail": 0}
    results = []

    for case in cases:
        res = run_test_case(
            case,
            token,
            backend_url=args.backend_url,
            timeout=args.timeout,
            save_dir=save_dir,
            save_all=args.save_all,
            verbose=args.verbose,
        )
        results.append(res)
        
        status_icon = "✅" if res["passed"] else "❌"
        print(f"{status_icon} [{case.id}] {case.category}: {case.query[:50]}...")
        if not res["passed"]:
            for issue in res["issues"]:
                print(f"   ↳ {issue}")
        if "latency_warning" in res["details"]:
             print(f"   ⚠️  Latency: {res['latency_ms']:.0f}ms")
        
        if res["passed"]: stats["pass"] += 1
        else: stats["fail"] += 1
        
        if args.stop_on_fail and not res["passed"]:
            print("🛑 Stop on fail enabled, aborting further cases.")
            break

        time.sleep(args.sleep) 

    print("-" * 60)
    total_cases = len(cases) if cases else 1
    print(f"📊 Summary: {stats['pass']}/{total_cases} Passed ({stats['pass']/total_cases*100:.1f}%)")
    failed = [r for r in results if not r["passed"]]
    if failed:
        issue_counter: Dict[str, int] = {}
        for r in failed:
            for issue in r["issues"]:
                issue_counter[issue] = issue_counter.get(issue, 0) + 1
        top_issues = sorted(issue_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        print("🔍 Top failure reasons:")
        for issue, count in top_issues:
            print(f"   - ({count}) {issue}")
    
    with open("happy_path_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("💾 Results saved to happy_path_results.json")

if __name__ == "__main__":
    main()
