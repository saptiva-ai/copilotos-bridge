"""
Simple Memory Service - JSON-based fact recall.

Extracts banking metrics from conversation via regex and stores
them as JSON for context injection into LLM prompts.
"""

from .memory_service import MemoryService, get_memory_service
from .fact_extractor import extract_all, extract_bank, extract_period, extract_metrics

__all__ = [
    "MemoryService",
    "get_memory_service",
    "extract_all",
    "extract_bank",
    "extract_period",
    "extract_metrics",
]
