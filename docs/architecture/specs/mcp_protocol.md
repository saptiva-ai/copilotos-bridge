# MCP Architecture - Model Context Protocol Integration

## Executive Summary

This document describes the **Model Context Protocol (MCP)** layer integrated into the Saptiva OctaviOS Chat platform. The MCP layer provides a standardized, extensible interface for tool invocations, enabling capabilities like Excel analysis, deep-research, document extraction, BI/visualization, and compliance validation—without breaking existing endpoints.

**Implementation Status**: ✅ **COMPLETED** - In-process MCP (Opción A) within the same FastAPI container.

**Available Tools** (as of 2025-11-11):
1. **audit_file** - COPILOTO_414 compliance validation
2. **excel_analyzer** - Excel data analysis and statistics
3. **viz_tool** - Data visualization (Plotly/ECharts)
4. **deep_research** - Multi-step research with Aletheia ✨ NEW
5. **extract_document_text** - Multi-tier text extraction ✨ NEW

---

## 1. Current Architecture Overview

### 1.1 High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 14)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Chat Store   │  │ Files Store  │  │ Audit Store  │         │
│  │ (Zustand)    │  │ (Zustand)    │  │ (Zustand)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│          │                  │                  │                │
│          └──────────────────┴──────────────────┘                │
│                           │                                     │
│                    API Client (Axios)                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/SSE
┌───────────────────────────┴─────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      Main Application (main.py)             │ │
│  │  ├── CORS, Auth, Rate Limiting, Telemetry Middleware       │ │
│  │  ├── Exception Handlers                                    │ │
│  │  └── Router Registry                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────── ROUTERS ──────────────────────────┐  │
│  │ /api/auth        │ /api/chat       │ /api/files          │  │
│  │ /api/documents   │ /api/review     │ /api/deep-research  │  │
│  │ /api/history     │ /api/stream     │ /api/conversations  │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌─────────────────────── DOMAIN LAYER ────────────────────┐   │
│  │ • ChatStrategy (Strategy Pattern)                        │   │
│  │ • ChatResponseBuilder (Builder Pattern)                  │   │
│  │ • ChatContext, ChatProcessingResult (DTO Pattern)        │   │
│  │ • MessageHandlers (Chain of Responsibility)              │   │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌─────────────────────── SERVICE LAYER ────────────────────┐  │
│  │ ChatService              │ DocumentService                │  │
│  │ ReviewService            │ ValidationCoordinator          │  │
│  │ HistoryService           │ DocumentExtraction             │  │
│  │ SaptivaClient            │ AletheiaClient                 │  │
│  │ MinIOService             │ CacheService (Redis)           │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────── DATA LAYER ──────────────────────┐  │
│  │ MongoDB (Beanie ODM)     │ Redis (Cache)                  │  │
│  │ • ChatSession            │ • Document text cache          │  │
│  │ • ChatMessage            │ • Rate limit counters          │  │
│  │ • Document               │ • Idempotency keys             │  │
│  │ • ValidationReport       │                                │  │
│  │ • ReviewJob              │                                │  │
│  │ • ResearchTask           │                                │  │
│  └──────────────────────────┴────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────────┐
│                     INFRASTRUCTURE (Docker Compose)              │
│  MongoDB  │  Redis  │  MinIO  │  LanguageTool  │  Aletheia      │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Backend Architecture Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Strategy Pattern** | `src/domain/chat_strategy.py` | Pluggable chat processing strategies (Standard, RAG) |
| **Builder Pattern** | `src/domain/chat_response_builder.py` | Declarative response construction |
| **DTO Pattern** | `src/domain/chat_context.py` | Type-safe data containers |
| **Chain of Responsibility** | `src/domain/message_handlers.py` | Sequential message processing pipeline |
| **Service Layer** | `src/services/` | Business logic orchestration |
| **Repository Pattern** | Beanie ODM models | Data access abstraction |

### 1.3 Key Components

#### Routers (17 total)
- `auth.py` - Authentication (JWT)
- `chat.py` - Main chat endpoint (streaming/non-streaming)
- `files.py` - File upload with rate limiting (5 uploads/min)
- `documents.py` - Document management (CRUD)
- `review.py` - Document review & COPILOTO_414 validation
- `deep_research.py` - Aletheia research orchestration
- `history.py` - Chat history with pagination
- `conversations.py` - Session management
- `stream.py` - SSE streaming endpoints
- `reports.py` - Report download/sharing
- `health.py`, `metrics.py`, `models.py`, `features.py`, `settings.py`, `intent.py`

#### Services (45+ total)
**Core Business Logic**:
- `chat_service.py` - Chat session management, Saptiva integration
- `document_service.py` - Document text retrieval, RAG context
- `review_service.py` - Review job orchestration
- `validation_coordinator.py` - COPILOTO_414 audit orchestration
- `history_service.py` - History retrieval with caching
- `deep_research_service.py` - Research task coordination

**Infrastructure**:
- `saptiva_client.py` - Saptiva LLM API client
- `aletheia_client.py` - Aletheia research client
- `minio_service.py` - Object storage (S3-compatible)
- `cache_service.py` - Redis caching abstraction
- `document_extraction.py` - 3-tier extraction (pypdf → Saptiva PDF SDK → OCR)

**Specialized Auditors (COPILOTO_414)**:
- `compliance_auditor.py` - Disclaimer validation
- `format_auditor.py` - Font/color/number format validation
- `grammar_auditor.py` - LanguageTool integration
- `logo_auditor.py` - OpenCV template matching
- `typography_auditor.py`, `semantic_consistency_auditor.py`, `entity_consistency_auditor.py`, `color_palette_auditor.py`

#### Domain Models (Beanie ODM)
- `ChatSession`, `ChatMessage` - Conversation storage
- `Document` - File metadata + extracted text
- `ValidationReport` - COPILOTO_414 results
- `ReviewJob` - Document review jobs
- `ResearchTask` - Deep research tasks
- `User` - User accounts
- `HistoryEvent` - Unified timeline

---

## 2. Endpoint → Service → Dependencies Mapping

### 2.1 Critical Endpoints

| Endpoint | Method | Service | Dependencies | Side Effects | Hot Spot |
|----------|--------|---------|--------------|--------------|----------|
| `/api/chat` | POST | `ChatService` | `SaptivaClient`, `DocumentService`, `ChatStrategy`, `SessionContextManager` | Creates `ChatMessage`, updates `ChatSession`, increments telemetry | LLM, RAG, Streaming |
| `/api/files/upload` | POST | `FileIngestService` | `DocumentExtractionService`, `MinIOService`, `CacheService`, `FileEventBus` | Creates `Document`, stores file, triggers extraction pipeline, emits SSE events | File Upload, OCR, Streaming |
| `/api/review/validate` | POST | `ValidationCoordinator` | `ComplianceAuditor`, `FormatAuditor`, `GrammarAuditor`, `LogoAuditor`, `PolicyManager` | Creates `ValidationReport`, links to `Document`, runs 4 parallel auditors | Document Audit, LLM |
| `/api/review/start` | POST | `ReviewService` | `LanguageToolClient`, `SaptivaClient`, `ColorAuditor` | Creates `ReviewJob`, processes grammar/style/summary in background | LLM, Streaming |
| `/api/deep-research` | POST | `DeepResearchService` | `AletheiaClient`, `ResearchCoordinator` | Creates `ResearchTask`, triggers background orchestration | LLM, Web Search |
| `/api/documents` | GET | `DocumentService` | `MongoDB` | Reads `Document` collection | - |
| `/api/history/{chat_id}` | GET | `HistoryService` | `MongoDB`, `CacheService` | Reads `ChatMessage`, `HistoryEvent` with pagination | - |
| `/api/auth/login` | POST | `AuthService` | `User` model, JWT utils | Creates JWT tokens, sets session cookie | - |

### 2.2 Hot Spot Details

#### File Attachments/Uploads
- **Endpoint**: `POST /api/files/upload`
- **Flow**:
  1. Rate limit check (Redis sliding window, 5 uploads/min)
  2. File validation (type, size)
  3. Create `Document` record (status=PENDING)
  4. Store file (local filesystem V1, MinIO V2)
  5. Trigger extraction pipeline (background task)
     - pypdf extraction
     - Fallback to Saptiva PDF SDK
     - Fallback to Saptiva OCR
  6. Cache extracted text in Redis (TTL: 1 hour)
  7. Emit SSE events (meta → processing → ready/failed)
  8. Update `Document` status (READY/FAILED)

#### LLM Calls (Saptiva)
- **Endpoints**: `/api/chat`, `/api/title`, `/api/review/start`
- **Client**: `saptiva_client.py`
- **Models**: Saptiva Turbo, Cortex, Ops
- **Flow**:
  1. Build payload with model-specific system prompt
  2. Add RAG context (if document IDs present)
  3. Send POST to Saptiva API
  4. Parse response (choices[0].message.content)
  5. Sanitize output (text_sanitizer.py)
  6. Track telemetry (tokens, latency)

#### OCR/Document Extraction
- **Service**: `document_extraction.py`
- **Strategy**: 3-tier fallback
  1. **pypdf**: Fast, works for text-based PDFs
  2. **Saptiva PDF SDK**: Handles complex layouts
  3. **Saptiva OCR**: Last resort for image-based PDFs
- **Caching**: Extracted text cached in Redis (key: `doc:text:{doc_id}`, TTL: 1 hour)

#### Streaming (SSE)
- **Endpoints**:
  - `POST /api/chat?stream=true`
  - `GET /api/files/events/{file_id}`
  - `GET /api/review/events/{job_id}`
  - `GET /api/stream/{task_id}`
- **Implementation**: `sse_starlette.EventSourceResponse`
- **Event Types**:
  - `meta` - Initial connection metadata
  - `progress` - Incremental updates
  - `content` - Streamed content chunks
  - `ready` - Completion
  - `failed` - Error state
  - `heartbeat` - Keep-alive (30s timeout)

#### Document Validation/Audit (COPILOTO_414)
- **Endpoint**: `POST /api/review/validate`
- **Orchestrator**: `validation_coordinator.py`
- **Auditors** (run in parallel):
  1. **Disclaimer Auditor**: Fuzzy text matching for legal disclaimers (footer detection)
  2. **Format Auditor**: PyMuPDF for fonts, colors, number formatting
  3. **Grammar Auditor**: LanguageTool for spelling/grammar
  4. **Logo Auditor**: OpenCV template matching for logo presence/position
- **Policy System**:
  - Policy configs in `policies.yaml`
  - Auto-detection based on document content
  - Custom policies: `414-std`, `414-strict`, `banamex`, `afore-xxi`
- **Output**: `ValidationReport` with findings, severity, suggestions

---

## 3. MCP Placement Decision: In-Process vs Out-of-Process

### 3.1 Trade-offs Matrix

| Criterion | Opción A: In-Process (same container) | Opción B: Out-of-Process (separate microservice) |
|-----------|---------------------------------------|---------------------------------------------------|
| **Complexity (Initial)** | ✅ **Low** - Single codebase, shared imports, no network layer | ❌ **High** - Separate repo/container, API design, service mesh |
| **Latency** | ✅ **~0ms** - Direct function calls | ❌ **10-50ms** - HTTP/gRPC overhead, serialization |
| **Deployment** | ✅ **Simple** - Single Docker image, atomic deploys | ❌ **Complex** - Multi-service orchestration, version compatibility |
| **Scalability** | ⚠️ **Moderate** - Vertical scaling only, shared resources | ✅ **High** - Independent horizontal scaling |
| **Blast Radius** | ❌ **High** - Tool crash = API downtime | ✅ **Low** - Tool crash isolated to MCP service |
| **Resource Isolation** | ❌ **None** - Shared CPU/memory pool | ✅ **Strong** - Dedicated resources per service |
| **Testing** | ✅ **Easy** - Unit tests, shared fixtures | ❌ **Hard** - Contract tests, service mocks |
| **Observability** | ✅ **Simple** - Single trace, shared logs | ❌ **Complex** - Distributed tracing, log aggregation |
| **Cost (Initial)** | ✅ **$0** - No additional infrastructure | ❌ **$$$** - Load balancer, service discovery, monitoring |
| **Future Migration** | ✅ **Easy** - Well-defined interface enables extraction | ❌ **Hard** - Already committed to distributed arch |

### 3.2 Decision: Opción A (In-Process)

**Rationale**:
1. **MVP Principle**: Start simple, extract if needed (YAGNI)
2. **Low Risk**: No breaking changes to existing endpoints
3. **Fast Development**: Reuse existing services, no network boilerplate
4. **Easy Testing**: Standard pytest, no service mesh
5. **Cost Efficient**: No additional infrastructure
6. **Proven Pattern**: Follows existing architecture (routers → services → domain)

**Migration Path**: The MCP layer is designed with clear boundaries:
- **ToolRegistry**: Can be moved to separate service without changing interface
- **ToolSpec**: Pydantic schemas can be shared via package
- **Invoke API**: HTTP contract already defined, easy to proxy

**When to Migrate to Out-of-Process**:
- Tool execution time > 5s (move to background jobs)
- Resource contention (high CPU/memory tools)
- Independent scaling needs (tool usage >> chat usage)
- Security isolation (untrusted code execution)

---

## 4. MCP Layer Design

### 4.1 Core Abstractions

```python
# apps/api/src/mcp/protocol.py

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ToolCategory(str, Enum):
    """Tool categories for discovery and organization."""
    DOCUMENT_ANALYSIS = "document_analysis"
    DATA_ANALYTICS = "data_analytics"
    VISUALIZATION = "visualization"
    RESEARCH = "research"
    COMPLIANCE = "compliance"


class ToolCapability(str, Enum):
    """Capabilities that tools can advertise."""
    SYNC = "sync"                    # Synchronous execution
    ASYNC = "async"                  # Asynchronous execution
    STREAMING = "streaming"          # Supports SSE streaming
    IDEMPOTENT = "idempotent"       # Safe to retry
    CACHEABLE = "cacheable"         # Results can be cached
    STATEFUL = "stateful"           # Maintains state across calls


class ToolSpec(BaseModel):
    """Tool specification - advertises tool capabilities."""
    name: str = Field(..., description="Unique tool identifier (e.g., 'audit_file')")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Tool purpose and use cases")
    category: ToolCategory
    capabilities: List[ToolCapability] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for input validation")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema for output structure")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    author: str = Field(default="OctaviOS", description="Tool author/maintainer")
    requires_auth: bool = Field(default=True, description="Requires user authentication")
    rate_limit: Optional[Dict[str, int]] = Field(
        default=None,
        description="Rate limit config: {'calls_per_minute': 10}"
    )
    timeout_ms: int = Field(default=30000, description="Max execution time in milliseconds")
    max_payload_size_kb: int = Field(default=1024, description="Max input payload size in KB")


class ToolInvokeRequest(BaseModel):
    """Request to invoke a tool."""
    tool: str = Field(..., description="Tool name")
    version: Optional[str] = Field(None, description="Tool version (defaults to latest)")
    payload: Dict[str, Any] = Field(..., description="Tool-specific input")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Execution context (user_id, trace_id, etc.)"
    )
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for retry safety")


class ToolInvokeResponse(BaseModel):
    """Response from tool invocation."""
    success: bool
    tool: str
    version: str
    result: Optional[Dict[str, Any]] = None
    error: Optional["ToolError"] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    invocation_id: str = Field(..., description="Unique invocation ID for tracing")
    duration_ms: float = Field(..., description="Execution time in milliseconds")
    cached: bool = Field(default=False, description="Was result served from cache?")


class ToolError(BaseModel):
    """Standardized tool error."""
    code: str = Field(..., description="Error code (e.g., 'INVALID_INPUT', 'TIMEOUT')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = None
    retry_after_ms: Optional[int] = Field(None, description="Retry delay for rate limits")


class ToolMetrics(BaseModel):
    """Tool execution metrics for observability."""
    tool: str
    version: str
    invocation_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    last_invoked_at: Optional[datetime] = None
    cache_hit_rate: float = 0.0


# Forward reference resolution
ToolInvokeResponse.model_rebuild()
```

### 4.2 Tool Interface

```python
# apps/api/src/mcp/tool.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import uuid4
import time
import structlog

from .protocol import ToolSpec, ToolInvokeResponse, ToolError, ToolCapability

logger = structlog.get_logger(__name__)


class Tool(ABC):
    """
    Abstract base class for all MCP tools.

    Subclasses must implement:
    - get_spec(): Return tool specification
    - validate_input(payload): Validate input against schema
    - execute(payload, context): Core tool logic
    """

    @abstractmethod
    def get_spec(self) -> ToolSpec:
        """Return tool specification."""
        pass

    @abstractmethod
    async def validate_input(self, payload: Dict[str, Any]) -> None:
        """
        Validate input payload against tool's input schema.

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    async def execute(
        self,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute tool logic.

        Args:
            payload: Tool-specific input (pre-validated)
            context: Execution context (user_id, trace_id, etc.)

        Returns:
            Tool-specific output

        Raises:
            Exception: Any execution error
        """
        pass

    async def invoke(
        self,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolInvokeResponse:
        """
        Full invocation lifecycle with error handling and metrics.

        This method wraps execute() with:
        - Input validation
        - Timeout enforcement
        - Error handling
        - Metrics collection
        """
        spec = self.get_spec()
        invocation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            "Tool invocation started",
            tool=spec.name,
            version=spec.version,
            invocation_id=invocation_id,
            user_id=context.get("user_id") if context else None,
        )

        try:
            # 1. Validate input
            await self.validate_input(payload)

            # 2. Execute tool logic
            result = await self.execute(payload, context)

            # 3. Build success response
            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "Tool invocation succeeded",
                tool=spec.name,
                version=spec.version,
                invocation_id=invocation_id,
                duration_ms=duration_ms,
            )

            return ToolInvokeResponse(
                success=True,
                tool=spec.name,
                version=spec.version,
                result=result,
                error=None,
                metadata={
                    "context": context or {},
                    "capabilities": [c.value for c in spec.capabilities],
                },
                invocation_id=invocation_id,
                duration_ms=duration_ms,
                cached=False,
            )

        except ValueError as validation_error:
            # Input validation failed
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(
                "Tool invocation failed: invalid input",
                tool=spec.name,
                version=spec.version,
                invocation_id=invocation_id,
                error=str(validation_error),
            )

            return ToolInvokeResponse(
                success=False,
                tool=spec.name,
                version=spec.version,
                result=None,
                error=ToolError(
                    code="INVALID_INPUT",
                    message=str(validation_error),
                    details={"payload": payload},
                ),
                metadata={},
                invocation_id=invocation_id,
                duration_ms=duration_ms,
                cached=False,
            )

        except Exception as execution_error:
            # Tool execution failed
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Tool invocation failed: execution error",
                tool=spec.name,
                version=spec.version,
                invocation_id=invocation_id,
                error=str(execution_error),
                exc_info=True,
            )

            return ToolInvokeResponse(
                success=False,
                tool=spec.name,
                version=spec.version,
                result=None,
                error=ToolError(
                    code="EXECUTION_ERROR",
                    message=f"Tool execution failed: {str(execution_error)}",
                    details={"exc_type": type(execution_error).__name__},
                ),
                metadata={},
                invocation_id=invocation_id,
                duration_ms=duration_ms,
                cached=False,
            )

    def is_idempotent(self) -> bool:
        """Check if tool supports idempotent execution."""
        return ToolCapability.IDEMPOTENT in self.get_spec().capabilities

    def is_cacheable(self) -> bool:
        """Check if tool results can be cached."""
        return ToolCapability.CACHEABLE in self.get_spec().capabilities

    def is_streaming(self) -> bool:
        """Check if tool supports streaming responses."""
        return ToolCapability.STREAMING in self.get_spec().capabilities
```

### 4.3 Tool Registry

```python
# apps/api/src/mcp/registry.py

from typing import Dict, List, Optional
import structlog

from .protocol import ToolSpec, ToolInvokeRequest, ToolInvokeResponse, ToolError
from .tool import Tool

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """
    Central registry for tool discovery and invocation.

    Manages tool lifecycle:
    - Registration
    - Discovery (list, search)
    - Invocation routing
    - Metrics aggregation
    """

    def __init__(self):
        # Key: tool_name, Value: Dict[version, Tool instance]
        self._tools: Dict[str, Dict[str, Tool]] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance

        Raises:
            ValueError: If tool with same name+version already registered
        """
        spec = tool.get_spec()

        if spec.name not in self._tools:
            self._tools[spec.name] = {}

        if spec.version in self._tools[spec.name]:
            raise ValueError(
                f"Tool '{spec.name}' version '{spec.version}' already registered"
            )

        self._tools[spec.name][spec.version] = tool

        logger.info(
            "Tool registered",
            tool=spec.name,
            version=spec.version,
            category=spec.category.value,
            capabilities=[c.value for c in spec.capabilities],
        )

    def unregister(self, tool_name: str, version: Optional[str] = None) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Tool name
            version: Optional version (if None, unregister all versions)
        """
        if tool_name not in self._tools:
            return

        if version:
            if version in self._tools[tool_name]:
                del self._tools[tool_name][version]
                logger.info("Tool unregistered", tool=tool_name, version=version)

                if not self._tools[tool_name]:
                    del self._tools[tool_name]
        else:
            # Unregister all versions
            del self._tools[tool_name]
            logger.info("Tool unregistered (all versions)", tool=tool_name)

    def get_tool(self, tool_name: str, version: Optional[str] = None) -> Optional[Tool]:
        """
        Get tool instance by name and version.

        Args:
            tool_name: Tool name
            version: Tool version (if None, returns latest)

        Returns:
            Tool instance or None if not found
        """
        if tool_name not in self._tools:
            return None

        versions = self._tools[tool_name]

        if version:
            return versions.get(version)
        else:
            # Return latest version (assumes semantic versioning)
            latest_version = max(versions.keys())
            return versions[latest_version]

    def list_tools(self, category: Optional[str] = None) -> List[ToolSpec]:
        """
        List all registered tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool specifications
        """
        specs = []
        for tool_versions in self._tools.values():
            for tool in tool_versions.values():
                spec = tool.get_spec()
                if category is None or spec.category.value == category:
                    specs.append(spec)

        return specs

    def search_tools(self, query: str) -> List[ToolSpec]:
        """
        Search tools by name, description, or tags.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching tool specifications
        """
        query_lower = query.lower()
        matches = []

        for tool_versions in self._tools.values():
            for tool in tool_versions.values():
                spec = tool.get_spec()
                if (
                    query_lower in spec.name.lower()
                    or query_lower in spec.description.lower()
                    or any(query_lower in tag.lower() for tag in spec.tags)
                ):
                    matches.append(spec)

        return matches

    async def invoke(self, request: ToolInvokeRequest) -> ToolInvokeResponse:
        """
        Invoke a tool by name.

        Args:
            request: Tool invocation request

        Returns:
            Tool invocation response
        """
        tool = self.get_tool(request.tool, request.version)

        if not tool:
            return ToolInvokeResponse(
                success=False,
                tool=request.tool,
                version=request.version or "unknown",
                result=None,
                error=ToolError(
                    code="TOOL_NOT_FOUND",
                    message=f"Tool '{request.tool}' not found",
                    details={"available_tools": list(self._tools.keys())},
                ),
                metadata={},
                invocation_id="error",
                duration_ms=0.0,
                cached=False,
            )

        # Invoke tool with context
        return await tool.invoke(request.payload, request.context)
```

---

## 5. Example Tool Implementations

### 5.1 Tool 1: `audit_file` (Document Compliance Validation)

```python
# apps/api/src/mcp/tools/audit_file.py

from typing import Any, Dict, Optional
from pathlib import Path
import structlog

from ..protocol import ToolSpec, ToolCategory, ToolCapability
from ..tool import Tool
from ...services.validation_coordinator import validate_document
from ...services.policy_manager import resolve_policy
from ...models.document import Document

logger = structlog.get_logger(__name__)


class AuditFileTool(Tool):
    """
    COPILOTO_414 Document Compliance Validation Tool.

    Validates PDFs against corporate compliance policies:
    - Disclaimer presence and coverage
    - Font/color/number formatting
    - Logo presence and positioning
    - Grammar and spelling

    Wraps existing `validate_document()` function with MCP interface.
    """

    def get_spec(self) -> ToolSpec:
        return ToolSpec(
            name="audit_file",
            version="1.0.0",
            display_name="Document Compliance Auditor",
            description=(
                "Validates PDF documents against COPILOTO_414 compliance policies. "
                "Checks disclaimers, formatting, logos, and grammar."
            ),
            category=ToolCategory.COMPLIANCE,
            capabilities=[
                ToolCapability.ASYNC,
                ToolCapability.IDEMPOTENT,
                ToolCapability.CACHEABLE,
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID to validate",
                    },
                    "policy_id": {
                        "type": "string",
                        "enum": ["auto", "414-std", "414-strict", "banamex", "afore-xxi"],
                        "default": "auto",
                        "description": "Compliance policy to apply",
                    },
                    "enable_disclaimer": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run disclaimer auditor",
                    },
                    "enable_format": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run format auditor",
                    },
                    "enable_logo": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run logo auditor",
                    },
                },
                "required": ["doc_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["done", "error"]},
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "category": {"type": "string"},
                                "rule": {"type": "string"},
                                "issue": {"type": "string"},
                                "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                                "location": {"type": "object"},
                                "suggestion": {"type": "string"},
                            },
                        },
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_findings": {"type": "integer"},
                            "policy_id": {"type": "string"},
                            "policy_name": {"type": "string"},
                            "disclaimer_coverage": {"type": "number"},
                            "findings_by_severity": {"type": "object"},
                        },
                    },
                },
            },
            tags=["compliance", "validation", "copiloto_414", "pdf", "audit"],
            requires_auth=True,
            rate_limit={"calls_per_minute": 10},
            timeout_ms=60000,  # 60 seconds
            max_payload_size_kb=10,  # Small payload (just doc_id)
        )

    async def validate_input(self, payload: Dict[str, Any]) -> None:
        """Validate input payload."""
        if "doc_id" not in payload:
            raise ValueError("Missing required field: doc_id")

        if not isinstance(payload["doc_id"], str):
            raise ValueError("doc_id must be a string")

        # Optional: Validate policy_id enum
        if "policy_id" in payload:
            valid_policies = ["auto", "414-std", "414-strict", "banamex", "afore-xxi"]
            if payload["policy_id"] not in valid_policies:
                raise ValueError(f"Invalid policy_id. Must be one of: {valid_policies}")

    async def execute(
        self,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute COPILOTO_414 validation.

        Args:
            payload: {
                "doc_id": "doc_123",
                "policy_id": "auto",
                "enable_disclaimer": True,
                "enable_format": True,
                "enable_logo": True
            }
            context: {
                "user_id": "user_456",
                "trace_id": "trace_789"
            }

        Returns:
            Validation report with findings and summary
        """
        doc_id = payload["doc_id"]
        policy_id = payload.get("policy_id", "auto")
        enable_disclaimer = payload.get("enable_disclaimer", True)
        enable_format = payload.get("enable_format", True)
        enable_logo = payload.get("enable_logo", True)
        user_id = context.get("user_id") if context else None

        logger.info(
            "Audit file tool execution started",
            doc_id=doc_id,
            policy_id=policy_id,
            user_id=user_id,
        )

        # 1. Get document
        doc = await Document.get(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        # 2. Check ownership
        if user_id and doc.user_id != user_id:
            raise PermissionError(f"User {user_id} not authorized to audit document {doc_id}")

        # 3. Resolve policy
        policy = await resolve_policy(policy_id, document=doc)

        # 4. Run validation (reuse existing service)
        from ...services.minio_storage import get_minio_storage
        minio_storage = get_minio_storage()
        pdf_path, is_temp = minio_storage.materialize_document(
            doc.minio_key,
            filename=doc.filename,
        )

        try:
            report = await validate_document(
                document=doc,
                pdf_path=pdf_path,
                client_name=policy.client_name,
                enable_disclaimer=enable_disclaimer,
                enable_format=enable_format,
                enable_logo=enable_logo,
                policy_config=policy.to_compliance_config(),
                policy_id=policy.id,
                policy_name=policy.name,
            )

            # 5. Convert to MCP output format
            return {
                "job_id": report.job_id,
                "status": report.status,
                "findings": [f.model_dump() for f in report.findings],
                "summary": report.summary,
                "attachments": report.attachments,
            }

        finally:
            # Cleanup temp file
            if is_temp and pdf_path.exists():
                pdf_path.unlink()
```

### 5.2 Tool 2: `excel_analyzer` (Excel Data Analysis)

```python
# apps/api/src/mcp/tools/excel_analyzer.py

from typing import Any, Dict, Optional, List
import pandas as pd
from pathlib import Path
import structlog

from ..protocol import ToolSpec, ToolCategory, ToolCapability
from ..tool import Tool
from ...models.document import Document

logger = structlog.get_logger(__name__)


class ExcelAnalyzerTool(Tool):
    """
    Excel Data Analysis Tool.

    Reads Excel files and performs:
    - Basic statistics (row count, column count, data types)
    - Column aggregations (sum, mean, median, std)
    - Data validation (missing values, type mismatches)
    - Sheet enumeration

    Future: SQL-like querying, pivot tables, chart generation.
    """

    def get_spec(self) -> ToolSpec:
        return ToolSpec(
            name="excel_analyzer",
            version="1.0.0",
            display_name="Excel Data Analyzer",
            description=(
                "Analyzes Excel files (xlsx/xls) and returns statistics, aggregations, "
                "and data validation results."
            ),
            category=ToolCategory.DATA_ANALYTICS,
            capabilities=[
                ToolCapability.SYNC,
                ToolCapability.IDEMPOTENT,
                ToolCapability.CACHEABLE,
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID (Excel file)",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Sheet name (default: first sheet)",
                    },
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["stats", "aggregate", "validate", "preview"],
                        },
                        "description": "Operations to perform",
                        "default": ["stats", "preview"],
                    },
                    "aggregate_columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to aggregate (for 'aggregate' operation)",
                    },
                },
                "required": ["doc_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                    "sheet_name": {"type": "string"},
                    "stats": {
                        "type": "object",
                        "properties": {
                            "row_count": {"type": "integer"},
                            "column_count": {"type": "integer"},
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "dtype": {"type": "string"},
                                        "non_null_count": {"type": "integer"},
                                        "null_count": {"type": "integer"},
                                    },
                                },
                            },
                        },
                    },
                    "aggregates": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "sum": {"type": "number"},
                                "mean": {"type": "number"},
                                "median": {"type": "number"},
                                "std": {"type": "number"},
                                "min": {"type": "number"},
                                "max": {"type": "number"},
                            },
                        },
                    },
                    "validation": {
                        "type": "object",
                        "properties": {
                            "total_missing_values": {"type": "integer"},
                            "columns_with_missing": {"type": "array", "items": {"type": "string"}},
                            "type_mismatches": {"type": "array"},
                        },
                    },
                    "preview": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "First 10 rows as JSON records",
                    },
                },
            },
            tags=["excel", "data", "analytics", "spreadsheet", "pandas"],
            requires_auth=True,
            rate_limit={"calls_per_minute": 20},
            timeout_ms=30000,  # 30 seconds
            max_payload_size_kb=10,
        )

    async def validate_input(self, payload: Dict[str, Any]) -> None:
        """Validate input payload."""
        if "doc_id" not in payload:
            raise ValueError("Missing required field: doc_id")

        if "operations" in payload:
            valid_ops = ["stats", "aggregate", "validate", "preview"]
            for op in payload["operations"]:
                if op not in valid_ops:
                    raise ValueError(f"Invalid operation: {op}. Must be one of: {valid_ops}")

    async def execute(
        self,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze Excel file.

        Args:
            payload: {
                "doc_id": "doc_123",
                "sheet_name": "Sheet1",
                "operations": ["stats", "aggregate", "validate", "preview"],
                "aggregate_columns": ["revenue", "cost"]
            }
            context: {
                "user_id": "user_456"
            }

        Returns:
            Analysis results with stats, aggregates, validation, preview
        """
        doc_id = payload["doc_id"]
        sheet_name = payload.get("sheet_name")
        operations = payload.get("operations", ["stats", "preview"])
        aggregate_columns = payload.get("aggregate_columns", [])
        user_id = context.get("user_id") if context else None

        logger.info(
            "Excel analyzer tool execution started",
            doc_id=doc_id,
            sheet_name=sheet_name,
            operations=operations,
            user_id=user_id,
        )

        # 1. Get document
        doc = await Document.get(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        # 2. Check ownership
        if user_id and doc.user_id != user_id:
            raise PermissionError(f"User {user_id} not authorized to analyze document {doc_id}")

        # 3. Check file type
        if doc.content_type not in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ]:
            raise ValueError(f"Document is not an Excel file: {doc.content_type}")

        # 4. Load Excel file
        from ...services.minio_storage import get_minio_storage
        minio_storage = get_minio_storage()
        excel_path, is_temp = minio_storage.materialize_document(
            doc.minio_key,
            filename=doc.filename,
        )

        try:
            # Read Excel file with pandas
            df = pd.read_excel(excel_path, sheet_name=sheet_name or 0)
            actual_sheet_name = sheet_name or "Sheet1"  # pandas default

            result: Dict[str, Any] = {
                "doc_id": doc_id,
                "sheet_name": actual_sheet_name,
            }

            # 5. Perform requested operations
            if "stats" in operations:
                result["stats"] = self._compute_stats(df)

            if "aggregate" in operations:
                result["aggregates"] = self._compute_aggregates(df, aggregate_columns)

            if "validate" in operations:
                result["validation"] = self._validate_data(df)

            if "preview" in operations:
                result["preview"] = df.head(10).to_dict(orient="records")

            return result

        finally:
            # Cleanup temp file
            if is_temp and excel_path.exists():
                excel_path.unlink()

    def _compute_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute basic statistics."""
        columns_info = []
        for col in df.columns:
            columns_info.append({
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null_count": int(df[col].count()),
                "null_count": int(df[col].isnull().sum()),
            })

        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns_info,
        }

    def _compute_aggregates(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Compute aggregations for numeric columns."""
        aggregates = {}

        for col in columns:
            if col not in df.columns:
                logger.warning("Column not found", column=col)
                continue

            if not pd.api.types.is_numeric_dtype(df[col]):
                logger.warning("Column is not numeric", column=col, dtype=df[col].dtype)
                continue

            aggregates[col] = {
                "sum": float(df[col].sum()),
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
            }

        return aggregates

    def _validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality."""
        total_missing = int(df.isnull().sum().sum())
        columns_with_missing = df.columns[df.isnull().any()].tolist()

        return {
            "total_missing_values": total_missing,
            "columns_with_missing": columns_with_missing,
            "type_mismatches": [],  # TODO: Implement type inference and mismatch detection
        }
```

### 5.3 Tool 3: `viz_tool` (Data Visualization)

```python
# apps/api/src/mcp/tools/viz_tool.py

from typing import Any, Dict, Optional, List
import structlog

from ..protocol import ToolSpec, ToolCategory, ToolCapability
from ..tool import Tool

logger = structlog.get_logger(__name__)


class VizTool(Tool):
    """
    Data Visualization Tool.

    Generates chart specifications (Plotly/ECharts JSON) from:
    - SQL query results
    - Excel data
    - CSV data
    - Manual data input

    Returns chart spec that frontend can render directly.
    Does NOT generate image files (keeps tool stateless).

    Future: Support for D3.js, Vega-Lite, custom dashboards.
    """

    def get_spec(self) -> ToolSpec:
        return ToolSpec(
            name="viz_tool",
            version="1.0.0",
            display_name="Data Visualization Generator",
            description=(
                "Generates interactive chart specifications (Plotly/ECharts) "
                "from data sources. Returns JSON spec for frontend rendering."
            ),
            category=ToolCategory.VISUALIZATION,
            capabilities=[
                ToolCapability.SYNC,
                ToolCapability.IDEMPOTENT,
                ToolCapability.CACHEABLE,
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter", "heatmap", "histogram"],
                        "description": "Type of chart to generate",
                    },
                    "data_source": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["inline", "excel", "sql"],
                                "description": "Data source type",
                            },
                            "doc_id": {
                                "type": "string",
                                "description": "Document ID (for excel type)",
                            },
                            "sheet_name": {
                                "type": "string",
                                "description": "Sheet name (for excel type)",
                            },
                            "sql_query": {
                                "type": "string",
                                "description": "SQL query (for sql type)",
                            },
                            "data": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "Inline data (for inline type)",
                            },
                        },
                        "required": ["type"],
                    },
                    "x_column": {
                        "type": "string",
                        "description": "X-axis column name",
                    },
                    "y_column": {
                        "type": "string",
                        "description": "Y-axis column name",
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title",
                    },
                    "library": {
                        "type": "string",
                        "enum": ["plotly", "echarts"],
                        "default": "plotly",
                        "description": "Charting library",
                    },
                },
                "required": ["chart_type", "data_source"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "library": {"type": "string", "enum": ["plotly", "echarts"]},
                    "spec": {
                        "type": "object",
                        "description": "Chart specification (library-specific JSON)",
                    },
                    "preview_data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "First 10 rows of data used for chart",
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "data_points": {"type": "integer"},
                            "columns": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            tags=["visualization", "charts", "plotly", "echarts", "bi", "analytics"],
            requires_auth=True,
            rate_limit={"calls_per_minute": 30},
            timeout_ms=15000,  # 15 seconds
            max_payload_size_kb=500,  # Allow larger payloads for inline data
        )

    async def validate_input(self, payload: Dict[str, Any]) -> None:
        """Validate input payload."""
        if "chart_type" not in payload:
            raise ValueError("Missing required field: chart_type")

        if "data_source" not in payload:
            raise ValueError("Missing required field: data_source")

        data_source = payload["data_source"]
        if "type" not in data_source:
            raise ValueError("Missing required field: data_source.type")

        source_type = data_source["type"]
        if source_type == "excel" and "doc_id" not in data_source:
            raise ValueError("Missing required field: data_source.doc_id for excel type")

        if source_type == "sql" and "sql_query" not in data_source:
            raise ValueError("Missing required field: data_source.sql_query for sql type")

        if source_type == "inline" and "data" not in data_source:
            raise ValueError("Missing required field: data_source.data for inline type")

    async def execute(
        self,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate chart specification.

        Args:
            payload: {
                "chart_type": "bar",
                "data_source": {
                    "type": "inline",
                    "data": [
                        {"month": "Jan", "revenue": 10000},
                        {"month": "Feb", "revenue": 15000},
                        {"month": "Mar", "revenue": 12000}
                    ]
                },
                "x_column": "month",
                "y_column": "revenue",
                "title": "Monthly Revenue",
                "library": "plotly"
            }
            context: {
                "user_id": "user_456"
            }

        Returns:
            Chart specification ready for frontend rendering
        """
        chart_type = payload["chart_type"]
        data_source = payload["data_source"]
        x_column = payload.get("x_column")
        y_column = payload.get("y_column")
        title = payload.get("title", "Chart")
        library = payload.get("library", "plotly")
        user_id = context.get("user_id") if context else None

        logger.info(
            "Viz tool execution started",
            chart_type=chart_type,
            data_source_type=data_source["type"],
            library=library,
            user_id=user_id,
        )

        # 1. Load data based on source type
        data = await self._load_data(data_source, user_id)

        if not data:
            raise ValueError("No data loaded from source")

        # 2. Generate chart spec
        if library == "plotly":
            spec = self._generate_plotly_spec(
                chart_type=chart_type,
                data=data,
                x_column=x_column,
                y_column=y_column,
                title=title,
            )
        elif library == "echarts":
            spec = self._generate_echarts_spec(
                chart_type=chart_type,
                data=data,
                x_column=x_column,
                y_column=y_column,
                title=title,
            )
        else:
            raise ValueError(f"Unsupported library: {library}")

        # 3. Build response
        return {
            "library": library,
            "spec": spec,
            "preview_data": data[:10],  # First 10 rows
            "metadata": {
                "data_points": len(data),
                "columns": list(data[0].keys()) if data else [],
            },
        }

    async def _load_data(
        self,
        data_source: Dict[str, Any],
        user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Load data from specified source."""
        source_type = data_source["type"]

        if source_type == "inline":
            return data_source["data"]

        elif source_type == "excel":
            # Delegate to ExcelAnalyzerTool
            from .excel_analyzer import ExcelAnalyzerTool
            from ...models.document import Document

            doc_id = data_source["doc_id"]
            sheet_name = data_source.get("sheet_name")

            doc = await Document.get(doc_id)
            if not doc:
                raise ValueError(f"Document not found: {doc_id}")

            if user_id and doc.user_id != user_id:
                raise PermissionError(f"User {user_id} not authorized to access document {doc_id}")

            # Load Excel data with pandas
            import pandas as pd
            from ...services.minio_storage import get_minio_storage
            minio_storage = get_minio_storage()
            excel_path, is_temp = minio_storage.materialize_document(
                doc.minio_key,
                filename=doc.filename,
            )

            try:
                df = pd.read_excel(excel_path, sheet_name=sheet_name or 0)
                return df.to_dict(orient="records")
            finally:
                if is_temp and excel_path.exists():
                    excel_path.unlink()

        elif source_type == "sql":
            # TODO: Implement SQL query execution (requires DB connection)
            raise NotImplementedError("SQL data source not yet implemented")

        else:
            raise ValueError(f"Unknown data source type: {source_type}")

    def _generate_plotly_spec(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        x_column: Optional[str],
        y_column: Optional[str],
        title: str,
    ) -> Dict[str, Any]:
        """Generate Plotly chart specification."""
        if chart_type == "bar":
            return {
                "data": [
                    {
                        "type": "bar",
                        "x": [row[x_column] for row in data] if x_column else list(range(len(data))),
                        "y": [row[y_column] for row in data] if y_column else [0] * len(data),
                    }
                ],
                "layout": {
                    "title": title,
                    "xaxis": {"title": x_column or "X"},
                    "yaxis": {"title": y_column or "Y"},
                },
            }

        elif chart_type == "line":
            return {
                "data": [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "x": [row[x_column] for row in data] if x_column else list(range(len(data))),
                        "y": [row[y_column] for row in data] if y_column else [0] * len(data),
                    }
                ],
                "layout": {
                    "title": title,
                    "xaxis": {"title": x_column or "X"},
                    "yaxis": {"title": y_column or "Y"},
                },
            }

        elif chart_type == "pie":
            return {
                "data": [
                    {
                        "type": "pie",
                        "labels": [row[x_column] for row in data] if x_column else list(range(len(data))),
                        "values": [row[y_column] for row in data] if y_column else [1] * len(data),
                    }
                ],
                "layout": {
                    "title": title,
                },
            }

        else:
            # Default to scatter
            return {
                "data": [
                    {
                        "type": "scatter",
                        "mode": "markers",
                        "x": [row[x_column] for row in data] if x_column else list(range(len(data))),
                        "y": [row[y_column] for row in data] if y_column else [0] * len(data),
                    }
                ],
                "layout": {
                    "title": title,
                    "xaxis": {"title": x_column or "X"},
                    "yaxis": {"title": y_column or "Y"},
                },
            }

    def _generate_echarts_spec(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        x_column: Optional[str],
        y_column: Optional[str],
        title: str,
    ) -> Dict[str, Any]:
        """Generate ECharts specification."""
        # Similar implementation for ECharts
        # For brevity, reusing Plotly logic (actual implementation would differ)
        return {
            "title": {"text": title},
            "tooltip": {},
            "xAxis": {
                "data": [row[x_column] for row in data] if x_column else list(range(len(data)))
            },
            "yAxis": {},
            "series": [
                {
                    "name": y_column or "Y",
                    "type": chart_type,
                    "data": [row[y_column] for row in data] if y_column else [0] * len(data),
                }
            ],
        }
```

---

## 6. NEW Tools - Deep Research & Document Extraction

### 6.1 Tool 4: `deep_research` (Aletheia Integration)

**Implementation**: `apps/api/src/mcp/tools/deep_research_tool.py`

**Purpose**: Multi-step research using the existing Aletheia service for comprehensive information gathering and synthesis.

**Key Features**:
- Breaks down complex queries into sub-questions
- Gathers information from multiple sources
- Synthesizes findings into coherent reports
- Tracks research progress and iterations
- Configurable depth (shallow/medium/deep)

**Input Schema**:
```python
{
    "query": str,                    # Research question (required)
    "depth": str,                    # "shallow", "medium", or "deep"
    "focus_areas": List[str],        # Specific areas to focus on (optional)
    "max_iterations": int,           # Max research iterations (1-10)
    "include_sources": bool          # Include source citations
}
```

**Output Schema**:
```python
{
    "task_id": str,                  # Research task ID for tracking
    "status": str,                   # "pending", "running", "completed", "failed"
    "query": str,                    # Original research query
    "summary": str,                  # Executive summary (when completed)
    "findings": List[Finding],       # Detailed research findings
    "iterations_completed": int,     # Number of iterations completed
    "sources": List[Source],         # All sources consulted
    "metadata": {
        "started_at": datetime,
        "completed_at": datetime,
        "total_duration_ms": float,
        "tokens_used": int
    }
}
```

**Integration Points**:
- `deep_research_service.create_research_task()` - Task creation
- `aletheia_client` - Research orchestration
- `research_coordinator` - Multi-step coordination

**Usage Example**:
```python
# Via FastMCP server
result = await deep_research(
    query="What are the latest trends in renewable energy?",
    depth="medium",
    focus_areas=["solar", "wind", "battery storage"]
)

# Via MCP Tool class
tool = DeepResearchTool()
response = await tool.invoke({
    "query": "AI trends 2025",
    "depth": "deep",
    "max_iterations": 5
}, context={"user_id": "user_123"})
```

**Testing**: `apps/api/tests/mcp/test_deep_research_tool.py`

---

### 6.2 Tool 5: `extract_document_text` (Multi-tier Extraction)

**Implementation**: `apps/api/src/mcp/tools/document_extraction_tool.py`

**Purpose**: Extract text from PDF and image documents using intelligent 3-tier fallback strategy.

**Extraction Strategy**:
1. **Cache Check** - Redis (1 hour TTL)
2. **pypdf** - Fast, for text-based PDFs
3. **Saptiva PDF SDK** - Complex layouts
4. **Saptiva OCR** - Image-based PDFs

**Key Features**:
- Automatic method selection
- Caching for performance
- Support for PDFs and images (PNG, JPEG, TIFF)
- Ownership validation
- Detailed metadata

**Input Schema**:
```python
{
    "doc_id": str,                   # Document ID (required)
    "method": str,                   # "auto", "pypdf", "saptiva_sdk", "ocr"
    "page_numbers": List[int],       # Specific pages (1-indexed, optional)
    "include_metadata": bool,        # Include document metadata
    "cache_ttl_seconds": int         # Cache TTL (60-86400)
}
```

**Output Schema**:
```python
{
    "doc_id": str,
    "text": str,                     # Extracted text content
    "method_used": str,              # Method that succeeded
    "pages": List[Page],             # Per-page extraction (if requested)
    "metadata": {
        "filename": str,
        "content_type": str,
        "size_bytes": int,
        "total_pages": int,
        "char_count": int,
        "word_count": int,
        "extraction_duration_ms": float,
        "cached": bool
    }
}
```

**Integration Points**:
- `document_service.get_document_text()` - Cache retrieval
- `document_extraction.extract_text_from_pdf()` - 3-tier extraction
- `minio_storage.materialize_document()` - File retrieval
- `cache_service` - Redis caching

**Usage Example**:
```python
# Via FastMCP server
result = await extract_document_text(
    doc_id="doc_123",
    method="auto",
    include_metadata=True
)

# Via MCP Tool class
tool = DocumentExtractionTool()
response = await tool.invoke({
    "doc_id": "doc_456",
    "method": "ocr",
    "cache_ttl_seconds": 7200
}, context={"user_id": "user_123"})
```

**Testing**: `apps/api/tests/mcp/test_document_extraction_tool.py`

---

## 7. Tools Catalog Integration

### 7.1 DEFAULT_AVAILABLE_TOOLS Update

The new MCP tools have been integrated into the `DEFAULT_AVAILABLE_TOOLS` catalog (`apps/api/src/services/tools.py`), making them discoverable and usable by the LLM prompt system.

**Updated Catalog**:
```python
DEFAULT_AVAILABLE_TOOLS = {
    # Web & Research Tools
    "web_search": {...},
    "deep_research": {...},          # ✨ NEW - MCP Integration

    # Document Tools (MCP)
    "audit_file": {...},
    "extract_document_text": {...},  # ✨ NEW - MCP Integration

    # Data Analytics Tools (MCP)
    "excel_analyzer": {...},
    "viz_tool": {...},

    # Utility Tools
    "calculator": {...},
    "code_executor": {...}
}
```

### 7.2 Function-Calling Integration

The tools are automatically converted to function-calling schemas via `tool_schemas_json()`:

```python
from services.tools import build_tools_context, DEFAULT_AVAILABLE_TOOLS

# Enable deep research and document extraction
tools_enabled = {
    "deep_research": True,
    "extract_document_text": True,
    "audit_file": True
}

# Generate context for LLM prompt
markdown, schemas = build_tools_context(
    tools_enabled=tools_enabled,
    available_tools=DEFAULT_AVAILABLE_TOOLS
)

# Inject into system prompt
system_prompt = f"""
You are OctaviOS, an AI assistant with access to these tools:

{markdown}

Use them to help the user effectively.
"""

# Attach schemas to API request
response = await saptiva_client.chat_completion(
    messages=[...],
    tools=schemas  # Function-calling schemas
)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Coverage**: All new tools have comprehensive unit tests

**Test Files**:
- `tests/mcp/test_deep_research_tool.py` (234 lines, 15 tests)
- `tests/mcp/test_document_extraction_tool.py` (289 lines, 18 tests)

**Test Categories**:
1. **Specification Tests** - Tool metadata and schemas
2. **Validation Tests** - Input validation edge cases
3. **Execution Tests** - Tool logic and service integration
4. **Invocation Tests** - Full lifecycle with error handling

**Run Tests**:
```bash
# Run all MCP tests
make test-api FILE=tests/mcp/

# Run specific tool tests
make test-api FILE=tests/mcp/test_deep_research_tool.py ARGS="-v"
make test-api FILE=tests/mcp/test_document_extraction_tool.py ARGS="-v"
```

### 8.2 Integration Tests

Integration tests should verify:
- ✅ Tool registration in FastMCP server
- ✅ HTTP endpoint functionality (`/mcp/tools/invoke`)
- ✅ Authentication and authorization
- ✅ Real service integration (Aletheia, document extraction)
- ✅ Caching behavior
- ✅ Error handling and logging

**TODO**: Create integration tests in `tests/integration/test_mcp_tools_integration.py`

---

## 9. Next Steps & Roadmap

### 9.1 Completed ✅
- [x] Deep Research Tool (Aletheia integration)
- [x] Document Extraction Tool (multi-tier strategy)
- [x] Integration with DEFAULT_AVAILABLE_TOOLS catalog
- [x] Comprehensive unit tests
- [x] FastMCP server registration
- [x] Documentation updates

### 9.2 In Progress 🚧
- [ ] Integration tests for new tools
- [ ] Frontend UI components for tool invocation
- [ ] Tool usage metrics and observability
- [ ] Rate limiting per tool

### 9.3 Future Enhancements 🚀
- [ ] **SQL Query Tool** - Execute read-only SQL queries against analytics DB
- [ ] **Web Scraper Tool** - Extract structured data from websites
- [ ] **Image Analysis Tool** - OCR + object detection + classification
- [ ] **Code Executor Tool** - Sandboxed Python/JavaScript execution
- [ ] **Workflow Orchestrator** - Chain multiple tools together
- [ ] **Custom Policy Designer** - Visual policy configuration for COPILOTO_414

### 9.4 Migration to Out-of-Process (Future)

**When to Consider**:
- Tool execution time > 5 seconds consistently
- Resource contention (high CPU/memory tools)
- Independent scaling needs
- Security isolation requirements

**Migration Path**:
- MCP tools are already well-abstracted
- `ToolRegistry` can be moved to separate service
- `ToolSpec` Pydantic schemas can be shared via package
- Invoke API already has HTTP contract defined

---

## 10. References

See also:
- `MIGRATION_PLAN.md` - Phase-by-phase implementation plan
- `SECURITY_OBS_CHECKLIST.md` - Security and observability requirements
- `MCP_TESTING_GUIDE.md` - Comprehensive testing guide
- `CLAUDE.md` - Project overview and development guidelines
