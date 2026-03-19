"""
Tests for Context Enricher - Semantic signals for clarification.

Tests that the context_enricher correctly:
1. Detects follow-up messages using SemanticIntentScorer
2. Computes semantic similarity with context
3. Returns enriched context for plugin consumption
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


class TestEnrichedContext:
    """Tests for EnrichedContext dataclass."""

    def test_default_values(self):
        """EnrichedContext has sensible defaults."""
        from src.services.intent.context_enricher import EnrichedContext

        ctx = EnrichedContext()

        assert ctx.last_banks == []
        assert ctx.last_metric is None
        assert ctx.has_recent_chart is False
        assert ctx.turn_count == 0
        assert ctx.is_followup is False
        assert ctx.followup_confidence == 0.0
        assert ctx.context_similarity == 0.0

    def test_to_dict(self):
        """to_dict() returns all fields."""
        from src.services.intent.context_enricher import EnrichedContext

        ctx = EnrichedContext(
            last_banks=["BBVA", "INVEX"],
            last_metric="IMOR",
            has_recent_chart=True,
            turn_count=3,
            is_followup=True,
            followup_confidence=0.75,
            context_similarity=0.65,
        )

        d = ctx.to_dict()

        assert d["last_banks"] == ["BBVA", "INVEX"]
        assert d["last_metric"] == "IMOR"
        assert d["has_recent_chart"] is True
        assert d["turn_count"] == 3
        assert d["is_followup"] is True
        assert d["followup_confidence"] == 0.75
        assert d["context_similarity"] == 0.65


class TestEnrichContext:
    """Tests for enrich_context function."""

    @pytest.mark.asyncio
    async def test_no_context_returns_basic(self):
        """Without prior context, returns unenriched context."""
        from src.services.intent.context_enricher import enrich_context

        result = await enrich_context(
            message="IMOR de BBVA",
            last_banks=None,
            last_metric=None,
            has_recent_chart=False,
            turn_count=0,
        )

        assert result.is_followup is False
        assert result.followup_confidence == 0.0
        assert result.context_similarity == 0.0

    @pytest.mark.asyncio
    async def test_followup_detected_by_scorer(self):
        """Follow-up is detected using SemanticIntentScorer."""
        from src.services.intent.context_enricher import enrich_context
        from src.services.intent.types import IntentCategory, IntentScores

        # Mock the scorer to return high follow-up score
        mock_scores = IntentScores(
            scores={
                IntentCategory.FOLLOW_UP: 0.72,
                IntentCategory.DATA_QUERY: 0.45,
                IntentCategory.GREETING: 0.1,
            },
            top_intent=IntentCategory.FOLLOW_UP,
            top_confidence=0.72,
        )

        mock_scorer = AsyncMock()
        mock_scorer.score = AsyncMock(return_value=mock_scores)

        # Mock embedding service for similarity
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(
            return_value=np.random.rand(384).tolist()
        )

        with patch(
            "src.services.intent.context_enricher.SemanticIntentScorer.get_instance",
            return_value=mock_scorer,
        ):
            with patch(
                "src.services.embedding_service.get_embedding_service",
                return_value=mock_embedding_svc,
            ):
                result = await enrich_context(
                    message="¿y la cartera?",
                    last_banks=["BBVA"],
                    last_metric="IMOR",
                    has_recent_chart=True,
                    turn_count=3,
                )

        assert result.is_followup is True
        assert result.followup_confidence == 0.72
        assert result.last_banks == ["BBVA"]
        assert result.last_metric == "IMOR"

    @pytest.mark.asyncio
    async def test_followup_by_top_intent(self):
        """Follow-up detected when top_intent is FOLLOW_UP."""
        from src.services.intent.context_enricher import enrich_context
        from src.services.intent.types import IntentCategory, IntentScores

        # Top intent is FOLLOW_UP but score is below 0.5
        mock_scores = IntentScores(
            scores={
                IntentCategory.FOLLOW_UP: 0.45,
                IntentCategory.DATA_QUERY: 0.40,
            },
            top_intent=IntentCategory.FOLLOW_UP,
            top_confidence=0.45,
        )

        mock_scorer = AsyncMock()
        mock_scorer.score = AsyncMock(return_value=mock_scores)

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(
            return_value=np.random.rand(384).tolist()
        )

        with patch(
            "src.services.intent.context_enricher.SemanticIntentScorer.get_instance",
            return_value=mock_scorer,
        ):
            with patch(
                "src.services.embedding_service.get_embedding_service",
                return_value=mock_embedding_svc,
            ):
                result = await enrich_context(
                    message="ese",
                    last_banks=["INVEX"],
                    last_metric="ICAP",
                    has_recent_chart=True,
                    turn_count=2,
                )

        # Should be follow-up because top_intent is FOLLOW_UP
        assert result.is_followup is True

    @pytest.mark.asyncio
    async def test_similarity_computed_with_last_metric(self):
        """Similarity is computed when last_metric exists."""
        from src.services.intent.context_enricher import enrich_context
        from src.services.intent.types import IntentCategory, IntentScores

        mock_scores = IntentScores(
            scores={IntentCategory.DATA_QUERY: 0.8},
            top_intent=IntentCategory.DATA_QUERY,
            top_confidence=0.8,
        )

        mock_scorer = AsyncMock()
        mock_scorer.score = AsyncMock(return_value=mock_scores)

        # Create embeddings that have known similarity
        query_emb = np.array([1.0, 0.0, 0.0])
        context_emb = np.array([0.707, 0.707, 0.0])  # ~45 degrees, similarity ~0.707

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(
            side_effect=[query_emb.tolist(), context_emb.tolist()]
        )

        with patch(
            "src.services.intent.context_enricher.SemanticIntentScorer.get_instance",
            return_value=mock_scorer,
        ):
            with patch(
                "src.services.embedding_service.get_embedding_service",
                return_value=mock_embedding_svc,
            ):
                result = await enrich_context(
                    message="cartera",
                    last_banks=["BBVA"],
                    last_metric="IMOR",
                    has_recent_chart=True,
                    turn_count=2,
                )

        # Similarity should be computed
        assert result.context_similarity > 0.0
        assert result.context_similarity <= 1.0

    @pytest.mark.asyncio
    async def test_no_similarity_without_last_metric(self):
        """Similarity is 0 when last_metric is None."""
        from src.services.intent.context_enricher import enrich_context
        from src.services.intent.types import IntentCategory, IntentScores

        mock_scores = IntentScores(
            scores={IntentCategory.DATA_QUERY: 0.8},
            top_intent=IntentCategory.DATA_QUERY,
            top_confidence=0.8,
        )

        mock_scorer = AsyncMock()
        mock_scorer.score = AsyncMock(return_value=mock_scores)

        with patch(
            "src.services.intent.context_enricher.SemanticIntentScorer.get_instance",
            return_value=mock_scorer,
        ):
            result = await enrich_context(
                message="IMOR de BBVA",
                last_banks=["INVEX"],
                last_metric=None,  # No last_metric
                has_recent_chart=True,
                turn_count=1,
            )

        assert result.context_similarity == 0.0

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_scorer_error(self):
        """Returns unenriched context if scorer fails."""
        from src.services.intent.context_enricher import enrich_context

        mock_scorer = AsyncMock()
        mock_scorer.score = AsyncMock(side_effect=Exception("Scorer error"))

        with patch(
            "src.services.intent.context_enricher.SemanticIntentScorer.get_instance",
            return_value=mock_scorer,
        ):
            result = await enrich_context(
                message="¿y la cartera?",
                last_banks=["BBVA"],
                last_metric="IMOR",
                has_recent_chart=True,
                turn_count=2,
            )

        # Should return context without enrichment
        assert result.is_followup is False
        assert result.followup_confidence == 0.0
        assert result.last_banks == ["BBVA"]
        assert result.last_metric == "IMOR"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_embedding_error(self):
        """Similarity is 0 if embedding service fails."""
        from src.services.intent.context_enricher import enrich_context
        from src.services.intent.types import IntentCategory, IntentScores

        mock_scores = IntentScores(
            scores={IntentCategory.FOLLOW_UP: 0.6},
            top_intent=IntentCategory.FOLLOW_UP,
            top_confidence=0.6,
        )

        mock_scorer = AsyncMock()
        mock_scorer.score = AsyncMock(return_value=mock_scores)

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(
            side_effect=Exception("Embedding error")
        )

        with patch(
            "src.services.intent.context_enricher.SemanticIntentScorer.get_instance",
            return_value=mock_scorer,
        ):
            with patch(
                "src.services.embedding_service.get_embedding_service",
                return_value=mock_embedding_svc,
            ):
                result = await enrich_context(
                    message="cartera",
                    last_banks=["BBVA"],
                    last_metric="IMOR",
                    has_recent_chart=True,
                    turn_count=2,
                )

        # Follow-up should still be detected
        assert result.is_followup is True
        # But similarity should be 0 due to error
        assert result.context_similarity == 0.0


class TestComputeSimilarity:
    """Tests for _compute_similarity helper."""

    @pytest.mark.asyncio
    async def test_identical_vectors_have_similarity_1(self):
        """Identical embeddings have similarity 1."""
        from src.services.intent.context_enricher import _compute_similarity

        embedding = np.random.rand(384).tolist()

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(return_value=embedding)

        with patch(
            "src.services.embedding_service.get_embedding_service",
            return_value=mock_embedding_svc,
        ):
            similarity = await _compute_similarity("IMOR", "IMOR")

        assert similarity == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_orthogonal_vectors_have_similarity_0(self):
        """Orthogonal embeddings have similarity 0."""
        from src.services.intent.context_enricher import _compute_similarity

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(
            side_effect=[vec1, vec2]
        )

        with patch(
            "src.services.embedding_service.get_embedding_service",
            return_value=mock_embedding_svc,
        ):
            similarity = await _compute_similarity("query", "context")

        assert similarity == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_similarity_clamped_to_0_1(self):
        """Similarity is clamped to [0, 1] range."""
        from src.services.intent.context_enricher import _compute_similarity

        # Negative dot product (opposite directions)
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.encode_single_async = AsyncMock(
            side_effect=[vec1, vec2]
        )

        with patch(
            "src.services.embedding_service.get_embedding_service",
            return_value=mock_embedding_svc,
        ):
            similarity = await _compute_similarity("a", "b")

        # Should be clamped to 0, not -1
        assert similarity >= 0.0
        assert similarity <= 1.0
