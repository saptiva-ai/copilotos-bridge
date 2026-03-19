# Backend Optimization Plan - Orchestrator Architecture

> Analysis Date: 2026-01-16
> Current Image Size: **13GB**
> Target: **~500MB** (pure orchestrator)
> Architecture Goal: Backend only orchestrates MCP/gRPC microservices

## Executive Summary

The backend currently bundles heavy ML/processing dependencies that should be extracted into dedicated microservices. This document outlines a migration path to a lightweight orchestrator pattern.

---

## Current State Analysis

### Image Size Breakdown

| Component | Size | Used By |
|-----------|------|---------|
| sentence-transformers + torch | ~6GB | `embedding_service.py` |
| tesseract-ocr + models | ~200MB | `ocr_service.py`, extractors |
| pymupdf | ~56MB | PDF extractors |
| opencv-python-headless | ~50MB | `policy_detector.py` |
| pandas + openpyxl | ~100MB | MCP tools (excel_analyzer) |
| Base Python + FastAPI | ~400MB | Core runtime |
| **Total** | **~13GB** | |

### Heavy Dependencies in requirements.txt

```python
# ML/Embeddings (~6GB)
sentence-transformers>=3.3.0  # Brings torch, numpy, scipy

# OCR (~200MB)
pytesseract>=0.3.10
Pillow>=10.0.0

# PDF Processing (~100MB)
pypdf>=3.17.0
pymupdf>=1.24.0

# Image Processing (~50MB)
opencv-python-headless>=4.8.0

# Data Analysis (~100MB)
pandas>=2.0.0
openpyxl>=3.1.0

# PDF Generation (unused?)
reportlab>=4.0.0
```

---

## Service Extraction Plan

### Microservice Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               BACKEND (Orchestrator) ~500MB                  │
│  - FastAPI + MCP Protocol                                   │
│  - Auth, Sessions, Rate Limiting                            │
│  - Chat Orchestration (no ML)                               │
│  - Routes requests to microservices                         │
└─────────────────────────────────────────────────────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Embedding    │ │ File Manager │ │ Bank Advisor │ │ Data         │
│ Service      │ │ (existing)   │ │ (existing)   │ │ Analysis     │
│ ~200MB       │ │ ~300MB       │ │ ~845MB       │ │ Service      │
│              │ │              │ │              │ │ ~200MB       │
│ - Embeddings │ │ - PDF/OCR    │ │ - NL2SQL     │ │ - Excel      │
│ - Vector ops │ │ - Extraction │ │ - Charts     │ │ - Pandas     │
│              │ │ - Thumbnails │ │ - Analytics  │ │ - Reports    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                              │
                              ▼
                    ┌──────────────┐
                    │   Databases  │
                    │ MongoDB/Redis│
                    │ Weaviate     │
                    │ PostgreSQL   │
                    └──────────────┘
```

### Service Definitions

#### 1. Embedding Service (New Microservice)
**Extract from:** `embedding_service.py`
**Protocol:** gRPC (high performance) or MCP
**Dependencies:**
- sentence-transformers
- torch (CPU-only for cost savings)

**API:**
```protobuf
service EmbeddingService {
  rpc Embed(TextRequest) returns (EmbeddingResponse);
  rpc EmbedBatch(BatchTextRequest) returns (BatchEmbeddingResponse);
}
```

**Alternative:** Use OpenAI/Cohere Embeddings API
- Pros: No infrastructure, lower latency
- Cons: Cost per request, vendor lock-in

---

#### 2. Document Processing → File Manager Plugin (EXISTING)
**Migrate from backend to:** `plugins/public/file-manager/`

> **Note:** The file-manager plugin already provides document processing capabilities.
> No new microservice needed—just delegate to file-manager via MCP.

**Backend files to remove:**
- `ocr_service.py`
- `document_extraction.py`
- `thumbnail_service.py`
- `extractors/*.py`

**File-Manager already provides:**
```python
# plugins/public/file-manager/src/services/extraction.py
async def extract_text_from_file(file_path, content_type) -> tuple[str, int]:
    """Extract text from PDF/images with OCR fallback."""

def extract_text_from_pdf(file_path) -> tuple[str, int]:
    """PDF extraction with pytesseract OCR fallback."""

def extract_text_from_image(file_path) -> str:
    """Image OCR using pytesseract."""
```

**Migration steps:**
1. Backend calls file-manager MCP tools instead of local extractors
2. Remove pytesseract, pymupdf, Pillow from backend requirements
3. Remove tesseract-ocr from backend Dockerfile
4. Add MCP tools to file-manager for thumbnail generation if needed

**Backend integration via MCP:**
```python
# Backend orchestrator pattern
async def extract_document(file_path: str) -> str:
    """Delegate to file-manager plugin via MCP."""
    async with mcp_client("file-manager") as client:
        return await client.call("extract_text", file_path=file_path)
```

---

#### 3. Data Analysis Service (New Microservice)
**Extract from:**
- `mcp/tools/excel_analyzer.py`
- `mcp/tools/viz_tool.py`

**Protocol:** MCP
**Dependencies:**
- pandas
- openpyxl

**MCP Tools:**
```python
@mcp.tool()
async def analyze_excel(file_path: str, query: str) -> dict:
    """Analyze Excel file with natural language query."""

@mcp.tool()
async def generate_chart(data: dict, chart_type: str) -> dict:
    """Generate Plotly chart configuration."""
```

---

## Backend Slim Requirements

Create `requirements-orchestrator.txt` for the slim backend:

```python
# Core FastAPI
fastapi>=0.115.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Database (metadata only, not heavy processing)
motor>=3.3.2
pymongo>=4.6.0
beanie>=1.24.0
redis>=5.0.1

# HTTP Client (for microservice calls)
httpx[http2]>=0.25.2
aiohttp>=3.9.5

# Authentication
python-jose[cryptography]>=3.3.0
passlib[argon2,bcrypt]>=1.7.4
python-multipart>=0.0.6
email-validator>=2.1.0

# Rate limiting
slowapi>=0.1.9

# Logging
structlog>=23.2.0

# Streaming
sse-starlette>=1.8.2

# MCP Protocol
mcp>=1.3.0
fastmcp>=2.0.0

# Metrics
prometheus-client>=0.19.0

# REMOVED (moved to microservices):
# - sentence-transformers (~6GB)
# - pytesseract, Pillow (~200MB)
# - pymupdf (~56MB)
# - opencv-python-headless (~50MB)
# - pandas, openpyxl (~100MB)
# - reportlab (~20MB)
# - qdrant-client, weaviate-client (if not directly needed)
```

---

## Migration Phases

### Phase 1: Quick Wins (Immediate)
**Effort:** 1-2 hours
**Impact:** ~6GB reduction

1. **Remove sentence-transformers from backend**
   - Backend calls Weaviate/bank-advisor for embeddings via MCP
   - OR use OpenAI Embeddings API

2. **Remove unused dependencies**
   - `reportlab` - no imports found
   - `opencv-python-headless` - only reference, not import

**Estimated size after Phase 1:** ~7GB → ~1GB

---

### Phase 2: Migrate Document Processing to File Manager (1-2 days)
**Effort:** 1-2 days
**Impact:** ~300MB reduction

1. Add MCP tools to existing file-manager plugin for extraction
2. Update backend to call file-manager via MCP instead of local extractors
3. Remove pytesseract, pymupdf, Pillow from backend requirements
4. Remove tesseract-ocr from backend Dockerfile

**Note:** File-manager already has `extract_text_from_file()`, `extract_text_from_pdf()`, and OCR capabilities.

**Estimated size after Phase 2:** ~1GB → ~700MB

---

### Phase 3: Extract Data Analysis (1 day)
**Effort:** 1 day
**Impact:** ~100MB reduction

1. Move excel_analyzer and viz_tool to dedicated service
2. Remove pandas, openpyxl from backend

**Estimated size after Phase 3:** ~700MB → ~500MB

---

## Dockerfile Changes

### Current Dockerfile Issues

```dockerfile
# Heavy system packages
RUN apt-get install -y \
    tesseract-ocr \        # Move to doc-processor
    tesseract-ocr-spa \    # Move to doc-processor
    tesseract-ocr-eng      # Move to doc-processor

# Heavy Python packages via requirements.txt
sentence-transformers  # 6GB+
pymupdf               # 56MB
pytesseract           # Needs tesseract
pandas                # 100MB
```

### Optimized Dockerfile (Orchestrator)

```dockerfile
FROM python:3.11-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app
COPY requirements-orchestrator.txt .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements-orchestrator.txt

FROM python:3.11-slim-bookworm AS production

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# NO tesseract, NO heavy apt packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/

RUN useradd --create-home --uid 1001 api_user
USER api_user

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Graceful Degradation Strategy

For services not yet extracted, implement optional imports:

```python
# embedding_service.py
class EmbeddingService:
    def __init__(self, use_local: bool = False):
        self._local_model = None
        self._use_local = use_local

    async def embed(self, text: str) -> List[float]:
        if self._use_local:
            return await self._embed_local(text)
        else:
            return await self._embed_via_api(text)

    async def _embed_via_api(self, text: str) -> List[float]:
        """Call external embedding service via MCP/gRPC."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"text": text}
            )
            return response.json()["embedding"]

    async def _embed_local(self, text: str) -> List[float]:
        """Fallback to local model (requires sentence-transformers)."""
        try:
            from sentence_transformers import SentenceTransformer
            if self._local_model is None:
                self._local_model = SentenceTransformer(MODEL_NAME)
            return self._local_model.encode(text).tolist()
        except ImportError:
            raise RuntimeError("Local embedding not available")
```

---

## Communication Protocols

### MCP (Model Context Protocol)
**Use for:** Tool execution, document processing, data analysis
**Pros:**
- Already implemented in codebase
- JSON-RPC based, easy to debug
- Built-in streaming support

### gRPC
**Use for:** High-throughput services (embeddings, vector search)
**Pros:**
- Binary protocol, lower latency
- Strong typing with protobuf
- Bidirectional streaming

### HTTP/REST
**Use for:** Simple services, external APIs (OpenAI, etc.)
**Pros:**
- Universal compatibility
- Easy debugging
- Caching via HTTP semantics

---

## Estimated Final Architecture

| Service | Size | Protocol | Responsibility |
|---------|------|----------|----------------|
| **Backend (Orchestrator)** | ~500MB | HTTP | Auth, routing, sessions |
| **Bank Advisor** | ~845MB | MCP | NL2SQL, analytics |
| **Embedding Service** | ~200MB | gRPC | Vector embeddings |
| **File Manager (existing)** | ~300MB | MCP | PDF, OCR, thumbnails |
| **Data Analysis** | ~200MB | MCP | Excel, charts |
| **Total** | ~2.0GB | - | Full system |

**vs Current:** ~30GB (13GB backend + 17GB bank-advisor)
**Reduction:** ~93%

---

## Implementation Priority

1. **[IMMEDIATE]** Remove sentence-transformers, use API or Weaviate
2. **[IMMEDIATE]** Remove unused reportlab
3. **[WEEK 1]** Migrate document processing to file-manager plugin (already exists)
4. **[WEEK 2]** Create embedding service microservice (or use OpenAI API)
5. **[WEEK 3]** Create data analysis microservice
6. **[WEEK 4]** Update CI/CD, deployment scripts

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Network latency between services | Use gRPC for high-frequency calls |
| Service discovery complexity | Use Docker Compose networks / K8s DNS |
| Debugging distributed system | Implement distributed tracing (OpenTelemetry) |
| Data consistency | Use event sourcing for critical operations |
| Cold start latency | Implement health checks and warm-up endpoints |

---

## Success Metrics

- [ ] Backend image < 600MB
- [ ] Cold start time < 5 seconds
- [ ] End-to-end latency unchanged or improved
- [ ] Memory usage < 500MB at idle
- [ ] All existing tests pass
