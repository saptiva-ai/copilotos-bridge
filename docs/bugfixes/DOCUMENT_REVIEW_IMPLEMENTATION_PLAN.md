# Document Review System - Implementation Plan (Long-term)

**Date:** 2025-10-08
**Status:** API Container Crashing - System Unstable
**Goal:** Implement document upload + review system in a sustainable way

---

## 📊 Current System State

### ✅ What's Working
- **Frontend**:
  - Web container running (healthy)
  - Add Files button implemented with progress animations
  - Auto-logout on 401 implemented
  - Real API client integration (`apiClient.uploadDocument()`)

- **Backend Infrastructure**:
  - MongoDB (healthy)
  - Redis (healthy)
  - Review pipeline already implemented (LanguageTool + Saptiva)
  - Color auditor working

### ❌ What's Broken
- **API Container**: Crashing constantly due to import errors
  - Current error: `ImportError: cannot import name 'saptiva_client'`
  - Previous errors:
    - `ModuleNotFoundError: No module named 'src.core.redis_client'`
    - `ModuleNotFoundError: No module named 'src.core.auth'`

- **Root Causes**:
  1. Changed router prefixes without understanding full dependency chain
  2. Created new files with incorrect imports
  3. Modified working routers (documents.py, review.py) causing cascade failures
  4. Mixed naming conventions (redis_client vs redis_cache)

### 📝 Modified Files (Potential Issues)
```
M  apps/api/src/main.py                   # Added files router
M  apps/api/src/routers/documents.py      # Changed prefix, redis imports
M  apps/api/src/routers/review.py         # Changed prefix
M  apps/api/src/services/document_service.py  # New file, import issues
?? apps/api/src/core/auth.py              # New file (created today)
?? apps/api/src/routers/files.py          # New file (created today)
```

---

## 🎯 Implementation Strategy (3 Phases)

### **Phase 1: Stabilize System** (Priority: CRITICAL)
**Goal:** Get API container running again

#### Step 1.1: Restore Working State
- **Revert problematic changes** to routers:
  - `git checkout apps/api/src/routers/documents.py` (restore original prefix `/api/documents`)
  - `git checkout apps/api/src/routers/review.py` (restore original prefix `/api/review`)
- **Remove new files** temporarily:
  - Delete `apps/api/src/routers/files.py` (not ready yet)
  - Keep `apps/api/src/core/auth.py` (needed by other routers)
  - Delete `apps/api/src/services/document_service.py` (has import issues)

#### Step 1.2: Fix Remaining Import Issues
- **Verify all imports** resolve correctly:
  - Check `redis_cache` vs `redis_client` naming
  - Ensure `auth.py` exports are correct
  - Test import chain: `main.py` → routers → services

#### Step 1.3: Verify System Health
```bash
make rebuild-api
sleep 15
curl http://localhost:8001/api/health  # Should return {"status":"healthy"}
```

**Expected outcome:** API container running, all endpoints accessible

---

### **Phase 2: Implement Document Upload (Correctly)** (Priority: HIGH)
**Goal:** Enable PDF upload with authentication

#### Step 2.1: Understand Existing Architecture
- **Document existing upload flow**:
  ```
  POST /api/documents/upload
    ↓
  documents.py router (line 40)
    ↓
  Saves to /tmp/copilotos_documents/
    ↓
  Extracts text with pypdf
    ↓
  Caches in Redis (1 hour TTL)
    ↓
  Returns: {doc_id, filename, total_pages, status}
  ```

- **Authentication flow**:
  ```
  Frontend → apiClient.uploadDocument(file)
    ↓
  Interceptor adds: Authorization: Bearer <token>
    ↓
  Backend: get_current_user() validates JWT
    ↓
  Processes upload for authenticated user
  ```

#### Step 2.2: Test Upload Flow
- **Create test script**:
  ```bash
  # apps/api/tests/manual/test_upload.sh
  TOKEN=$(make get-token | grep "export TOKEN" | cut -d'"' -f2)
  curl -X POST http://localhost:8001/api/documents/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test_document.pdf"
  ```

- **Expected response**:
  ```json
  {
    "doc_id": "abc123...",
    "filename": "test_document.pdf",
    "total_pages": 5,
    "status": "ready"
  }
  ```

#### Step 2.3: Frontend Integration Test
- **Manual test steps**:
  1. Login as demo user
  2. Click "+" → "Add files"
  3. Upload PDF
  4. Verify progress bar 0% → 100%
  5. Verify green card with checkmark appears
  6. Check browser console for `doc_id` in response

**Expected outcome:** End-to-end upload working with auth

---

### **Phase 3: Add Artifact Serving (files endpoint)** (Priority: MEDIUM)
**Goal:** Serve uploaded documents and review reports securely

#### Step 3.1: Implement Files Router (Clean Implementation)
- **Create minimal `/files` router**:
  - Start with ONLY one endpoint: `GET /api/files/docs/{doc_id}/raw.{ext}`
  - Use existing `core.auth.get_current_user` (from Phase 1)
  - Implement path traversal protection
  - Verify ownership before serving

#### Step 3.2: Test Security
- **Security tests**:
  ```bash
  # Test 1: Valid request (should work)
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8001/api/files/docs/abc123/raw.pdf

  # Test 2: Path traversal (should fail)
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8001/api/files/docs/../../../etc/passwd

  # Test 3: Unauthorized (should fail with 401)
  curl http://localhost:8001/api/files/docs/abc123/raw.pdf
  ```

#### Step 3.3: Add Remaining Endpoints (Iteratively)
- Add one endpoint at a time, testing between each:
  1. `GET /api/files/docs/{doc_id}/derived/{filename}`
  2. `GET /api/files/reports/{doc_id}/report.json`
  3. `GET /api/files/reports/{doc_id}/annotated.pdf`

**Expected outcome:** Secure file serving with ownership validation

---

## 🔧 Technical Debt to Address

### 1. Import Naming Consistency
**Problem:** Mixed naming conventions cause confusion
- Some files use: `from ..core.redis_client import get_redis`
- Others use: `from ..core.redis_cache import get_redis_cache`

**Solution:** Pick ONE convention and document it:
```python
# Standard: Use redis_cache everywhere
from ..core.redis_cache import get_redis_cache

# Usage:
redis = await get_redis_cache()
await redis.client.set(key, value)
```

### 2. Router Prefix Convention
**Problem:** Inconsistent prefixes cause 404 errors
- Some routers: `APIRouter(prefix="/api/documents")` → Double prefix `/api/api/documents`
- Others: `APIRouter(prefix="/documents")` → Correct `/api/documents`

**Solution:** Document the pattern:
```python
# ✅ CORRECT (main.py adds /api globally)
router = APIRouter(prefix="/documents", tags=["documents"])

# ❌ WRONG (creates double prefix)
router = APIRouter(prefix="/api/documents", tags=["documents"])
```

### 3. Authentication Module Location
**Problem:** `core.auth` didn't exist, causing import failures

**Solution:** Keep `apps/api/src/core/auth.py` with:
```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency to get authenticated user from JWT token."""
    # Implementation already created
```

---

## 📋 Testing Checklist (Per Phase)

### Phase 1 Checklist
- [ ] API container starts without crashes
- [ ] `/api/health` returns 200 with `{"status":"healthy"}`
- [ ] All existing endpoints respond (chat, history, etc.)
- [ ] No import errors in logs

### Phase 2 Checklist
- [ ] User can login successfully
- [ ] `/api/documents/upload` accepts PDF with valid JWT
- [ ] Upload returns `doc_id` and `status: "ready"`
- [ ] Frontend shows progress bar 0% → 100%
- [ ] Green card appears after successful upload
- [ ] 401 if no token (triggers auto-logout)

### Phase 3 Checklist
- [ ] `/api/files/docs/{doc_id}/raw.pdf` serves file to owner
- [ ] 403 if requesting someone else's document
- [ ] Path traversal attacks blocked
- [ ] Download works in browser

---

## 🚨 Risk Mitigation

### Risk 1: Breaking Existing Features
**Mitigation:**
- Test existing endpoints after each change
- Run `make test-api` before committing
- Keep git history clean (one logical change per commit)

### Risk 2: Auth Token Not Working
**Mitigation:**
- Test with `make get-token` first
- Verify token in browser DevTools: `localStorage.getItem('copilotos-auth-state')`
- Check token expiration: look for `expiresAt` in localStorage

### Risk 3: Import Errors Cascade
**Mitigation:**
- Use `docker logs copilotos-api` immediately after changes
- If ANY import error appears, stop and fix before continuing
- Don't stack multiple changes without testing

---

## 📚 Documentation Updates Needed

1. **README.md** (Section: Document Review)
   - Update endpoint URLs to `/api/documents/upload` (not `/api/api/...`)
   - Add authentication requirement
   - Update curl examples with JWT token

2. **API Docs** (Auto-generated at `/docs`)
   - Ensure `/api/documents/upload` appears correctly
   - Mark endpoints that require authentication

3. **Frontend Integration Guide**
   - Document `apiClient.uploadDocument()` usage
   - Explain auto-logout on 401
   - Show how to check upload progress

---

## 🎯 Success Criteria

### Minimum Viable Product (MVP)
- [ ] User can login
- [ ] User can upload PDF (<30MB)
- [ ] Upload shows progress
- [ ] Upload completes successfully
- [ ] API container stays healthy

### Full Feature Complete
- [ ] All Phase 3 file endpoints working
- [ ] Auto-logout on token expiration
- [ ] Path traversal protection verified
- [ ] Tests passing (unit + E2E)
- [ ] Documentation updated

---

## 🔄 Next Steps (After Approval)

1. **Execute Phase 1** (Stabilization)
   - Revert problematic changes
   - Fix import issues
   - Verify API health

2. **Execute Phase 2** (Upload Flow)
   - Test existing upload endpoint
   - Integrate with frontend
   - Verify end-to-end

3. **Execute Phase 3** (File Serving)
   - Implement `/files` router
   - Add security tests
   - Complete integration

---

**Estimated Time:**
- Phase 1: 30 minutes
- Phase 2: 1 hour
- Phase 3: 2 hours
- **Total: ~3.5 hours** for stable, tested implementation

**Key Principle:** Test after each step. Don't move forward if something breaks.
