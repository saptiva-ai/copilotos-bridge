"""
Streaming Services Package.

Extracted services from streaming_handler.py for better testability and maintainability.

Services:
    Phase 1:
    - AuditorResultFormatterService: Format audit validation results

    Phase 2:
    - DocumentContextBuilder: RAG document retrieval and context building

    Phase 3:
    - MessagePersistenceService: Build metadata and persist assistant messages

    Phase 4:
    - TokenBudgetManager: Token estimation, dynamic max_tokens, message truncation
    - ResponsePostProcessor: Empty response handling, SQL sanitization, truth-gating

    Phase 5:
    - ChunkEmitter: Uniform text chunking for SSE streaming
    - SaptivaStreamer: LLM interaction abstraction with normalized response handling
    - AuditResponseBuilder: Audit validation response building

    Phase 6:
    - ChatStreamProducer: LLM streaming producer with backpressure support

    Phase 7:
    - FileIngestionService: Document ingestion with anti-hallucination wait
    - AuditDocumentResolver: Document resolution and materialization for audit

    Phase 8:
    - SystemPromptBuilder: System prompt resolution and enhancement

    Phase 9:
    - StreamResponseFinalizer: Post-streaming finalization and persistence

    Phase 10:
    - StreamingErrorLogger: Centralized error logging for streaming handlers
"""

from .audit_document_resolver import (
    AuditDocumentResolver,
    ResolutionError,
    ResolvedDocument,
)
from .audit_response_builder import AuditResponseBuilder, AuditResult, AuditSummary
from .chat_stream_producer import (
    ChatStreamProducer,
    ProducerConfig,
    ProducerContext,
    ProducerResult,
)
from .chunk_emitter import ChunkEmitter
from .document_context import DocumentContextBuilder
from .error_logger import ErrorContext, StreamingErrorLogger
from .file_ingestion_service import FileIngestionService
from .message_persistence import MessagePersistenceService
from .response_postprocessor import PostProcessResult, ResponsePostProcessor
from .saptiva_streamer import CompletionResult, SaptivaStreamer, StreamerConfig
from .stream_response_finalizer import (
    FinalizerContext,
    FinalizerResult,
    StreamResponseFinalizer,
)
from .system_prompt_builder import PromptBuildResult, SystemPromptBuilder
from .token_budget import TokenBudgetManager, TokenBudgetResult

__all__ = [
    # Phase 1
    "AuditorResultFormatterService",
    # Phase 2
    "DocumentContextBuilder",
    # Phase 3
    "MessagePersistenceService",
    # Phase 4
    "TokenBudgetManager",
    "TokenBudgetResult",
    "ResponsePostProcessor",
    "PostProcessResult",
    # Phase 5
    "ChunkEmitter",
    "SaptivaStreamer",
    "StreamerConfig",
    "CompletionResult",
    "AuditResponseBuilder",
    "AuditResult",
    "AuditSummary",
    # Phase 6
    "ChatStreamProducer",
    "ProducerConfig",
    "ProducerContext",
    "ProducerResult",
    # Phase 7
    "FileIngestionService",
    "AuditDocumentResolver",
    "ResolvedDocument",
    "ResolutionError",
    # Phase 8
    "SystemPromptBuilder",
    "PromptBuildResult",
    # Phase 9
    "StreamResponseFinalizer",
    "FinalizerContext",
    "FinalizerResult",
    # Phase 10
    "StreamingErrorLogger",
    "ErrorContext",
]
