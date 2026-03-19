"""
Document Context Builder Service.

Extracted from streaming_handler.py for better testability.
Handles RAG document retrieval and context building for LLM prompts.

REFACTOR-001: Phase 2 extraction.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class DocumentContextBuilder:
    """
    Service for building document context via RAG retrieval.

    Responsibilities:
        - Retrieve relevant segments via GetRelevantSegmentsTool
        - Fallback to full document text from cache
        - Track document processing status
        - Build formatted context string for LLM
    """

    def __init__(
        self,
        max_segments: int = 5,
        max_text_chars: int = 12000,
    ):
        """
        Initialize DocumentContextBuilder.

        Args:
            max_segments: Maximum number of segments to retrieve from RAG
            max_text_chars: Maximum characters per document in fallback mode
        """
        self.max_segments = max_segments
        self.max_text_chars = max_text_chars

    async def build(
        self,
        document_ids: List[str],
        session_id: str,
        user_id: str,
        question: str,
    ) -> Tuple[Optional[str], List[str]]:
        """
        Build document context from attached documents.

        Uses semantic retrieval (GetRelevantSegmentsTool) with fallback
        to full document text from Redis/MongoDB cache.

        Args:
            document_ids: List of document IDs to retrieve context from
            session_id: Session/conversation ID for RAG retrieval
            user_id: User ID for cache access
            question: User's question for semantic matching

        Returns:
            Tuple of (context_string, warnings_list)
            - context_string: Formatted document context or None if no documents
            - warnings_list: List of warning messages (e.g., "Documents processing")
        """
        if not document_ids:
            return None, []

        logger.info(
            "📚 [DOC CONTEXT] Starting document context retrieval",
            session_id=session_id,
            document_count=len(document_ids),
            question_preview=question[:100] if question else "",
        )

        warnings: List[str] = []

        try:
            # Try semantic retrieval first
            context = await self._retrieve_via_rag(
                session_id=session_id,
                question=question,
                warnings=warnings,
            )

            if context:
                return context, warnings

            # Fallback to cache if RAG returns no segments
            context = await self._retrieve_from_cache(
                document_ids=document_ids,
                user_id=user_id,
                session_id=session_id,
                warnings=warnings,
            )

            return context, warnings

        except Exception as exc:
            logger.error(
                "❌ [DOC CONTEXT] Document retrieval failed",
                error=str(exc),
                exc_type=type(exc).__name__,
                document_ids=document_ids,
            )
            warnings.append(
                f"No se pudieron cargar los documentos adjuntos: {str(exc)[:100]}"
            )
            return None, warnings

    async def _retrieve_via_rag(
        self,
        session_id: str,
        question: str,
        warnings: List[str],
    ) -> Optional[str]:
        """Retrieve document segments via GetRelevantSegmentsTool."""
        try:
            # Import here to avoid circular imports
            from ...mcp_integration.tools.get_segments import GetRelevantSegmentsTool

            logger.info(
                "[RAG] Starting GetRelevantSegmentsTool",
                conversation_id=session_id,
            )

            get_segments_tool = GetRelevantSegmentsTool()
            segments_result = await get_segments_tool.execute(
                payload={
                    "conversation_id": session_id,
                    "question": question,
                    "max_segments": self.max_segments,
                }
            )

            segments = segments_result.get("segments", [])

            if segments:
                # Build context from retrieved segments
                segment_texts = []
                for seg in segments:
                    source = f"**{seg['doc_name']}** (relevancia: {seg['score']:.2f})"
                    segment_texts.append(f"{source}\n{seg['text']}")

                context = "\n\n---\n\n".join(segment_texts)

                logger.info(
                    "✅ [RAG] Segments retrieved successfully",
                    session_id=session_id,
                    segments_count=len(segments),
                    ready_docs=segments_result.get("ready_docs", 0),
                    total_docs=segments_result.get("total_docs", 0),
                )

                return context

            # No segments - check if documents are still processing
            message = segments_result.get("message", "")
            if "procesando" in message.lower() or "processing" in message.lower():
                warning_msg = "⏳ Los documentos se están procesando. Estarán disponibles en breve."
                warnings.append(warning_msg)
                logger.warning(
                    "⚠️ [RAG] Documents still processing",
                    session_id=session_id,
                    total_docs=segments_result.get("total_docs", 0),
                    ready_docs=segments_result.get("ready_docs", 0),
                )

            logger.info(
                "🔄 [RAG] No segments from Weaviate, will try fallback",
                session_id=session_id,
            )
            return None

        except Exception as rag_exc:
            logger.error(
                "❌ [RAG] Segment retrieval failed",
                error=str(rag_exc),
                exc_type=type(rag_exc).__name__,
            )
            # Don't add warning here - will try fallback
            return None

    async def _retrieve_from_cache(
        self,
        document_ids: List[str],
        user_id: str,
        session_id: str,
        warnings: List[str],
    ) -> Optional[str]:
        """Fallback: retrieve document text from Redis/MongoDB cache."""
        try:
            # Import here to avoid circular imports
            from ...services.document_service import DocumentService

            logger.info(
                "🔄 [CACHE FALLBACK] Loading document text from cache",
                session_id=session_id,
                document_ids=document_ids,
            )

            doc_texts = await DocumentService.get_document_text_from_cache(
                document_ids=document_ids,
                user_id=user_id,
            )

            if not doc_texts:
                logger.warning(
                    "⚠️ [CACHE FALLBACK] No documents found in cache",
                    session_id=session_id,
                )
                return None

            segment_texts = []
            for doc_id, doc_data in doc_texts.items():
                text = doc_data.get("text", "")
                filename = doc_data.get("filename", doc_id)
                if text:
                    # Truncate to avoid token overflow
                    truncated_text = text[: self.max_text_chars]
                    segment_texts.append(f"**{filename}**\n{truncated_text}")

            if not segment_texts:
                logger.warning(
                    "⚠️ [CACHE FALLBACK] Documents in cache but no extractable text",
                    session_id=session_id,
                )
                return None

            context = "\n\n---\n\n".join(segment_texts)

            logger.info(
                "✅ [CACHE FALLBACK] Successfully loaded document text",
                session_id=session_id,
                docs_loaded=len(segment_texts),
                total_chars=len(context),
            )

            return context

        except Exception as cache_exc:
            logger.error(
                "❌ [CACHE FALLBACK] Failed to load documents from cache",
                error=str(cache_exc),
                exc_type=type(cache_exc).__name__,
                session_id=session_id,
            )
            return None

    @staticmethod
    def format_for_prompt(document_context: str) -> str:
        """
        Format document context for inclusion in system prompt.

        Args:
            document_context: Raw document context string

        Returns:
            Formatted string with header for LLM prompt
        """
        if not document_context:
            return ""
        return f"\n\n**Documentos adjuntos por el usuario:**\n{document_context}"
