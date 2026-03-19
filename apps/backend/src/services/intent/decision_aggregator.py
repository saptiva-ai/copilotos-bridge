"""
Decision Aggregator - Combines signals into routing decision.

Q1 2026: Aggregates semantic scores, context enhancement, and feedback
signals into a final routing decision.

Decision rules (in priority order):
1. Explicit tool enablement → INVOKE (backward compatibility)
2. Known negative (from feedback) → SKIP
3. High data score (data_query/knowledge_query > 0.55) → INVOKE
4. High non-data score (greeting/acknowledgment > 0.65) → SKIP
5. Ambiguous → INVOKE (delegate to tool)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import structlog

from .types import IntentCategory, IntentScores

logger = structlog.get_logger(__name__)


class RoutingDecision(str, Enum):
    """Routing decision for tool invocation."""

    INVOKE = "invoke"
    SKIP = "skip"


@dataclass
class IntentDecision:
    """Final routing decision with full reasoning."""

    decision: RoutingDecision
    confidence: float
    reason: str
    intent_category: IntentCategory
    scores: Dict[str, float]

    def to_tuple(self):
        """Convert to (should_run, reason) tuple for backward compatibility."""
        should_run = self.decision == RoutingDecision.INVOKE
        return should_run, self.reason


class DecisionAggregator:
    """
    Aggregates intent signals into a final routing decision.

    Thresholds are configurable and can be tuned based on
    observed performance from feedback data.
    """

    # Thresholds (can be overridden in constructor)
    DEFAULT_DATA_THRESHOLD = 0.55
    DEFAULT_NON_DATA_THRESHOLD = 0.65

    def __init__(
        self,
        data_threshold: Optional[float] = None,
        non_data_threshold: Optional[float] = None,
    ):
        """
        Initialize aggregator with optional custom thresholds.

        Args:
            data_threshold: Minimum score to invoke for data queries
            non_data_threshold: Minimum score to skip for non-data
        """
        self.data_threshold = data_threshold or self.DEFAULT_DATA_THRESHOLD
        self.non_data_threshold = (
            non_data_threshold or self.DEFAULT_NON_DATA_THRESHOLD
        )

    def decide(
        self,
        scores: IntentScores,
        is_negative_cached: bool = False,
        explicit_enabled: bool = False,
    ) -> IntentDecision:
        """
        Make final routing decision.

        Args:
            scores: Intent scores from semantic + context enhancement
            is_negative_cached: Whether message is in negative feedback cache
            explicit_enabled: Whether tools explicitly enabled by user

        Returns:
            IntentDecision with full reasoning
        """
        scores_dict = scores.to_dict()

        # Rule 1: Explicit enablement always wins
        if explicit_enabled:
            return IntentDecision(
                decision=RoutingDecision.INVOKE,
                confidence=1.0,
                reason="explicitly_enabled",
                intent_category=scores.top_intent,
                scores=scores_dict,
            )

        # Rule 2: Negative cache → skip
        if is_negative_cached:
            return IntentDecision(
                decision=RoutingDecision.SKIP,
                confidence=0.9,
                reason="cached_as_negative",
                intent_category=scores.top_intent,
                scores=scores_dict,
            )

        # Calculate aggregate scores
        data_score = max(
            scores.scores.get(IntentCategory.DATA_QUERY, 0.0),
            scores.scores.get(IntentCategory.KNOWLEDGE_QUERY, 0.0),
        )

        non_data_score = max(
            scores.scores.get(IntentCategory.GREETING, 0.0),
            scores.scores.get(IntentCategory.ACKNOWLEDGMENT, 0.0),
        )

        follow_up_score = scores.scores.get(IntentCategory.FOLLOW_UP, 0.0)

        # Rule 3: High data confidence → invoke
        if data_score > self.data_threshold:
            return IntentDecision(
                decision=RoutingDecision.INVOKE,
                confidence=data_score,
                reason=f"high_data_score:{data_score:.2f}",
                intent_category=scores.top_intent,
                scores=scores_dict,
            )

        # Rule 4: High follow-up with some data context → invoke
        # (Follow-ups often don't have explicit data terms)
        if follow_up_score > 0.5 and data_score > 0.3:
            combined_score = (follow_up_score + data_score) / 2
            return IntentDecision(
                decision=RoutingDecision.INVOKE,
                confidence=combined_score,
                reason=f"follow_up_with_context:{follow_up_score:.2f}",
                intent_category=IntentCategory.FOLLOW_UP,
                scores=scores_dict,
            )

        # Rule 5: High non-data confidence → skip
        if non_data_score > self.non_data_threshold:
            return IntentDecision(
                decision=RoutingDecision.SKIP,
                confidence=non_data_score,
                reason=f"high_non_data_score:{non_data_score:.2f}",
                intent_category=scores.top_intent,
                scores=scores_dict,
            )

        # Rule 6: Ambiguous → delegate
        # This is the "thin backend" philosophy - when in doubt, delegate
        return IntentDecision(
            decision=RoutingDecision.INVOKE,
            confidence=0.5,
            reason="ambiguous_delegating",
            intent_category=scores.top_intent,
            scores=scores_dict,
        )

    def explain_decision(self, decision: IntentDecision) -> str:
        """
        Generate human-readable explanation of decision.

        Useful for debugging and logging.
        """
        lines = [
            f"Decision: {decision.decision.value.upper()}",
            f"Confidence: {decision.confidence:.2f}",
            f"Reason: {decision.reason}",
            f"Top Intent: {decision.intent_category.value}",
            "Scores:",
        ]

        for cat, score in sorted(
            decision.scores.items(), key=lambda x: x[1], reverse=True
        ):
            bar = "█" * int(score * 20)
            lines.append(f"  {cat}: {score:.2f} {bar}")

        return "\n".join(lines)
