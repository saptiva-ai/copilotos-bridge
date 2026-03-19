# Plan: Semantic Intent Router for Bank Advisor Pre-Check

## Overview

This plan replaces hardcoded regex patterns with a semantic similarity-based system using the existing `EmbeddingService` (Saptiva internal, `paraphrase-multilingual-MiniLM-L12-v2`).

---

## Phase 1: Semantic Intent Scorer

**Goal:** Create a scorer that classifies messages by semantic similarity to category exemplars.

### 1.1 Create Intent Module Structure

```bash
# New files to create
apps/backend/src/services/intent/__init__.py
apps/backend/src/services/intent/semantic_scorer.py
apps/backend/src/services/intent/types.py
```

### 1.2 Define Intent Types (`types.py`)

```python
# apps/backend/src/services/intent/types.py

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional

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
    """Scores for each intent category."""
    scores: Dict[IntentCategory, float]
    top_intent: IntentCategory
    top_confidence: float

    @classmethod
    def from_dict(cls, scores: Dict[str, float]) -> "IntentScores":
        enum_scores = {IntentCategory(k): v for k, v in scores.items()}
        top = max(enum_scores, key=enum_scores.get)
        return cls(
            scores=enum_scores,
            top_intent=top,
            top_confidence=enum_scores[top],
        )
```

### 1.3 Implement Semantic Scorer (`semantic_scorer.py`)

```python
# apps/backend/src/services/intent/semantic_scorer.py
"""
Semantic Intent Scorer using EmbeddingService.

Uses cosine similarity between message embeddings and category exemplar
embeddings to classify user intent.

Leverages Saptiva's internal EmbeddingService (paraphrase-multilingual-MiniLM-L12-v2).
"""

import numpy as np
from typing import Dict, List, Optional
import structlog

from ..embedding_service import get_embedding_service
from .types import IntentCategory, IntentScores

logger = structlog.get_logger(__name__)


# =============================================================================
# CATEGORY EXEMPLARS
# =============================================================================
# These are "semantic anchors" - representative examples for each category.
# Unlike regex, semantic similarity handles typos and variations automatically.

CATEGORY_EXEMPLARS: Dict[str, List[str]] = {
    IntentCategory.GREETING.value: [
        "hola",
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "qué tal",
        "saludos",
        "hey",
        "holi",  # Common variation
    ],
    IntentCategory.ACKNOWLEDGMENT.value: [
        "gracias",
        "muchas gracias",
        "ok entendido",
        "perfecto",
        "de acuerdo",
        "vale",
        "genial",
        "excelente",
        "adiós",
        "hasta luego",
    ],
    IntentCategory.KNOWLEDGE_QUERY.value: [
        "qué es el IMOR",
        "qué significa capitalización",
        "qué es la morosidad",
        "explica qué es el ICAP",
        "define cartera vencida",
        "cómo se calcula el índice de cobertura",
        "qué es la CNBV",
    ],
    IntentCategory.DATA_QUERY.value: [
        "dame el IMOR de BBVA",
        "muestra la evolución del ICAP",
        "cuál es la morosidad de Banorte",
        "top 5 bancos por capitalización",
        "compara INVEX con Santander",
        "ranking de bancos por cartera",
        "histórico de reservas de BBVA",
    ],
    IntentCategory.FOLLOW_UP.value: [
        "y por qué subió",
        "explícame más",
        "cuánto cambió",
        "compáralo con el anterior",
        "el primero de la lista",
        "ese banco",
        "más detalles",
    ],
}


class SemanticIntentScorer:
    """
    Scores user intent using semantic similarity with EmbeddingService.

    Architecture:
    - Pre-computes embeddings for category exemplars at initialization
    - For each query, computes embedding and cosine similarity to categories
    - Returns scores for all categories (enables confidence-based routing)
    """

    _instance: Optional["SemanticIntentScorer"] = None
    _initialized: bool = False

    def __init__(self):
        """Initialize scorer (lazy - embeddings computed on first use)."""
        self._embedding_service = None
        self._category_embeddings: Dict[str, np.ndarray] = {}
        self._embedding_dim: int = 384  # MiniLM default

    @classmethod
    async def get_instance(cls) -> "SemanticIntentScorer":
        """Get singleton instance with initialized embeddings."""
        if cls._instance is None:
            cls._instance = SemanticIntentScorer()

        if not cls._initialized:
            await cls._instance._initialize()
            cls._initialized = True

        return cls._instance

    async def _initialize(self):
        """Pre-compute embeddings for category exemplars."""
        self._embedding_service = get_embedding_service()

        logger.info("Initializing semantic intent scorer embeddings...")

        for category, exemplars in CATEGORY_EXEMPLARS.items():
            # Use batch encoding for efficiency
            embeddings = await self._embedding_service.encode_async(exemplars)
            self._category_embeddings[category] = np.array(embeddings)

            logger.debug(
                "Category embeddings computed",
                category=category,
                exemplar_count=len(exemplars),
            )

        # Update dimension from actual embeddings
        first_cat = list(self._category_embeddings.values())[0]
        self._embedding_dim = first_cat.shape[1]

        logger.info(
            "Semantic intent scorer initialized",
            categories=len(self._category_embeddings),
            embedding_dim=self._embedding_dim,
        )

    async def score(self, message: str) -> IntentScores:
        """
        Score a message against all intent categories.

        Args:
            message: User message to classify

        Returns:
            IntentScores with confidence for each category
        """
        if not self._embedding_service:
            await self._initialize()

        # Get message embedding (uses internal cache)
        message_embedding = await self._embedding_service.encode_single_async(
            message, use_cache=True
        )
        message_vec = np.array(message_embedding)

        # Compute similarity to each category
        scores: Dict[str, float] = {}

        for category, exemplar_embeddings in self._category_embeddings.items():
            # Cosine similarity = dot product for normalized vectors
            # We use max similarity (closest exemplar) as category score
            similarities = np.dot(exemplar_embeddings, message_vec)
            similarities = similarities / (
                np.linalg.norm(exemplar_embeddings, axis=1) *
                np.linalg.norm(message_vec)
            )
            scores[category] = float(np.max(similarities))

        result = IntentScores.from_dict(scores)

        logger.debug(
            "Intent scored",
            message_preview=message[:50],
            top_intent=result.top_intent.value,
            top_confidence=f"{result.top_confidence:.3f}",
        )

        return result

    async def score_batch(self, messages: List[str]) -> List[IntentScores]:
        """Score multiple messages efficiently."""
        # Batch encode all messages
        embeddings = await self._embedding_service.encode_async(messages)

        results = []
        for i, msg_embedding in enumerate(embeddings):
            msg_vec = np.array(msg_embedding)
            scores = {}

            for category, exemplar_embeddings in self._category_embeddings.items():
                similarities = np.dot(exemplar_embeddings, msg_vec)
                similarities = similarities / (
                    np.linalg.norm(exemplar_embeddings, axis=1) *
                    np.linalg.norm(msg_vec)
                )
                scores[category] = float(np.max(similarities))

            results.append(IntentScores.from_dict(scores))

        return results
```

### 1.4 Tests for Semantic Scorer

```python
# apps/backend/tests/unit/test_semantic_intent_router.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import numpy as np

from src.services.intent.semantic_scorer import SemanticIntentScorer
from src.services.intent.types import IntentCategory


class TestSemanticIntentScorer:
    """Tests for semantic intent scoring."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        mock = MagicMock()
        # Return random embeddings for testing
        mock.encode_async = AsyncMock(
            side_effect=lambda texts: [np.random.randn(384).tolist() for _ in texts]
        )
        mock.encode_single_async = AsyncMock(
            return_value=np.random.randn(384).tolist()
        )
        return mock

    @pytest.mark.asyncio
    async def test_greeting_detection(self, mock_embedding_service):
        """Should detect greetings with high confidence."""
        with patch(
            'src.services.intent.semantic_scorer.get_embedding_service',
            return_value=mock_embedding_service
        ):
            scorer = SemanticIntentScorer()
            # Manually set embeddings to control test
            scorer._embedding_service = mock_embedding_service
            scorer._category_embeddings = {
                IntentCategory.GREETING.value: np.array([[1, 0, 0]]),
                IntentCategory.DATA_QUERY.value: np.array([[0, 1, 0]]),
            }
            scorer._embedding_dim = 3

            # Mock greeting-like embedding
            mock_embedding_service.encode_single_async.return_value = [0.9, 0.1, 0]

            scores = await scorer.score("hola buenos días")

            assert scores.top_intent == IntentCategory.GREETING

    @pytest.mark.asyncio
    async def test_data_query_detection(self, mock_embedding_service):
        """Should detect data queries."""
        # Similar test structure for data queries
        pass

    @pytest.mark.asyncio
    async def test_handles_typos_semantically(self):
        """Should handle typos via semantic similarity (not exact match)."""
        # "Holi" should be similar to "Hola" embedding
        pass
```

---

## Phase 2: Context Enhancer

**Goal:** Adjust intent scores based on conversation history.

### 2.1 Implement Context Enhancer (`context_enhancer.py`)

```python
# apps/backend/src/services/intent/context_enhancer.py
"""
Context Enhancer - Adjusts intent scores based on conversation history.

If the conversation has recent banking context (charts, metrics),
follow-up questions should be routed to bank-advisor.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import structlog

from .types import IntentCategory, IntentScores
from .semantic_scorer import SemanticIntentScorer

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

    Rules:
    1. If recent chart exists + message is follow-up → boost data_query
    2. If short message after chart → likely follow-up
    3. If explicit banking terms in context → boost data_query
    """

    # Weight multipliers for context signals
    FOLLOW_UP_BOOST = 0.3
    CHART_CONTEXT_BOOST = 0.2

    def __init__(self):
        self._scorer: Optional[SemanticIntentScorer] = None

    @classmethod
    def extract_context(
        cls,
        recent_messages: List[Dict],
        memory_context: Dict,
    ) -> ConversationContext:
        """Extract relevant context from conversation."""
        has_chart = bool(
            memory_context.get("last_chart_data") or
            memory_context.get("last_metric") or
            any(
                msg.get("metadata", {}).get("bank_chart_data")
                for msg in recent_messages[-3:]  # Last 3 messages
            )
        )

        last_metric = memory_context.get("last_metric")
        last_banks = memory_context.get("last_banks", [])

        # Check if last assistant message had a chart
        last_assistant_had_chart = False
        for msg in reversed(recent_messages):
            if msg.get("role") == "assistant":
                last_assistant_had_chart = bool(
                    msg.get("metadata", {}).get("bank_chart_data")
                )
                break

        return ConversationContext(
            has_recent_chart=has_chart,
            last_metric=last_metric,
            last_banks=last_banks if isinstance(last_banks, list) else [],
            turn_count=len(recent_messages),
            last_assistant_had_chart=last_assistant_had_chart,
        )

    async def enhance(
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
        enhanced = dict(base_scores.scores)

        # Rule 1: Recent chart + follow-up pattern → boost data_query
        if context.has_recent_chart:
            follow_up_score = base_scores.scores.get(IntentCategory.FOLLOW_UP, 0)

            if follow_up_score > 0.5:
                # Strong follow-up signal + chart context
                current = enhanced.get(IntentCategory.DATA_QUERY, 0)
                enhanced[IntentCategory.DATA_QUERY] = min(
                    1.0,
                    current + self.FOLLOW_UP_BOOST + self.CHART_CONTEXT_BOOST
                )

                # Reduce greeting/acknowledgment scores
                enhanced[IntentCategory.GREETING] *= 0.5
                enhanced[IntentCategory.ACKNOWLEDGMENT] *= 0.7

                logger.debug(
                    "Context enhanced: follow-up with chart context",
                    original_data_query=current,
                    enhanced_data_query=enhanced[IntentCategory.DATA_QUERY],
                )

        # Rule 2: Short message after chart → likely follow-up
        if (
            context.last_assistant_had_chart and
            len(message.split()) <= 5
        ):
            current = enhanced.get(IntentCategory.DATA_QUERY, 0)
            enhanced[IntentCategory.DATA_QUERY] = min(
                1.0,
                current + self.CHART_CONTEXT_BOOST
            )

        # Reconstruct IntentScores
        return IntentScores.from_dict({k.value: v for k, v in enhanced.items()})
```

---

## Phase 3: Feedback Collector

**Goal:** Learn from bank-advisor responses to improve future routing.

### 3.1 Implement Feedback Collector (`feedback_collector.py`)

```python
# apps/backend/src/services/intent/feedback_collector.py
"""
Feedback Collector - Learns from bank-advisor responses.

When bank-advisor returns None for a message we routed to it,
we learn that similar messages are not banking queries.
"""

import hashlib
import json
from datetime import datetime
from typing import Optional
import structlog

from ...core.redis_cache import get_redis_cache

logger = structlog.get_logger(__name__)


class IntentFeedbackCollector:
    """
    Collects implicit feedback to improve intent routing.

    Feedback signals:
    - bank-advisor returns chart → message was correctly routed (positive)
    - bank-advisor returns None → message was NOT a banking query (negative)

    Uses Redis for storage with TTL-based expiration.
    """

    # Redis key prefixes
    PREFIX_FEEDBACK = "intent_feedback"
    PREFIX_NEGATIVE = "intent_negative"

    # TTLs
    TTL_FEEDBACK_LOG = 7 * 24 * 3600  # 7 days
    TTL_NEGATIVE_CACHE = 24 * 3600    # 1 day (short, allow relearning)

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            self._redis = await get_redis_cache()
        return self._redis

    def _hash_message(self, message: str) -> str:
        """Create hash for message (for cache keys)."""
        normalized = message.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    async def record_feedback(
        self,
        message: str,
        routed_to_advisor: bool,
        advisor_returned_data: bool,
        intent_scores: Optional[dict] = None,
    ):
        """
        Record routing feedback for learning.

        Args:
            message: Original user message
            routed_to_advisor: Whether we routed to bank-advisor
            advisor_returned_data: Whether bank-advisor returned chart/data
            intent_scores: Optional scores from classifier
        """
        redis = await self._get_redis()
        if not redis:
            return

        try:
            feedback = {
                "message_hash": self._hash_message(message),
                "message_preview": message[:100],
                "routed": routed_to_advisor,
                "success": advisor_returned_data,
                "scores": intent_scores,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Log feedback for analysis
            key = f"{self.PREFIX_FEEDBACK}:log"
            await redis.lpush(key, json.dumps(feedback))
            await redis.ltrim(key, 0, 9999)  # Keep last 10k

            # If false positive (routed but no data), mark as negative
            if routed_to_advisor and not advisor_returned_data:
                await self._mark_negative(message)

                logger.info(
                    "Intent feedback: false positive recorded",
                    message_preview=message[:50],
                )

        except Exception as e:
            logger.warning(
                "Failed to record intent feedback",
                error=str(e),
            )

    async def _mark_negative(self, message: str):
        """Mark message as known non-banking query."""
        redis = await self._get_redis()
        if not redis:
            return

        key = f"{self.PREFIX_NEGATIVE}:{self._hash_message(message)}"
        await redis.setex(key, self.TTL_NEGATIVE_CACHE, "1")

    async def is_known_negative(self, message: str) -> bool:
        """Check if message is in negative cache."""
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            key = f"{self.PREFIX_NEGATIVE}:{self._hash_message(message)}"
            return bool(await redis.exists(key))
        except Exception:
            return False

    async def get_feedback_stats(self) -> dict:
        """Get feedback statistics for monitoring."""
        redis = await self._get_redis()
        if not redis:
            return {}

        try:
            key = f"{self.PREFIX_FEEDBACK}:log"
            recent = await redis.lrange(key, 0, 999)  # Last 1k

            total = len(recent)
            if not total:
                return {"total": 0}

            successes = sum(
                1 for f in recent
                if json.loads(f).get("success")
            )

            return {
                "total": total,
                "successes": successes,
                "false_positives": total - successes,
                "accuracy": successes / total if total else 0,
            }
        except Exception as e:
            logger.warning("Failed to get feedback stats", error=str(e))
            return {}
```

---

## Phase 4: Decision Aggregator

**Goal:** Combine all signals into a final routing decision.

### 4.1 Implement Aggregator (`decision_aggregator.py`)

```python
# apps/backend/src/services/intent/decision_aggregator.py
"""
Decision Aggregator - Combines signals into routing decision.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import structlog

from .types import IntentCategory, IntentScores

logger = structlog.get_logger(__name__)


class RoutingDecision(str, Enum):
    INVOKE = "invoke"
    SKIP = "skip"


@dataclass
class IntentDecision:
    """Final routing decision with reasoning."""
    decision: RoutingDecision
    confidence: float
    reason: str
    intent_category: IntentCategory
    scores: dict


class DecisionAggregator:
    """
    Aggregates intent signals into a final routing decision.

    Thresholds (configurable):
    - INVOKE if data_query OR knowledge_query confidence > 0.55
    - SKIP if greeting OR acknowledgment confidence > 0.65
    - Default: INVOKE (delegate to bank-advisor)
    """

    # Thresholds
    BANKING_THRESHOLD = 0.55
    NON_BANKING_THRESHOLD = 0.65

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
            explicit_enabled: Whether tools explicitly enabled

        Returns:
            IntentDecision with reasoning
        """
        # Rule 1: Explicit enablement always wins
        if explicit_enabled:
            return IntentDecision(
                decision=RoutingDecision.INVOKE,
                confidence=1.0,
                reason="explicitly_enabled",
                intent_category=scores.top_intent,
                scores={k.value: v for k, v in scores.scores.items()},
            )

        # Rule 2: Negative cache → skip
        if is_negative_cached:
            return IntentDecision(
                decision=RoutingDecision.SKIP,
                confidence=0.9,
                reason="cached_as_non_banking",
                intent_category=scores.top_intent,
                scores={k.value: v for k, v in scores.scores.items()},
            )

        # Rule 3: High banking confidence → invoke
        banking_score = max(
            scores.scores.get(IntentCategory.DATA_QUERY, 0),
            scores.scores.get(IntentCategory.KNOWLEDGE_QUERY, 0),
        )

        if banking_score > self.BANKING_THRESHOLD:
            return IntentDecision(
                decision=RoutingDecision.INVOKE,
                confidence=banking_score,
                reason=f"high_banking_score:{banking_score:.2f}",
                intent_category=scores.top_intent,
                scores={k.value: v for k, v in scores.scores.items()},
            )

        # Rule 4: High non-banking confidence → skip
        non_banking_score = max(
            scores.scores.get(IntentCategory.GREETING, 0),
            scores.scores.get(IntentCategory.ACKNOWLEDGMENT, 0),
        )

        if non_banking_score > self.NON_BANKING_THRESHOLD:
            return IntentDecision(
                decision=RoutingDecision.SKIP,
                confidence=non_banking_score,
                reason=f"high_non_banking_score:{non_banking_score:.2f}",
                intent_category=scores.top_intent,
                scores={k.value: v for k, v in scores.scores.items()},
            )

        # Rule 5: Ambiguous → delegate (let bank-advisor decide)
        return IntentDecision(
            decision=RoutingDecision.INVOKE,
            confidence=0.5,
            reason="ambiguous_delegating",
            intent_category=scores.top_intent,
            scores={k.value: v for k, v in scores.scores.items()},
        )
```

---

## Phase 5: Integration

**Goal:** Integrate into `BankAdvisorPreCheckService`.

### 5.1 Refactor `bank_advisor_precheck.py`

```python
# apps/backend/src/services/streaming/bank_advisor_precheck.py
"""
Bank Advisor Pre-Check Service - Semantic Intent Routing.

Uses semantic similarity + contextual signals for intelligent routing.
"""

from typing import Dict, List, Optional, Tuple
import structlog

from ..intent.semantic_scorer import SemanticIntentScorer
from ..intent.context_enhancer import ContextEnhancer, ConversationContext
from ..intent.feedback_collector import IntentFeedbackCollector
from ..intent.decision_aggregator import DecisionAggregator, RoutingDecision

logger = structlog.get_logger(__name__)


class BankAdvisorPreCheckService:
    """
    Intelligent routing service using semantic intent detection.
    """

    _scorer: Optional[SemanticIntentScorer] = None
    _enhancer: Optional[ContextEnhancer] = None
    _feedback: Optional[IntentFeedbackCollector] = None
    _aggregator: Optional[DecisionAggregator] = None
    _initialized: bool = False

    @classmethod
    async def _ensure_initialized(cls):
        """Lazy initialization of components."""
        if cls._initialized:
            return

        cls._scorer = await SemanticIntentScorer.get_instance()
        cls._enhancer = ContextEnhancer()
        cls._feedback = IntentFeedbackCollector()
        cls._aggregator = DecisionAggregator()
        cls._initialized = True

        logger.info("BankAdvisorPreCheckService initialized with semantic routing")

    @classmethod
    async def should_run_advisor(
        cls,
        message: str,
        tools_enabled: Dict[str, bool],
        recent_messages: Optional[List[Dict]] = None,
        memory_context: Optional[Dict] = None,
    ) -> Tuple[bool, str]:
        """
        Determine if bank advisor should run using semantic routing.

        Args:
            message: User message
            tools_enabled: Explicit tool enablement
            recent_messages: Recent conversation messages
            memory_context: Session memory context

        Returns:
            (should_run, reason)
        """
        await cls._ensure_initialized()

        # Check explicit enablement first
        explicit = (
            tools_enabled.get("bank-advisor", False) or
            tools_enabled.get("bank_analytics", False)
        )

        # Get semantic scores
        base_scores = await cls._scorer.score(message)

        # Extract and apply context
        context = ContextEnhancer.extract_context(
            recent_messages or [],
            memory_context or {},
        )
        enhanced_scores = await cls._enhancer.enhance(
            message, base_scores, context
        )

        # Check feedback cache
        is_negative = await cls._feedback.is_known_negative(message)

        # Make decision
        decision = cls._aggregator.decide(
            scores=enhanced_scores,
            is_negative_cached=is_negative,
            explicit_enabled=explicit,
        )

        logger.debug(
            "intent_routing.decision",
            message_preview=message[:50],
            decision=decision.decision.value,
            confidence=f"{decision.confidence:.2f}",
            reason=decision.reason,
            intent=decision.intent_category.value,
        )

        should_run = decision.decision == RoutingDecision.INVOKE
        return should_run, decision.reason

    @classmethod
    async def record_feedback(
        cls,
        message: str,
        advisor_returned_data: bool,
    ):
        """Record feedback after bank-advisor response."""
        await cls._ensure_initialized()

        await cls._feedback.record_feedback(
            message=message,
            routed_to_advisor=True,
            advisor_returned_data=advisor_returned_data,
        )

    # ... rest of existing methods (load_recent_messages, check_and_invoke)
```

---

## Phase 6: Testing & Validation

### 6.1 Unit Tests

```bash
# Run semantic intent tests
make test-local TEST_FILE="tests/unit/test_semantic_intent_router.py"

# Run bank advisor precheck tests
make test-local TEST_FILE="tests/unit/test_streaming_services.py" TEST_ARGS="-k BankAdvisorPreCheckService"
```

### 6.2 Integration Tests

```python
# Test cases to verify
test_cases = [
    # Greetings (should skip)
    ("Hola", False, "greeting"),
    ("Holi buenos días", False, "greeting"),  # Typo handled
    ("Hey que tal", False, "greeting"),

    # Acknowledgments (should skip)
    ("Gracias", False, "acknowledgment"),
    ("Ok perfecto", False, "acknowledgment"),

    # Knowledge queries (should invoke)
    ("¿Qué es el IMOR?", True, "knowledge_query"),
    ("Explica qué significa capitalización", True, "knowledge_query"),

    # Data queries (should invoke)
    ("Dame el IMOR de BBVA", True, "data_query"),
    ("Top 5 bancos por morosidad", True, "data_query"),

    # Follow-ups with context (should invoke)
    ("¿Por qué subió?", True, "follow_up"),  # After chart shown
    ("El primero", True, "follow_up"),  # After ranking shown
]
```

### 6.3 Latency Validation

```python
# Benchmark: must be <50ms for cached embeddings
import time

async def benchmark_latency():
    scorer = await SemanticIntentScorer.get_instance()

    # Warm up cache
    await scorer.score("test message")

    # Measure
    times = []
    for _ in range(100):
        start = time.perf_counter()
        await scorer.score("Dame el IMOR de BBVA")
        times.append((time.perf_counter() - start) * 1000)

    avg = sum(times) / len(times)
    p99 = sorted(times)[99]

    print(f"Avg: {avg:.2f}ms, P99: {p99:.2f}ms")
    assert avg < 50, f"Latency too high: {avg}ms"
```

---

## Validation Checklist

- [ ] All existing tests pass (`TestBankAdvisorPreCheckService`)
- [ ] Typos handled semantically ("Holi" → greeting)
- [ ] Follow-ups with chart context routed correctly
- [ ] Feedback loop records false positives
- [ ] Latency <50ms for cached queries
- [ ] No external API dependencies
- [ ] Uses only Saptiva EmbeddingService

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/services/intent/__init__.py` | Create | Module init |
| `src/services/intent/types.py` | Create | Intent types and dataclasses |
| `src/services/intent/semantic_scorer.py` | Create | Semantic similarity scorer |
| `src/services/intent/context_enhancer.py` | Create | Context-aware enhancement |
| `src/services/intent/feedback_collector.py` | Create | Redis feedback loop |
| `src/services/intent/decision_aggregator.py` | Create | Final decision logic |
| `src/services/streaming/bank_advisor_precheck.py` | Modify | Integration |
| `tests/unit/test_semantic_intent_router.py` | Create | Unit tests |
