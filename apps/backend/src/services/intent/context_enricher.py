"""
Context Enricher - Adds semantic signals to conversation context.

Uses existing services to enrich context with:
- Follow-up detection via SemanticIntentScorer (embeddings)
- Query-context similarity via EmbeddingService

This enriched context is used for intelligent clarification decisions.

Usage:
    from src.services.intent import enrich_context, EnrichedContext

    enriched = await enrich_context(
        message="¿y la cartera?",
        last_banks=[],
        last_metric="IMOR",
        has_recent_chart=True,
        turn_count=3
    )

    # enriched.is_followup = True
    # enriched.context_similarity = 0.65
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import structlog

from .semantic_scorer import SemanticIntentScorer
from .types import IntentCategory

logger = structlog.get_logger(__name__)


@dataclass
class EnrichedContext:
    """
    Contexto enriquecido con señales semánticas para clarificación.

    Campos existentes (de ConversationContext):
        last_banks: Bancos del mensaje anterior
        last_metric: Métrica del mensaje anterior
        has_recent_chart: Si hay gráfica reciente
        turn_count: Número de turnos en la conversación

    Campos nuevos (señales semánticas):
        is_followup: Si el mensaje es un follow-up (detectado por embeddings)
        followup_confidence: Confianza del score de follow-up [0-1]
        context_similarity: Similaridad semántica con el contexto [0-1]
    """

    # Campos existentes
    last_banks: List[str] = field(default_factory=list)
    last_metric: Optional[str] = None
    has_recent_chart: bool = False
    turn_count: int = 0

    # Campos nuevos - señales semánticas
    is_followup: bool = False
    followup_confidence: float = 0.0
    context_similarity: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dict for passing to plugin."""
        return {
            "last_banks": self.last_banks,
            "last_metric": self.last_metric,
            "has_recent_chart": self.has_recent_chart,
            "turn_count": self.turn_count,
            "is_followup": self.is_followup,
            "followup_confidence": self.followup_confidence,
            "context_similarity": self.context_similarity,
        }


async def enrich_context(
    message: str,
    last_banks: Optional[List[str]] = None,
    last_metric: Optional[str] = None,
    has_recent_chart: bool = False,
    turn_count: int = 0,
) -> EnrichedContext:
    """
    Enriquece el contexto con señales semánticas.

    Usa servicios existentes:
    - SemanticIntentScorer: Detecta si es follow-up usando embeddings
    - EmbeddingService: Calcula similaridad query-contexto

    Args:
        message: Mensaje actual del usuario
        last_banks: Bancos del mensaje anterior
        last_metric: Métrica del mensaje anterior
        has_recent_chart: Si hay gráfica reciente
        turn_count: Número de turnos en la conversación

    Returns:
        EnrichedContext con señales de follow-up y similaridad

    Example:
        enriched = await enrich_context(
            message="¿y la cartera?",
            last_banks=["BBVA"],
            last_metric="IMOR",
            has_recent_chart=True,
            turn_count=3
        )
        # enriched.is_followup = True
        # enriched.followup_confidence = 0.72
        # enriched.context_similarity = 0.45
    """
    enriched = EnrichedContext(
        last_banks=last_banks or [],
        last_metric=last_metric,
        has_recent_chart=has_recent_chart,
        turn_count=turn_count,
    )

    # Solo enriquecer si hay contexto previo relevante
    if not has_recent_chart and not last_metric:
        logger.debug(
            "context_enricher.skip_no_context",
            message_preview=message[:50] if message else "",
        )
        return enriched

    try:
        # 1. Detectar follow-up usando SemanticIntentScorer
        scorer = await SemanticIntentScorer.get_instance()
        scores = await scorer.score(message)

        followup_score = scores.scores.get(IntentCategory.FOLLOW_UP, 0.0)
        enriched.followup_confidence = followup_score

        # Es follow-up si:
        # - Top intent es FOLLOW_UP, o
        # - Score de follow-up > 0.5
        enriched.is_followup = (
            scores.top_intent == IntentCategory.FOLLOW_UP or followup_score > 0.5
        )

        # 2. Calcular similaridad con contexto (usa cache de embeddings)
        if last_metric:
            enriched.context_similarity = await _compute_similarity(
                message, last_metric
            )

        logger.info(
            "context_enricher.enriched",
            is_followup=enriched.is_followup,
            followup_confidence=f"{enriched.followup_confidence:.2f}",
            context_similarity=f"{enriched.context_similarity:.2f}",
            has_chart=has_recent_chart,
            last_metric=last_metric,
            last_banks=last_banks,
        )

    except Exception as e:
        logger.warning(
            "context_enricher.enrichment_failed",
            error=str(e),
            message_preview=message[:50] if message else "",
        )
        # Retornar contexto sin enriquecer en caso de error

    return enriched


async def _compute_similarity(query: str, context_text: str) -> float:
    """
    Calcula similaridad coseno entre query y texto de contexto.

    Usa EmbeddingService con cache para evitar recomputar embeddings.

    Args:
        query: Query actual del usuario
        context_text: Texto del contexto (e.g., last_metric)

    Returns:
        Similaridad coseno [0, 1]
    """
    try:
        from ..embedding_service import get_embedding_service

        embedding_svc = get_embedding_service()

        # Ambas llamadas usan cache LRU
        query_emb = await embedding_svc.encode_single_async(query, use_cache=True)
        context_emb = await embedding_svc.encode_single_async(
            context_text, use_cache=True
        )

        # Cosine similarity
        query_arr = np.array(query_emb)
        context_arr = np.array(context_emb)

        norm_product = np.linalg.norm(query_arr) * np.linalg.norm(context_arr)
        if norm_product == 0:
            return 0.0

        similarity = float(np.dot(query_arr, context_arr) / norm_product)

        logger.debug(
            "context_enricher.similarity_computed",
            query_preview=query[:30],
            context_text=context_text,
            similarity=f"{similarity:.3f}",
        )

        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

    except Exception as e:
        logger.warning(
            "context_enricher.similarity_failed",
            error=str(e),
        )
        return 0.0
