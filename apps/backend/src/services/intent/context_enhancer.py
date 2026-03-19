"""
Context Enhancer - Adjusts intent scores based on conversation history.

Q1 2026: If the conversation has recent data context (charts, metrics),
follow-up questions should be routed appropriately even if they don't
contain explicit data keywords.

Rules:
1. If recent chart exists + message looks like follow-up → boost data_query
2. If short message after chart → likely follow-up
3. Reduce greeting/acknowledgment scores when data context exists
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from .types import IntentCategory, IntentScores

logger = structlog.get_logger(__name__)


@dataclass
class ConversationContext:
    """Extracted context from conversation history."""

    has_recent_chart: bool
    last_metric: Optional[str]
    last_banks: List[str]
    turn_count: int
    last_assistant_had_chart: bool


class ContextEnhancer:
    """
    Enhances intent scores using conversation context.

    Design:
    - Does NOT call embedding service (context extraction is rule-based)
    - Adjusts scores from SemanticScorer based on conversation state
    - Boosts data_query when context suggests follow-up
    """

    # Weight adjustments
    FOLLOW_UP_BOOST = 0.25
    CHART_CONTEXT_BOOST = 0.15
    NON_DATA_PENALTY = 0.5  # Multiplier (reduces score)

    @classmethod
    def extract_context(
        cls,
        recent_messages: Optional[List[Dict[str, Any]]],
        memory_context: Optional[Dict[str, Any]],
    ) -> ConversationContext:
        """
        Extract relevant context from conversation history.

        Args:
            recent_messages: List of recent messages with metadata
            memory_context: Session memory context dict

        Returns:
            ConversationContext with extracted signals
        """
        recent_messages = recent_messages or []
        memory_context = memory_context or {}

        # Check for recent chart data
        has_chart = bool(
            memory_context.get("last_chart_data")
            or memory_context.get("last_metric")
            or memory_context.get("last_banks")
        )

        # Also check recent messages for chart metadata
        if not has_chart and recent_messages:
            for msg in recent_messages[-3:]:  # Last 3 messages
                if msg.get("metadata", {}).get("chart_data"):
                    has_chart = True
                    break

        # Extract last metric and banks
        last_metric = memory_context.get("last_metric")
        last_banks = memory_context.get("last_banks", [])
        if not isinstance(last_banks, list):
            last_banks = []

        # Check if last assistant message had a chart
        last_assistant_had_chart = False
        for msg in reversed(recent_messages):
            if msg.get("role") == "assistant":
                last_assistant_had_chart = bool(
                    msg.get("metadata", {}).get("chart_data")
                )
                break

        return ConversationContext(
            has_recent_chart=has_chart,
            last_metric=last_metric,
            last_banks=last_banks,
            turn_count=len(recent_messages),
            last_assistant_had_chart=last_assistant_had_chart,
        )

    def enhance(
        self,
        message: str,
        base_scores: IntentScores,
        context: ConversationContext,
    ) -> IntentScores:
        """
        Enhance intent scores based on context.

        Args:
            message: User message
            base_scores: Scores from semantic scorer
            context: Conversation context

        Returns:
            Enhanced IntentScores
        """
        # Start with a copy of base scores
        enhanced: Dict[IntentCategory, float] = dict(base_scores.scores)

        # No context → return base scores unchanged
        if not context.has_recent_chart and not context.last_assistant_had_chart:
            return base_scores

        follow_up_score = base_scores.scores.get(IntentCategory.FOLLOW_UP, 0.0)
        data_query_score = base_scores.scores.get(IntentCategory.DATA_QUERY, 0.0)

        # Rule 1: Recent chart + follow-up pattern → boost data_query
        if context.has_recent_chart and follow_up_score > 0.4:
            current = enhanced.get(IntentCategory.DATA_QUERY, 0.0)
            boost = self.FOLLOW_UP_BOOST + self.CHART_CONTEXT_BOOST
            enhanced[IntentCategory.DATA_QUERY] = min(1.0, current + boost)

            # Reduce greeting/acknowledgment scores
            if IntentCategory.GREETING in enhanced:
                enhanced[IntentCategory.GREETING] *= self.NON_DATA_PENALTY
            if IntentCategory.ACKNOWLEDGMENT in enhanced:
                enhanced[IntentCategory.ACKNOWLEDGMENT] *= 0.7

            logger.debug(
                "Context enhanced: follow-up with chart context",
                original_data_query=f"{current:.2f}",
                enhanced_data_query=f"{enhanced[IntentCategory.DATA_QUERY]:.2f}",
                follow_up_score=f"{follow_up_score:.2f}",
            )

        # Rule 2: Short message after chart → likely follow-up
        word_count = len(message.split())
        if context.last_assistant_had_chart and word_count <= 5:
            current = enhanced.get(IntentCategory.DATA_QUERY, 0.0)
            enhanced[IntentCategory.DATA_QUERY] = min(
                1.0, current + self.CHART_CONTEXT_BOOST
            )

            logger.debug(
                "Context enhanced: short message after chart",
                word_count=word_count,
                original=f"{current:.2f}",
                enhanced=f"{enhanced[IntentCategory.DATA_QUERY]:.2f}",
            )

        # Rule 3: If data_query is now higher, reduce conflicting intents
        if enhanced.get(IntentCategory.DATA_QUERY, 0) > data_query_score:
            # Greeting shouldn't be high after a data interaction
            if IntentCategory.GREETING in enhanced:
                enhanced[IntentCategory.GREETING] = min(
                    enhanced[IntentCategory.GREETING], 0.3
                )

        return IntentScores.from_dict({k.value: v for k, v in enhanced.items()})
