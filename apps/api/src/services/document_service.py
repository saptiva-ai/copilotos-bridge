"""
Document Service - Handles document retrieval and content extraction.

V1 Simplified: Retrieves text from Redis cache (1 hour TTL)
V2 Future: Retrieve from MinIO + MongoDB with full page structure

Provides methods for:
- Retrieving document text from Redis cache
- Formatting content for RAG context
- Validating document ownership
"""

from typing import List, Optional, Dict, Any
import structlog

from ..models.document import Document, DocumentStatus
from ..core.redis_cache import get_redis_cache

logger = structlog.get_logger(__name__)


class DocumentService:
    """Service for document operations in chat context."""

    @staticmethod
    async def get_document_text_from_cache(
        document_ids: List[str],
        user_id: str
    ) -> Dict[str, str]:
        """
        V1: Retrieve document text from Redis cache with ownership validation.

        Args:
            document_ids: List of document IDs to retrieve.
            user_id: User ID for ownership validation.

        Returns:
            Dict mapping document_id -> text content
        """
        if not document_ids:
            return {}

        logger.info(
            "Retrieving documents from Redis cache",
            document_count=len(document_ids),
            user_id=user_id
        )

        # First validate ownership via MongoDB
        documents = await Document.find(
            Document.id.in_(document_ids),
            Document.user_id == user_id,
            Document.status == DocumentStatus.READY
        ).to_list()

        if len(documents) < len(document_ids):
            logger.warning(
                "Some documents not found or not accessible",
                requested=len(document_ids),
                retrieved=len(documents),
                user_id=user_id
            )

        # Retrieve text from Redis for valid documents
        redis_cache = await get_redis_cache()
        redis_client = redis_cache.client
        doc_texts = {}

        for doc in documents:
            doc_id = str(doc.id)
            redis_key = f"doc:text:{doc_id}"

            text = await redis_client.get(redis_key)
            if text:
                doc_texts[doc_id] = text.decode('utf-8')
                logger.debug("Retrieved text from Redis", doc_id=doc_id, length=len(text))
            else:
                logger.warning("Document text not in Redis cache (expired?)", doc_id=doc_id)
                doc_texts[doc_id] = f"[Documento '{doc.filename}' expirado de cache]"

        return doc_texts

    @staticmethod
    async def get_documents_by_ids(
        document_ids: List[str],
        user_id: str
    ) -> List[Document]:
        """
        V2 Future: Retrieve full Document objects with page structure.
        V1: Kept for backward compatibility but prefer get_document_text_from_cache()

        Args:
            document_ids: List of document IDs to retrieve.
            user_id: User ID for ownership validation.

        Returns:
            List of Document objects that belong to the user.
        """
        if not document_ids:
            return []

        logger.info(
            "Retrieving documents for chat",
            document_count=len(document_ids),
            user_id=user_id
        )

        # Query documents with ownership validation
        documents = await Document.find(
            Document.id.in_(document_ids),
            Document.user_id == user_id,
            Document.status == DocumentStatus.READY
        ).to_list()

        retrieved_count = len(documents)
        if retrieved_count < len(document_ids):
            logger.warning(
                "Some documents not found or not accessible",
                requested=len(document_ids),
                retrieved=retrieved_count,
                user_id=user_id
            )

        return documents

    @staticmethod
    def extract_content_for_rag_from_cache(
        doc_texts: Dict[str, str],
        max_chars_per_doc: int = 8000
    ) -> str:
        """
        V1: Format cached document text for RAG context.

        Args:
            doc_texts: Dict mapping doc_id -> text content from Redis
            max_chars_per_doc: Maximum characters per document (for truncation)

        Returns:
            Formatted string with document contents
        """
        if not doc_texts:
            return ""

        formatted_parts = []

        for doc_id, text in doc_texts.items():
            # Truncate if too long
            if len(text) > max_chars_per_doc:
                truncated_text = text[:max_chars_per_doc]
                truncated_text += f"\n\n*[Contenido truncado - {len(text) - max_chars_per_doc} caracteres omitidos]*"
            else:
                truncated_text = text

            # Format with header
            formatted = f"## Documento ID: {doc_id}\n\n{truncated_text}"
            formatted_parts.append(formatted)

        result = "\n\n---\n\n".join(formatted_parts)

        logger.info(
            "Formatted document content for RAG (from cache)",
            document_count=len(doc_texts),
            total_chars=len(result)
        )

        return result

    @staticmethod
    def extract_content_for_rag(
        documents: List[Document],
        max_chars_per_doc: int = 8000
    ) -> str:
        """
        Extract and format document content for RAG context.

        Args:
            documents: List of Document objects.
            max_chars_per_doc: Maximum characters per document (for chunking).

        Returns:
            Formatted string with document contents.
        """
        if not documents:
            return ""

        formatted_parts = []

        for doc in documents:
            # Build document header
            header = f"## Documento: {doc.filename}\n"
            content_parts = [header]

            # Extract text from all pages
            total_chars = 0
            for page in doc.pages:
                page_text = page.text_md.strip()
                if not page_text:
                    continue

                # Add page content
                page_header = f"\n### Página {page.page}\n"
                content_parts.append(page_header)
                content_parts.append(page_text)

                total_chars += len(page_header) + len(page_text)

                # Check if we've reached the limit
                if total_chars >= max_chars_per_doc:
                    content_parts.append(
                        f"\n\n*[Contenido truncado - {doc.total_pages - page.page} páginas restantes]*"
                    )
                    break

            formatted_parts.append("".join(content_parts))

        result = "\n\n---\n\n".join(formatted_parts)

        logger.info(
            "Extracted document content for RAG",
            document_count=len(documents),
            total_chars=len(result)
        )

        return result

    @staticmethod
    def build_document_context_message(
        documents: List[Document],
        max_chars: int = 16000
    ) -> Dict[str, Any]:
        """
        Build a system message with document context for chat.

        Args:
            documents: List of Document objects.
            max_chars: Maximum total characters for all documents.

        Returns:
            Dict with role and content for system message.
        """
        if not documents:
            return None

        content = DocumentService.extract_content_for_rag(
            documents,
            max_chars_per_doc=max_chars // max(len(documents), 1)
        )

        # Truncate if still too long
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n*[Contenido truncado]*"

        system_message = {
            "role": "system",
            "content": (
                f"El usuario ha adjuntado {len(documents)} documento(s) para tu referencia. "
                f"Usa esta información para responder sus preguntas:\n\n{content}"
            )
        }

        logger.debug(
            "Built document context message",
            document_count=len(documents),
            message_length=len(system_message["content"])
        )

        return system_message

    @staticmethod
    async def validate_documents_access(
        document_ids: List[str],
        user_id: str
    ) -> tuple[List[str], List[str]]:
        """
        Validate which documents the user has access to.

        Args:
            document_ids: List of document IDs to validate.
            user_id: User ID for ownership validation.

        Returns:
            Tuple of (valid_ids, invalid_ids).
        """
        if not document_ids:
            return [], []

        documents = await Document.find(
            Document.id.in_(document_ids),
            Document.user_id == user_id,
            Document.status == DocumentStatus.READY
        ).to_list()

        valid_ids = [str(doc.id) for doc in documents]
        invalid_ids = [doc_id for doc_id in document_ids if doc_id not in valid_ids]

        if invalid_ids:
            logger.warning(
                "Some documents are invalid or inaccessible",
                valid_count=len(valid_ids),
                invalid_count=len(invalid_ids),
                user_id=user_id
            )

        return valid_ids, invalid_ids
