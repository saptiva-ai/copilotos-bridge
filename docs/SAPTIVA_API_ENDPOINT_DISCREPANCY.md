# Saptiva API Endpoint Discrepancy - Investigation Report

**Date**: 2025-10-16  
**Status**: 🔴 **BLOCKER** - API endpoints return 404  
**Priority**: P0 - Blocks staging deployment

---

## Executive Summary

API validation revealed that the implemented Saptiva endpoints return **404 Not Found**. Investigation shows conflicting specifications between documentation and implementation.

### Quick Facts
- ✅ Credentials configured correctly (API key valid)
- ✅ API server responding (not 401/403/timeout)
- ❌ Endpoints return 404 (routes don't exist)
- ❓ Two different endpoint specifications in project

---

## Validation Results

### Test Execution
```bash
$ python tools/validate_saptiva_api.py

✓ Base URL: https://api.saptiva.com
✓ API Key: va-ai-Dn...FICE

✗ PDF Extraction: 404 Not Found
  Endpoint: /v1/tools/extractor-pdf
  Response: {"detail":"Not Found"}

✗ OCR Extraction: 404 Not Found  
  Endpoint: /v1/tools/ocr
  Response: {"detail":"Not Found"}
```

### HTTP Details
```
Request:
  POST https://api.saptiva.com/v1/tools/extractor-pdf
  Authorization: Bearer va-ai-***
  Content-Type: application/json
  Body: {"doc_type": "pdf", "document": "<base64>"}

Response:
  Status: 404 Not Found
  Body: {"detail":"Not Found"}
```

---

## Conflicting Specifications

### Specification #1: Integration Guide
**Source**: `docs/SAPTIVA_INTEGRATION_GUIDE.md`

**PDF Endpoint**:
```
POST https://api.saptiva.com/v1/extract/pdf
Content-Type: multipart/form-data

Body:
  - file: <PDF binary data>
  - filename: "document.pdf"
```

**OCR Endpoint**:
```
POST https://api.saptiva.com/v1/extract/image  
Content-Type: multipart/form-data

Body:
  - file: <Image binary data>
  - filename: "scan.png"
```

**Features**:
- Uses standard multipart/form-data
- Binary file upload (not base64)
- Filename in form field

---

### Specification #2: Current Implementation
**Source**: `apps/api/src/services/extractors/saptiva.py`

**PDF Endpoint**:
```python
# Line 143
url = f"{self.base_url}/v1/tools/extractor-pdf"

POST /v1/tools/extractor-pdf
Content-Type: application/json
Authorization: Bearer {api_key}

Body:
{
  "doc_type": "pdf",
  "document": "<base64_encoded_pdf>",
  "key": "<optional_api_key>"
}
```

**OCR Endpoint**:
```python
# Line 329
url = f"{self.base_url}/v1/tools/ocr"

POST /v1/tools/ocr
Content-Type: application/json

Body:
{
  "image": "<base64_encoded_image>",
  "mime_type": "image/png",
  "language": "spa"
}
```

**Features**:
- Uses JSON with base64 encoding
- Custom Tool style (obtener_texto_en_documento)
- Idempotency keys
- Spanish language hints

---

## Analysis

### Why the Current Implementation Was Chosen

Looking at comments in `saptiva.py` (lines 105-125):

```python
"""
Extract text from PDF using Saptiva Custom Tool 'obtener_texto_en_documento'.

API Specification (from Saptiva docs):
    Endpoint: POST {base_url}/v1/tools/extractor-pdf
    ...
"""
```

This suggests the implementation was based on Saptiva **Custom Tools** documentation, which uses:
- `/v1/tools/*` paths
- JSON with base64 encoding
- Custom tool naming convention

### Why Integration Guide Shows Different Endpoints

The Integration Guide shows `/v1/extract/*` which appears to be:
- Standard REST API pattern
- Multipart form data (typical for file uploads)
- Simpler API contract

### Which is Correct?

**Evidence points to Integration Guide being correct**:

1. **API responds with 404** - endpoints don't exist
2. **Integration Guide is official documentation** - likely more accurate
3. **Multipart/form-data is standard** - common pattern for file uploads
4. **Base URL uses `.com`** not `.ai` - matches guide

However, we need **official confirmation** from Saptiva team.

---

## Impact Assessment

### Immediate Impact
- ❌ **Cannot validate with real API** - All extraction calls fail with 404
- ❌ **Blocks staging deployment** - Cannot test in real environment
- ❌ **Integration tests cannot run** - Require working API
- ❌ **Performance benchmarks blocked** - Cannot compare providers

### Code Impact
- 📝 Need to refactor `saptiva.py` to use correct endpoints
- 📝 Change from JSON/base64 to multipart/form-data
- 📝 Update all 13 unit tests (currently passing with mocks)
- 📝 Update integration tests
- 📝 Update validation script

### Timeline Impact
- ⏱️ **Estimated refactor**: 2-4 hours
- ⏱️ **Testing**: 1-2 hours  
- ⏱️ **Validation**: 30 minutes
- **Total delay**: 3-6 hours once correct endpoints confirmed

---

## Recommended Actions

### Priority 1: Confirm Correct API Specification (TODAY)

**Action**: Contact Saptiva team or review official API documentation

**Questions to ask**:
1. What are the correct endpoint paths?
   - `/v1/extract/pdf` vs `/v1/tools/extractor-pdf`
2. What is the correct request format?
   - `multipart/form-data` vs `application/json` + base64
3. Are there authentication differences?
4. Are there rate limits or quotas?
5. Is there a sandbox/staging environment for testing?

**Contacts**:
- Saptiva Support: [contact info needed]
- API Documentation: [link needed]
- Slack/Email: [channel needed]

### Priority 2: Update Implementation (AFTER CONFIRMATION)

Once correct specification is confirmed:

1. **Update `saptiva.py`**:
   - Change endpoint URLs (lines 143, 329)
   - Implement multipart/form-data if needed
   - Remove base64 encoding if not required
   - Test with curl/httpx first

2. **Update Tests**:
   - Fix unit test mocks to match new API contract
   - Update integration tests
   - Re-run full test suite

3. **Update Documentation**:
   - Correct SAPTIVA_INTEGRATION_GUIDE.md if needed
   - Update validation script
   - Document actual API behavior

4. **Validate Again**:
   ```bash
   python tools/validate_saptiva_api.py
   ```

### Priority 3: Alternative Approaches (IF API NOT READY)

If Saptiva API endpoints are not yet available:

**Option A: Use Mock Server**
- Deploy mock Saptiva API for testing
- Implement expected responses
- Continue development/testing
- Timeline: +1 day

**Option B: Use Third-Party Only**
- Keep `EXTRACTOR_PROVIDER=third_party`
- Delay Saptiva integration to Phase 3
- Focus on other features
- Timeline: No delay

**Option C: Hybrid Approach**
- Use third_party for now
- Prepare Saptiva code with feature flag disabled
- Deploy when API ready
- Timeline: +2 hours (feature flag setup)

---

## Testing Strategy (After Fix)

### Step 1: Manual Curl Test
```bash
# Test with actual API
curl -X POST https://api.saptiva.com/v1/extract/pdf \
  -H "Authorization: Bearer $SAPTIVA_API_KEY" \
  -F "file=@test.pdf"
```

### Step 2: Run Validation Script
```bash
python tools/validate_saptiva_api.py
```

### Step 3: Unit Tests
```bash
pytest tests/unit/test_extractors.py::TestSaptivaExtractor -v
```

### Step 4: Integration Tests  
```bash
pytest tests/integration/test_saptiva_integration.py --marker=integration -v
```

### Step 5: Performance Benchmark
```bash
python tests/benchmarks/benchmark_extractors.py --compare --documents 10
```

---

## Current Workarounds

### For Development
- ✅ Unit tests pass (use mocks, don't hit real API)
- ✅ Code structure is sound (just endpoint/format wrong)
- ✅ Can continue with third_party extractor

### For Testing
- ❌ Cannot test Saptiva integration without correct endpoints
- ✅ Can test other features (file upload, UI, etc.)
- ✅ Can validate architecture/patterns

---

## Success Criteria (When Resolved)

- [ ] Receive official Saptiva API specification
- [ ] Update implementation to match specification
- [ ] All 36 unit tests passing
- [ ] Validation script shows 6/6 tests passing
- [ ] Integration tests can connect to real API
- [ ] Performance benchmarks can run comparisons
- [ ] Documentation updated with correct endpoints

---

## Timeline Estimate

| Scenario | Timeline |
|----------|----------|
| **Endpoints are correct** (documentation error) | +0 days |
| **Need simple endpoint change** | +0.5 days |
| **Need multipart/form-data refactor** | +1 day |
| **API not ready, use mock** | +2 days |
| **Delay to Phase 3** | +0 days (rescope) |

---

## Communication Plan

### Stakeholders to Notify
1. **Engineering Manager** - Blocks staging deployment
2. **Product Owner** - May affect Phase 2 timeline
3. **QA Team** - Cannot start integration testing
4. **Saptiva Technical Contact** - Need API clarification

### Status Updates
- **Daily**: Update in standup until resolved
- **Slack**: Post in #engineering when resolved
- **Documentation**: Update this file with findings

---

## Next Steps (Immediate)

1. ✅ Document findings (this file)
2. ⏳ Contact Saptiva team for API specification
3. ⏳ Test with Integration Guide endpoints manually (curl)
4. ⏳ Update implementation once confirmed
5. ⏳ Re-validate and update status

---

## Appendix: Code References

### Files Affected
- `apps/api/src/services/extractors/saptiva.py` (lines 143, 329)
- `tools/validate_saptiva_api.py` (endpoints)
- `tests/unit/test_extractors.py` (API mocks)
- `tests/integration/test_saptiva_integration.py` (live tests)
- `docs/SAPTIVA_INTEGRATION_GUIDE.md` (documentation)

### Environment Configuration
```bash
# Current configuration (working)
SAPTIVA_BASE_URL=https://api.saptiva.com
SAPTIVA_API_KEY=va-ai-***

# Possible alternatives to test
SAPTIVA_BASE_URL=https://api.saptiva.ai  # Different TLD?
SAPTIVA_BASE_URL=https://staging.saptiva.com  # Staging env?
```

---

**Last Updated**: 2025-10-16  
**Status**: 🔴 Awaiting Saptiva API Specification  
**Blocking**: Staging Deployment, Integration Testing, Performance Benchmarks

**Assigned To**: Backend Team  
**Next Review**: After Saptiva team response
