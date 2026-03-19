"""
Intent Classification Module - Semantic routing for bank advisor.

Q1 2026: Provides intelligent intent detection using:
- Semantic similarity (via EmbeddingService)
- Conversation context enhancement
- Feedback-based learning

Usage:
    from src.services.intent import (
        SemanticIntentScorer,
        ContextEnhancer,
        IntentFeedbackCollector,
        DecisionAggregator,
        score_intent,
    )

    # Quick scoring
    scores = await score_intent("Dame el IMOR de BBVA")

    # Full pipeline
    scorer = await SemanticIntentScorer.get_instance()
    scores = await scorer.score(message)

    enhancer = ContextEnhancer()
    context = ContextEnhancer.extract_context(recent_messages, memory_context)
    enhanced = enhancer.enhance(message, scores, context)

    aggregator = DecisionAggregator()
    decision = aggregator.decide(enhanced)
"""

from .context_enhancer import ContextEnhancer, ConversationContext
from .context_enricher import EnrichedContext, enrich_context
from .decision_aggregator import DecisionAggregator, IntentDecision, RoutingDecision
from .feedback_collector import IntentFeedbackCollector
from .semantic_scorer import SemanticIntentScorer, score_intent
from .types import IntentCategory, IntentScores

__all__ = [
    # Types
    "IntentCategory",
    "IntentScores",
    # Scorer
    "SemanticIntentScorer",
    "score_intent",
    # Context
    "ContextEnhancer",
    "ConversationContext",
    # Context Enrichment (for clarification)
    "EnrichedContext",
    "enrich_context",
    # Feedback
    "IntentFeedbackCollector",
    # Decision
    "DecisionAggregator",
    "IntentDecision",
    "RoutingDecision",
]
