"""
RAG Bridge - Dependency injection bridge to main backend services

This module provides a clean interface for injecting Qdrant and Embedding
services from the main OctaviOS backend into the BankAdvisor plugin.

Architecture:
    - Plugin remains decoupled from main backend
    - Services are injected via HTTP or direct import (if co-located)
    - Graceful fallback if services unavailable

Usage:
    # Option 1: Direct import (if running in same process)
    from bankadvisor.services.rag_bridge import inject_rag_services
    inject_rag_services()

    # Option 2: HTTP proxy (if running as separate service)
    from bankadvisor.services.rag_bridge import RagHttpProxy
    inject_rag_services(http_proxy=RagHttpProxy(base_url="http://backend:8000"))
"""

import os
from typing import Optional, Any
import structlog

logger = structlog.get_logger(__name__)


class RagServiceBridge:
    """
    Bridge to access Qdrant and Embedding services from main backend.

    This class handles the complexity of importing from the main backend
    while keeping the plugin loosely coupled.
    """

    def __init__(self):
        self.qdrant_service: Optional[Any] = None
        self.embedding_service: Optional[Any] = None
        self._initialized = False

    def inject_from_main_backend(self) -> bool:
        """
        Attempt to import and inject services from main backend.

        Returns:
            True if successful, False otherwise
        """
        if self._initialized:
            logger.debug("rag_bridge.already_initialized")
            return True

        try:
            # Import path to main backend services
            # This assumes the plugin has access to the main backend's Python path
            import sys
            backend_path = os.environ.get(
                "BACKEND_SRC_PATH",
                "/home/jazielflo/Proyects/octavios-chat-bajaware_invex/apps/backend/src"
            )

            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
                logger.info("rag_bridge.backend_path_added", path=backend_path)

            # Import services
            from services.qdrant_service import get_qdrant_service
            from services.embedding_service import get_embedding_service

            self.qdrant_service = get_qdrant_service()
            self.embedding_service = get_embedding_service()

            # Ensure Qdrant collection exists (with connection error handling)
            try:
                self.qdrant_service.ensure_collection()
            except Exception as conn_error:
                # Connection failed (Qdrant not available) - this is expected in standalone mode
                logger.warning(
                    "rag_bridge.qdrant_unavailable",
                    error=str(conn_error),
                    message="Qdrant service not accessible. RAG disabled."
                )
                return False

            self._initialized = True

            logger.info(
                "rag_bridge.initialized",
                qdrant_collection=self.qdrant_service.collection_name,
                embedding_dim=self.embedding_service.embedding_dim
            )

            return True

        except ImportError as e:
            logger.warning(
                "rag_bridge.import_failed",
                error=str(e),
                message="Main backend services not available. RAG disabled."
            )
            return False

        except Exception as e:
            logger.error(
                "rag_bridge.initialization_failed",
                error=str(e),
                exc_info=True
            )
            return False

    def get_qdrant_service(self) -> Optional[Any]:
        """Get QdrantService instance or None."""
        return self.qdrant_service

    def get_embedding_service(self) -> Optional[Any]:
        """Get EmbeddingService instance or None."""
        return self.embedding_service

    def is_available(self) -> bool:
        """Check if RAG services are available."""
        return self._initialized and self.qdrant_service is not None


# Singleton instance
_rag_bridge: Optional[RagServiceBridge] = None


def get_rag_bridge() -> RagServiceBridge:
    """
    Get or create RAG bridge singleton.

    Returns:
        RagServiceBridge instance
    """
    global _rag_bridge

    if _rag_bridge is None:
        _rag_bridge = RagServiceBridge()

    return _rag_bridge


def inject_rag_services() -> bool:
    """
    Convenience function to inject RAG services.

    Returns:
        True if successful, False otherwise

    Usage:
        from bankadvisor.services.rag_bridge import inject_rag_services

        if inject_rag_services():
            print("RAG enabled!")
        else:
            print("RAG disabled - using fallback")
    """
    bridge = get_rag_bridge()
    return bridge.inject_from_main_backend()


class RagHttpProxy:
    """
    HTTP proxy for RAG services when running as separate microservice.

    This allows the plugin to access Qdrant/Embedding services via HTTP
    instead of direct imports.

    TODO Phase 5: Implement if plugin is deployed separately from main backend.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        logger.info("rag_http_proxy.initialized", base_url=base_url)

    async def generate_embedding(self, text: str) -> list:
        """
        Generate embedding via HTTP.

        TODO: Implement HTTP call to backend's embedding endpoint.
        """
        raise NotImplementedError("HTTP proxy not implemented yet")

    async def search_vectors(
        self,
        collection: str,
        query_vector: list,
        top_k: int = 3
    ) -> list:
        """
        Search Qdrant via HTTP.

        TODO: Implement HTTP call to backend's Qdrant proxy endpoint.
        """
        raise NotImplementedError("HTTP proxy not implemented yet")
