# Validation: File Processing gRPC Migration

## Status: Not Started

---

## Validation Checklist

### Phase 1: Infrastructure

- [ ] Proto file compiles without errors
- [ ] Generated Python stubs are valid
- [ ] gRPC server starts on port 50052
- [ ] grpcurl Health check returns OK
- [ ] Docker compose exposes port 50052

### Phase 2: Core Services

- [ ] Upload via gRPC works (unary)
- [ ] Upload via gRPC works (streaming)
- [ ] Download via gRPC works (streaming)
- [ ] Extract via gRPC works
- [ ] Thumbnail generation works
- [ ] Metadata retrieval works
- [ ] Delete operation works

### Phase 3: Backend Integration

- [ ] Backend gRPC client connects
- [ ] file_ingest.py uses gRPC client
- [ ] Feature flag works (enable/disable)
- [ ] Backward compatibility maintained
- [ ] MCP tools work with gRPC

### Phase 4: Cleanup

- [ ] minio_service.py removed
- [ ] minio_storage.py removed
- [ ] No import errors after removal
- [ ] All tests pass
- [ ] Performance acceptable (< 50ms latency)

---

## Test Commands

```bash
# Proto compilation
cd plugins/public/file-manager
python -m grpc_tools.protoc -I./proto \
  --python_out=./src/grpc/generated \
  --grpc_python_out=./src/grpc/generated \
  ./proto/file_manager.proto

# Health check
grpcurl -plaintext localhost:50052 filemanager.FileManagerService/Health

# Unit tests
make test T=api TEST_ARGS="-k grpc"

# Integration tests
make test T=api TEST_ARGS="-k file_manager"

# Performance benchmark
ghz --insecure --proto ./proto/file_manager.proto \
    --call filemanager.FileManagerService.Extract \
    -d '{"file_path": "test.pdf"}' \
    -n 100 -c 10 \
    localhost:50052
```

---

## Acceptance Criteria

1. **Functional:** All file operations work via gRPC
2. **Performance:** < 50ms latency for metadata, < 500ms for extraction
3. **Reliability:** No regressions in existing functionality
4. **Observability:** gRPC calls logged with structlog

---

## Validation Log

_To be filled during implementation_

| Date | Phase | Result | Notes |
|------|-------|--------|-------|
| - | - | - | - |
