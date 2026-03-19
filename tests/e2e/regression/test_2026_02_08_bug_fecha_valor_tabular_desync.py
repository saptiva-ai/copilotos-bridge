#!/usr/bin/env python3
"""
E2E Regression: Fecha-Valor Tabular Desync (BUG-2026-02-08)

Goal:
Detect regressions where the LLM table aligns a value with the wrong date
when one bank has missing months.

Validations per case:
1. bank_chart exists with chart_status=success
2. every trace has len(x) == len(y)
3. markdown table exists for table-mode queries
4. each table cell (date, bank, value) matches chart trace data by exact date key
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message


BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "90"))
RESULTS_PATH = Path(__file__).with_name("fecha_valor_tabular_desync_results.json")

TOLERANCE = 0.11

MONTHS = {
    "ene": 1,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
    "dec": 12,
}


@dataclass
class BugTestCase:
    case_id: str
    description: str
    query: str
    require_table: bool = True


@dataclass
class CaseResult:
    case_id: str
    description: str
    query: str
    passed: bool
    detail: str


TEST_CASES: List[BugTestCase] = [
    BugTestCase(
        case_id="TABSYNC-001",
        description="ICAP multi-bank full table should preserve date-value mapping",
        query="dame los datos del ICAP de BBVA y Santander en 2025",
    ),
    BugTestCase(
        case_id="TABSYNC-002",
        description="IMOR multi-bank full table should preserve date-value mapping",
        query="dame los datos del IMOR de BBVA y Santander en 2024",
    ),
    BugTestCase(
        case_id="TABSYNC-003",
        description="Cartera comercial multi-bank full table should preserve date-value mapping",
        query="dame los datos de la cartera comercial de BBVA y Santander en 2025",
    ),
]


def _normalize_text(value: str) -> str:
    clean = (
        unicodedata.normalize("NFD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )
    return clean


def _normalize_bank_name(name: str) -> str:
    clean = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
    return _normalize_text(clean).upper()


def _month_key_from_label(label: str) -> Optional[str]:
    text = label.strip()

    m_iso = re.match(r"^(\d{4})-(\d{2})(?:-\d{2})?$", text)
    if m_iso:
        return f"{m_iso.group(1)}-{m_iso.group(2)}-01"

    m_named = re.match(r"^([A-Za-zÁÉÍÓÚáéíóú.]+)\s+(\d{4})$", text)
    if not m_named:
        return None

    month_token = _normalize_text(m_named.group(1).replace(".", ""))
    year = int(m_named.group(2))
    month = MONTHS.get(month_token[:3])
    if not month:
        return None
    return f"{year:04d}-{month:02d}-01"


def _extract_table_block(content: str) -> Optional[List[str]]:
    blocks: List[List[str]] = []
    current: List[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("|"):
            current.append(line)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)

    for block in blocks:
        if block and "Período" in block[0]:
            return block
    return None


def _split_row(line: str) -> List[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def _parse_numeric(cell: str) -> Optional[float]:
    raw = cell.strip()
    if raw in {"—", "-", ""}:
        return None
    m = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?", raw)
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


def _build_chart_map(bank_chart: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Dict[str, float]]]:
    plotly = bank_chart.get("plotly_config", {}) or {}
    traces = plotly.get("data", []) or []
    if not traces:
        return "No traces in plotly_config.data", {}

    data: Dict[str, Dict[str, float]] = {}
    for trace in traces:
        name = _normalize_bank_name(str(trace.get("name", "")))
        x_vals = trace.get("x", []) or []
        y_vals = trace.get("y", []) or []

        if len(x_vals) != len(y_vals):
            return f"Trace '{name}' has len(x)={len(x_vals)} != len(y)={len(y_vals)}", {}

        series = data.setdefault(name, {})
        for x, y in zip(x_vals, y_vals):
            key = _month_key_from_label(str(x))
            if not key or y is None:
                continue
            try:
                series[key] = float(y)
            except (ValueError, TypeError):
                continue

    return None, data


def _validate_table_against_chart(
    content: str, chart_map: Dict[str, Dict[str, float]]
) -> Tuple[bool, str]:
    block = _extract_table_block(content)
    if not block:
        return False, "No markdown table with 'Período' found in response content"
    if len(block) < 3:
        return False, "Markdown table is incomplete"

    header_cells = _split_row(block[0])
    if len(header_cells) < 2:
        return False, "Table header has no bank columns"

    table_banks = [_normalize_bank_name(h) for h in header_cells[1:]]

    mismatches: List[str] = []

    for row in block[2:]:
        cells = _split_row(row)
        if len(cells) < 2:
            continue
        date_key = _month_key_from_label(cells[0])
        if not date_key:
            continue

        values = cells[1:]
        for idx, bank in enumerate(table_banks):
            if idx >= len(values):
                continue
            table_value = _parse_numeric(values[idx])
            chart_value = chart_map.get(bank, {}).get(date_key)

            if table_value is None:
                if chart_value is not None:
                    mismatches.append(
                        f"{bank} {date_key}: table='—' but chart={chart_value:.2f}"
                    )
                continue

            if chart_value is None:
                mismatches.append(
                    f"{bank} {date_key}: table={table_value:.2f} but chart missing"
                )
                continue

            if abs(table_value - chart_value) > TOLERANCE:
                mismatches.append(
                    f"{bank} {date_key}: table={table_value:.2f} chart={chart_value:.2f}"
                )

    if mismatches:
        preview = "; ".join(mismatches[:4])
        return False, f"Date-value mismatches detected: {preview}"

    return True, "Table values align with chart data by date key"


def _run_case(token: str, case: BugTestCase) -> CaseResult:
    response = send_chat_message(
        token=token,
        message=case.query,
        backend_url=BACKEND_URL,
        timeout=TIMEOUT,
    )

    if response.get("error"):
        return CaseResult(
            case_id=case.case_id,
            description=case.description,
            query=case.query,
            passed=False,
            detail=f"Request error: {response['error']}",
        )

    bank_chart = response.get("bank_chart")
    if not isinstance(bank_chart, dict):
        return CaseResult(
            case_id=case.case_id,
            description=case.description,
            query=case.query,
            passed=False,
            detail="No bank_chart payload in SSE response",
        )

    status = str(bank_chart.get("chart_status", ""))
    if status != "success":
        return CaseResult(
            case_id=case.case_id,
            description=case.description,
            query=case.query,
            passed=False,
            detail=f"chart_status={status} (expected success)",
        )

    axis_error, chart_map = _build_chart_map(bank_chart)
    if axis_error:
        return CaseResult(
            case_id=case.case_id,
            description=case.description,
            query=case.query,
            passed=False,
            detail=axis_error,
        )

    if case.require_table:
        ok, detail = _validate_table_against_chart(
            content=response.get("content", ""),
            chart_map=chart_map,
        )
        return CaseResult(
            case_id=case.case_id,
            description=case.description,
            query=case.query,
            passed=ok,
            detail=detail,
        )

    return CaseResult(
        case_id=case.case_id,
        description=case.description,
        query=case.query,
        passed=True,
        detail="Chart alignment checks passed",
    )


def main() -> int:
    print("=" * 72)
    print("E2E Regression: BUG-2026-02-08 Fecha-Valor Tabular Desync")
    print("=" * 72)
    print(f"Backend URL: {BACKEND_URL}")

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print("FAIL: Could not authenticate against backend.")
        return 1

    results: List[CaseResult] = []
    for case in TEST_CASES:
        print(f"\n[{case.case_id}] {case.description}")
        result = _run_case(token, case)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"{status}: {result.detail}")

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    payload = {
        "bug_id": "2026-02-08__BUG__fecha-valor-tabular-desync",
        "backend_url": BACKEND_URL,
        "passed": passed,
        "failed": failed,
        "results": [asdict(r) for r in results],
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    print("\n" + "-" * 72)
    print(f"Results saved: {RESULTS_PATH}")
    print(f"Summary: {passed} passed, {failed} failed")
    print("-" * 72)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
