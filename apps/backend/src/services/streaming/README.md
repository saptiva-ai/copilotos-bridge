# Streaming Services Architecture

> **REFACTOR-001**: This package was extracted from a 2929-line `streaming_handler.py` to improve testability, maintainability, and separation of concerns.

## Overview

The streaming architecture handles real-time Server-Sent Events (SSE) for chat responses. It follows a **producer-consumer pattern** with backpressure support.

```
┌─────────────────────────────────────────────────────────────────┐
│                      StreamingHandler                           │
│                    (Orchestrator - 499 LOC)                     │
├─────────────────────────────────────────────────────────────────┤
│  handle_stream()        │  _stream_audit_response()             │
│  - Build context        │  - Document resolution                │
│  - Session management   │  - MCP auditor invocation             │
│  - Route to audit/chat  │  - Validation report persistence      │
├─────────────────────────┼───────────────────────────────────────┤
│  _stream_chat_response()                                        │
│  - Document context     → DocumentContextBuilder                │
│  - System prompt        → SystemPromptBuilder                   │
│  - LLM streaming        → ChatStreamProducer                    │
│  - Post-processing      → StreamResponseFinalizer               │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture Diagram

```
                                    ┌──────────────────┐
                                    │   FastAPI Route  │
                                    └────────┬─────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                        StreamingHandler                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ handle_     │  │ _stream_    │  │ _stream_    │                 │
│  │ stream()    │→ │ audit_      │  │ chat_       │                 │
│  │             │  │ response()  │  │ response()  │                 │
│  └─────────────┘  └──────┬──────┘  └──────┬──────┘                 │
└──────────────────────────┼────────────────┼────────────────────────┘
                           │                │
           ┌───────────────┘                └───────────────┐
           ▼                                                ▼
┌─────────────────────┐                        ┌─────────────────────┐
│  Audit Flow         │                        │  Chat Flow          │
│  ┌───────────────┐  │                        │  ┌───────────────┐  │
│  │AuditDocument  │  │                        │  │DocumentContext│  │
│  │Resolver       │  │                        │  │Builder        │  │
│  └───────┬───────┘  │                        │  └───────┬───────┘  │
│          ▼          │                        │          ▼          │
│  ┌───────────────┐  │                        │  ┌───────────────┐  │
│  │AuditResponse  │  │                        │  │SystemPrompt   │  │
│  │Builder        │  │                        │  │Builder        │  │
│  └───────────────┘  │                        │  └───────┬───────┘  │
└─────────────────────┘                        │          ▼          │
                                               │  ┌───────────────┐  │
                                               │  │ChatStream     │  │
                                               │  │Producer       │──┼──► Queue
                                               │  └───────┬───────┘  │     │
                                               │          ▼          │     │
                                               │  ┌───────────────┐  │     │
                                               │  │StreamResponse │◄─┼─────┘
                                               │  │Finalizer      │  │
                                               │  └───────────────┘  │
                                               └─────────────────────┘
```

## Service Catalog

### Core Services

| Service | Responsibility | LOC |
|---------|----------------|-----|
| `ChatStreamProducer` | LLM streaming with backpressure | ~110 |
| `StreamResponseFinalizer` | Post-stream cleanup and persistence | ~70 |
| `DocumentContextBuilder` | RAG document retrieval | ~80 |
| `SystemPromptBuilder` | Prompt resolution and enhancement | ~35 |

### Audit Services

| Service | Responsibility | LOC |
|---------|----------------|-----|
| `AuditDocumentResolver` | Document resolution for audit | ~60 |
| `AuditResponseBuilder` | Audit result formatting and SSE events | ~130 |
| `AuditorResultFormatterService` | Format MCP auditor results | ~130 |

### Bank Analytics Services

| Service | Responsibility | LOC |
|---------|----------------|-----|
| `BankAdvisorPreCheckService` | Bank advisor eligibility check | ~40 |
| `ChartFlowHandler` | Chart/clarification/refusal flows | ~155 |
| `ChartEventBuilder` | Bank chart SSE events | ~75 |
| `BankChartNormalizer` | Chart data normalization | ~130 |

### Utility Services

| Service | Responsibility | LOC |
|---------|----------------|-----|
| `TokenBudgetManager` | Token estimation and truncation | ~65 |
| `ResponsePostProcessor` | SQL sanitization, truth-gating | ~70 |
| `MessagePersistenceService` | Message metadata and persistence | ~60 |
| `ChunkEmitter` | Uniform text chunking for SSE | ~40 |
| `SaptivaStreamer` | LLM interaction abstraction | ~100 |
| `FileIngestionService` | Document ingestion with wait | ~60 |
| `StreamingErrorLogger` | Centralized error logging | ~60 |

## Data Flow

### 1. Chat Streaming Flow

```python
# StreamingHandler._stream_chat_response()

# Step 1: Build document context (RAG)
doc_context = await DocumentContextBuilder().build(
    document_ids=context.document_ids,
    session_id=context.session_id,
    question=context.message,
)

# Step 2: Resolve system prompt
prompt_result = SystemPromptBuilder.build(
    model=context.model,
    document_context=doc_context,
    bank_chart_data=bank_chart_data,
)

# Step 3: Start producer (puts events on queue)
producer = ChatStreamProducer()
producer_task = create_task(producer.produce(producer_context))

# Step 4: Consumer loop (yields events to client)
while True:
    event = await event_queue.get()
    if event is None:  # End signal
        break
    yield event

# Step 5: Finalize (cleanup, post-process, persist)
result = await StreamResponseFinalizer.finalize(producer_task, ctx)
yield result.done_event
```

### 2. Audit Streaming Flow

```python
# StreamingHandler._stream_audit_response()

# Step 1: Resolve document
resolved, error = await AuditDocumentResolver.resolve(
    message=context.message,
    document_ids=context.document_ids,
)

# Step 2: Call MCP auditor
mcp_result = await audit_document_via_mcp(file_path=pdf_path, ...)

# Step 3: Build and yield events
yield AuditResponseBuilder.build_meta_event(...)
yield AuditResponseBuilder.build_chunk_event(content, audit_event)

# Step 4: Persist report
await AuditResponseBuilder.persist_validation_report(...)

# Step 5: Final event
yield AuditResponseBuilder.build_done_event(...)
```

## Dependencies

### Import Graph

```
streaming_handler.py
├── services/streaming/
│   ├── AuditDocumentResolver
│   ├── AuditResponseBuilder
│   ├── BankAdvisorPreCheckService
│   ├── ChatStreamProducer
│   ├── DocumentContextBuilder
│   ├── FileIngestionService
│   ├── FinalizerContext (dataclass)
│   ├── MessagePersistenceService
│   ├── ProducerContext (dataclass)
│   ├── StreamingErrorLogger
│   ├── StreamResponseFinalizer
│   └── SystemPromptBuilder
├── domain/
│   └── ChatContext
├── services/
│   ├── chat_service.ChatService
│   ├── saptiva_client.get_saptiva_client
│   └── audit_mcp_client.audit_document_via_mcp
└── core/
    ├── config.Settings
    └── redis_cache.get_redis_cache
```

### Circular Dependency Prevention

Services use **lazy imports** inside methods to avoid circular dependencies:

```python
# GOOD: Lazy import inside method
class AuditResponseBuilder:
    @staticmethod
    async def persist_validation_report(...):
        # Import only when method is called
        from ...models.validation_report import ValidationReport
        ...

# BAD: Top-level import causing circular dependency
from ...models.validation_report import ValidationReport  # Don't do this
```

## SSE Event Format

All streaming services emit events in this format:

```python
{
    "event": "meta" | "chunk" | "done" | "error",
    "data": json.dumps({...})
}
```

### Event Types

| Event | Purpose | Data Fields |
|-------|---------|-------------|
| `meta` | Stream metadata | `chat_id`, `user_message_id`, `model` |
| `chunk` | Content chunk | `content`, optional `audit_event` or `chart_event` |
| `done` | Stream complete | `message_id`, `content`, `metadata`, optional `artifact` |
| `error` | Error occurred | `error`, `message`, optional `details` |

## Best Practices

### 1. Service Design

```python
# GOOD: Stateless service with static/class methods
class MyService:
    @staticmethod
    def process(data: Dict) -> Result:
        """Pure function, easy to test."""
        return Result(...)

# BAD: Stateful service requiring complex setup
class MyService:
    def __init__(self, db, cache, client, settings):
        self.db = db
        # ... lots of dependencies
```

### 2. Error Handling

```python
# GOOD: Use StreamingErrorLogger for consistent error handling
except Exception as exc:
    StreamingErrorLogger.log_from_request(exc, user_id, request, context)
    yield MessagePersistenceService.build_error_event(str(exc), type(exc).__name__)

# BAD: Inconsistent error handling
except Exception as e:
    print(f"Error: {e}")  # Don't print to stdout
    import traceback; traceback.print_exc()  # Redundant with exc_info=True
```

### 3. Immutable Context Updates

```python
# GOOD: Use with_* methods on frozen dataclasses
context = context.with_document_ids(file_ids)
context = context.with_session(session_id)

# BAD: Recreate entire object manually
context = ChatContext(
    user_id=context.user_id,
    request_id=context.request_id,
    # ... 15 more fields
    document_ids=file_ids,
)
```

### 4. Logging

```python
# GOOD: Concise, structured logs
logger.info("System prompt resolved", model=context.model, has_docs=bool(docs))

# BAD: Verbose debug logs in production code
logger.info(
    "🔍 [RAG DEBUG] Session file context",  # Emoji + DEBUG prefix
    session_id=chat_session.id,
    session_attached_file_ids=getattr(chat_session, "attached_file_ids", []),
    request_file_ids=request_file_ids,
    timestamp=context.timestamp,  # Too many fields
)
```

### 5. Producer-Consumer Pattern

```python
# GOOD: Use Queue with maxsize for backpressure
event_queue: Queue = Queue(maxsize=10)

# Producer puts events
await event_queue.put(event)
await event_queue.put(None)  # End signal

# Consumer yields events
while True:
    event = await event_queue.get()
    if event is None:
        break
    yield event
```

## Anti-Patterns to Avoid

### 1. God Methods

```python
# BAD: 1453-line method doing everything
async def _stream_chat_response(self, ...):
    # RAG context preparation (130 lines)
    # LLM client setup (30 lines)
    # Bank analytics handling (700 lines)
    # Memory management (70 lines)
    # Response routing (50 lines)
    # Streaming loop (450 lines)
    pass

# GOOD: Orchestrator delegating to services
async def _stream_chat_response(self, ...):
    doc_context = await DocumentContextBuilder().build(...)
    prompt = SystemPromptBuilder.build(...)
    producer_task = create_task(producer.produce(...))
    # ... ~120 lines total
```

### 2. Backwards Compatibility Aliases

```python
# BAD: Keep aliases that add maintenance burden
format_auditor_markdown = AuditorResultFormatterService.format_auditor_markdown

# GOOD: Update callers to use the new path directly
from services.streaming import AuditorResultFormatterService
AuditorResultFormatterService.format_auditor_markdown(text)
```

### 3. Debug Code in Production

```python
# BAD: Debug code left in production
import traceback
traceback.print_exc()  # Redundant with exc_info=True

event_count += 1
logger.debug("📥 [DEBUG] Consumer yielding event", event_number=event_count)

# GOOD: Use structured logging with exc_info
logger.error("Streaming failed", error=str(exc), exc_info=True)
```

### 4. Tight Coupling

```python
# BAD: Handler knows about MongoDB models
from models.validation_report import ValidationReport
report = ValidationReport(**data)
await report.insert()

# GOOD: Service encapsulates persistence
await AuditResponseBuilder.persist_validation_report(...)
```

## Testing

### Unit Testing Services

```python
# Services are designed for easy unit testing
def test_audit_response_builder_extracts_summary():
    mcp_result = {
        "total_findings": 5,
        "findings_by_severity": {"critical": 1, "high": 2, "medium": 2},
    }

    summary = AuditResponseBuilder.extract_summary(mcp_result)

    assert summary.total_findings == 5
    assert summary.critical == 1
```

### Running Tests

```bash
# Run streaming service tests
TEST_MODE=true pytest tests/unit/test_streaming_services.py -v

# Run all unit tests
TEST_MODE=true pytest tests/unit/ -v
```

## Migration Guide

### From Old Code

If you have code importing from the old location:

```python
# OLD (before REFACTOR-001)
from routers.chat.handlers.streaming_handler import format_auditor_markdown

# NEW (after REFACTOR-001)
from services.streaming import AuditorResultFormatterService
AuditorResultFormatterService.format_auditor_markdown(text)
```

## Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| `streaming_handler.py` | 2929 LOC | 499 LOC | -83% |
| `_stream_chat_response` | 1453 LOC | ~120 LOC | -92% |
| Extracted services | 0 | 20 | N/A |
| Test coverage | ~40% | 171 tests | Improved |

## Related Documentation

- [Chat Domain Models](../../domain/chat_context.py)
- [Chat Service](../chat_service.py)
- [Saptiva Client](../saptiva_client.py)
- [REFACTOR-001 Card](../../../../../docs/kanban/BACKLOG/REFACTOR-001_streaming-handler/card.md)
