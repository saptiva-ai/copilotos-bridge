"""
Intent Types - Data structures for intent classification.

Q1 2026: Semantic intent routing for bank advisor pre-check.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class IntentCategory(str, Enum):
    """Categories for intent classification."""

    GREETING = "greeting"
    ACKNOWLEDGMENT = "acknowledgment"
    KNOWLEDGE_QUERY = "knowledge_query"
    DATA_QUERY = "data_query"
    FOLLOW_UP = "follow_up"
    UNKNOWN = "unknown"


@dataclass
class IntentScores:
    """Scores for each intent category with computed top intent."""

    scores: Dict[IntentCategory, float] = field(default_factory=dict)
    top_intent: IntentCategory = IntentCategory.UNKNOWN
    top_confidence: float = 0.0

    @classmethod
    def from_dict(cls, scores: Dict[str, float]) -> "IntentScores":
        """
        Create IntentScores from a dictionary of category -> score.

        Automatically computes top_intent and top_confidence.
        """
        # Convert string keys to enum
        enum_scores: Dict[IntentCategory, float] = {}
        for k, v in scores.items():
            try:
                enum_scores[IntentCategory(k)] = v
            except ValueError:
                # Skip unknown categories
                pass

        if not enum_scores:
            return cls(
                scores={},
                top_intent=IntentCategory.UNKNOWN,
                top_confidence=0.0,
            )

        # Find top intent
        top = max(enum_scores, key=lambda x: enum_scores[x])

        return cls(
            scores=enum_scores,
            top_intent=top,
            top_confidence=enum_scores[top],
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary with string keys."""
        return {k.value: v for k, v in self.scores.items()}
