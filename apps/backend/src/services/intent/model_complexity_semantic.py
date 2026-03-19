"""
Semantic model-complexity routing using EmbeddingService.

Classifies whether a user query is "complex" (needs a more accurate model)
or "simple" (default fast model is sufficient).

Complex queries involve: evolution over time, multi-bank comparisons,
month-by-month breakdowns, detailed data analysis.

Simple queries involve: single lookups, general summaries, last-value checks.

Follows the same pattern as table_mode_semantic.py:
- Lazy-loaded exemplar embeddings (once per process)
- Cosine similarity against query embedding
- Silent fallback when embeddings are unavailable
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


COMPLEXITY_EXEMPLARS: Dict[str, List[str]] = {
    "complex": [
        # Evolution / time series
        "muéstrame la evolución de la cartera comercial de invex en 2024",
        "cómo ha cambiado el IMOR mes a mes este año",
        "cuál ha sido el comportamiento histórico de la cartera",
        "dame la tendencia mensual del ICAP de BBVA",
        "evolución trimestral de la morosidad",
        # Multi-bank comparison
        "compara la cartera comercial de invex y bbva",
        "invex vs banorte en cartera de vivienda",
        "diferencia entre santander y scotiabank en IMOR",
        "cuál banco tiene mejor ICAP comparado con los demás",
        # Dense data / breakdown
        "desglose mes a mes de la cartera de consumo",
        "quiero ver todos los datos mensuales del último año",
        "muéstrame los valores de cada mes de 2024",
        "análisis detallado por periodo de la cartera",
        "dame las cifras de cada trimestre para comparar",
    ],
    "simple": [
        # Single lookups
        "cuál es la cartera comercial de invex",
        "dame el IMOR de BBVA",
        "saldo de cartera de vivienda de Santander",
        "cuánto tiene invex en cartera comercial",
        # Summary / last value
        "cómo va la cartera de invex",
        "resumen del ICAP de banorte",
        "cuál es el último dato de morosidad",
        "estado actual de la cartera comercial",
        # General questions
        "qué es el IMOR",
        "explícame qué es la cartera comercial",
        "qué bancos hay disponibles",
    ],
}

_complexity_embeddings: Optional[Dict[str, np.ndarray]] = None


def _ensure_embeddings() -> Optional[Dict[str, np.ndarray]]:
    """Lazy-load exemplar embeddings once per process."""
    global _complexity_embeddings
    if _complexity_embeddings is not None:
        return _complexity_embeddings

    try:
        from ..embedding_service import get_embedding_service

        # Reuse encode helpers from table_mode_semantic to handle async boundaries
        from .table_mode_semantic import _encode_texts_sync

        embedding_service = get_embedding_service()
        built: Dict[str, np.ndarray] = {}
        for mode, exemplars in COMPLEXITY_EXEMPLARS.items():
            vectors = _encode_texts_sync(embedding_service, exemplars)
            built[mode] = np.array(vectors, dtype=np.float32)

        _complexity_embeddings = built
        logger.info(
            "model_complexity_semantic.embeddings_initialized",
            modes=list(_complexity_embeddings.keys()),
            exemplar_counts={k: len(v) for k, v in COMPLEXITY_EXEMPLARS.items()},
        )
        return _complexity_embeddings

    except Exception as exc:
        logger.warning(
            "model_complexity_semantic.embeddings_unavailable",
            error=str(exc),
        )
        _complexity_embeddings = None
        return None


def _cosine_max(query_vec: np.ndarray, exemplar_vecs: np.ndarray) -> float:
    """Max cosine similarity between query vector and exemplar matrix."""
    if exemplar_vecs.size == 0:
        return 0.0

    q_norm = np.linalg.norm(query_vec)
    if q_norm == 0:
        return 0.0
    q = query_vec / q_norm

    ex_norms = np.linalg.norm(exemplar_vecs, axis=1)
    valid = ex_norms > 0
    if not np.any(valid):
        return 0.0

    ex_valid = exemplar_vecs[valid]
    ex_norms_valid = ex_norms[valid]
    sims = np.dot(ex_valid, q) / ex_norms_valid
    return float(np.max(sims))


def resolve_semantic_complexity(
    user_query: str,
    *,
    threshold: float = 0.62,
    min_margin: float = 0.05,
) -> Optional[str]:
    """
    Classify query as "complex" or "simple" using embedding similarity.

    Returns:
        "complex" — query needs accurate model (Legacy)
        "simple"  — default fast model (Turbo) is fine
        None      — embeddings unavailable or uncertain (caller should fallback)
    """
    embeddings = _ensure_embeddings()
    if not embeddings:
        return None

    try:
        from ..embedding_service import get_embedding_service
        from .table_mode_semantic import _encode_single_sync

        embedding_service = get_embedding_service()
        query_vec = np.array(
            _encode_single_sync(embedding_service, user_query), dtype=np.float32
        )

        scores: Dict[str, float] = {}
        for mode, exemplar_vecs in embeddings.items():
            scores[mode] = _cosine_max(query_vec, exemplar_vecs)

        ranked: List[Tuple[str, float]] = sorted(
            scores.items(), key=lambda kv: kv[1], reverse=True
        )
        if not ranked:
            return None

        top_mode, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        if top_score < threshold:
            return None
        if (top_score - second_score) < min_margin:
            return None

        logger.debug(
            "model_complexity_semantic.classified",
            query_preview=user_query[:80],
            top_mode=top_mode,
            top_score=f"{top_score:.3f}",
            second_score=f"{second_score:.3f}",
        )

        return top_mode

    except Exception as exc:
        logger.warning(
            "model_complexity_semantic.classification_failed",
            error=str(exc),
            query_preview=user_query[:80],
        )
        return None
