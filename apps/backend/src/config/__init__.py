"""
Backend Configuration Module.

Centralized configuration for banking keywords, patterns, and settings.
"""

from .banking_keywords import (
    ACRONYM_NORMALIZATIONS,
    AMBIGUOUS_WORDS,
    BANKING_CONTEXT_KEYWORDS,
    CHART_INTENT_TOKENS,
    DEFAULT_METRIC_OPTIONS,
    DEFINITION_TRIGGERS,
    GLOSSARY_CONCEPTS,
    HIGH_CONFIDENCE_KEYWORDS,
    HISTORY_FILTER_TOPICS,
    KNOWN_DEFINITION_ACRONYMS,
    NEGATIVE_KEYWORDS,
    PLACE_INDICATORS,
    RAG_SWITCH_TRIGGERS,
    has_banking_context,
    has_chart_intent,
    has_definition_trigger,
    has_rag_switch_trigger,
    is_high_confidence_banking_keyword,
    is_history_topic,
    is_negative_keyword,
    is_place_context,
    normalize_acronyms,
)

__all__ = [
    # Constants
    "GLOSSARY_CONCEPTS",
    "DEFINITION_TRIGGERS",
    "CHART_INTENT_TOKENS",
    "RAG_SWITCH_TRIGGERS",
    "KNOWN_DEFINITION_ACRONYMS",
    "HIGH_CONFIDENCE_KEYWORDS",
    "NEGATIVE_KEYWORDS",
    "HISTORY_FILTER_TOPICS",
    "PLACE_INDICATORS",
    "AMBIGUOUS_WORDS",
    "BANKING_CONTEXT_KEYWORDS",
    "ACRONYM_NORMALIZATIONS",
    "DEFAULT_METRIC_OPTIONS",
    # Functions
    "normalize_acronyms",
    "is_high_confidence_banking_keyword",
    "is_negative_keyword",
    "has_definition_trigger",
    "has_chart_intent",
    "has_rag_switch_trigger",
    "is_history_topic",
    "is_place_context",
    "has_banking_context",
]
