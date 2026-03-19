#!/usr/bin/env python3
"""
E2E Regression — Value Swap Detection (Cross-Bank / Cross-Month)

Detects the subtle grounding bug where the LLM cites REAL values but
attributes them to the wrong bank or month. This differs from hallucination
(inventing numbers) — here the numbers exist in the data but are misattributed.

Swap categories:
  CROSS_BANK:  Value belongs to Bank A but text says it's Bank B
  CROSS_MONTH: Value belongs to Month X but text says it's Month Y
  TREND_SWAP:  Bank A grew but text says Bank B grew (or vice versa)
  RANK_SWAP:   Text says "the highest was Bank A" but Bank B had the max

Scenarios:
  VSD-01: 2-bank comparison, same metric, 12 months → detect bank swaps
  VSD-02: 3-bank comparison, same metric → detect ranking swaps
  VSD-03: Single bank, explicit months → detect month swaps
  VSD-04: 2-bank trend description → detect trend direction swaps
  VSD-05: Dense comparison (3 banks × Q1 2025) → max swap opportunity
  VSD-06: Cross-bank ratio query → detect ratio misattribution
  VSD-07: Year-over-year for 2 banks → cross-bank temporal swaps
  VSD-08: "cuál es el mayor/menor" → ranking attribution check
  VSD-09: Multi-year month comparison → truncation-before-filtering bug
  VSD-10: 10-bank query → max_series truncation bug

Usage:
    python tests/e2e/regression/test_value_swap_detection.py

Requires:
    - Backend running at TEST_BACKEND_URL (default: http://localhost:8000)
    - Valid test credentials (TEST_AUTH_USER / TEST_AUTH_PASS)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token, send_chat_message

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

# Tolerance for value matching (1% relative or 0.1 absolute)
RELATIVE_TOLERANCE = 0.01
ABSOLUTE_TOLERANCE = 0.1


# ══════════════════════════════════════════════════════════════════════════════
# Ground truth extraction from chart data
# ══════════════════════════════════════════════════════════════════════════════


def _close(a: float, b: float) -> bool:
    """Check if two values are approximately equal."""
    if b == 0:
        return abs(a) < ABSOLUTE_TOLERANCE
    return abs(a - b) / abs(b) <= RELATIVE_TOLERANCE or abs(a - b) <= ABSOLUTE_TOLERANCE


# FIX 2026-02-11: Lenient tolerance for "is the value plausibly correct for this month?"
# Prevents false-positive cross-month swaps when adjacent months have similar values
# (e.g., ICAP 15.89% vs 15.76% — only 0.82% apart → could be rounding/display drift).
_LENIENT_RELATIVE_TOLERANCE = 0.02  # 2%
_LENIENT_ABSOLUTE_TOLERANCE = 1.0


def _close_lenient(a: float, b: float) -> bool:
    """Lenient check — is the value plausibly correct (not just matching another month)?"""
    if b == 0:
        return abs(a) < _LENIENT_ABSOLUTE_TOLERANCE
    return (
        abs(a - b) / abs(b) <= _LENIENT_RELATIVE_TOLERANCE
        or abs(a - b) <= _LENIENT_ABSOLUTE_TOLERANCE
    )


def extract_bank_time_series(
    bank_chart: Dict[str, Any],
) -> Dict[str, List[Tuple[str, float]]]:
    """Extract per-bank time series as {BANK: [(date_str, value), ...]}."""
    result: Dict[str, List[Tuple[str, float]]] = {}
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return result
    for trace in plotly.get("data", []):
        name = (trace.get("name") or "").upper().strip()
        if not name:
            continue
        x_vals = trace.get("x", [])
        y_vals = trace.get("y", [])
        series = []
        for x, y in zip(x_vals, y_vals):
            if y is not None and isinstance(y, (int, float)):
                series.append((str(x), float(y)))
        if series:
            result[name] = series
    return result


def build_ground_truth_map(
    bank_series: Dict[str, List[Tuple[str, float]]],
) -> Dict[Tuple[str, str], float]:
    """Build (bank, month_label) → value map for swap detection.

    Normalizes dates from ISO (2025-01-01) or short (Ene 2025) to a
    canonical "Mmm YYYY" label for matching against LLM text.
    """
    month_labels = {
        "01": "Ene",
        "02": "Feb",
        "03": "Mar",
        "04": "Abr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Ago",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dic",
    }
    gt: Dict[Tuple[str, str], float] = {}
    for bank, series in bank_series.items():
        for date_str, value in series:
            label = _normalize_date_label(date_str, month_labels)
            if label:
                gt[(bank, label)] = value
    return gt


def _normalize_date_label(date_str: str, month_labels: Dict[str, str]) -> Optional[str]:
    """Convert various date formats to 'Mmm YYYY'."""
    # Synthetic label from bar chart extraction — pass through as-is
    if date_str == "latest":
        return "latest"
    # ISO: 2025-01-01, 2025-01-15, 2025-01
    iso_match = re.match(r"(\d{4})-(\d{2})(?:-\d{2})?", date_str)
    if iso_match:
        year, month = iso_match.group(1), iso_match.group(2)
        abbr = month_labels.get(month)
        if abbr:
            return f"{abbr} {year}"
    # Already short: "Ene 2025", "ene 2025"
    short_match = re.match(
        r"(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)\s+(\d{4})",
        date_str,
        re.IGNORECASE,
    )
    if short_match:
        return f"{short_match.group(1).capitalize()} {short_match.group(2)}"
    return None


def extract_bank_values_from_bar_chart(
    bank_chart: Dict[str, Any],
) -> Dict[str, List[Tuple[str, float]]]:
    """Extract per-bank values from horizontal bar charts (ranking handler).

    Bar charts store banks in y-axis and values in x-axis within a single trace,
    unlike line charts which use one trace per bank with `name`.
    Returns the same format as extract_bank_time_series for compatibility.
    """
    result: Dict[str, List[Tuple[str, float]]] = {}
    plotly = bank_chart.get("plotly_config", {})
    if not plotly:
        return result
    for trace in plotly.get("data", []):
        trace_type = (trace.get("type") or "").lower()
        orientation = (trace.get("orientation") or "").lower()
        # Horizontal bar: banks in y, values in x
        if trace_type == "bar" and orientation == "h":
            banks = trace.get("y", [])
            values = trace.get("x", [])
        # Vertical bar: banks in x, values in y
        elif trace_type == "bar":
            banks = trace.get("x", [])
            values = trace.get("y", [])
        else:
            continue
        for bank_name, value in zip(banks, values):
            if bank_name and value is not None and isinstance(value, (int, float)):
                key = str(bank_name).upper().strip()
                result.setdefault(key, []).append(("latest", float(value)))
    return result


def build_value_to_bank_map(
    gt_map: Dict[Tuple[str, str], float],
) -> Dict[float, List[Tuple[str, str]]]:
    """Reverse map: value → [(bank, month), ...] for swap detection.

    Groups by rounded value (2 decimal places) to handle minor precision.
    """
    reverse: Dict[float, List[Tuple[str, str]]] = {}
    for (bank, month), value in gt_map.items():
        key = round(value, 2)
        reverse.setdefault(key, []).append((bank, month))
    return reverse


# ══════════════════════════════════════════════════════════════════════════════
# Citation extraction from LLM text
# ══════════════════════════════════════════════════════════════════════════════

# Month name → canonical abbreviation
MONTH_MAP = {
    "enero": "Ene",
    "febrero": "Feb",
    "marzo": "Mar",
    "abril": "Abr",
    "mayo": "May",
    "junio": "Jun",
    "julio": "Jul",
    "agosto": "Ago",
    "septiembre": "Sep",
    "octubre": "Oct",
    "noviembre": "Nov",
    "diciembre": "Dic",
    "ene": "Ene",
    "feb": "Feb",
    "mar": "Mar",
    "abr": "Abr",
    "may": "May",
    "jun": "Jun",
    "jul": "Jul",
    "ago": "Ago",
    "sep": "Sep",
    "oct": "Oct",
    "nov": "Nov",
    "dic": "Dic",
}

# Known bank names for attribution search
KNOWN_BANKS = [
    "INVEX",
    "BBVA",
    "BANORTE",
    "SANTANDER",
    "SCOTIABANK",
    "HSBC",
    "CITIBANAMEX",
    "AFIRME",
    "BANREGIO",
    "BAJIO",
    "INBURSA",
    "MULTIVA",
    "SISTEMA",
    "CIBANCO",
    "MONEX",
    "MIFEL",
    "INTERCAM",
    "ACTINVER",
    "BANCO BASE",
    "VE POR MAS",
    "COMPARTAMOS",
    "BANCOPPEL",
    "AZTECA",
]

# False-negative phrases — synced with response_postprocessor.py FALSE_NEGATIVE_PHRASES.
# Detects when the LLM claims "no tengo datos" despite chart_status=success.
FALSE_NEGATIVE_PHRASES = [
    "no encuentro información",
    "no tengo información",
    "no dispongo de información",
    "no puedo encontrar",
    "no hay datos",
    "no tengo datos",
    "no tengo el dato",
    "no cuento con datos",
    "no cuento con información",
    "no está disponible",
    "información no disponible",
    "no se encontró",
    "sin información",
    "lamentablemente no",
    "desafortunadamente no",
]

FALSE_NEGATIVE_EXCEPTIONS = [
    "no hay datos históricos",
    "no hay datos adicionales",
    "no hay datos para ese período",
    # Partial data statements: LLM correctly reports missing data for a
    # specific bank/metric while still analyzing the rest.
    "no tengo datos para",
    "no hay datos para",
    "solo tengo datos",
    "sólo tengo datos",
]


def detect_false_negatives(
    text: str,
    chart_status: str,
) -> List[str]:
    """Detect false-negative phrases when chart data exists.

    Returns list of matched phrases. Empty list = no false negatives.
    """
    if chart_status != "success" or not text:
        return []
    lower = text.lower()
    # Exception phrases are valid uses (e.g., "no hay datos históricos")
    for exc in FALSE_NEGATIVE_EXCEPTIONS:
        if exc in lower:
            return []
    return [phrase for phrase in FALSE_NEGATIVE_PHRASES if phrase in lower]


@dataclass
class CitedTriple:
    """A (bank, month, value) triple extracted from LLM text."""

    bank: str
    month: str  # "Mmm YYYY" canonical format
    value: float
    raw_text: str  # Original text span
    line_number: int = 0


def extract_cited_triples(text: str) -> List[CitedTriple]:
    """Extract (bank, month, value) triples from LLM response.

    Strategy:
    1. Find (month year ... value) patterns via regex
    2. Search nearby text (backwards 200 chars, forwards 100) for bank name
    3. Assemble into CitedTriple
    """
    bank_pattern = re.compile(
        r"\b(" + "|".join(re.escape(b) for b in KNOWN_BANKS) + r")\b",
        re.IGNORECASE,
    )

    # Match: month_name [de] year ... numeric_value
    value_pattern = re.compile(
        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre|"
        r"ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
        r"\.?\s+(?:de\s+)?(20\d{2})"
        r"[^0-9]{0,80}?"
        r"([\d]{1,3}(?:[,.][\d]{3})*(?:\.[\d]{1,2})?)",
        re.IGNORECASE,
    )

    results: List[CitedTriple] = []
    lines = text.split("\n")
    char_offset = 0
    line_map: List[Tuple[int, int]] = []  # (start, end) per line
    for i, line in enumerate(lines):
        line_map.append((char_offset, char_offset + len(line)))
        char_offset += len(line) + 1

    for match in value_pattern.finditer(text):
        month_raw = match.group(1).lower()
        year = match.group(2)
        value_raw = match.group(3)

        month_abbr = MONTH_MAP.get(month_raw, month_raw.capitalize()[:3])
        month_label = f"{month_abbr} {year}"

        # Parse value: handle both "12,403.17" and "12.403,17" formats
        value_str = value_raw.replace(",", "")
        try:
            value = float(value_str)
        except ValueError:
            continue

        # Skip arithmetic expressions
        after_val = text[match.end() : match.end() + 5]
        before_val = text[max(0, match.start(3) - 3) : match.start(3)]
        if re.search(r"^\s*[-=]", after_val) or re.search(r"[=]\s*$", before_val):
            continue

        # Skip if gap between month and value contains another month name
        gap = text[match.end(2) : match.start(3)]
        if re.search(
            r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
            r"septiembre|octubre|noviembre|diciembre)\b",
            gap,
            re.IGNORECASE,
        ):
            continue

        # Skip if gap contains context-switching words — the value belongs
        # to a different temporal/statistical context, not the captured month.
        # Examples: "mínimo histórico de 0.80%", "promedio de 3.5%"
        if re.search(
            r"(m[ií]nimo|m[aá]ximo|promedio|hist[oó]ric[oa])",
            gap,
            re.IGNORECASE,
        ):
            continue

        # Skip range expressions: "(de 15,047 a 16,402)" — value is range
        # start, not the value for the captured month.
        before_value = text[max(0, match.start(3) - 5) : match.start(3)]
        if re.search(r"\(de\s*$", before_value):
            continue

        # Find nearest bank name
        bank = _find_nearest_bank(text, match, bank_pattern)

        # Determine line number
        line_num = 0
        for i, (start, end) in enumerate(line_map):
            if start <= match.start() < end:
                line_num = i + 1
                break

        results.append(
            CitedTriple(
                bank=bank,
                month=month_label,
                value=value,
                raw_text=text[max(0, match.start() - 30) : match.end() + 10].strip(),
                line_number=line_num,
            )
        )

    return results


_PARAGRAPH_BOUNDARIES = ("\n- **", "\n\n", "\n### ", "\n## ")


def _find_nearest_bank(text: str, match: re.Match, bank_pattern: re.Pattern) -> str:
    """Search for bank name near a cited value, using proximity heuristics.

    Priority order:
    1. Immediately after the value (≤40 chars) — catches "16,402.59 MDP de INVEX"
    2. Within the gap between month+year and value
    3. Before the match (up to 400 chars, trimmed to paragraph boundary)
    4. After the match (up to 200 chars, trimmed to paragraph boundary)
    """
    # 1. Immediately after the value (highest priority — "X MDP de BANCO")
    # Trim to paragraph boundary to avoid cross-section attribution.
    after_value = text[match.end() : match.end() + 40]
    for boundary in _PARAGRAPH_BOUNDARIES:
        idx = after_value.find(boundary)
        if idx >= 0:
            after_value = after_value[:idx]
            break
    bank_right = bank_pattern.search(after_value)
    if bank_right:
        return bank_right.group(1).upper()

    # 2. Within the gap (between month+year and value)
    gap_start = match.start() + len(match.group(1)) + len(match.group(2)) + 2
    gap_text = text[gap_start : match.start(3)]
    gap_banks = list(bank_pattern.finditer(gap_text))
    if gap_banks:
        return gap_banks[-1].group(1).upper()

    # 3. Before the match (up to 400 chars, trimmed to paragraph boundary)
    search_start = max(0, match.start() - 400)
    preceding = text[search_start : match.start()]
    for boundary in _PARAGRAPH_BOUNDARIES:
        idx = preceding.rfind(boundary)
        if idx >= 0:
            preceding = preceding[idx:]
            break
    bank_matches = list(bank_pattern.finditer(preceding))
    if bank_matches:
        return bank_matches[-1].group(1).upper()

    # 4. After the match (up to 200 chars, trimmed to paragraph boundary)
    following = text[match.end() : match.end() + 200]
    for boundary in _PARAGRAPH_BOUNDARIES:
        idx = following.find(boundary)
        if idx >= 0:
            following = following[:idx]
            break
    bank_after = bank_pattern.search(following)
    if bank_after:
        return bank_after.group(1).upper()

    return "UNKNOWN"


def extract_line_bank_values(
    text: str, chart_by_bank: Dict[str, List[float]]
) -> List[Dict[str, Any]]:
    """Per-line analysis: find values attributed to banks, check grounding.

    More granular than triple extraction — works for responses without
    explicit month mentions (e.g., "INVEX: 15,048 MDP").
    """
    bank_names = list(chart_by_bank.keys())
    if len(bank_names) < 2:
        return []

    results = []
    currency_re = re.compile(
        r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?:MDP|mdp|millones|mil\s+millones|pesos|%)"
    )

    for line_num, line in enumerate(text.split("\n"), 1):
        line_upper = line.upper()
        banks_in_line = [b for b in bank_names if b in line_upper]
        if len(banks_in_line) != 1:
            continue

        bank = banks_in_line[0]
        own_values = chart_by_bank[bank]
        other_values = []
        other_banks_map: Dict[float, str] = {}
        for other_bank, vals in chart_by_bank.items():
            if other_bank != bank:
                for v in vals:
                    other_values.append(v)
                    other_banks_map[round(v, 2)] = other_bank

        for m in currency_re.finditer(line):
            raw = m.group(1).replace(",", "")
            try:
                cited = float(raw)
            except ValueError:
                continue

            # Check own bank
            matched_own = any(_close(cited, v) for v in own_values)
            if matched_own:
                continue

            # Check if matches chart value of another bank
            for ov in other_values:
                if _close(cited, ov):
                    actual_bank = other_banks_map.get(round(ov, 2), "?")
                    results.append(
                        {
                            "line": line_num,
                            "text": line.strip()[:120],
                            "cited_value": cited,
                            "attributed_to": bank,
                            "actually_belongs_to": actual_bank,
                            "chart_value": ov,
                            "type": "CROSS_BANK_SWAP",
                        }
                    )
                    break

                # Try MDP conversion (text in MDP, chart in raw pesos)
                if abs(ov) >= 1000 and _close(cited, ov / 1e6):
                    actual_bank = other_banks_map.get(round(ov, 2), "?")
                    results.append(
                        {
                            "line": line_num,
                            "text": line.strip()[:120],
                            "cited_value": cited,
                            "attributed_to": bank,
                            "actually_belongs_to": actual_bank,
                            "chart_value": ov,
                            "type": "CROSS_BANK_SWAP",
                        }
                    )
                    break

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Swap detectors
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class SwapViolation:
    """A detected value swap."""

    swap_type: str  # CROSS_BANK, CROSS_MONTH, TREND_SWAP, RANK_SWAP
    severity: str  # S0 (hard data error), S1 (attribution error), S2 (trend)
    description: str
    cited: CitedTriple
    expected_bank: Optional[str] = None
    expected_month: Optional[str] = None
    actual_value: Optional[float] = None


def detect_cross_bank_swaps(
    triples: List[CitedTriple],
    gt_map: Dict[Tuple[str, str], float],
    value_reverse: Dict[float, List[Tuple[str, str]]],
) -> List[SwapViolation]:
    """Detect values attributed to wrong bank."""
    violations = []
    for t in triples:
        if t.bank == "UNKNOWN":
            continue
        gt = gt_map.get((t.bank, t.month))
        if gt is not None and _close(t.value, gt):
            continue  # Correctly grounded

        # Value is wrong for this bank+month — check if it belongs elsewhere
        for other_key, owners in value_reverse.items():
            if _close(t.value, other_key):
                for owner_bank, owner_month in owners:
                    if owner_bank != t.bank and owner_month == t.month:
                        violations.append(
                            SwapViolation(
                                swap_type="CROSS_BANK",
                                severity="S0",
                                description=(
                                    f"{t.month}: cited {t.value:,.2f} for {t.bank} "
                                    f"but that value belongs to {owner_bank}"
                                ),
                                cited=t,
                                expected_bank=owner_bank,
                            )
                        )
                        break
                break
    return violations


def detect_cross_month_swaps(
    triples: List[CitedTriple],
    gt_map: Dict[Tuple[str, str], float],
    value_reverse: Dict[float, List[Tuple[str, str]]],
) -> List[SwapViolation]:
    """Detect values attributed to wrong month (same bank)."""
    violations = []
    for t in triples:
        if t.bank == "UNKNOWN":
            continue
        gt = gt_map.get((t.bank, t.month))
        if gt is not None and _close(t.value, gt):
            continue

        # FIX 2026-02-11: If the value is plausibly correct for the claimed month
        # (within 2%), don't flag it — adjacent months in low-volatility metrics
        # (ICAP, cartera) have similar values that trigger false positives.
        if gt is not None and _close_lenient(t.value, gt):
            continue

        for other_key, owners in value_reverse.items():
            if _close(t.value, other_key):
                for owner_bank, owner_month in owners:
                    if owner_bank == t.bank and owner_month != t.month:
                        violations.append(
                            SwapViolation(
                                swap_type="CROSS_MONTH",
                                severity="S0",
                                description=(
                                    f"{t.bank}: cited {t.value:,.2f} for {t.month} "
                                    f"but that value corresponds to {owner_month}"
                                ),
                                cited=t,
                                expected_month=owner_month,
                            )
                        )
                        break
                break
    return violations


def detect_trend_swaps(
    text: str,
    bank_series: Dict[str, List[Tuple[str, float]]],
) -> List[SwapViolation]:
    """Detect when the LLM swaps which bank grew vs declined.

    Looks for "BANK_A subió/creció" and "BANK_B bajó/disminuyó" patterns
    and validates against actual trend direction.
    """
    growth_words = re.compile(
        r"(subi[oó]|creci[oó]|crecimiento|aument[oó]|aumento|"
        r"increment[oó]|incremento|alza|positiv[ao]|mejor[oó]|mejora)",
        re.IGNORECASE,
    )
    decline_words = re.compile(
        r"(baj[oó]|disminu[yó]|disminuci[oó]n|ca[iyí]|ca[ií]da|"
        r"reduj[oó]|reducci[oó]n|retrocedi[oó]|retroceso|"
        r"negativ[ao]|deterior[oó]|deterioro)",
        re.IGNORECASE,
    )
    bank_pattern = re.compile(
        r"\b(" + "|".join(re.escape(b) for b in bank_series.keys()) + r")\b",
        re.IGNORECASE,
    )

    violations = []
    # Compute actual trends
    actual_trend: Dict[str, str] = {}
    for bank, series in bank_series.items():
        if len(series) >= 2:
            first_val = series[0][1]
            last_val = series[-1][1]
            if last_val > first_val * 1.005:
                actual_trend[bank] = "up"
            elif last_val < first_val * 0.995:
                actual_trend[bank] = "down"
            else:
                actual_trend[bank] = "flat"

    # Scan sentences for trend claims
    # Split on sentence boundaries AND markdown list items to avoid
    # multi-clause bullets like "- INVEX creció pero sigue por debajo..."
    # being treated as a single sentence.
    sentences = re.split(r"[.;]\s+|\n[-*]\s+|\n\d+\.\s+", text)
    for sentence in sentences:
        banks_mentioned = list(
            set(m.group(1).upper() for m in bank_pattern.finditer(sentence))
        )
        if len(banks_mentioned) != 1:
            continue

        bank = banks_mentioned[0]
        if bank not in actual_trend:
            continue

        has_growth = growth_words.search(sentence)
        has_decline = decline_words.search(sentence)

        if has_growth and not has_decline:
            if actual_trend[bank] == "down":
                violations.append(
                    SwapViolation(
                        swap_type="TREND_SWAP",
                        severity="S2",
                        description=(
                            f"Text says {bank} grew but actual trend is DOWN "
                            f"({sentence[:80]}...)"
                        ),
                        cited=CitedTriple(
                            bank=bank, month="", value=0, raw_text=sentence[:80]
                        ),
                    )
                )
        elif has_decline and not has_growth:
            if actual_trend[bank] == "up":
                violations.append(
                    SwapViolation(
                        swap_type="TREND_SWAP",
                        severity="S2",
                        description=(
                            f"Text says {bank} declined but actual trend is UP "
                            f"({sentence[:80]}...)"
                        ),
                        cited=CitedTriple(
                            bank=bank, month="", value=0, raw_text=sentence[:80]
                        ),
                    )
                )

    return violations


def detect_ranking_swaps(
    text: str,
    bank_series: Dict[str, List[Tuple[str, float]]],
) -> List[SwapViolation]:
    """Detect when the LLM claims the wrong bank has max/min value.

    Looks for "BANK tiene el mayor/menor" patterns.
    """
    violations = []

    # Compute actual max/min last values
    last_values = {}
    for bank, series in bank_series.items():
        if series:
            last_values[bank] = series[-1][1]

    if len(last_values) < 2:
        return violations

    actual_max_bank = max(last_values, key=last_values.get)  # type: ignore[arg-type]

    # Patterns for superlative claims
    max_patterns = [
        r"(\w+)\s+(?:tiene|tuvo|registr[oó]|present[oó])\s+(?:el|la)\s+(?:mayor|más\s+alt[oa]|más\s+grand[oe])",
        r"(?:el|la)\s+(?:mayor|más\s+alt[oa])\s+(?:fue|es|correspond[ei])\s+(?:a|de)\s+(\w+)",
    ]

    for pattern in max_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            claimed_bank = m.group(1).upper()
            if claimed_bank in last_values and claimed_bank != actual_max_bank:
                violations.append(
                    SwapViolation(
                        swap_type="RANK_SWAP",
                        severity="S1",
                        description=(
                            f"Text claims {claimed_bank} has the highest value "
                            f"but {actual_max_bank} does ({last_values[actual_max_bank]:,.2f} "
                            f"vs {last_values[claimed_bank]:,.2f})"
                        ),
                        cited=CitedTriple(
                            bank=claimed_bank,
                            month="",
                            value=0,
                            raw_text=m.group(0)[:80],
                        ),
                        expected_bank=actual_max_bank,
                    )
                )

    return violations


# ══════════════════════════════════════════════════════════════════════════════
# Test cases
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class SwapTestCase:
    """A test case focused on value swap detection."""

    id: str
    query: str
    description: str
    # Which swap types to check (all by default)
    check_cross_bank: bool = True
    check_cross_month: bool = True
    check_trend: bool = True
    check_ranking: bool = False
    # Also run per-line bank-value grounding
    check_line_grounding: bool = True
    # Check for false-negative phrases ("no tengo datos" despite chart success)
    check_false_negative: bool = True
    # Tolerance for number of acceptable mismatches
    max_false_negatives: int = 0
    max_cross_bank_swaps: int = 0
    max_cross_month_swaps: int = 0
    max_trend_swaps: int = 0
    max_ranking_swaps: int = 0
    max_line_misattributions: int = 0
    # Expect chart
    expect_chart: bool = True


@dataclass
class SwapTestResult:
    """Result of a swap detection test."""

    case: SwapTestCase
    passed: bool
    content: str = ""
    chart_status: str = ""
    bank_count: int = 0
    data_points: int = 0
    cited_triples: List[CitedTriple] = field(default_factory=list)
    cross_bank_swaps: List[SwapViolation] = field(default_factory=list)
    cross_month_swaps: List[SwapViolation] = field(default_factory=list)
    trend_swaps: List[SwapViolation] = field(default_factory=list)
    ranking_swaps: List[SwapViolation] = field(default_factory=list)
    line_misattributions: List[Dict[str, Any]] = field(default_factory=list)
    false_negatives: List[str] = field(default_factory=list)
    error: Optional[str] = None


TEST_CASES = [
    # VSD-01: Classic 2-bank comparison — highest swap risk
    SwapTestCase(
        id="VSD-01",
        query="compara la cartera comercial de INVEX y BBVA en 2025",
        description="2-bank comparison (INVEX vs BBVA) — cross-bank swap detection",
        check_cross_bank=True,
        check_cross_month=True,
        check_trend=True,
        check_ranking=False,
        check_line_grounding=True,
    ),
    # VSD-02: 3-bank comparison — even more swap surface
    SwapTestCase(
        id="VSD-02",
        query="compara el IMOR de BBVA, Santander y Banorte en 2025",
        description="3-bank IMOR comparison — values must not cross between banks",
        check_cross_bank=True,
        check_cross_month=True,
        check_trend=True,
        check_ranking=True,
        check_line_grounding=True,
    ),
    # VSD-03: Single bank, multiple explicit months — month swap detection
    SwapTestCase(
        id="VSD-03",
        query=(
            "muéstrame la cartera comercial de INVEX "
            "en enero, marzo, junio y septiembre de 2025"
        ),
        description="Single bank, 4 explicit months — cross-month swap detection",
        check_cross_bank=False,  # Only 1 bank, no cross-bank possible
        check_cross_month=True,
        check_trend=False,
        check_ranking=False,
        check_line_grounding=False,
    ),
    # VSD-04: Trend comparison — which bank grew more
    SwapTestCase(
        id="VSD-04",
        query=(
            "¿cómo evolucionó la cartera comercial de INVEX vs BBVA "
            "durante 2025? ¿cuál creció más?"
        ),
        description="2-bank trend comparison — detect trend direction swaps",
        check_cross_bank=True,
        check_cross_month=False,
        check_trend=True,
        check_ranking=True,
        check_line_grounding=True,
    ),
    # VSD-05: Dense comparison — 3 banks × Q1 = max swap opportunity
    SwapTestCase(
        id="VSD-05",
        query=(
            "muéstrame el ICAP de INVEX, BBVA y Santander "
            "en el primer trimestre de 2025 (enero, febrero, marzo)"
        ),
        description="3 banks × 3 months — dense matrix, maximum swap opportunity",
        check_cross_bank=True,
        check_cross_month=True,
        check_trend=False,
        check_ranking=False,
        check_line_grounding=True,
    ),
    # VSD-06: Ratio metric — small numbers more prone to confusion
    SwapTestCase(
        id="VSD-06",
        query="compara el ROE de INVEX y BBVA en 2025",
        description="ROE ratio comparison — small values prone to misattribution",
        check_cross_bank=True,
        check_cross_month=True,
        check_trend=True,
        check_ranking=False,
        check_line_grounding=True,
    ),
    # VSD-07: Year-over-year for 2 banks — temporal cross-bank swap risk
    SwapTestCase(
        id="VSD-07",
        query=(
            "¿cuánto cambió la cartera comercial de INVEX y Banorte "
            "entre enero 2025 y el último dato disponible?"
        ),
        description="2-bank YoY change — cross-bank temporal swap detection",
        check_cross_bank=True,
        check_cross_month=True,
        check_trend=True,
        check_ranking=False,
        check_line_grounding=True,
    ),
    # VSD-08: Explicit ranking query — "which is the highest"
    SwapTestCase(
        id="VSD-08",
        query=(
            "entre BBVA, Santander, Banorte e INVEX, "
            "¿cuál tiene la cartera comercial más grande en 2025?"
        ),
        description="4-bank ranking query — must correctly identify max/min",
        check_cross_bank=True,
        check_cross_month=False,
        check_trend=False,
        check_ranking=True,
        check_line_grounding=True,
    ),
    # VSD-09: Multi-year month comparison — truncation-before-filtering bug
    # Before fix: datos[-12:] lost enero 2024 from context → LLM says "no tengo datos"
    SwapTestCase(
        id="VSD-09",
        query=("compara la cartera comercial de INVEX " "en enero 2024 vs enero 2025"),
        description="Multi-year month comparison — truncation-before-filtering fix",
        check_cross_bank=False,
        check_cross_month=True,
        check_trend=False,
        check_ranking=False,
        check_line_grounding=False,
        check_false_negative=True,
    ),
    # VSD-10: 10-bank query — max_series truncation
    # Before fix: max_series=6 dropped 4 banks from context table → LLM says "no tengo datos"
    SwapTestCase(
        id="VSD-10",
        query=(
            "compara la cartera comercial de INVEX, BBVA, Banorte, "
            "Santander, Scotiabank, HSBC, Afirme, Banregio, Bajío e Inbursa "
            "en 2025"
        ),
        description="10-bank query — max_series=10 verification",
        check_cross_bank=True,
        check_cross_month=False,
        check_trend=False,
        check_ranking=False,
        check_line_grounding=True,
        check_false_negative=True,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Test runner
# ══════════════════════════════════════════════════════════════════════════════


def run_swap_test(token: str, tc: SwapTestCase) -> SwapTestResult:
    """Execute a single swap detection test."""
    result = SwapTestResult(case=tc, passed=False)

    resp = send_chat_message(
        token, tc.query, backend_url=BACKEND_URL, stream=True, timeout=TIMEOUT
    )

    if resp.get("error"):
        result.error = f"Request failed: {resp['error']}"
        return result

    result.content = resp.get("content") or ""
    bc = resp.get("bank_chart")

    if tc.expect_chart and (not bc or bc.get("chart_status") != "success"):
        status = bc.get("chart_status", "missing") if bc else "missing"
        result.chart_status = status
        result.error = f"Expected chart but got status={status}"
        return result

    if bc:
        result.chart_status = str(bc.get("chart_status", "unknown"))

    if not bc or result.chart_status != "success":
        # No chart data to validate against — pass vacuously
        result.passed = True
        return result

    # Extract ground truth from chart (line charts first, bar charts as fallback)
    bank_series = extract_bank_time_series(bc)
    if not bank_series:
        bank_series = extract_bank_values_from_bar_chart(bc)
    result.bank_count = len(bank_series)
    result.data_points = sum(len(s) for s in bank_series.values())

    if result.bank_count == 0:
        result.error = "Chart has no named traces or bar data"
        return result

    gt_map = build_ground_truth_map(bank_series)
    value_reverse = build_value_to_bank_map(gt_map)

    # Bar charts (ranking) have synthetic "latest" dates — triple-based
    # cross-bank/month checks don't apply (no temporal series to cross-ref).
    is_bar_chart = all(d == "latest" for _, d in gt_map.keys()) and len(gt_map) > 0

    # Extract cited triples from text
    result.cited_triples = extract_cited_triples(result.content)

    issues = []

    # 1. Cross-bank swaps (skip for bar charts — use line grounding instead)
    if tc.check_cross_bank and result.bank_count >= 2 and not is_bar_chart:
        result.cross_bank_swaps = detect_cross_bank_swaps(
            result.cited_triples, gt_map, value_reverse
        )
        if len(result.cross_bank_swaps) > tc.max_cross_bank_swaps:
            swap_desc = "; ".join(s.description for s in result.cross_bank_swaps[:3])
            issues.append(
                f"CROSS_BANK: {len(result.cross_bank_swaps)} swaps — {swap_desc}"
            )

    # 2. Cross-month swaps (skip for bar charts — no temporal dimension)
    if tc.check_cross_month and not is_bar_chart:
        result.cross_month_swaps = detect_cross_month_swaps(
            result.cited_triples, gt_map, value_reverse
        )
        if len(result.cross_month_swaps) > tc.max_cross_month_swaps:
            swap_desc = "; ".join(s.description for s in result.cross_month_swaps[:3])
            issues.append(
                f"CROSS_MONTH: {len(result.cross_month_swaps)} swaps — {swap_desc}"
            )

    # 3. Trend swaps
    if tc.check_trend and result.bank_count >= 2:
        result.trend_swaps = detect_trend_swaps(result.content, bank_series)
        if len(result.trend_swaps) > tc.max_trend_swaps:
            swap_desc = "; ".join(s.description for s in result.trend_swaps[:2])
            issues.append(f"TREND_SWAP: {len(result.trend_swaps)} swaps — {swap_desc}")

    # 4. Ranking swaps
    if tc.check_ranking and result.bank_count >= 2:
        result.ranking_swaps = detect_ranking_swaps(result.content, bank_series)
        if len(result.ranking_swaps) > tc.max_ranking_swaps:
            swap_desc = "; ".join(s.description for s in result.ranking_swaps[:2])
            issues.append(f"RANK_SWAP: {len(result.ranking_swaps)} swaps — {swap_desc}")

    # 5. Per-line bank-value grounding
    if tc.check_line_grounding and result.bank_count >= 2:
        chart_by_bank: Dict[str, List[float]] = {}
        for bank, series in bank_series.items():
            chart_by_bank[bank] = [v for _, v in series]
        result.line_misattributions = extract_line_bank_values(
            result.content, chart_by_bank
        )
        if len(result.line_misattributions) > tc.max_line_misattributions:
            mis_desc = "; ".join(
                f"L{m['line']}: {m['cited_value']:.2f} cited for "
                f"{m['attributed_to']} but is {m['actually_belongs_to']}'s"
                for m in result.line_misattributions[:3]
            )
            issues.append(
                f"LINE_MISATTR: {len(result.line_misattributions)} — {mis_desc}"
            )

    # 6. False-negative detection ("no tengo datos" despite chart success)
    if tc.check_false_negative:
        result.false_negatives = detect_false_negatives(
            result.content, result.chart_status
        )
        if len(result.false_negatives) > tc.max_false_negatives:
            fn_desc = "; ".join(f'"{p}"' for p in result.false_negatives[:3])
            issues.append(
                f"FALSE_NEGATIVE: LLM says {fn_desc} despite chart_status=success"
            )

    if issues:
        result.error = " | ".join(issues)
    else:
        result.passed = True

    return result


def main() -> int:
    print("=" * 70)
    print("E2E Regression: Value Swap Detection (Cross-Bank / Cross-Month)")
    print("=" * 70)
    print()

    token = get_auth_token(backend_url=BACKEND_URL)
    if not token:
        print(
            "FATAL: Auth failed — check TEST_BACKEND_URL, TEST_AUTH_USER, TEST_AUTH_PASS"
        )
        return 2

    print(f"Authenticated against {BACKEND_URL}")
    print()

    results: List[SwapTestResult] = []
    passed = failed = 0

    for tc in TEST_CASES:
        print(f"--- {tc.id}: {tc.description} ---")
        print(f'  Query: "{tc.query}"')

        r = run_swap_test(token, tc)
        results.append(r)

        if r.passed:
            passed += 1
            print("  PASSED")
            print(
                f"     Banks: {r.bank_count} | Data points: {r.data_points} | "
                f"Cited triples: {len(r.cited_triples)}"
            )
            if r.false_negatives:
                print(
                    f"     False negatives caught by postprocessor: "
                    f"{len(r.false_negatives)}"
                )
            # Report any found-but-within-tolerance swaps
            total_swaps = (
                len(r.cross_bank_swaps)
                + len(r.cross_month_swaps)
                + len(r.trend_swaps)
                + len(r.ranking_swaps)
                + len(r.line_misattributions)
            )
            if total_swaps > 0:
                print(
                    f"     Swaps within tolerance: "
                    f"bank={len(r.cross_bank_swaps)}, "
                    f"month={len(r.cross_month_swaps)}, "
                    f"trend={len(r.trend_swaps)}, "
                    f"rank={len(r.ranking_swaps)}, "
                    f"line={len(r.line_misattributions)}"
                )
        else:
            failed += 1
            print(f"  FAILED: {r.error}")
            if r.content:
                print("     Text (first 400 chars):")
                for line in r.content[:400].split("\n"):
                    print(f"       {line}")
            if r.cited_triples:
                print("     Cited triples:")
                for t in r.cited_triples[:8]:
                    print(
                        f"       [{t.bank}] {t.month} = {t.value:,.2f} "
                        f"(line {t.line_number})"
                    )
            for sv in r.cross_bank_swaps[:3]:
                print(f"     >> CROSS_BANK: {sv.description}")
            for sv in r.cross_month_swaps[:3]:
                print(f"     >> CROSS_MONTH: {sv.description}")
            for sv in r.trend_swaps[:2]:
                print(f"     >> TREND: {sv.description}")
            for sv in r.ranking_swaps[:2]:
                print(f"     >> RANK: {sv.description}")
            for m in r.line_misattributions[:3]:
                print(
                    f"     >> LINE_SWAP: L{m['line']} {m['cited_value']:.2f} "
                    f"said {m['attributed_to']} but is {m['actually_belongs_to']}"
                )
            for fn in r.false_negatives[:3]:
                print(f'     >> FALSE_NEG: "{fn}"')

        print()

    # ── Summary ──
    print("=" * 70)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    print()

    # Aggregate swap counts
    total_cross_bank = sum(len(r.cross_bank_swaps) for r in results)
    total_cross_month = sum(len(r.cross_month_swaps) for r in results)
    total_trend = sum(len(r.trend_swaps) for r in results)
    total_rank = sum(len(r.ranking_swaps) for r in results)
    total_line = sum(len(r.line_misattributions) for r in results)
    total_false_neg = sum(len(r.false_negatives) for r in results)
    total_triples = sum(len(r.cited_triples) for r in results)

    print("Swap Summary Across All Tests:")
    print(f"  Cited triples extracted: {total_triples}")
    print(f"  Cross-bank swaps:  {total_cross_bank}")
    print(f"  Cross-month swaps: {total_cross_month}")
    print(f"  Trend swaps:       {total_trend}")
    print(f"  Ranking swaps:     {total_rank}")
    print(f"  Line misattr:      {total_line}")
    print(f"  False negatives:   {total_false_neg}")
    print()

    if total_cross_bank + total_cross_month + total_line > 0:
        swap_rate = (
            (total_cross_bank + total_cross_month + total_line)
            / max(total_triples, 1)
            * 100
        )
        print(f"  Value swap rate: {swap_rate:.1f}%")

    # ── Save results JSON ──
    output_path = Path(__file__).parent / "value_swap_results.json"
    json_results = []
    for r in results:
        json_results.append(
            {
                "id": r.case.id,
                "query": r.case.query,
                "passed": r.passed,
                "error": r.error,
                "bank_count": r.bank_count,
                "data_points": r.data_points,
                "cited_triples": len(r.cited_triples),
                "cross_bank_swaps": len(r.cross_bank_swaps),
                "cross_month_swaps": len(r.cross_month_swaps),
                "trend_swaps": len(r.trend_swaps),
                "ranking_swaps": len(r.ranking_swaps),
                "line_misattributions": len(r.line_misattributions),
                "false_negatives": r.false_negatives,
                "swap_details": [
                    {"type": s.swap_type, "severity": s.severity, "desc": s.description}
                    for s in (
                        r.cross_bank_swaps
                        + r.cross_month_swaps
                        + r.trend_swaps
                        + r.ranking_swaps
                    )
                ],
            }
        )

    with open(output_path, "w") as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {output_path}")

    print("=" * 70)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
