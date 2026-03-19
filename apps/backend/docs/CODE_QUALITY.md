# Backend Code Quality Analysis

> Analysis Date: 2026-01-16
> Scope: `apps/backend/src/**`

## Executive Summary

The backend codebase is well-structured with proper separation of concerns (routers/services/models). Key improvement areas:
- Large service classes need refactoring
- Async parallelization opportunities
- Error handling standardization
- Dependency injection formalization

---

## 1. Code Organization - God Classes

### Critical Files

| File | Lines | Issues |
|------|-------|--------|
| `streaming_handler.py` | 1,292 | SSE streaming, document processing, artifact creation, chart handling combined |
| `tool_execution_service.py` | 1,510 | 100+ keyword patterns, metric detection, intent analysis combined |
| `bank_analytics_client.py` | 1,510 | HTTP client, response parsing, error handling combined |

### Recommended Extractions

**streaming_handler.py** - COMPLETED (REFACTOR-001 Phase 6):
- ✅ `DocumentContextBuilder` - RAG document processing (services/streaming/)
- ✅ `ChartFlowHandler` - Chart/artifact creation (services/streaming/)
- ✅ `ChartEventBuilder` - Plotly chart events (services/streaming/)
- ✅ `MessagePersistenceService` - Chat message storage (services/streaming/)
- ✅ `SaptivaStreamer` - LLM streaming abstraction (services/streaming/)
- ✅ `ChunkEmitter` - SSE chunk emission (services/streaming/)
- ✅ `TokenBudgetManager` - Token management (services/streaming/)
- ✅ `ResponsePostProcessor` - Post-processing (services/streaming/)
- ✅ `ChatStreamProducer` - LLM streaming producer (services/streaming/) - 2026-01-16

> **Note**: 13 services extracted total. Handler now ~1,100 lines (consumer loop
> + coordination). Producer logic is fully decoupled and unit-testable.

**tool_execution_service.py** should become:
- `MetricDetector` - Keyword pattern matching (lines 44-103)
- `IntentAnalyzer` - Additive intent detection (lines 128-177)
- `ToolCacheManager` - Tool result caching
- `ToolExecutionService` - Core execution only

---

## 2. Async Patterns - Parallelization Opportunities

### Sequential Operations (Anti-Pattern)

**tool_execution_service.py:406-448**
```python
# CURRENT: Sequential - slow
for doc_id in context.document_ids:
    excel_result = await cls._execute_tool_with_cache(...)  # BLOCKING

# BETTER: Parallel
results = await asyncio.gather(*[
    cls._execute_tool_with_cache(doc_id, ...)
    for doc_id in context.document_ids
])
```
**Impact:** 5-10x slower for multi-document chats.

### Files Using asyncio.gather (Good)
- `routers/review.py`
- `services/aletheia_streaming.py`
- `services/file_ingest.py`

### Global State (Anti-Pattern)

**saptiva_client.py:22-24**
```python
_global_mock_mode: bool = False  # BAD: Module-level global
_global_mock_reason: Optional[str] = None

# BETTER: Constructor injection
class SaptivaClient:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
```

---

## 3. Error Handling

### Issues Found
- **212 bare `except Exception` catches** across 52 files
- Silent failures return `None` without user notification

### Examples

**chat_service.py:85**
```python
# BAD: Swallows all errors
except Exception as exc:
    logger.warning(...)
    return None  # Silent failure

# BETTER: Specific exceptions
except HTTPException as e:
    raise
except ValidationError as e:
    logger.error("Validation failed", error=e)
    raise ChatServiceError("Invalid input") from e
```

### Recommended Exception Hierarchy

```python
class BackendError(Exception):
    """Base for all backend errors."""

class ToolExecutionError(BackendError):
    """Tool invocation failures."""

class DocumentProcessingError(BackendError):
    """Document extraction/OCR failures."""

class ChatServiceError(BackendError):
    """Chat session/message failures."""
```

---

## 4. Caching Strategy

### Good Patterns
- Redis cache with zstd compression (`extraction_cache.py`)
- Tool result caching with TTL per type (`tool_execution_service.py`)
- 24h TTL for document text extraction

### Issues

**Missing cache invalidation** - When documents update, cache isn't invalidated:
```python
# After document update, add:
await cache.invalidate(f"doc:text:{doc_id}")
```

**MD5 for cache keys** - Using weak hash:
```python
# tool_execution_service.py:260
# Current: MD5
# Better: SHA-256 (extraction_cache.py does this correctly)
```

---

## 5. Database Patterns

### Good (No N+1)
- Document queries use `In()` operator for batch (`document_service.py:60-66`)
- Chat history limited to 20 messages (`chat_service.py:206-211`)

### Recommended Indexes

```python
# MongoDB indexes for performance
ChatMessage.index([("chat_id", 1), ("created_at", -1)])
Document.index([("user_id", 1), ("status", 1)])
ChatSession.index([("user_id", 1), ("updated_at", -1)])
```

---

## 6. Dependency Injection

### Current (Tight Coupling)
```python
class ChatService:
    def __init__(self):
        self.saptiva = SaptivaClient()  # Hidden dependency
        self.memory = get_memory_service()  # Function call
```

### Better (Explicit)
```python
class ChatService:
    def __init__(
        self,
        saptiva: SaptivaClient,
        memory: MemoryService,
    ):
        self.saptiva = saptiva  # Inject via constructor
        self.memory = memory
```

---

## Priority Fixes

| Location | Issue | Impact | Fix |
|----------|-------|--------|-----|
| ~~`tool_execution_service.py:406`~~ | ~~Sequential tool execution~~ | ~~5-10x slower multi-doc chats~~ | ~~`asyncio.gather()`~~ ✅ |
| ~~`saptiva_client.py:22-24`~~ | ~~Global state mock flags~~ | ~~Hard to test~~ | ~~Inject via constructor~~ ✅ |
| `chat_service.py:85` | Bare `except Exception` | Silent failures | Specific exceptions |
| ~~`streaming_handler.py`~~ | ~~1,292 line god class~~ | ~~Unmaintainable~~ | ~~Split into services~~ ✅ (1,090 lines) |
| `document_service.py:94-100` | Sequential Redis gets | Slow multi-doc RAG | Use `mget()` batch |

---

## Summary Metrics

- **Service files with >500 lines:** 20 files
- **Bare exception catches:** 212+ instances
- **Global state instances:** 8+ files
- **Sequential async operations:** 3+ critical paths
- **Database queries risk:** Low (batch queries used)
- **API consistency:** Good (Problem Details format)

---

## Implementation Tracking

- [x] Split streaming_handler.py (13 services extracted, Phase 6 complete 2026-01-16)
- [x] Parallelize tool execution with asyncio.gather (2026-01-16)
- [x] Remove global state from saptiva_client (2026-01-16)
- [~] Replace bare except with specific exceptions (2026-01-16)
  - [x] Added BackendError hierarchy to core/exceptions.py
  - [x] Fixed chat_service.py (PyMongoError, ChatServiceError)
  - [x] Fixed redis_cache.py (RedisError with graceful degradation)
  - [ ] Remaining: 350+ instances in 50+ files (non-critical)
- [x] Add cache invalidation on document updates (2026-01-16)
  - [x] documents.py: delete endpoint invalidates MCP tool caches
  - [x] file_ingest.py: READY status invalidates stale caches
- [x] Implement MongoDB indexes (2026-01-16)
  - [x] ChatMessage: compound index exists [("chat_id", 1), ("created_at", 1)]
  - [x] ChatSession: compound index exists [("user_id", 1), ("updated_at", -1)]
  - [x] Document: added [("user_id", 1), ("status", 1)] for filtering
- [ ] Formalize dependency injection
