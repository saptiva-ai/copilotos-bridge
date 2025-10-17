# Developer Guide - Text Extraction Abstraction

## Overview

This guide explains how to work with the text extraction abstraction layer that was introduced to prepare for migrating from third-party libraries (pypdf + pytesseract) to Saptiva Native Tools.

**Current Status:** Phase 1 Complete ✅
- Abstraction layer implemented
- Third-party extractor wrapped
- Saptiva extractor stubbed
- Feature flag added
- Tests written

**Next Steps:** Phase 2 (Future)
- Complete Saptiva implementation
- A/B testing
- Production rollout

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer                                            │
│                                                              │
│  document_extraction.py                                      │
│  file_ingest.py                                              │
│  routers/files.py                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Abstraction Layer                                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ get_text_extractor()  ← Factory Pattern             │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│       ┌───────┴───────┐                                      │
│       │               │                                      │
│       ▼               ▼                                      │
│  ┌─────────┐    ┌──────────┐                                │
│  │ Third   │    │ Saptiva  │                                │
│  │ Party   │    │ Extractor│                                │
│  └────┬────┘    └────┬─────┘                                │
└───────┼──────────────┼──────────────────────────────────────┘
        │              │
        ▼              ▼
┌──────────────┐  ┌──────────────┐
│ pypdf        │  │ Saptiva      │
│ pytesseract  │  │ Native API   │
│ PIL          │  │ (Phase 2)    │
└──────────────┘  └──────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `services/extractors/base.py` | Abstract interface (TextExtractor ABC) |
| `services/extractors/third_party.py` | Current implementation (pypdf + pytesseract) |
| `services/extractors/saptiva.py` | Future implementation (stub) |
| `services/extractors/factory.py` | Factory pattern (get_text_extractor) |
| `services/document_extraction.py` | High-level API used by application |
| `core/config.py` | Settings (EXTRACTOR_PROVIDER feature flag) |
| `tests/unit/test_extractors.py` | Unit tests for abstraction layer |

---

## Quick Start

### Using the Extractor in Code

```python
from services.extractors import get_text_extractor

# Get extractor (factory selects based on EXTRACTOR_PROVIDER env var)
extractor = get_text_extractor()

# Extract text from PDF
pdf_text = await extractor.extract_text(
    media_type="pdf",
    data=pdf_bytes,
    mime="application/pdf",
    filename="document.pdf",
)

# Extract text from image (OCR)
image_text = await extractor.extract_text(
    media_type="image",
    data=image_bytes,
    mime="image/png",
    filename="scan.png",
)

# Health check
is_healthy = await extractor.health_check()
```

### Configuration

Add to `.env` file:

```bash
# Text Extraction Provider
# Options: "third_party" (default) | "saptiva"
EXTRACTOR_PROVIDER=third_party

# Saptiva Configuration (for Phase 2)
SAPTIVA_BASE_URL=https://api.saptiva.com
SAPTIVA_API_KEY=your-api-key-here
```

### Switching Providers

**Development:**
```bash
# Use third-party libs (default)
export EXTRACTOR_PROVIDER=third_party

# Use Saptiva (Phase 2)
export EXTRACTOR_PROVIDER=saptiva
```

**Docker Compose:**
```yaml
services:
  api:
    environment:
      - EXTRACTOR_PROVIDER=third_party
      - SAPTIVA_API_KEY=${SAPTIVA_API_KEY}
```

---

## API Reference

### TextExtractor ABC

All extractors must implement this interface.

```python
class TextExtractor(ABC):
    @abstractmethod
    async def extract_text(
        self,
        *,
        media_type: Literal["pdf", "image"],
        data: bytes,
        mime: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Extract text from document bytes.

        Args:
            media_type: Type of document ("pdf" or "image")
            data: Raw document bytes
            mime: MIME type (e.g., "application/pdf", "image/png")
            filename: Optional filename for context/logging

        Returns:
            Extracted text as plain string

        Raises:
            UnsupportedFormatError: If MIME type not supported
            ExtractionError: If extraction fails
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if extraction backend is available.

        Returns:
            True if operational, False otherwise
        """
```

### Factory Functions

```python
def get_text_extractor(*, force_new: bool = False) -> TextExtractor:
    """
    Get text extractor instance.

    Implements singleton pattern - returns cached instance unless force_new=True.

    Returns:
        TextExtractor implementation based on EXTRACTOR_PROVIDER
    """

def clear_extractor_cache() -> None:
    """
    Clear cached extractor instance.

    Useful for testing or config reloading.
    """

async def health_check_extractor() -> bool:
    """
    Check if current extractor is healthy.

    Convenience function for health endpoints.
    """
```

### Exception Classes

```python
class ExtractionError(Exception):
    """Base exception for extraction failures."""
    media_type: Optional[MediaType]
    original_error: Optional[Exception]

class UnsupportedFormatError(ExtractionError):
    """Raised when document format is not supported."""

class ExtractionTimeoutError(ExtractionError):
    """Raised when extraction exceeds timeout limit."""
```

---

## Testing

### Running Tests

```bash
# Run all extractor tests
pytest apps/api/tests/unit/test_extractors.py -v

# Run specific test class
pytest apps/api/tests/unit/test_extractors.py::TestFactory -v

# Run with coverage
pytest apps/api/tests/unit/test_extractors.py --cov=src/services/extractors
```

### Test Coverage

```bash
# Generate coverage report
pytest apps/api/tests/unit/test_extractors.py --cov=src/services/extractors --cov-report=html

# Open report
open htmlcov/index.html
```

### Writing New Tests

```python
import pytest
from src.services.extractors import get_text_extractor, clear_extractor_cache

class TestMyFeature:
    def setup_method(self):
        """Reset cache before each test."""
        clear_extractor_cache()

    @pytest.mark.asyncio
    async def test_extraction(self):
        """Test extraction logic."""
        extractor = get_text_extractor()
        text = await extractor.extract_text(
            media_type="pdf",
            data=b"%PDF-test",
            mime="application/pdf",
        )
        assert text
```

---

## Development Workflow

### Adding a New Extractor

1. **Create implementation** in `services/extractors/my_extractor.py`:

```python
from .base import TextExtractor, MediaType

class MyExtractor(TextExtractor):
    async def extract_text(self, *, media_type, data, mime, filename=None):
        # Implementation
        pass

    async def health_check(self):
        # Check availability
        pass
```

2. **Update factory** in `services/extractors/factory.py`:

```python
from .my_extractor import MyExtractor

def get_text_extractor(*, force_new=False):
    provider = os.getenv("EXTRACTOR_PROVIDER", "third_party")

    if provider == "my_extractor":
        return MyExtractor()
    # ... existing code
```

3. **Add tests** in `tests/unit/test_extractors.py`:

```python
class TestMyExtractor:
    @pytest.mark.asyncio
    async def test_extract_text(self):
        # Test implementation
        pass
```

4. **Update documentation**:
   - `docs/extraction-inventory.md`
   - `apps/api/.env.example`
   - This README

### Debugging Extraction Issues

**Enable debug logging:**

```python
import structlog
logger = structlog.get_logger(__name__)
logger.debug("Extraction debug info", ...)
```

**Check which extractor is active:**

```python
from services.extractors import get_text_extractor

extractor = get_text_extractor()
print(f"Active extractor: {type(extractor).__name__}")
```

**Test health check:**

```python
from services.extractors import health_check_extractor

is_healthy = await health_check_extractor()
print(f"Extractor healthy: {is_healthy}")
```

---

## Security Considerations

### ⚠️ Important Security Notes

1. **Never log raw document bytes**
   - Logs might contain sensitive content
   - Use `text_length` or `file_size` metrics instead

2. **Clean up temporary files**
   - ThirdPartyExtractor creates temp files
   - Cleanup happens automatically in `finally` block
   - Verify with file system monitoring in tests

3. **Validate MIME types**
   - Always validate `media_type` matches `mime`
   - Use `_validate_mime_type()` helper
   - Reject unsupported formats early

4. **API key management**
   - `SAPTIVA_API_KEY` must be in `.env` (not committed)
   - Use `mask_secret()` for logging
   - Never expose keys in error messages

5. **Input validation**
   - Max file size: 10 MB (enforced in `file_ingest.py`)
   - Allowed MIME types: Whitelist only
   - Rate limiting: 5 uploads/minute per user

### Environment Variable Checklist

**Required (Production):**
- ✅ `SAPTIVA_API_KEY` - Set in `.env` (never commit!)
- ✅ `EXTRACTOR_PROVIDER` - Set to `third_party` by default

**Optional (Phase 2):**
- ⏳ `SAPTIVA_BASE_URL` - Override default API endpoint
- ⏳ `EXTRACTOR_TIMEOUT` - Extraction timeout in seconds

**Never Commit:**
- ❌ `.env` file
- ❌ API keys or credentials
- ❌ Production database URLs

---

## Performance Optimization

### Current Bottlenecks

1. **OCR is slow** (~2-5s per image)
   - Tesseract blocks thread during extraction
   - Solution: Use async wrappers or thread pool

2. **Large images consume memory**
   - Resize to max 4000px before OCR
   - Convert to RGB (reduces memory)
   - Consider streaming for very large files

3. **Multi-page PDFs are sequential**
   - Each page processed one-by-one
   - Solution: Parallel page extraction (Phase 2)

### Monitoring Metrics

Add to observability stack:

```python
logger.info(
    "Extraction metrics",
    media_type=media_type,
    file_size=len(data),
    text_length=len(text),
    latency_ms=elapsed_ms,
    extractor_type=type(extractor).__name__,
)
```

**Key metrics to track:**
- Extraction latency (p50, p95, p99)
- Error rate by provider
- File size distribution
- OCR accuracy (manual sampling)

---

## Troubleshooting

### Common Issues

#### Issue: `pypdf not installed`

**Symptom:** ImportError when using ThirdPartyExtractor

**Solution:**
```bash
pip install pypdf>=3.17.0
```

#### Issue: `Tesseract not found`

**Symptom:** ExtractionError with "tesseract" in message

**Solution:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Verify installation
tesseract --version
```

#### Issue: `SaptivaExtractor not yet implemented`

**Symptom:** NotImplementedError when EXTRACTOR_PROVIDER=saptiva

**Solution:**
- Set `EXTRACTOR_PROVIDER=third_party` (default)
- SaptivaExtractor is a stub until Phase 2

#### Issue: `Spanish language pack not available`

**Symptom:** Warning in logs, OCR falls back to English

**Solution:**
```bash
# Install Spanish language data
sudo apt-get install tesseract-ocr-spa

# Verify
tesseract --list-langs
```

#### Issue: Extraction times out

**Symptom:** ExtractionTimeoutError after 30s

**Solution:**
- Check file size (max 10 MB)
- Reduce image resolution
- Increase timeout in Phase 2

### Debug Checklist

- [ ] Check `EXTRACTOR_PROVIDER` env var
- [ ] Verify dependencies installed (`pypdf`, `pytesseract`, `tesseract`)
- [ ] Check file permissions for temp directory
- [ ] Review logs for detailed error messages
- [ ] Test with small sample file first
- [ ] Run health check: `await health_check_extractor()`

---

## Migration Timeline

### Phase 1: Abstraction Layer ✅ COMPLETE

**Status:** Merged to `develop`

**Deliverables:**
- [x] `services/extractors/` module structure
- [x] `TextExtractor` ABC
- [x] `ThirdPartyExtractor` (wraps current code)
- [x] `SaptivaExtractor` stub
- [x] Factory pattern implementation
- [x] `EXTRACTOR_PROVIDER` feature flag
- [x] Unit tests (>80% coverage)
- [x] Documentation (this README)

**Validation:**
- All existing tests pass
- No behavior changes (backwards compatible)
- Production uses `third_party` by default

### Phase 2: Saptiva Integration 🚧 FUTURE

**Target:** Q1 2026 (TBD)

**Tasks:**
- [ ] Complete `SaptivaExtractor.extract_text()` implementation
- [ ] Wire up Saptiva API endpoints (spec TBD)
- [ ] Add retry logic with exponential backoff
- [ ] Implement circuit breaker for API failures
- [ ] Performance testing (latency benchmarks)
- [ ] Accuracy testing (sample comparisons)
- [ ] A/B testing framework
- [ ] Staging deployment with `EXTRACTOR_PROVIDER=saptiva`
- [ ] Monitor metrics for 2 weeks

**Acceptance Criteria:**
- Latency ≤ current solution (p95)
- Accuracy ≥ current solution (manual sampling)
- Error rate < 1%
- Cost per extraction < $X (TBD)

### Phase 3: Production Rollout 🔮 FUTURE

**Target:** Q2 2026 (TBD)

**Tasks:**
- [ ] Gradual rollout (5% → 25% → 50% → 100%)
- [ ] Monitor error rates and latency
- [ ] Gather user feedback
- [ ] Make `saptiva` the default in `.env.example`
- [ ] Update documentation
- [ ] Deprecate `third_party` (keep as fallback)
- [ ] Remove third-party dependencies from `requirements.txt` (optional)

**Rollback Plan:**
- Set `EXTRACTOR_PROVIDER=third_party` in production `.env`
- Redeploy containers
- Monitor recovery

---

## FAQ

### Q: Why not keep both extractors forever?

**A:** Maintaining two implementations doubles testing burden and increases complexity. Once Saptiva is proven superior, we can simplify by deprecating third-party libs.

### Q: What happens if Saptiva API is down?

**A:** In Phase 2, we'll implement:
- Circuit breaker (fail fast after N errors)
- Fallback to `third_party` (optional via config)
- Detailed error logging for ops team

### Q: Can I use a different extractor in tests?

**A:** Yes, use environment variables:

```python
@pytest.fixture
def use_third_party():
    with patch.dict(os.environ, {"EXTRACTOR_PROVIDER": "third_party"}):
        clear_extractor_cache()
        yield
        clear_extractor_cache()
```

### Q: How do I profile extraction performance?

**A:** Add timing instrumentation:

```python
import time
from services.extractors import get_text_extractor

start = time.time()
extractor = get_text_extractor()
text = await extractor.extract_text(...)
elapsed = time.time() - start

print(f"Extraction took {elapsed:.2f}s")
```

### Q: What if I need to extract tables or images?

**A:** Current abstraction only handles text. For structured extraction:
- Tables: Future enhancement (return structured data)
- Images: Separate endpoint (return image URLs)

---

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings (Google style)
- Run `black` and `ruff` before committing

### Pull Request Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] `docs/extraction-inventory.md` updated (if applicable)
- [ ] No secrets committed
- [ ] Feature flag tested manually
- [ ] Backwards compatible (unless breaking change approved)

### Reviewers

Tag these people for review:

- Extraction logic: @backend-team
- API design: @architecture-team
- Security: @security-team

---

## References

### Related Documentation

- [Extraction Inventory](./extraction-inventory.md) - Complete code inventory
- [OCR Validation Report](./OCR_VALIDATION_REPORT.md) - OCR quality assessment
- [File Context Tests](./MVP-FILE-CONTEXT-TESTS.md) - Integration tests

### External Links

- [pypdf Documentation](https://pypdf.readthedocs.io/)
- [pytesseract Documentation](https://pypi.org/project/pytesseract/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Saptiva Native Tools API](https://docs.saptiva.com) (Phase 2)

---

## Changelog

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-10-16 | 1.0.0 | Initial abstraction layer (Phase 1) | Claude Code |
| TBD | 2.0.0 | Saptiva integration (Phase 2) | TBD |
| TBD | 3.0.0 | Production rollout (Phase 3) | TBD |

---

**Last Updated:** 2025-10-16
**Maintainer:** Backend Team
**Status:** Phase 1 Complete ✅
