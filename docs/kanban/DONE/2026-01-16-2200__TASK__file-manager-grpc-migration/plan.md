# Plan: File Processing gRPC Migration

## Phase 1: gRPC Infrastructure (Week 1)

### 1.1 Create Proto Definitions

**File:** `plugins/public/file-manager/proto/file_manager.proto`

```protobuf
syntax = "proto3";
package filemanager;

// Core Messages
message FileChunk {
  bytes data = 1;
  int64 offset = 2;
  bool is_last = 3;
}

message FileMetadata {
  string file_id = 1;
  string filename = 2;
  int64 size = 3;
  string content_type = 4;
  string minio_key = 5;
  string sha256 = 6;
  optional string last_modified = 7;
}

message PageContent {
  int32 page = 1;
  string text_md = 2;
  bool has_table = 3;
  optional string table_csv_key = 4;
  bool has_images = 5;
  repeated string image_keys = 6;
}

message ExtractionResult {
  string file_id = 1;
  repeated PageContent pages = 2;
  int32 total_pages = 3;
  bool ocr_applied = 4;
  string source = 5;
}

message ProgressEvent {
  string file_id = 1;
  string phase = 2;
  float progress = 3;
  string status = 4;
  optional string error = 5;
}

// Service Definition
service FileManagerService {
  rpc UploadSimple(UploadSimpleRequest) returns (UploadResponse);
  rpc Upload(stream FileChunk) returns (stream ProgressEvent);
  rpc Download(DownloadRequest) returns (stream DownloadResponse);
  rpc Extract(ExtractRequest) returns (ExtractResponse);
  rpc ExtractStream(ExtractRequest) returns (stream ProgressEvent);
  rpc GenerateThumbnail(ThumbnailRequest) returns (ThumbnailResponse);
  rpc GetMetadata(MetadataRequest) returns (MetadataResponse);
  rpc Delete(DeleteRequest) returns (DeleteResponse);
  rpc Health(HealthRequest) returns (HealthResponse);
}

// Request/Response Messages
message UploadRequest {
  string user_id = 1;
  string filename = 2;
  string content_type = 3;
  optional string session_id = 4;
  optional string idempotency_key = 5;
  bool auto_extract = 6;
}

message UploadSimpleRequest {
  UploadRequest metadata = 1;
  bytes file_data = 2;
}

message UploadResponse {
  string file_id = 1;
  FileMetadata metadata = 2;
  optional ExtractionResult extraction = 3;
}

message DownloadRequest {
  string file_path = 1;
  optional string bucket = 2;
}

message DownloadResponse {
  oneof content {
    FileChunk chunk = 1;
    FileMetadata metadata = 2;
  }
}

message ExtractRequest {
  string file_path = 1;
  bool force = 2;
  optional string provider = 3;
}

message ExtractResponse {
  ExtractionResult result = 1;
}

message ThumbnailRequest {
  string file_path = 1;
  optional int32 width = 2;
  optional int32 height = 3;
}

message ThumbnailResponse {
  bytes thumbnail = 1;
  string content_type = 2;
}

message MetadataRequest {
  string file_path = 1;
  bool include_text = 2;
}

message MetadataResponse {
  FileMetadata metadata = 1;
  optional ExtractionResult extraction = 2;
}

message DeleteRequest {
  string file_path = 1;
}

message DeleteResponse {
  bool success = 1;
  string message = 2;
}

message HealthRequest {}

message HealthResponse {
  string status = 1;
  map<string, bool> dependencies = 2;
}
```

### 1.2 Update Dependencies

**plugins/public/file-manager/requirements.txt** - Add:
```
grpcio>=1.60.0
grpcio-tools>=1.60.0
grpcio-reflection>=1.60.0
```

**apps/backend/requirements.txt** - Verify:
```
grpcio>=1.60.0  # Already present via qdrant
```

### 1.3 Create gRPC Directory Structure

```bash
mkdir -p plugins/public/file-manager/proto
mkdir -p plugins/public/file-manager/src/grpc/generated
touch plugins/public/file-manager/src/grpc/__init__.py
touch plugins/public/file-manager/src/grpc/server.py
touch plugins/public/file-manager/src/grpc/servicer.py
touch plugins/public/file-manager/src/grpc/interceptors.py
```

### 1.4 Generate Python Stubs

```bash
cd plugins/public/file-manager
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=./src/grpc/generated \
  --grpc_python_out=./src/grpc/generated \
  ./proto/file_manager.proto
```

### 1.5 Update Docker Compose

**infra/docker-compose.yml:**
```yaml
file-manager:
  ports:
    - "${FILE_MANAGER_PORT:-8001}:8001"
    - "${FILE_MANAGER_GRPC_PORT:-50052}:50052"
  environment:
    - GRPC_PORT=50052
```

---

## Phase 2: gRPC Server Implementation (Week 2)

### 2.1 Server Setup

**File:** `plugins/public/file-manager/src/grpc/server.py`

```python
import grpc
from grpc_reflection.v1alpha import reflection
from concurrent import futures
import structlog

from .generated import file_manager_pb2, file_manager_pb2_grpc
from .servicer import FileManagerServicer
from ..config import get_settings

logger = structlog.get_logger(__name__)

async def serve():
    settings = get_settings()
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
        ]
    )

    servicer = FileManagerServicer()
    file_manager_pb2_grpc.add_FileManagerServiceServicer_to_server(
        servicer, server
    )

    SERVICE_NAMES = (
        file_manager_pb2.DESCRIPTOR.services_by_name['FileManagerService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    listen_addr = f'[::]:{settings.grpc_port}'
    server.add_insecure_port(listen_addr)

    logger.info("gRPC server starting", port=settings.grpc_port)
    await server.start()
    await server.wait_for_termination()
```

### 2.2 Servicer Implementation

**File:** `plugins/public/file-manager/src/grpc/servicer.py`

Maps gRPC methods to existing services:

| gRPC Method | Maps To |
|-------------|---------|
| `UploadSimple` | `upload.router` logic |
| `Download` | `download.router` logic |
| `Extract` | `extraction.py` service |
| `GenerateThumbnail` | New thumbnail service |
| `GetMetadata` | `metadata.router` logic |
| `Delete` | `metadata.router` delete |
| `Health` | `health.router` logic |

### 2.3 Migrate Thumbnail Service

Copy from backend and adapt:
- `apps/backend/src/services/thumbnail_service.py`
- → `plugins/public/file-manager/src/services/thumbnail.py`

### 2.4 Migrate Extractors Framework

Copy from backend:
- `apps/backend/src/services/extractors/`
- → `plugins/public/file-manager/src/services/extractors/`

Remove backend-specific dependencies (Document model).

---

## Phase 3: gRPC Client in Backend (Week 3)

### 3.1 Create Client

**File:** `apps/backend/src/clients/file_manager_grpc.py`

```python
import grpc
from typing import AsyncIterator, Optional
import structlog

from ..core.config import get_settings

logger = structlog.get_logger(__name__)

class FileManagerGrpcClient:
    def __init__(self):
        settings = get_settings()
        self.channel = grpc.aio.insecure_channel(
            f'{settings.file_manager_grpc_host}:{settings.file_manager_grpc_port}'
        )
        # Import generated stubs
        from .generated import file_manager_pb2_grpc
        self.stub = file_manager_pb2_grpc.FileManagerServiceStub(self.channel)

    async def upload(self, file_data: bytes, user_id: str,
                     filename: str, content_type: str, **kwargs):
        from .generated import file_manager_pb2
        request = file_manager_pb2.UploadSimpleRequest(
            metadata=file_manager_pb2.UploadRequest(
                user_id=user_id,
                filename=filename,
                content_type=content_type,
                **kwargs
            ),
            file_data=file_data
        )
        return await self.stub.UploadSimple(request)

    async def download_stream(self, file_path: str) -> AsyncIterator[bytes]:
        from .generated import file_manager_pb2
        request = file_manager_pb2.DownloadRequest(file_path=file_path)
        async for response in self.stub.Download(request):
            if response.HasField('chunk'):
                yield response.chunk.data

    async def extract(self, file_path: str, force: bool = False):
        from .generated import file_manager_pb2
        request = file_manager_pb2.ExtractRequest(
            file_path=file_path,
            force=force
        )
        response = await self.stub.Extract(request)
        return response.result

    async def generate_thumbnail(self, file_path: str) -> bytes:
        from .generated import file_manager_pb2
        request = file_manager_pb2.ThumbnailRequest(file_path=file_path)
        response = await self.stub.GenerateThumbnail(request)
        return response.thumbnail

    async def close(self):
        await self.channel.close()
```

### 3.2 Add DI Provider

**File:** `apps/backend/src/core/dependencies.py` - Add:

```python
_file_manager_client: Optional["FileManagerGrpcClient"] = None

async def get_file_manager_client() -> "FileManagerGrpcClient":
    from ..clients.file_manager_grpc import FileManagerGrpcClient
    global _file_manager_client
    if _file_manager_client is None:
        _file_manager_client = FileManagerGrpcClient()
    return _file_manager_client
```

### 3.3 Update file_ingest.py

Add feature flag for gradual migration:

```python
async def extract_text(file_path: str) -> List[PageContent]:
    settings = get_settings()
    if settings.use_grpc_file_manager:
        client = await get_file_manager_client()
        result = await client.extract(file_path)
        return [PageContent(**p) for p in result.pages]
    else:
        # Legacy path
        return await extract_text_from_file(...)
```

---

## Phase 4: Cleanup & Testing (Week 4)

### 4.1 Remove Duplicate Services

After gRPC migration verified:
- Delete `apps/backend/src/services/minio_service.py`
- Delete `apps/backend/src/services/minio_storage.py`
- Update imports in remaining files

### 4.2 Integration Tests

```python
# tests/integration/test_file_manager_grpc.py
import pytest
import grpc

@pytest.mark.asyncio
async def test_upload_and_extract():
    async with grpc.aio.insecure_channel('localhost:50052') as channel:
        stub = FileManagerServiceStub(channel)

        # Upload
        response = await stub.UploadSimple(...)
        assert response.file_id

        # Extract
        result = await stub.Extract(ExtractRequest(
            file_path=response.metadata.minio_key
        ))
        assert result.result.total_pages > 0
```

### 4.3 Performance Benchmarks

```bash
ghz --insecure --proto ./proto/file_manager.proto \
    --call filemanager.FileManagerService.Extract \
    -d '{"file_path": "test.pdf"}' \
    -n 100 -c 10 \
    localhost:50052
```

### 4.4 Documentation

- Update README with gRPC endpoints
- Add proto documentation
- Update architecture diagrams

---

## Files to Create/Modify

### New Files (Plugin)

| File | Purpose |
|------|---------|
| `proto/file_manager.proto` | gRPC contract |
| `src/grpc/__init__.py` | Package init |
| `src/grpc/server.py` | gRPC server |
| `src/grpc/servicer.py` | Service implementation |
| `src/grpc/interceptors.py` | Logging, metrics |
| `src/grpc/generated/` | Auto-generated stubs |
| `src/services/thumbnail.py` | Migrated from backend |
| `src/services/extractors/` | Migrated framework |

### New Files (Backend)

| File | Purpose |
|------|---------|
| `src/clients/file_manager_grpc.py` | gRPC client |
| `src/clients/generated/` | Copied proto stubs |

### Modified Files

| File | Change |
|------|--------|
| `plugins/.../requirements.txt` | Add grpcio |
| `plugins/.../src/config.py` | Add grpc_port |
| `plugins/.../src/main.py` | Start gRPC server |
| `apps/backend/src/core/config.py` | Add gRPC settings |
| `apps/backend/src/core/dependencies.py` | Add client provider |
| `apps/backend/src/services/file_ingest.py` | Use gRPC client |
| `infra/docker-compose.yml` | Add port 50052 |
| `envs/.env.example` | Add gRPC env vars |

### Files to Delete (After Migration)

| File | Reason |
|------|--------|
| `apps/backend/src/services/minio_service.py` | Duplicate |
| `apps/backend/src/services/minio_storage.py` | Duplicate |

---

## Validation Commands

```bash
# 1. Proto compilation
cd plugins/public/file-manager
python -m grpc_tools.protoc -I./proto \
  --python_out=./src/grpc/generated \
  --grpc_python_out=./src/grpc/generated \
  ./proto/file_manager.proto

# 2. Start services
docker compose -f infra/docker-compose.yml up -d

# 3. Health check
grpcurl -plaintext localhost:50052 filemanager.FileManagerService/Health

# 4. Run tests
make test T=api TEST_ARGS="-k grpc"

# 5. Performance test
ghz --insecure --proto ./proto/file_manager.proto \
    --call filemanager.FileManagerService.Health \
    -n 1000 -c 50 \
    localhost:50052
```

---

## Rollback Plan

If issues arise:
1. Set `USE_GRPC_FILE_MANAGER=false` in environment
2. Backend falls back to direct service calls
3. gRPC server can remain running (no impact)
4. Investigate logs and fix before re-enabling
