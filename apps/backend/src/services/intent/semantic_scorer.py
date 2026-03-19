"""
Semantic Intent Scorer - Classification using embedding similarity.

Q1 2026: Uses Saptiva's internal EmbeddingService (paraphrase-multilingual-MiniLM-L12-v2)
to classify user intent by semantic similarity to category exemplars.

Architecture:
- Pre-computes embeddings for category exemplars at initialization
- For each query, computes embedding and cosine similarity to categories
- Returns scores for all categories (enables confidence-based routing)

Key advantage over regex:
- Handles typos ("Holi" ≈ "Hola")
- Handles variations ("Dame el índice de mora" ≈ "Muestra el IMOR")
- No manual pattern maintenance
"""

from typing import Dict, List, Optional

import numpy as np
import structlog

from .types import IntentCategory, IntentScores

logger = structlog.get_logger(__name__)


# =============================================================================
# CATEGORY EXEMPLARS
# =============================================================================
# These are "semantic anchors" - representative examples for each category.
# The scorer finds which category's exemplars are most similar to the input.

CATEGORY_EXEMPLARS: Dict[str, List[str]] = {
    IntentCategory.GREETING.value: [
        "hola",
        "holi",  # Common typo/variation
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "buen día",
        "qué tal",
        "que tal",
        "saludos",
        "hey",
        "hola qué tal",
        "buenas",
    ],
    IntentCategory.ACKNOWLEDGMENT.value: [
        "gracias",
        "muchas gracias",
        "ok",
        "okey",
        "okay",
        "entendido",
        "perfecto",
        "de acuerdo",
        "vale",
        "genial",
        "excelente",
        "muy bien",
        "adiós",
        "adios",
        "hasta luego",
        "nos vemos",
        "chao",
    ],
    IntentCategory.KNOWLEDGE_QUERY.value: [
        "qué es el IMOR",
        "qué es el ICAP",
        "qué es la morosidad",
        "qué significa capitalización",
        "qué significa cartera vencida",
        "explica qué es el ICOR",
        "define morosidad",
        "definición de IMOR",
        "cómo se calcula el índice de cobertura",
        "qué es la CNBV",
        "qué significa PDM",
        "explícame qué es el índice de capitalización",
    ],
    IntentCategory.DATA_QUERY.value: [
        "dame el IMOR de BBVA",
        "muestra la evolución del ICAP",
        "cuál es la morosidad de Banorte",
        "cuál es el IMOR de INVEX",
        "top 5 bancos por capitalización",
        "top bancos por morosidad",
        "compara INVEX con Santander",
        "ranking de bancos por cartera",
        "histórico de reservas de BBVA",
        "evolución del ICAP de INVEX",
        "dame los datos de cartera vencida",
        "muéstrame el IMOR del sistema",
        "bancos más capitalizados",
        "bancos con mayor morosidad",
        "comparativa de IMOR entre bancos",
        # Catalog queries (2026-02-04 FIX - institution listing)
        "dame las instituciones",
        "qué bancos tienes",
        "instituciones financieras disponibles",
        "lista de instituciones",
        "qué instituciones hay en tu base",
        "bancos disponibles",
        "entidades financieras que tienes",
    ],
    IntentCategory.FOLLOW_UP.value: [
        "y por qué subió",
        "por qué bajó",
        "explícame más",
        "cuéntame más",
        "cuánto cambió",
        "compáralo con el anterior",
        "el primero de la lista",
        "el segundo",
        "ese banco",
        "más detalles",
        "amplía eso",
        "qué significa eso",
        "y el siguiente",
        "muéstrame más",
    ],
}


class SemanticIntentScorer:
    """
    Scores user intent using semantic similarity with EmbeddingService.

    Uses a singleton pattern with lazy initialization to avoid startup overhead.
    Embeddings are computed on first use and cached in memory.

    Thread-safety: Initialization is not thread-safe, but scoring is.
    In practice, FastAPI handles this via dependency injection.
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
        """
        Get singleton instance with initialized embeddings.

        This is the preferred way to access the scorer.
        """
        if cls._instance is None:
            cls._instance = SemanticIntentScorer()

        if not cls._initialized:
            await cls._instance._initialize()
            cls._initialized = True

        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
        cls._initialized = False

    async def _initialize(self):
        """Pre-compute embeddings for category exemplars."""
        from ..embedding_service import get_embedding_service

        self._embedding_service = get_embedding_service()

        logger.info(
            "Initializing semantic intent scorer",
            categories=len(CATEGORY_EXEMPLARS),
        )

        for category, exemplars in CATEGORY_EXEMPLARS.items():
            try:
                # Use batch encoding for efficiency
                embeddings = await self._embedding_service.encode_async(exemplars)
                self._category_embeddings[category] = np.array(embeddings)

                logger.debug(
                    "Category embeddings computed",
                    category=category,
                    exemplar_count=len(exemplars),
                    embedding_shape=self._category_embeddings[category].shape,
                )
            except Exception as e:
                logger.error(
                    "Failed to compute embeddings for category",
                    category=category,
                    error=str(e),
                )
                # Create zero embeddings as fallback
                self._category_embeddings[category] = np.zeros((len(exemplars), 384))

        # Update dimension from actual embeddings
        if self._category_embeddings:
            first_cat = list(self._category_embeddings.values())[0]
            if first_cat.size > 0:
                self._embedding_dim = first_cat.shape[1]

        logger.info(
            "Semantic intent scorer initialized",
            categories=len(self._category_embeddings),
            embedding_dim=self._embedding_dim,
        )

    def _cosine_similarity(
        self,
        query_vec: np.ndarray,
        exemplar_vecs: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and exemplars.

        Args:
            query_vec: Query embedding (1D array)
            exemplar_vecs: Exemplar embeddings (2D array, each row is an exemplar)

        Returns:
            Array of similarities (one per exemplar)
        """
        # Normalize vectors
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return np.zeros(len(exemplar_vecs))

        query_normalized = query_vec / query_norm

        exemplar_norms = np.linalg.norm(exemplar_vecs, axis=1, keepdims=True)
        # Avoid division by zero
        exemplar_norms = np.where(exemplar_norms == 0, 1, exemplar_norms)
        exemplars_normalized = exemplar_vecs / exemplar_norms

        # Cosine similarity = dot product of normalized vectors
        similarities = np.dot(exemplars_normalized, query_normalized)

        return similarities

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
        try:
            message_embedding = await self._embedding_service.encode_single_async(
                message, use_cache=True
            )
            message_vec = np.array(message_embedding)
        except Exception as e:
            logger.error(
                "Failed to encode message",
                error=str(e),
                message_preview=message[:50],
            )
            # Return unknown on error
            return IntentScores(
                scores={cat: 0.0 for cat in IntentCategory},
                top_intent=IntentCategory.UNKNOWN,
                top_confidence=0.0,
            )

        # Compute similarity to each category
        scores: Dict[str, float] = {}

        for category, exemplar_embeddings in self._category_embeddings.items():
            if exemplar_embeddings.size == 0:
                scores[category] = 0.0
                continue

            similarities = self._cosine_similarity(message_vec, exemplar_embeddings)

            # Use max similarity (closest exemplar) as category score
            scores[category] = float(np.max(similarities))

        result = IntentScores.from_dict(scores)

        logger.debug(
            "Intent scored",
            message_preview=message[:50],
            top_intent=result.top_intent.value,
            top_confidence=f"{result.top_confidence:.3f}",
            all_scores={k: f"{v:.2f}" for k, v in result.to_dict().items()},
        )

        return result

    async def score_batch(self, messages: List[str]) -> List[IntentScores]:
        """
        Score multiple messages efficiently.

        Args:
            messages: List of messages to classify

        Returns:
            List of IntentScores (one per message)
        """
        if not messages:
            return []

        if not self._embedding_service:
            await self._initialize()

        # Batch encode all messages
        try:
            embeddings = await self._embedding_service.encode_async(messages)
        except Exception as e:
            logger.error("Failed to batch encode messages", error=str(e))
            return [
                IntentScores(
                    scores={},
                    top_intent=IntentCategory.UNKNOWN,
                    top_confidence=0.0,
                )
                for _ in messages
            ]

        results = []
        for msg_embedding in embeddings:
            msg_vec = np.array(msg_embedding)
            scores = {}

            for category, exemplar_embeddings in self._category_embeddings.items():
                if exemplar_embeddings.size == 0:
                    scores[category] = 0.0
                    continue

                similarities = self._cosine_similarity(msg_vec, exemplar_embeddings)
                scores[category] = float(np.max(similarities))

            results.append(IntentScores.from_dict(scores))

        return results


# Convenience function for one-off scoring
async def score_intent(message: str) -> IntentScores:
    """
    Score a message's intent (convenience function).

    Usage:
        from src.services.intent import score_intent
        scores = await score_intent("Hola, qué tal")
    """
    scorer = await SemanticIntentScorer.get_instance()
    return await scorer.score(message)
