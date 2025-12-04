"""
Simple fact extractor using regex.

No LLM needed - pure pattern matching for banking metrics.
Extracts bank names, periods (quarters/years), and financial metrics.
"""

import re
from typing import Dict, Optional, Tuple

# Known Mexican banks (aligned with BankAdvisor DB)
BANKS = {
    # Primary banks (available in BankAdvisor)
    "invex",
    "bbva",
    "banorte",
    "santander",
    "hsbc",
    "citibanamex",  # Added - available in DB
    "sistema",      # Added - aggregate metric

    # Additional Mexican banks
    "scotiabank",
    "banamex",      # Alias for Citibanamex
    "banregio",
    "afirme",
    "azteca",
    "inbursa",
    "multiva",
    "mifel",
    "bajio",
    "compartamos",
}

# Bank aliases (alternative names)
BANK_ALIASES = {
    "banamex": "citibanamex",
    "citi": "citibanamex",
    "citibank": "citibanamex",
}

# Period patterns: (regex, formatter function)
PERIOD_PATTERNS = [
    # Q3 2025, Q3 de 2025, q3_2025
    (r"q([1-4])\s*(?:de\s*)?(\d{4})", lambda m: f"q{m.group(1)}_{m.group(2)}"),
    # 2025 Q3, 2025-Q3
    (r"(\d{4})\s*[-_]?\s*q([1-4])", lambda m: f"q{m.group(2)}_{m.group(1)}"),
    # T1 2025, 1T 2025 (Spanish trimestre)
    (r"([1-4])t\s*(?:de\s*)?(\d{4})", lambda m: f"q{m.group(1)}_{m.group(2)}"),
    (r"t([1-4])\s*(?:de\s*)?(\d{4})", lambda m: f"q{m.group(1)}_{m.group(2)}"),
    # Just year: 2024, 2025
    (r"\b(\d{4})\b", lambda m: m.group(1)),
]

# Metric patterns: metric_name -> regex pattern
# Each pattern captures the numeric value AND optional unit (%, MDP, millones)
# Patterns handle: "IMOR de INVEX es de 4 MDP" and "IMOR es 4%" and "IMOR: 4"
METRIC_PATTERNS = {
    # Credit quality metrics - requires "es/de/fue/:" before number to avoid matching dates
    # Pattern: metric_name + non-digits + (es|de|fue|:) + number + optional_unit
    # Handles: "IMOR de INVEX es de 4 MDP", "IMOR: 4%", "IMOR actual es 4"
    # Avoids: "datos actualizados al 2025-07-01" (no es/de before 2025)
    "imor": r"imor\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "icor": r"icor\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "icap": r"icap\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "roe": r"roe\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "roa": r"roa\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "roi": r"roi\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",

    # Additional banking metrics
    "morosidad": r"morosidad\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "solvencia": r"solvencia\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "liquidez": r"liquidez\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "margen": r"margen\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",
    "utilidad": r"utilidad(?:es)?\b[^0-9]*(?:es|de|fue|son|:|=)\s*\$?\s*(\d+[.,]?\d*)\s*(mdp|millones)?",
    "rentabilidad": r"rentabilidad\b[^0-9]*(?:es|de|fue|son|:|=)\s*(\d+[.,]?\d*)\s*(%|mdp|millones)?",

    # Loan metrics
    "dscr": r"dscr\s*(?:es|de|fue|=|:)?\s*(\d+[.,]?\d*)",
    "ltv": r"ltv\s*(?:es|de|fue|=|:)?\s*(\d+[.,]?\d*)\s*%?",
    "plazo": r"plazo\s*(?:es|de|fue|=|:)?\s*(\d+)\s*(?:meses|años|dias)?",

    # Interest rates
    "tasa_interes": r"tasa\s*(?:de\s+)?inter[eé]s?\s*(?:es|de|fue|=|:)?\s*(\d+[.,]?\d*)\s*%?",
    "tasa": r"(?<!in)tasa\s*(?:es|de|fue|=|:)?\s*(\d+[.,]?\d*)\s*%?",

    # Portfolio amounts
    "cartera_vencida": r"cartera\s+vencida\s*(?:es|de|fue|=|:)?\s*\$?\s*(\d+(?:[,.\s]\d{3})*(?:[.,]\d+)?)",
    "cartera_total": r"cartera\s+total\s*(?:es|de|fue|=|:)?\s*\$?\s*(\d+(?:[,.\s]\d{3})*(?:[.,]\d+)?)",
    "monto": r"monto\s*(?:es|de|fue|=|:)?\s*\$?\s*(\d+(?:[,.\s]\d{3})*(?:[.,]\d+)?)",

    # Reserves and provisions
    "reservas": r"reservas?\s*(?:es|de|fue|=|:)?\s*\$?\s*(\d+(?:[,.\s]\d{3})*(?:[.,]\d+)?)",
    "provision": r"provisi[oó]n\s*(?:es|de|fue|=|:)?\s*\$?\s*(\d+(?:[,.\s]\d{3})*(?:[.,]\d+)?)",
}


def extract_bank(text: str) -> Optional[str]:
    """
    Find bank name in text.

    Args:
        text: Input text to search

    Returns:
        Bank name (lowercase) if found, None otherwise
    """
    text_lower = text.lower()
    for bank in BANKS:
        # Word boundary match to avoid partial matches
        if re.search(rf"\b{bank}\b", text_lower):
            return bank
    return None


def extract_period(text: str) -> Optional[str]:
    """
    Find period (quarter/year) in text.

    Args:
        text: Input text to search

    Returns:
        Period string (e.g., "q3_2025" or "2024") if found, None otherwise
    """
    text_lower = text.lower()
    for pattern, formatter in PERIOD_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return formatter(match)
    return None


def extract_metrics(text: str) -> Dict[str, str]:
    """
    Extract all financial metrics from text.

    Args:
        text: Input text to search

    Returns:
        Dict of metric_name -> value (as string)
    """
    facts = {}
    text_lower = text.lower()

    for metric, pattern in METRIC_PATTERNS.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            # Clean the value: normalize decimal format
            value = match.group(1)

            # Handle European decimal format (2,3 -> 2.3) vs thousand separator (1,000 -> 1000)
            # If comma is followed by exactly 1-2 digits at end, it's a decimal
            if re.match(r"^\d+,\d{1,2}$", value):
                # European decimal: 2,3 or 2,35 -> 2.3 or 2.35
                value = value.replace(",", ".")
            else:
                # Thousand separator: 1,000,000 -> 1000000
                value = value.replace(",", "").replace(" ", "")

            # Check if a unit was captured (group 2 for metrics with unit patterns)
            captured_unit = None
            if match.lastindex and match.lastindex >= 2:
                captured_unit = match.group(2)

            # Add appropriate suffix based on captured unit or metric type
            if captured_unit:
                unit_lower = captured_unit.lower()
                if unit_lower == "%":
                    value = f"{value}%"
                elif unit_lower in ("mdp", "millones"):
                    value = f"{value} MDP"
            elif metric in ("imor", "icor", "icap", "roe", "roa", "roi", "ltv", "tasa_interes", "tasa", "morosidad", "solvencia", "liquidez", "margen", "rentabilidad"):
                # Default to % for percentage metrics only if no unit was captured
                if not value.endswith("%"):
                    value = f"{value}%"

            facts[metric] = value

    return facts


def extract_all(
    text: str,
    current_context: Optional[Dict[str, str]] = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Extract facts and update context from message.

    This is the main entry point for fact extraction.
    Uses regex patterns to find banking metrics and scopes them
    to the appropriate bank and period.

    Args:
        text: User message text
        current_context: Existing context (bank, period, metric) to inherit from

    Returns:
        Tuple of (facts_dict, updated_context)
        - facts_dict keys are formatted as: bank.period.metric or bank.metric
        - updated_context includes any new bank/period/metric detected

    Example:
        >>> facts, ctx = extract_all("El IMOR de INVEX Q2 2025 es 2.3%")
        >>> facts
        {"invex.q2_2025.imor": "2.3%"}
        >>> ctx
        {"bank": "invex", "period": "q2_2025", "metric": "imor"}
    """
    current_context = current_context or {}

    # Extract components from text
    bank = extract_bank(text) or current_context.get("bank")
    period = extract_period(text) or current_context.get("period")
    metrics = extract_metrics(text)

    # Build scoped fact keys
    facts = {}
    for metric, value in metrics.items():
        if bank and period:
            key = f"{bank}.{period}.{metric}"
        elif bank:
            key = f"{bank}.{metric}"
        elif period:
            key = f"{period}.{metric}"
        else:
            key = metric
        facts[key] = value

    # Update context with newly detected values
    new_context = current_context.copy()
    if bank:
        new_context["bank"] = bank
    if period:
        new_context["period"] = period
    if metrics:
        # Track most recent metric mentioned
        new_context["metric"] = list(metrics.keys())[0]

    return facts, new_context
