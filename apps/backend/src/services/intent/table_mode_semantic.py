"""
Semantic table-mode routing using EmbeddingService.

This module classifies whether a query implicitly asks for:
- "full" table
- "excerpt" table

It is designed as an optional enhancement over keyword routing.
When disabled or unavailable, callers should fall back to rule-based logic.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


TABLE_MODE_EXEMPLARS: Dict[str, List[str]] = {
    "full": [
        "muéstrame la tabla completa mes a mes del IMOR",
        "quiero el desglose completo de la evolución mensual",
        "dame todos los datos en formato tabla por mes",
        "listado completo mensual de valores por banco",
        "tabla mes a mes con todos los periodos",
    ],
    "excerpt": [
        "dame los datos del IMOR de BBVA",
        "cuáles son las cifras de ICAP",
        "muéstrame los valores más recientes",
        "compara los valores de BBVA y Santander",
        "necesito los números de esta métrica",
    ],
}

_mode_embeddings: Optional[Dict[str, np.ndarray]] = None


def _run_in_thread(func, *args, timeout: float = 30.0, **kwargs):
    """Run blocking/sync work in a worker thread and return result."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func, *args, **kwargs)
        return future.result(timeout=timeout)


def _run_coro_in_thread(coro_factory, *, timeout: float = 30.0):
    """Run an async callable from sync code even when event loop is running."""
    return _run_in_thread(lambda: asyncio.run(coro_factory()), timeout=timeout)


def _in_running_event_loop() -> bool:
    """Check whether current thread already has a running asyncio loop."""
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _reset_async_clients(embedding_service) -> None:
    """
    Clear cached async clients before crossing event-loop boundaries.

    EmbeddingService caches async HTTP/gRPC clients that are bound to the
    event loop where they were created. Reusing them from another loop causes
    "bound to a different event loop" runtime errors.
    """
    for attr in ("_grpc_client", "_http_client"):
        if hasattr(embedding_service, attr):
            try:
                setattr(embedding_service, attr, None)
            except Exception:
                # Best-effort reset for compatibility with mocked services.
                pass


def _encode_texts_sync(embedding_service, texts: List[str]) -> List[List[float]]:
    """
    Encode texts safely from sync code.

    In an async request context, avoid calling sync wrappers that may rely on
    asyncio.run() in the active loop.
    """
    if not _in_running_event_loop():
        return embedding_service.encode(texts, batch_size=len(texts))

    _reset_async_clients(embedding_service)
    try:
        return _run_in_thread(embedding_service.encode, texts, batch_size=len(texts))
    except Exception:
        if hasattr(embedding_service, "encode_async"):
            return _run_coro_in_thread(
                lambda: embedding_service.encode_async(texts, batch_size=len(texts))
            )
        raise


def _encode_single_sync(embedding_service, user_query: str) -> List[float]:
    """Encode one query safely from sync code in both sync/async callers."""
    if not _in_running_event_loop():
        return embedding_service.encode_single(user_query, use_cache=True)

    _reset_async_clients(embedding_service)
    try:
        return _run_in_thread(
            embedding_service.encode_single,
            user_query,
            use_cache=True,
        )
    except Exception:
        if hasattr(embedding_service, "encode_single_async"):
            return _run_coro_in_thread(
                lambda: embedding_service.encode_single_async(
                    user_query, use_cache=True
                )
            )
        raise


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


def _ensure_embeddings() -> Optional[Dict[str, np.ndarray]]:
    """Lazy-load exemplar embeddings once per process."""
    global _mode_embeddings
    if _mode_embeddings is not None:
        return _mode_embeddings

    try:
        from ..embedding_service import get_embedding_service

        embedding_service = get_embedding_service()
        built: Dict[str, np.ndarray] = {}
        for mode, exemplars in TABLE_MODE_EXEMPLARS.items():
            vectors = _encode_texts_sync(embedding_service, exemplars)
            built[mode] = np.array(vectors, dtype=np.float32)

        _mode_embeddings = built
        logger.info(
            "table_mode_semantic.embeddings_initialized",
            modes=list(_mode_embeddings.keys()),
            exemplar_counts={k: len(v) for k, v in TABLE_MODE_EXEMPLARS.items()},
        )
        return _mode_embeddings

    except Exception as exc:
        logger.warning(
            "table_mode_semantic.embeddings_unavailable",
            error=str(exc),
        )
        # Keep cache uninitialized so a later request can retry.
        _mode_embeddings = None
        return None


def resolve_semantic_table_mode(
    user_query: str,
    *,
    threshold: float = 0.62,
    min_margin: float = 0.05,
) -> Optional[str]:
    """
    Return semantic table mode ("full" | "excerpt") or None if uncertain.
    """
    embeddings = _ensure_embeddings()
    if not embeddings:
        return None

    try:
        from ..embedding_service import get_embedding_service

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
            "table_mode_semantic.classified",
            query_preview=user_query[:80],
            top_mode=top_mode,
            top_score=f"{top_score:.3f}",
            second_score=f"{second_score:.3f}",
            threshold=threshold,
            min_margin=min_margin,
        )

        return top_mode

    except Exception as exc:
        logger.warning(
            "table_mode_semantic.classification_failed",
            error=str(exc),
            query_preview=user_query[:80],
        )
        return None
