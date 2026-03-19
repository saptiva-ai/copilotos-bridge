# Research: File Processing Migration to file-manager Plugin

## 1. Current File-Manager Plugin State

**Location:** `plugins/public/file-manager/`

### Already Implemented

| Component | File | Status |
|-----------|------|--------|
| MinIO Client | `src/services/minio_client.py` | ✅ Complete |
| Redis Cache | `src/services/redis_client.py` | ✅ Complete |
| Extraction Service | `src/services/extraction.py` | ✅ Basic (pypdf + pytesseract) |
| Upload Router | `src/routers/upload.py` | ✅ Complete |
| Download Router | `src/routers/download.py` | ✅ Complete |
| Metadata Router | `src/routers/metadata.py` | ✅ Complete |
| Health Checks | `src/routers/health.py` | ✅ Complete |
| MCP Tools | `src/mcp/tools/` | ❌ Empty structure |

### Current REST Endpoints

```
POST   /upload                    # File upload with auto-extraction
GET    /download/{path}           # File download
GET    /download/{path}/stream    # Streaming download
GET    /presigned/{path}          # Presigned URL generation
GET    /metadata/{path}           # File metadata
POST   /extract/{path}            # Manual text extraction
DELETE /files/{path}              # File deletion
GET    /health                    # Full health check
GET    /ready                     # Kubernetes readiness
GET    /live                      # Kubernetes liveness
```

### Configuration

```python
# From src/config.py
- port: 8001
- minio_endpoint: "minio:9000"
- minio_bucket_documents: "documents"
- redis_url: "${REDIS_URL}"
- max_file_size_mb: 50
- supported_mime_types: [PDF, PNG, JPEG, HEIC, HEIF, GIF]
- ocr_max_pages: 30
- ocr_raster_dpi: 180
- extraction_cache_ttl_seconds: 3600
```

### Dependencies (requirements.txt)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
minio>=7.2.0
redis>=5.0.0
pypdf>=4.0.0
PyMuPDF>=1.23.0
pytesseract>=0.3.10
pillow>=10.0.0
python-magic>=0.4.27
fastmcp>=2.0.0  # Not yet used
structlog>=24.1.0
```

---

## 2. Backend File Processing Services

**Location:** `apps/backend/src/services/`

### Services to Migrate (High Priority)

| Service | Size | Purpose | Dependencies |
|---------|------|---------|--------------|
| `minio_service.py` | 10.6 KB | MinIO client wrapper | minio SDK |
| `minio_storage.py` | 20.2 KB | Async MinIO + streaming | minio SDK, aiofiles |
| `document_extraction.py` | 17.4 KB | Extraction routing | extractors/, minio |
| `thumbnail_service.py` | 10.5 KB | PDF/image thumbnails | PyMuPDF, Pillow |

### Extractors Framework

**Location:** `apps/backend/src/services/extractors/`

| File | Purpose |
|------|---------|
| `base.py` | Abstract base class for extractors |
| `factory.py` | Factory pattern for backend selection |
| `third_party.py` | pypdf + pytesseract (matches plugin) |
| `saptiva.py` | Saptiva Native Tools API |
| `huggingface.py` | DeepSeek OCR via HF Space |
| `pdf_raster_ocr.py` | Single-page PDF rasterization |
| `ab_testing.py` | A/B testing framework |
| `cache.py` | Redis caching abstraction |

### Services to Keep in Backend

| Service | Reason |
|---------|--------|
| `file_ingest.py` | Orchestration + Document model coupling |
| `file_events.py` | SSE for chat sessions (will use gRPC streaming) |
| `document_processing_service.py` | RAG integration |
| `document_service.py` | Document CRUD + MongoDB |

---

## 3. Dependency Analysis

### Backend Models Used by File Services

```python
# apps/backend/src/models/document.py
class Document(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    minio_key: str
    minio_bucket: str
    status: DocumentStatus  # UPLOADING → PROCESSING → READY/FAILED
    pages: List[PageContent]
    total_pages: int
    ocr_applied: bool
    ocr_language: str
    user_id: str
    conversation_id: str

class PageContent(BaseModel):
    page: int
    text_md: str
    has_table: bool
    table_csv_key: Optional[str]
    has_images: bool
    image_keys: List[str]
```

### Circular Dependencies

```
file_ingest.py
    ├── document_extraction.py
    │   └── extractors/*.py
    ├── document_processing_service.py
    │   └── document_extraction.py
    ├── minio_service.py
    ├── storage.py
    └── file_events.py
```

**Breaking the cycle:**
- Plugin handles: storage, extraction, thumbnails
- Backend handles: orchestration, persistence, events

---

## 4. gRPC Infrastructure Analysis

### Existing gRPC Usage

- **Weaviate client** uses gRPC on port 50051
- **qdrant_client** has gRPC proto files in `.venv`
- **No project-defined proto files** exist

### Proto Files Found

```
# In backend/.venv (libraries only)
qdrant_client/proto/*.proto
google/api/*.proto
google/rpc/*.proto
google/type/*.proto
```

### gRPC Dependencies Available

```python
# Already in backend via qdrant/weaviate
grpcio>=1.60.0  # Available
```

### Port Allocation

| Service | Port | Protocol |
|---------|------|----------|
| Backend | 8000 | HTTP |
| file-manager | 8001 | HTTP |
| Weaviate | 50051 | gRPC |
| **file-manager** | **50052** | **gRPC (new)** |

---

## 5. Interface Design Requirements

### Core Operations

1. **Upload**
   - Client streams file chunks
   - Server responds with metadata + optional extraction
   - Bidirectional: progress events during upload

2. **Download**
   - Server streams file chunks
   - First message: metadata
   - Subsequent: file data

3. **Extract**
   - Unary: request → response
   - Stream variant: progress events for large PDFs

4. **Thumbnail**
   - Unary: request → image bytes
   - Options: width, height

5. **Metadata**
   - Unary: request → file info + cached extraction

6. **Delete**
   - Unary: request → success/failure

### Message Sizes

- Max upload: 100MB (configurable)
- Max response: 100MB
- Streaming chunk size: 64KB recommended

---

## 6. Migration Blockers

### Must Resolve

1. **PageContent Model**
   - Backend embeds in Document (MongoDB)
   - Plugin needs to return compatible format
   - **Solution:** Define proto PageContent, map in backend

2. **User Context**
   - Backend tracks user_id, conversation_id
   - Plugin is stateless
   - **Solution:** Pass via gRPC metadata headers

3. **Event Bus**
   - file_events.py is in-memory SSE
   - Can't feed into backend's chat streams
   - **Solution:** gRPC bidirectional streaming replaces SSE

### Won't Block

- Redis cache: Same prefix `doc:text:` already shared
- MinIO access: Both services have credentials
- Extraction quality: Plugin already validates

---

## 7. Test Coverage Analysis

### Current Tests

```
apps/backend/tests/unit/
├── test_chat_stream_producer.py   # 10 tests
├── test_document_extraction.py    # Not found
├── test_file_ingest.py            # Not found
└── services/                      # 17 tests
```

### Tests Needed

1. Proto serialization/deserialization
2. gRPC servicer unit tests (mocked clients)
3. Integration tests (real gRPC calls)
4. Streaming tests (upload/download)
5. Error handling (network failures)

---

## 8. Recommendations

### Phase 1: Infrastructure (Week 1)
- Create `proto/file_manager.proto`
- Generate Python stubs
- Add gRPC server skeleton to plugin
- Add gRPC client skeleton to backend
- Update docker-compose (port 50052)

### Phase 2: Core Services (Week 2)
- Migrate `extractors/` framework
- Migrate `thumbnail_service.py`
- Implement gRPC servicer methods
- Wire up backend client

### Phase 3: Integration (Week 3)
- Update `file_ingest.py` to use gRPC
- Remove `minio_service.py` and `minio_storage.py`
- Update MCP tools to use gRPC
- Backward compatibility flag

### Phase 4: Cleanup (Week 4)
- Remove migrated services
- Integration tests
- Performance benchmarks
- Documentation

---

## 9. References

- File-manager plugin: `plugins/public/file-manager/`
- Backend services: `apps/backend/src/services/`
- Document model: `apps/backend/src/models/document.py`
- gRPC Python docs: https://grpc.io/docs/languages/python/
