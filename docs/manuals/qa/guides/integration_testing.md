# Plan de Testing de Integración - Plugin-First Architecture

## Índice
1. [Objetivo](#objetivo)
2. [Arquitectura a Testear](#arquitectura-a-testear)
3. [Niveles de Testing](#niveles-de-testing)
4. [Tests de Integración Críticos](#tests-de-integración-críticos)
5. [Tests de Comunicación Inter-Plugin](#tests-de-comunicación-inter-plugin)
6. [Tests de Resiliencia](#tests-de-resiliencia)
7. [Tests de Performance](#tests-de-performance)
8. [Automatización](#automatización)

---

## Objetivo

Validar la **integración correcta** entre los componentes de la arquitectura Plugin-First:
- **Backend Core** (Port 8000) - Kernel ligero
- **File Manager Plugin** (Port 8001) - Operaciones de archivos
- **Capital414 Plugin** (Port 8002) - Auditorías COPILOTO_414
- **Infraestructura** - MongoDB, Redis, MinIO, LanguageTool

---

## Arquitectura a Testear

```
Frontend (3000)
    ↓ HTTP
Backend Core (8000) - Orchestration
    ↓ HTTP Client          ↓ MCP Protocol
File Manager (8001)     Capital414 (8002)
    ↓                       ↓
MinIO/Redis         File Manager (HTTP Client)
```

**Puntos críticos de integración:**
1. Backend Core → File Manager (HTTP Client)
2. Backend Core → Capital414 (MCP Protocol)
3. Capital414 → File Manager (HTTP Client)
4. Todos → Infraestructura (MongoDB, Redis, MinIO)

---

## Niveles de Testing

### Nivel 1: Tests Unitarios (fuera de scope)
- Cada servicio tiene sus propios tests unitarios
- Backend: `make test-api`
- Frontend: `make test-web`

### Nivel 2: Tests de Integración de Componente
- Backend Core + MongoDB/Redis
- File Manager + MinIO/Redis
- Capital414 + File Manager + LanguageTool

### Nivel 3: Tests de Integración Inter-Plugin (ESTE DOCUMENTO)
- Backend Core → File Manager → MinIO
- Backend Core → Capital414 → File Manager → MinIO
- Frontend → Backend Core → Plugins → Infraestructura

### Nivel 4: Tests E2E
- User journey completo desde UI

---

## Tests de Integración Críticos

### Test Suite 1: Backend Core → File Manager

#### Test 1.1: Upload delegation (Backend → FileManager → MinIO)
```bash
#!/bin/bash
# tests/integration/test_backend_to_filemanager_upload.sh

echo "🧪 Test 1.1: Backend delegates upload to File Manager"

# 1. Login to get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234"}' | jq -r '.access_token')

# 2. Create test file
echo "Integration test content" > /tmp/integration_test.txt

# 3. Upload via Backend API (should delegate to File Manager)
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/integration_test.txt" \
  -F "session_id=integration_test")

echo $UPLOAD_RESPONSE | jq

# 4. Assertions
MINIO_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.minio_key')
if [ -z "$MINIO_KEY" ]; then
  echo "❌ FAIL: No minio_key in response"
  exit 1
fi

# 5. Verify file exists in MinIO via File Manager
FILE_CONTENT=$(curl -s "http://localhost:8001/download/$MINIO_KEY")
if [[ "$FILE_CONTENT" != *"Integration test content"* ]]; then
  echo "❌ FAIL: File content mismatch"
  exit 1
fi

echo "✅ PASS: Backend → File Manager → MinIO upload works"
```

**Expected behavior:**
- Backend Core receives upload request
- Backend Core delegates to File Manager via `FileManagerClient.upload_file()`
- File Manager saves to MinIO
- Backend receives `minio_key` from File Manager
- File is downloadable from File Manager

**Failure scenarios to test:**
- File Manager is down → Backend returns 503 Service Unavailable
- MinIO is down → File Manager returns error, Backend propagates
- Invalid file type → Validation error before reaching File Manager

---

#### Test 1.2: Download delegation (Backend → FileManager → MinIO)
```bash
#!/bin/bash
# tests/integration/test_backend_to_filemanager_download.sh

echo "🧪 Test 1.2: Backend delegates download to File Manager"

# Prerequisite: MINIO_KEY from Test 1.1
MINIO_KEY="demo/integration_test/test.txt"

# Download via Backend API
curl -s "http://localhost:8000/api/files/download/$MINIO_KEY" \
  -H "Authorization: Bearer $TOKEN" \
  -o /tmp/downloaded_file.txt

# Verify content
if grep -q "Integration test content" /tmp/downloaded_file.txt; then
  echo "✅ PASS: Backend → File Manager → MinIO download works"
else
  echo "❌ FAIL: Downloaded content mismatch"
  exit 1
fi
```

---

#### Test 1.3: Extract text delegation
```bash
#!/bin/bash
# tests/integration/test_backend_to_filemanager_extract.sh

echo "🧪 Test 1.3: Backend delegates text extraction to File Manager"

# Upload PDF via Backend
PDF_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/sample.pdf" \
  -F "session_id=extract_test")

DOC_ID=$(echo $PDF_RESPONSE | jq -r '.file_id')

# Request extraction via Backend (should delegate to File Manager)
EXTRACT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/files/$DOC_ID/extract" \
  -H "Authorization: Bearer $TOKEN")

EXTRACTED_TEXT=$(echo $EXTRACT_RESPONSE | jq -r '.extracted_text')

if [ -n "$EXTRACTED_TEXT" ]; then
  echo "✅ PASS: Text extraction works via delegation"
else
  echo "❌ FAIL: No text extracted"
  exit 1
fi
```

---

### Test Suite 2: Backend Core → Capital414 (MCP Protocol)

#### Test 2.1: MCP tool invocation (Backend → Capital414 → FileManager)
```bash
#!/bin/bash
# tests/integration/test_backend_to_capital414_mcp.sh

echo "🧪 Test 2.1: Backend invokes Capital414 audit via MCP"

# 1. Upload PDF to File Manager first
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8001/upload \
  -F "file=@tests/fixtures/copiloto414_compliant.pdf" \
  -F "user_id=audit_test" \
  -F "session_id=mcp_test")

MINIO_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.minio_key')

# 2. Invoke audit via Backend Chat API (should use MCP to Capital414)
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Auditar archivo: copiloto414_compliant.pdf\",
    \"session_id\": \"mcp_test\",
    \"file_ids\": [\"$MINIO_KEY\"]
  }")

echo $CHAT_RESPONSE | jq

# 3. Assertions
TOOL_INVOCATIONS=$(echo $CHAT_RESPONSE | jq '.metadata.tool_invocations')
if [ "$TOOL_INVOCATIONS" == "null" ]; then
  echo "❌ FAIL: No tool_invocations in response"
  exit 1
fi

AUDIT_RESULT=$(echo $CHAT_RESPONSE | jq -r '.metadata.tool_invocations[0].result')
if [[ "$AUDIT_RESULT" == *"audit_document_full"* ]]; then
  echo "✅ PASS: Backend → Capital414 MCP invocation works"
else
  echo "❌ FAIL: MCP tool not invoked"
  exit 1
fi
```

**Expected behavior:**
- Backend receives chat message "Auditar archivo:..."
- Backend detects audit command
- Backend calls `MCPClient.call_tool("audit_document_full", {...})`
- Capital414 receives MCP invocation
- Capital414 downloads PDF from File Manager using HTTP Client
- Capital414 executes ValidationCoordinator with 8 auditors
- Capital414 returns audit report via MCP
- Backend injects `tool_invocations` metadata
- Frontend receives audit result

---

#### Test 2.2: Capital414 fallback strategies
```bash
#!/bin/bash
# tests/integration/test_capital414_fallback.sh

echo "🧪 Test 2.2: Capital414 uses fallback when file_path and minio_key provided"

# Call Capital414 directly with both params
AUDIT_RESPONSE=$(curl -s -X POST http://localhost:8002/mcp/tools/audit_document_full \
  -H "Content-Type: application/json" \
  -d "{
    \"minio_key\": \"$MINIO_KEY\",
    \"file_path\": \"/tmp/legacy.pdf\",
    \"policy_id\": \"auto\"
  }")

# Should prefer minio_key over file_path
STATUS=$(echo $AUDIT_RESPONSE | jq -r '.status')
if [ "$STATUS" == "completed" ]; then
  echo "✅ PASS: Capital414 fallback strategy works"
else
  echo "❌ FAIL: Audit failed"
  exit 1
fi
```

---

### Test Suite 3: Capital414 → File Manager (HTTP Client)

#### Test 3.1: Direct download from Capital414
```python
# tests/integration/test_capital414_to_filemanager.py
import pytest
import httpx
from plugins.capital414.src.clients.file_manager import FileManagerClient

@pytest.mark.asyncio
async def test_capital414_downloads_from_filemanager():
    """Test that Capital414 can download PDFs from File Manager."""
    # 1. Upload PDF to File Manager
    async with httpx.AsyncClient() as client:
        files = {"file": open("tests/fixtures/sample.pdf", "rb")}
        data = {"user_id": "capital414_test", "session_id": "test1"}

        upload_resp = await client.post(
            "http://file-manager:8001/upload",
            files=files,
            data=data
        )
        assert upload_resp.status_code == 200
        minio_key = upload_resp.json()["minio_key"]

    # 2. Capital414 downloads via FileManagerClient
    fm_client = FileManagerClient(base_url="http://file-manager:8001")
    pdf_path = await fm_client.download_to_temp(minio_key)

    # 3. Assertions
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")

    # 4. Cleanup
    os.remove(pdf_path)
```

---

### Test Suite 4: Persistencia Distribuida

#### Test 4.1: Cache de extracción en Redis (File Manager)
```bash
#!/bin/bash
# tests/integration/test_filemanager_redis_cache.sh

echo "🧪 Test 4.1: File Manager caches extracted text in Redis"

# 1. Upload PDF
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8001/upload \
  -F "file=@tests/fixtures/sample.pdf" \
  -F "user_id=cache_test")

MINIO_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.minio_key')

# 2. First extraction (should cache in Redis)
time curl -s -X POST "http://localhost:8001/extract/$MINIO_KEY" > /tmp/extract1.json

# 3. Second extraction (should hit cache)
time curl -s -X POST "http://localhost:8001/extract/$MINIO_KEY" > /tmp/extract2.json

# 4. Verify cache hit in Redis
docker compose -f infra/docker-compose.yml exec redis redis-cli GET "extract:$MINIO_KEY"

# 5. Assertions
EXTRACT1=$(cat /tmp/extract1.json | jq -r '.extracted_text')
EXTRACT2=$(cat /tmp/extract2.json | jq -r '.extracted_text')

if [ "$EXTRACT1" == "$EXTRACT2" ]; then
  echo "✅ PASS: Redis cache works"
else
  echo "❌ FAIL: Cache mismatch"
  exit 1
fi
```

---

#### Test 4.2: Audit reports en MongoDB (Capital414)
```python
# tests/integration/test_capital414_mongodb_persistence.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

@pytest.mark.asyncio
async def test_audit_reports_persisted_in_mongodb():
    """Verify Capital414 saves audit reports to MongoDB."""
    # 1. Run audit via Capital414
    # (Código similar a Test 2.1)

    # 2. Query MongoDB directly
    mongo_client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    db = mongo_client["capital414_chat"]
    reports_collection = db["validation_reports"]

    # 3. Find recent audit report
    report = await reports_collection.find_one(
        {"minio_key": minio_key},
        sort=[("created_at", -1)]
    )

    # 4. Assertions
    assert report is not None
    assert report["status"] == "completed"
    assert "findings" in report
    assert len(report["findings"]) > 0

    # 5. Verify report structure
    assert "disclaimer_auditor" in report["findings"]
    assert "format_auditor" in report["findings"]
```

---

## Tests de Comunicación Inter-Plugin

### Test IPC-1: Flujo completo de auditoría
```bash
#!/bin/bash
# tests/integration/test_full_audit_flow.sh

echo "🧪 Test IPC-1: Full audit flow (Frontend → Backend → Capital414 → FileManager)"

# 1. Upload PDF via Backend (Backend → FileManager)
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/copiloto414_compliant.pdf" \
  -F "session_id=full_flow_test")

FILE_ID=$(echo $UPLOAD_RESPONSE | jq -r '.file_id')

# 2. Send audit command via Chat (Backend → Capital414 via MCP)
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Auditar archivo: copiloto414_compliant.pdf\",
    \"session_id\": \"full_flow_test\",
    \"file_ids\": [\"$FILE_ID\"]
  }")

# 3. Extract audit result
ARTIFACT_ID=$(echo $CHAT_RESPONSE | jq -r '.metadata.tool_invocations[0].result.id')

# 4. Fetch artifact (audit report)
ARTIFACT=$(curl -s "http://localhost:8000/api/artifacts/$ARTIFACT_ID" \
  -H "Authorization: Bearer $TOKEN")

echo $ARTIFACT | jq

# 5. Assertions
EXECUTIVE_SUMMARY=$(echo $ARTIFACT | jq -r '.content')
if [[ "$EXECUTIVE_SUMMARY" == *"Auditoría completada"* ]]; then
  echo "✅ PASS: Full audit flow works end-to-end"
else
  echo "❌ FAIL: Audit flow incomplete"
  exit 1
fi
```

**Expected call chain:**
1. Frontend → Backend Core (`POST /api/files/upload`)
2. Backend Core → File Manager (`POST /upload`)
3. File Manager → MinIO (upload binary)
4. Frontend → Backend Core (`POST /api/chat` with "Auditar archivo")
5. Backend Core → Capital414 via MCP (`call_tool("audit_document_full")`)
6. Capital414 → File Manager (`GET /download/{minio_key}`)
7. File Manager → MinIO (download binary)
8. Capital414 → LanguageTool (grammar check)
9. Capital414 → MongoDB (save report)
10. Capital414 → Backend Core (return via MCP)
11. Backend Core → Frontend (return chat response)

---

### Test IPC-2: Concurrent requests
```python
# tests/integration/test_concurrent_requests.py
import asyncio
import httpx

async def upload_file(client, file_path, user_id):
    """Upload file via Backend Core."""
    files = {"file": open(file_path, "rb")}
    data = {"user_id": user_id, "session_id": "concurrent_test"}
    resp = await client.post(
        "http://backend:8000/api/files/upload",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    return resp.json()

async def test_concurrent_uploads():
    """Test 10 concurrent uploads (Backend → FileManager stress test)."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = [
            upload_file(client, "tests/fixtures/sample.pdf", f"user_{i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert all(isinstance(r, dict) for r in results)
        assert all("minio_key" in r for r in results)

        print(f"✅ PASS: {len(results)} concurrent uploads succeeded")
```

---

## Tests de Resiliencia

### Test R-1: File Manager restart durante upload
```bash
#!/bin/bash
# tests/integration/test_filemanager_restart_resilience.sh

echo "🧪 Test R-1: File Manager restart resilience"

# 1. Start upload en background
(curl -X POST http://localhost:8000/api/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/large_file.pdf" \
  -F "session_id=resilience_test" > /tmp/upload_result.json) &

UPLOAD_PID=$!

# 2. Wait 2 seconds and restart File Manager
sleep 2
docker compose -f infra/docker-compose.yml restart file-manager

# 3. Wait for upload to finish
wait $UPLOAD_PID
UPLOAD_EXIT_CODE=$?

# 4. Check result
if [ $UPLOAD_EXIT_CODE -eq 0 ]; then
  echo "❌ FAIL: Upload should have failed during restart"
  exit 1
fi

# 5. Verify File Manager is healthy again
sleep 10
HEALTH=$(curl -s http://localhost:8001/health | jq -r '.status')

if [ "$HEALTH" == "healthy" ]; then
  echo "✅ PASS: File Manager recovered after restart"
else
  echo "❌ FAIL: File Manager not healthy"
  exit 1
fi
```

---

### Test R-2: Capital414 graceful degradation
```bash
#!/bin/bash
# tests/integration/test_capital414_degradation.sh

echo "🧪 Test R-2: Capital414 down - Backend handles gracefully"

# 1. Stop Capital414
docker compose -f infra/docker-compose.yml stop file-auditor

# 2. Try audit command via Backend
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Auditar archivo: test.pdf\",
    \"session_id\": \"degradation_test\"
  }")

# 3. Backend should respond with error but not crash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/health")

if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ PASS: Backend survived Capital414 being down"
else
  echo "❌ FAIL: Backend crashed"
  exit 1
fi

# 4. Restart Capital414
docker compose -f infra/docker-compose.yml start file-auditor
```

---

### Test R-3: MinIO outage (File Manager handles gracefully)
```bash
#!/bin/bash
# tests/integration/test_minio_outage.sh

echo "🧪 Test R-3: MinIO down - File Manager returns proper error"

# 1. Stop MinIO
docker compose -f infra/docker-compose.yml stop minio

# 2. Try upload via File Manager
UPLOAD_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST http://localhost:8001/upload \
  -F "file=@tests/fixtures/sample.pdf" \
  -F "user_id=outage_test")

HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | grep HTTP_CODE | cut -d: -f2)

# 3. Should return 503 Service Unavailable
if [ "$HTTP_CODE" == "503" ]; then
  echo "✅ PASS: File Manager returns 503 when MinIO is down"
else
  echo "❌ FAIL: Unexpected HTTP code: $HTTP_CODE"
  exit 1
fi

# 4. Restart MinIO
docker compose -f infra/docker-compose.yml start minio
sleep 10

# 5. Verify upload works again
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8001/upload \
  -F "file=@tests/fixtures/sample.pdf" \
  -F "user_id=outage_test")

MINIO_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.minio_key')

if [ -n "$MINIO_KEY" ]; then
  echo "✅ PASS: File Manager recovered after MinIO restart"
else
  echo "❌ FAIL: Upload still failing"
  exit 1
fi
```

---

## Tests de Performance

### Test P-1: Throughput de File Manager
```bash
#!/bin/bash
# tests/integration/test_filemanager_throughput.sh

echo "🧪 Test P-1: File Manager throughput test"

# Install hey if not available
if ! command -v hey &> /dev/null; then
  echo "Installing hey..."
  go install github.com/rakyll/hey@latest
fi

# Create test file (1MB)
dd if=/dev/urandom of=/tmp/perf_test_1mb.bin bs=1M count=1

# Run throughput test (100 requests, 10 concurrent)
hey -n 100 -c 10 -m POST \
  -T "multipart/form-data; boundary=----WebKitFormBoundary" \
  -D /tmp/perf_test_1mb.bin \
  "http://localhost:8001/upload?user_id=perf_test&session_id=perf1" \
  > /tmp/hey_results.txt

# Parse results
REQUESTS_PER_SEC=$(grep "Requests/sec" /tmp/hey_results.txt | awk '{print $2}')
MEAN_LATENCY=$(grep "Average:" /tmp/hey_results.txt | awk '{print $2}')

echo "Throughput: $REQUESTS_PER_SEC req/sec"
echo "Mean latency: $MEAN_LATENCY"

# Assertions (adjust thresholds based on environment)
if (( $(echo "$REQUESTS_PER_SEC > 10" | bc -l) )); then
  echo "✅ PASS: Throughput acceptable (>10 req/sec)"
else
  echo "⚠️  WARNING: Throughput low (<10 req/sec)"
fi
```

---

### Test P-2: Audit latency (Backend → Capital414)
```python
# tests/integration/test_audit_latency.py
import pytest
import time
import httpx

@pytest.mark.asyncio
async def test_audit_latency_under_30s():
    """Audit should complete in <30s for standard PDF."""
    start = time.time()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Upload PDF
        files = {"file": open("tests/fixtures/sample_10pages.pdf", "rb")}
        upload_resp = await client.post(
            "http://backend:8000/api/files/upload",
            files=files,
            data={"session_id": "latency_test"},
            headers={"Authorization": f"Bearer {TOKEN}"}
        )
        minio_key = upload_resp.json()["minio_key"]

        # Trigger audit
        chat_resp = await client.post(
            "http://backend:8000/api/chat",
            json={
                "message": "Auditar archivo: sample_10pages.pdf",
                "session_id": "latency_test",
                "file_ids": [minio_key]
            },
            headers={"Authorization": f"Bearer {TOKEN}"}
        )

    end = time.time()
    latency = end - start

    assert latency < 30, f"Audit took {latency}s (expected <30s)"
    print(f"✅ PASS: Audit completed in {latency:.2f}s")
```

---

## Automatización

### Script de ejecución completa
```bash
#!/bin/bash
# tests/integration/run_all_integration_tests.sh

set -e  # Exit on first failure

echo "🚀 Running Integration Test Suite for Plugin-First Architecture"
echo "================================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED_TESTS=()
PASSED_TESTS=()

run_test() {
  TEST_NAME=$1
  TEST_SCRIPT=$2

  echo -e "\n${YELLOW}▶ Running: $TEST_NAME${NC}"

  if bash "$TEST_SCRIPT"; then
    echo -e "${GREEN}✅ PASSED: $TEST_NAME${NC}"
    PASSED_TESTS+=("$TEST_NAME")
  else
    echo -e "${RED}❌ FAILED: $TEST_NAME${NC}"
    FAILED_TESTS+=("$TEST_NAME")
  fi
}

# Prerequisites
echo "📋 Prerequisites check..."
if ! curl -s http://localhost:8000/api/health > /dev/null; then
  echo "❌ Backend not running. Run 'make dev' first."
  exit 1
fi

# Get auth token
export TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
  echo "❌ Failed to get auth token. Check demo user exists."
  exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Run test suites
run_test "Backend → FileManager Upload" "tests/integration/test_backend_to_filemanager_upload.sh"
run_test "Backend → FileManager Download" "tests/integration/test_backend_to_filemanager_download.sh"
run_test "Backend → FileManager Extract" "tests/integration/test_backend_to_filemanager_extract.sh"
run_test "Backend → Capital414 MCP" "tests/integration/test_backend_to_capital414_mcp.sh"
run_test "Full Audit Flow" "tests/integration/test_full_audit_flow.sh"
run_test "FileManager Redis Cache" "tests/integration/test_filemanager_redis_cache.sh"

# Resilience tests
run_test "FileManager Restart Resilience" "tests/integration/test_filemanager_restart_resilience.sh"
run_test "Capital414 Degradation" "tests/integration/test_capital414_degradation.sh"
run_test "MinIO Outage Handling" "tests/integration/test_minio_outage.sh"

# Performance tests (optional)
if [ "$RUN_PERF_TESTS" == "true" ]; then
  run_test "FileManager Throughput" "tests/integration/test_filemanager_throughput.sh"
fi

# Summary
echo ""
echo "================================================================"
echo "📊 Test Summary"
echo "================================================================"
echo -e "${GREEN}Passed: ${#PASSED_TESTS[@]}${NC}"
echo -e "${RED}Failed: ${#FAILED_TESTS[@]}${NC}"

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
  echo ""
  echo -e "${RED}Failed tests:${NC}"
  for test in "${FAILED_TESTS[@]}"; do
    echo "  - $test"
  done
  exit 1
else
  echo ""
  echo -e "${GREEN}🎉 All integration tests passed!${NC}"
  exit 0
fi
```

---

### Makefile targets
```makefile
# Add to existing Makefile

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	bash tests/integration/run_all_integration_tests.sh

.PHONY: test-integration-quick
test-integration-quick: ## Run quick integration tests (no resilience/perf)
	@echo "⚡ Running quick integration tests..."
	bash tests/integration/test_backend_to_filemanager_upload.sh
	bash tests/integration/test_backend_to_capital414_mcp.sh
	bash tests/integration/test_full_audit_flow.sh

.PHONY: test-integration-resilience
test-integration-resilience: ## Run resilience tests only
	@echo "🛡️  Running resilience tests..."
	bash tests/integration/test_filemanager_restart_resilience.sh
	bash tests/integration/test_capital414_degradation.sh
	bash tests/integration/test_minio_outage.sh

.PHONY: test-integration-perf
test-integration-perf: ## Run performance tests only
	@echo "⚡ Running performance tests..."
	RUN_PERF_TESTS=true bash tests/integration/test_filemanager_throughput.sh
	pytest tests/integration/test_audit_latency.py -v
```

---

## CI/CD Integration

### GitHub Actions workflow
```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [main, refactor/*]
  pull_request:
    branches: [main]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: |
          make dev
          sleep 30  # Wait for services to be healthy

      - name: Create demo user
        run: make create-demo-user

      - name: Run integration tests
        run: make test-integration-quick

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: integration-test-results
          path: /tmp/*.json

      - name: Stop services
        if: always()
        run: make stop
```

---

## Checklist de Testing Completo

### Pre-merge Checklist
- [ ] Todos los smoke tests pasan (`make health`)
- [ ] Test 1.1: Backend → FileManager Upload ✅
- [ ] Test 1.2: Backend → FileManager Download ✅
- [ ] Test 1.3: Backend → FileManager Extract ✅
- [ ] Test 2.1: Backend → Capital414 MCP ✅
- [ ] Test 2.2: Capital414 fallback strategies ✅
- [ ] Test 3.1: Capital414 → FileManager HTTP Client ✅
- [ ] Test 4.1: Redis cache (FileManager) ✅
- [ ] Test 4.2: MongoDB persistence (Capital414) ✅
- [ ] Test IPC-1: Full audit flow ✅
- [ ] Test IPC-2: Concurrent requests ✅
- [ ] Test R-1: FileManager restart resilience ✅
- [ ] Test R-2: Capital414 graceful degradation ✅
- [ ] Test R-3: MinIO outage handling ✅

### Optional (Performance)
- [ ] Test P-1: FileManager throughput >10 req/sec
- [ ] Test P-2: Audit latency <30s for 10-page PDF

---

## Troubleshooting

### Debug de tests fallidos
```bash
# Logs de todos los servicios
make logs

# Logs específicos
make logs S=backend
make logs S=file-manager
make logs S=file-auditor

# Health check individual
curl -s http://localhost:8000/api/health | jq
curl -s http://localhost:8001/health | jq
curl -s http://localhost:8002/health | jq

# Verificar conectividad entre servicios
docker compose -f infra/docker-compose.yml exec backend ping file-manager
docker compose -f infra/docker-compose.yml exec file-auditor ping file-manager

# Verificar Redis
docker compose -f infra/docker-compose.yml exec redis redis-cli ping
docker compose -f infra/docker-compose.yml exec redis redis-cli KEYS '*'

# Verificar MinIO
docker compose -f infra/docker-compose.yml exec minio mc ls local/documents
```

---

## Métricas de Éxito

**Definición de "Integration Tests Passing":**
- ✅ 100% de tests críticos (Suite 1-4) pasan
- ✅ 80% de tests de resiliencia pasan
- ✅ Performance aceptable (P-1 >10 req/sec, P-2 <30s)
- ✅ No errores críticos en logs
- ✅ Todos los servicios healthy después de tests

**Antes de merge a `main`:**
- [ ] `make test-integration` retorna exit code 0
- [ ] Manual smoke test en UI (login → upload → audit → canvas)
- [ ] Review de logs (no errores críticos)
- [ ] Performance baseline documentado
