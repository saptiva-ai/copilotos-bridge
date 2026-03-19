---
id: "TASK-2026-01-16-2200__file-manager-grpc-migration"
title: "Migrate File Processing to file-manager Plugin via gRPC"
status: "BACKLOG"
phase: "Research"
scope_in:
  - "Create gRPC proto definitions for file operations"
  - "Implement gRPC server in file-manager plugin"
  - "Implement gRPC client in backend"
  - "Migrate extractors/ framework to plugin"
  - "Migrate thumbnail_service.py to plugin"
  - "Consolidate duplicate MinIO services"
  - "Update file_ingest.py to use gRPC client"
scope_out:
  - "Document model changes (stays in backend)"
  - "file_events.py SSE (replaced by gRPC streaming)"
  - "RAG integration (stays in backend)"
  - "MCP tool definitions (separate task)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
  rust_research: rust-acceleration-research.md
plan_phase: 1
validation_commands:
  - "python -m grpc_tools.protoc -I./proto --python_out=./src/grpc/generated --grpc_python_out=./src/grpc/generated ./proto/file_manager.proto"
  - "grpcurl -plaintext localhost:50052 filemanager.FileManagerService/Health"
  - "make test T=api TEST_ARGS='-k grpc'"
pr_files:
  - "plugins/public/file-manager/proto/file_manager.proto"
  - "plugins/public/file-manager/src/grpc/"
  - "apps/backend/src/clients/file_manager_grpc.py"
  - "apps/backend/src/core/dependencies.py"
test_status: "Not Started"
---

# Summary

- **Objective:** Migrate all file processing logic from backend to file-manager plugin using gRPC for inter-service communication. This enables better separation of concerns, streaming for large files, and bidirectional streaming for progress events.

- **Constraints:**
  - Must maintain backward compatibility during migration
  - Document model stays in backend (MongoDB coupling)
  - gRPC port 50052 (avoid conflict with Weaviate on 50051)
  - Max message size: 100MB for file uploads

# Key Benefits

1. **Streaming:** gRPC supports client/server/bidirectional streaming for large files
2. **Efficiency:** Binary protocol more efficient than JSON for file data
3. **Type Safety:** Protobuf contracts between services
4. **Progress Events:** Bidirectional streaming replaces SSE for file events

# Service Migration Matrix

| Service | Size | Can Migrate | Priority |
|---------|------|-------------|----------|
| `extractors/` framework | ~2K LOC | ✅ Full | High |
| `document_extraction.py` | 17.4 KB | ✅ Full | High |
| `thumbnail_service.py` | 10.5 KB | ✅ Full | Medium |
| `minio_service.py` | 10.6 KB | ✅ Consolidate | High |
| `minio_storage.py` | 20.2 KB | ✅ Consolidate | High |
| `file_ingest.py` | 24.4 KB | ⚠️ Partial | Low |

# Updates

- 2026-01-16 22:00 - Created task from exploration and planning session.
- 2026-01-16 22:00 - Comprehensive research completed on current state.
- 2026-01-16 22:00 - gRPC migration plan designed with 4-week timeline.
- 2026-01-16 22:30 - Added Rust acceleration research (PyO3, PDF Oxide, leptess).
  - PDF Oxide: 47.9x faster than PyMuPDF4LLM
  - Recommendation: Hybrid approach with PyO3 modules first
