# Text Extraction Inventory

## Overview

This document inventories all code that extracts text from PDFs and images using third-party libraries. The goal is to prepare migration to Saptiva Native Tools.

**Current Architecture:**
- PDFs → `pypdf` (PdfReader)
- Images → `pytesseract` (Tesseract OCR)
- Image preprocessing → `Pillow` (PIL)
- HEIC support → `pillow-heif`

**Migration Target:**
- All extraction → Saptiva Native Tools API
- Feature flag controlled: `EXTRACTOR_PROVIDER=third_party|saptiva`

---

## Extraction Points Table

| File:Line | Symbol | Library Used | Type | Called By | I/O | Notes |
|-----------|--------|--------------|------|-----------|-----|-------|
| `services/ocr_service.py:19-128` | `extract_text_from_image()` | pytesseract | IMAGE | `document_extraction.py:extract_text_from_file()` | `(image_path: Path, content_type: str) → str` | - Uses Tesseract with `--oem 3 --psm 3` config<br>- Language fallback: spa+eng → eng only<br>- Image preprocessing: resize to max 4000px<br>- HEIC/HEIF support via pillow-heif<br>- Checks Tesseract availability with `is_tesseract_installed()` |
| `services/ocr_service.py:131-139` | `is_tesseract_installed()` | pytesseract | UTIL | `extract_text_from_image()` | `() → bool` | Checks if Tesseract is installed on system |
| `services/ocr_service.py:142-150` | `get_tesseract_languages()` | pytesseract | UTIL | Not used | `() → list[str]` | Returns available Tesseract languages |
| `services/document_extraction.py:28-37` | `extract_text_from_file()` (PDF branch) | pypdf | PDF | `file_ingest.py:FileIngestService.ingest_file()` | `(file_path: Path, content_type: str) → List[PageContent]` | - Uses `PdfReader(file_path)`<br>- Extracts text with `page.extract_text()`<br>- Returns list of PageContent objects |
| `services/document_extraction.py:39-50` | `extract_text_from_file()` (Image branch) | pytesseract (via ocr_service) | IMAGE | `file_ingest.py:FileIngestService.ingest_file()` | `(file_path: Path, content_type: str) → List[PageContent]` | - Delegates to `extract_text_from_image()`<br>- Wraps result in PageContent model |
| `services/file_ingest.py:145` | `FileIngestService.ingest_file()` | N/A (orchestrator) | BOTH | `routers/files.py:upload_files()` | `(upload: UploadFile, user_id: str, ...) → Document` | - Main upload pipeline<br>- Saves file to disk temporarily<br>- Calls `extract_text_from_file()`<br>- Caches result in Redis (`doc:text:{file_id}`)<br>- Updates Document model with pages |
| `services/file_ingest.py:214-219` | `FileIngestService._cache_pages()` | N/A (Redis storage) | BOTH | `ingest_file()` | `(file_id: str, pages: List[PageContent]) → None` | - Stores extracted text in Redis<br>- Key: `doc:text:{file_id}`<br>- TTL: 3600 seconds (1 hour) |

---

## Call Chain Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User Upload                                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/files/upload                                          │
│ File: routers/files.py:56-90                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ FileIngestService.ingest_file()                                 │
│ File: services/file_ingest.py:44-209                            │
│ • Saves file to /tmp                                            │
│ • Determines content_type                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ extract_text_from_file(file_path, content_type)                 │
│ File: services/document_extraction.py:16-64                     │
└──────────────┬────────────────────────┬─────────────────────────┘
               │                        │
       [PDF]   │                        │   [IMAGE]
               ▼                        ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│ pypdf.PdfReader      │    │ extract_text_from_image()        │
│ page.extract_text()  │    │ File: services/ocr_service.py    │
│                      │    │ • PIL image preprocessing        │
│ Returns: str         │    │ • pytesseract.image_to_string()  │
└──────────────────────┘    │ • Language: spa+eng fallback     │
                            │ • Config: --oem 3 --psm 3        │
                            └──────────────────────────────────┘
               │                        │
               └────────────┬───────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Returns: List[PageContent]                                      │
│ • page: int                                                     │
│ • text_md: str                                                  │
│ • has_table: bool                                               │
│ • has_images: bool                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Store in Document.pages (MongoDB)                               │
│ Cache in Redis: doc:text:{file_id} (TTL: 1hr)                  │
│ Update status → READY                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies (from requirements.txt)

```txt
Line 44: pypdf>=3.17.0          # PDF text extraction
Line 47: pytesseract>=0.3.10    # OCR for images
Line 48: Pillow>=10.0.0         # Image processing
Line 49: pillow-heif>=0.13.0    # HEIC/HEIF support
```

---

## Environment Variables

### Current Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAX_DOCS_PER_CHAT` | 3 | Max documents included per chat context |
| `MAX_TOTAL_DOC_CHARS` | 16000 | Max total characters across all documents |
| `LLM_TIMEOUT_SECONDS` | 30 | Timeout for LLM API calls |

### New Configuration (to be added)

| Variable | Default | Values | Purpose |
|----------|---------|--------|---------|
| `EXTRACTOR_PROVIDER` | `third_party` | `third_party`, `saptiva` | Controls which extraction backend to use |
| `SAPTIVA_BASE_URL` | TBD | URL | Base URL for Saptiva Native Tools API |
| `SAPTIVA_API_KEY` | (exists) | string | API key for Saptiva authentication |

---

## Data Flow - RAG Context Generation

After extraction, text flows through the RAG pipeline:

```
Redis Cache (doc:text:{file_id})
    ↓
DocumentService.get_document_text_from_cache()
    • Retrieves from Redis
    • Validates ownership (user_id)
    • Returns List[Tuple[Document, str]]
    ↓
DocumentService.extract_content_for_rag_from_cache()
    • Applies limits (max 3 docs, 16K chars total)
    • Formats with emoji headers (📷 for images, 📄 for PDFs)
    • Truncates individual docs to 8K chars
    • Returns: (formatted_context, warnings, metadata)
    ↓
ChatService.process_with_saptiva(document_context=...)
    • Injects document context into system message
    • Adjusts prompt based on content type:
      - Images: Mentions OCR extraction
      - PDFs: Standard document context
      - Mixed: Both types mentioned
    ↓
LLM receives formatted context with extracted text
```

---

## Side Effects & Storage

### Temporary Files

- **Location:** `/tmp/` (default system temp)
- **Pattern:** Random UUID filenames
- **Lifecycle:**
  - Created during upload in `file_ingest.py:72-78`
  - Used for extraction
  - **NOT automatically cleaned** ⚠️ (potential disk leak)
  - File path stored in `Document.minio_key` (misnomer - actually local path)

### Redis Cache

- **Key Format:** `doc:text:{file_id}`
- **Content:** Full extracted text (all pages concatenated)
- **TTL:** 3600 seconds (1 hour)
- **Size:** Unbounded per document (⚠️ potential memory issue for large files)

### MongoDB Storage

- **Collection:** `documents`
- **Fields:**
  - `pages: List[PageContent]` - Full extracted content
  - `total_pages: int`
  - `ocr_applied: bool`
  - `status: DocumentStatus` (UPLOADING → PROCESSING → READY/FAILED)

---

## Error Handling

### Tesseract Not Installed

**File:** `ocr_service.py:131-139`

```python
def is_tesseract_installed() -> bool:
    try:
        subprocess.run(["tesseract", "--version"], ...)
        return True
    except FileNotFoundError:
        return False
```

- **Action:** Returns empty string from `extract_text_from_image()`
- **User Impact:** No error, just empty OCR result (⚠️ silent failure)

### Language Fallback

**File:** `ocr_service.py:82-97`

```python
try:
    text = pytesseract.image_to_string(img, lang="spa+eng", config=config)
except pytesseract.TesseractError:
    text = pytesseract.image_to_string(img, lang="eng", config=config)
```

- Falls back to English-only if Spanish+English fails

### Unsupported Format

**File:** `document_extraction.py:51-58`

```python
else:
    raise ValueError(f"Unsupported content type for extraction: {content_type}")
```

- Returns error to user via FastAPI

---

## Performance Characteristics

### PDF Extraction (pypdf)

- **Speed:** Fast (~100ms per page)
- **Accuracy:** Depends on PDF structure (searchable vs scanned)
- **Limitations:**
  - Does not handle scanned PDFs (no OCR)
  - Struggles with complex layouts
  - Tables extracted as plain text (no structure)

### Image OCR (pytesseract)

- **Speed:** Slow (~2-5 seconds per image)
- **Blocking:** Synchronous, blocks thread during extraction
- **Language Detection:** None (hardcoded spa+eng)
- **Preprocessing:**
  - Resize to max 4000px (helps with memory)
  - Convert to RGB
  - Format conversion (HEIC → PNG)

### Bottlenecks

1. **No async extraction** - OCR blocks thread
2. **No parallelization** - Multi-page PDFs processed sequentially
3. **Large images** - 4000px limit may still OOM on some systems
4. **Redis cache size** - No limit on document size in cache

---

## Security Considerations

### Current Issues ⚠️

1. **Temp file cleanup:** Files in `/tmp` not deleted after processing
2. **File size validation:** Max 10MB enforced in `file_ingest.py:31`, but could be bypassed
3. **Content type trust:** Uses client-provided `content_type` without verification
4. **Path traversal:** Not validated in temp file creation
5. **Redis unbounded:** Large documents can fill Redis memory

### Secrets Management

- `SAPTIVA_API_KEY` stored in `.env` ✅
- No hardcoded API keys in codebase ✅

---

## Migration Strategy

### Phase 1: Abstraction Layer (This PR)

**Goal:** Create pluggable architecture without changing behavior

**Tasks:**
1. Create `services/extractors/` module structure
2. Define `TextExtractor` ABC (abstract base class)
3. Implement `ThirdPartyExtractor` wrapping current code
4. Create `SaptivaExtractor` stub with TODOs
5. Add `get_text_extractor()` factory
6. Refactor `document_extraction.py` to use factory
7. Add `EXTRACTOR_PROVIDER` environment variable
8. Write unit tests for abstraction layer

**Acceptance Criteria:**
- ✅ Setting `EXTRACTOR_PROVIDER=third_party` works identically to current behavior
- ✅ All existing tests pass
- ✅ No change to API contracts or response formats

### Phase 2: Saptiva Integration (Future)

**Goal:** Complete `SaptivaExtractor` implementation

**Tasks:**
1. Wire up Saptiva Native Tools API endpoints
2. Add error handling and retries
3. Update authentication headers
4. Performance testing (latency, accuracy)
5. A/B testing in staging

**Acceptance Criteria:**
- ✅ Setting `EXTRACTOR_PROVIDER=saptiva` uses Saptiva backend
- ✅ Latency ≤ current solution
- ✅ Accuracy ≥ current solution
- ✅ Error rate < 1%

### Phase 3: Migration & Cleanup (Future)

**Goal:** Make Saptiva default, retire third-party libs

**Tasks:**
1. Deploy to production with `EXTRACTOR_PROVIDER=saptiva`
2. Monitor for 2 weeks
3. Remove third-party dependencies from `requirements.txt`
4. Archive `ThirdPartyExtractor` or keep as emergency fallback

---

## Test Coverage

### Existing Tests

**E2E Test:** `tests/ocr_e2e_test.py`
- Creates test image with PIL
- Uploads via `/api/files/upload`
- Sends chat message with file context
- Validates Redis cache contains extracted text
- Verifies LLM receives OCR context

**Prompt Validation:** `tests/validate_ocr_prompt.py`
- Tests emoji markers (📷 vs 📄)
- Validates system prompt structure
- Tests RAG formatting limits

**Integration Test:** `apps/api/tests/integration/test_chat_file_context.py`
- Tests file context persistence across messages
- Validates `ChatSession.attached_file_ids` merging

### Tests to Add (Phase 1)

**Unit Tests:** `apps/api/tests/unit/test_extractors.py`
- `test_third_party_extractor_pdf()`
- `test_third_party_extractor_image()`
- `test_saptiva_extractor_not_implemented()`
- `test_factory_returns_correct_provider()`
- `test_factory_defaults_to_third_party()`

**Contract Tests:**
- Ensure both extractors conform to `TextExtractor` ABC
- Validate output format (always returns `str`)
- Test error propagation

---

## References

### Related Documentation

- `docs/BUG_FIXES_SUMMARY.md` - Recent fixes to file context persistence
- `docs/METADATA_PERSISTENCE_SOLUTION.md` - File metadata handling
- `docs/MVP-FILE-CONTEXT-TESTS.md` - Test scenarios for file features
- `docs/OCR_PROMPT_IMPROVEMENT.md` - Prompt engineering for OCR context
- `docs/OCR_VALIDATION_REPORT.md` - OCR quality assessment

### Related Code

- `apps/api/src/models/document.py` - Document and PageContent models
- `apps/api/src/services/document_service.py` - RAG formatting logic
- `apps/api/src/domain/chat_strategy.py` - Document retrieval in chat flow
- `apps/api/src/routers/files.py` - Upload endpoints
- `apps/api/src/routers/chat.py` - Chat with file context

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-10-16 | Initial inventory created | Claude Code |
| TBD | Phase 1 implementation | TBD |
| TBD | Phase 2 Saptiva integration | TBD |
| TBD | Phase 3 migration complete | TBD |
