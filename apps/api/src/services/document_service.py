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

from beanie.operators import In
from beanie import PydanticObjectId

from ..models.document import Document, DocumentStatus
from ..core.redis_cache import get_redis_cache

logger = structlog.get_logger(__name__)


class DocumentService:
    """Service for document operations in chat context."""

    @staticmethod
    async def get_document_text_from_cache(
        document_ids: List[str],
        user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        V1: Retrieve document text from Redis cache with ownership validation.

        Args:
            document_ids: List of document IDs to retrieve.
            user_id: User ID for ownership validation.

        Returns:
            Dict mapping document_id -> {text, filename, content_type, ocr_applied}
        """
        if not document_ids:
            return {}

        logger.info(
            "Retrieving documents from Redis cache",
            document_count=len(document_ids),
            user_id=user_id
        )

        # Convert string IDs to PydanticObjectId for querying
        try:
            object_ids = [PydanticObjectId(doc_id) for doc_id in document_ids]
        except Exception as e:
            logger.warning("Invalid document IDs provided", error=str(e))
            return {}

        # First validate ownership via MongoDB
        documents = await Document.find(
            In(Document.id, object_ids),
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
                # Handle both bytes and string (redis-py might return either)
                if isinstance(text, bytes):
                    text_content = text.decode('utf-8')
                else:
                    text_content = text

                # Return metadata along with text
                doc_texts[doc_id] = {
                    "text": text_content,
                    "filename": doc.filename,
                    "content_type": doc.content_type,
                    "ocr_applied": doc.ocr_applied
                }
                logger.debug("Retrieved text from Redis with metadata", doc_id=doc_id, length=len(text))
            else:
                logger.warning("Document text not in Redis cache (expired?)", doc_id=doc_id)
                doc_texts[doc_id] = {
                    "text": f"[Documento '{doc.filename}' expirado de cache]",
                    "filename": doc.filename,
                    "content_type": doc.content_type,
                    "ocr_applied": doc.ocr_applied
                }

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

        # Convert string IDs to PydanticObjectId
        try:
            object_ids = [PydanticObjectId(doc_id) for doc_id in document_ids]
        except Exception as e:
            logger.warning("Invalid document IDs", error=str(e))
            return []

        # Query documents with ownership validation
        documents = await Document.find(
            In(Document.id, object_ids),
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
        doc_texts: Dict[str, Dict[str, Any]],
        max_chars_per_doc: int = 8000,
        max_total_chars: int = 16000,
        max_docs: int = 3
    ) -> tuple[str, List[str], Dict[str, Any]]:
        """
        V1: Format cached document text for RAG context with global limits.

        BE-PERF-1 Hardening: Implements document count and total character budget
        to control LLM token costs and prevent context overflow.

        Args:
            doc_texts: Dict mapping doc_id -> {text, filename, content_type, ocr_applied}
            max_chars_per_doc: Maximum characters per document (for truncation)
            max_total_chars: Maximum total characters across all documents (global budget)
            max_docs: Maximum number of documents to include

        Returns:
            Tuple of (formatted_content, warnings_list, metadata)
            - formatted_content: String with valid document contents
            - warnings_list: List of warning messages for expired/invalid/omitted docs
            - metadata: Dict with 'used_chars' and 'used_docs' for telemetry
        """
        if not doc_texts:
            return "", [], {"used_chars": 0, "used_docs": 0}

        formatted_parts = []
        warnings = []
        used_chars = 0
        used_docs = 0

        for doc_id, doc_data in doc_texts.items():
            # Extract text and metadata
            text = doc_data.get("text", "")
            filename = doc_data.get("filename", "unknown")
            content_type = doc_data.get("content_type", "")
            ocr_applied = doc_data.get("ocr_applied", False)
            # Check document count limit
            if used_docs >= max_docs:
                warnings.append(
                    f"Se usaron {max_docs} documentos máximo; el resto se omitió. "
                    f"Considera dividir tu consulta o priorizar documentos clave."
                )
                logger.warning(
                    "Document count limit reached",
                    max_docs=max_docs,
                    omitted_count=len(doc_texts) - used_docs
                )
                break

            # BE-2: Detect expired documents (set in get_document_text_from_cache)
            if isinstance(text, str) and text.startswith("[Documento") and "expirado" in text:
                warning_msg = f"Documento {doc_id} expiró en Redis. Sube nuevamente si deseas incluirlo."
                warnings.append(warning_msg)
                logger.warning("Skipping expired document", doc_id=doc_id)
                continue

            # Truncate by per-doc limit first
            if len(text) > max_chars_per_doc:
                text = text[:max_chars_per_doc]
                text += f"\n\n*[Contenido truncado - documento excede límite por archivo]*"

            # Check global character budget
            remaining_budget = max_total_chars - used_chars
            if remaining_budget <= 0:
                warnings.append(
                    "Se alcanzó el límite global de contexto; se omitió contenido adicional. "
                    "Intenta con menos documentos o consultas más específicas."
                )
                logger.warning(
                    "Global character budget exhausted",
                    max_total_chars=max_total_chars,
                    used_chars=used_chars,
                    omitted_docs=len(doc_texts) - used_docs
                )
                break

            # Truncate to fit remaining budget
            if len(text) > remaining_budget:
                text = text[:remaining_budget]
                text += f"\n\n*[Contenido truncado por presupuesto global de contexto]*"
                warnings.append(
                    f"Documento {doc_id} truncado para respetar presupuesto global de {max_total_chars} caracteres."
                )

            # Format with header - differentiate images from PDFs
            is_image = content_type.startswith("image/")
            if is_image and ocr_applied:
                header = f"## 📷 Imagen: {filename}\n**Texto extraído con OCR:**\n\n"
            elif is_image:
                header = f"## 📷 Imagen: {filename}\n\n"
            else:
                header = f"## 📄 Documento: {filename}\n\n"

            formatted = f"{header}{text}"
            formatted_parts.append(formatted)

            # Track usage
            used_chars += len(text)
            used_docs += 1

        result = "\n\n---\n\n".join(formatted_parts)

        metadata = {
            "used_chars": used_chars,
            "used_docs": used_docs,
            "requested_docs": len(doc_texts),
            "omitted_docs": len(doc_texts) - used_docs
        }

        logger.info(
            "Formatted document content for RAG (from cache) with limits",
            document_count=len(formatted_parts),
            expired_count=len([w for w in warnings if "expiró" in w]),
            total_chars=used_chars,
            max_total_chars=max_total_chars,
            max_docs=max_docs,
            used_docs=used_docs,
            omitted_docs=metadata["omitted_docs"]
        )

        return result, warnings, metadata

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

        # Convert string IDs to PydanticObjectId
        try:
            object_ids = [PydanticObjectId(doc_id) for doc_id in document_ids]
        except Exception as e:
            logger.warning("Invalid document IDs in validation", error=str(e))
            return [], document_ids

        documents = await Document.find(
            In(Document.id, object_ids),
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
