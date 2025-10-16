# Saptiva Native Tools Integration Guide

## Overview

This guide provides the complete specification for integrating Saptiva's native OCR and PDF extraction tools into the `SaptivaExtractor` implementation.

**Status:** Phase 2 Specification (Ready for Implementation)

---

## Architecture Decision

### ✅ Chosen Approach: Backend-Driven Extraction

**Extraction happens at upload time**, not during LLM inference.

```
┌─────────────────────────────────────────────────────────────────┐
│ Upload Flow (Synchronous Extraction)                            │
└─────────────────────────────────────────────────────────────────┘

User uploads file
    ↓
POST /api/files/upload
    ↓
FileIngestService.ingest_file()
    ├─ Save file to /tmp
    ├─ Call SaptivaExtractor.extract_text()  ← Saptiva API called here
    ├─ Parse response → PageContent[]
    ├─ Save to MongoDB (Document.pages)
    └─ Cache in Redis (doc:text:{file_id})
    ↓
Return Document with status=READY

┌─────────────────────────────────────────────────────────────────┐
│ Chat Flow (Use Cached Text)                                     │
└─────────────────────────────────────────────────────────────────┘

User sends chat with file_ids
    ↓
ChatService retrieves from Redis cache
    ↓
Format text with headers (📷 or 📄)
    ↓
Inject into system prompt
    ↓
LLM processes with pre-extracted context
    ↓
Respond instantly (no extraction latency)
```

**Rationale:**

| Criterion | Backend Extraction | Agent Tool |
|-----------|-------------------|------------|
| User Experience | ✅ Predictable (upload slow, chat fast) | ❌ Unpredictable (chat slow) |
| Cost Efficiency | ✅ Extract once, use N times | ❌ Re-extract per chat |
| Reliability | ✅ Error handling at upload | ❌ Error during inference breaks chat |
| Observability | ✅ Centralized logs | ❌ Distributed across tool calls |
| Cache Strategy | ✅ Redis with TTL | ❌ No cache (or complex tool cache) |

---

## API Specification

### Endpoint 1: PDF Text Extraction

**Endpoint:**
```
POST https://api.saptiva.com/v1/extract/pdf
```

**Request:**
```http
POST /v1/extract/pdf HTTP/1.1
Host: api.saptiva.com
Authorization: Bearer {SAPTIVA_API_KEY}
Content-Type: multipart/form-data; boundary=---boundary

---boundary
Content-Disposition: form-data; name="file"; filename="document.pdf"
Content-Type: application/pdf

{PDF_BINARY_DATA}
---boundary
Content-Disposition: form-data; name="options"

{
  "language": "auto",
  "extract_tables": false,
  "extract_images": false
}
---boundary--
```

**Response (Success - 200 OK):**
```json
{
  "success": true,
  "pages": [
    {
      "page_number": 1,
      "text": "Contenido de la primera página del PDF...",
      "confidence": 0.98,
      "language": "es",
      "has_tables": false,
      "has_images": true
    },
    {
      "page_number": 2,
      "text": "Contenido de la segunda página...",
      "confidence": 0.96,
      "language": "es",
      "has_tables": true,
      "has_images": false
    }
  ],
  "metadata": {
    "total_pages": 2,
    "processing_time_ms": 1234,
    "model_version": "saptiva-pdf-v3.0",
    "file_size_bytes": 524288
  }
}
```

**Response (Error - 4xx/5xx):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PDF",
    "message": "The uploaded file is not a valid PDF",
    "details": "PDF header missing or corrupted"
  }
}
```

---

### Endpoint 2: Image OCR

**Endpoint:**
```
POST https://api.saptiva.com/v1/extract/image
```

**Request:**
```http
POST /v1/extract/image HTTP/1.1
Host: api.saptiva.com
Authorization: Bearer {SAPTIVA_API_KEY}
Content-Type: multipart/form-data; boundary=---boundary

---boundary
Content-Disposition: form-data; name="file"; filename="scan.png"
Content-Type: image/png

{IMAGE_BINARY_DATA}
---boundary
Content-Disposition: form-data; name="options"

{
  "language": "auto",
  "preprocessing": "auto",
  "deskew": true
}
---boundary--
```

**Response (Success - 200 OK):**
```json
{
  "success": true,
  "text": "Texto extraído de la imagen mediante OCR...",
  "metadata": {
    "confidence": 0.92,
    "language": "es",
    "detected_orientation": 0,
    "preprocessing_applied": ["resize", "grayscale", "contrast"],
    "processing_time_ms": 2345,
    "model_version": "saptiva-ocr-v2.1",
    "image_size": {
      "width": 1920,
      "height": 1080
    }
  }
}
```

**Response (Error - 4xx/5xx):**
```json
{
  "success": false,
  "error": {
    "code": "IMAGE_TOO_LARGE",
    "message": "Image exceeds maximum size of 10MB",
    "details": "Image size: 15728640 bytes"
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Parse response and return text |
| 400 | Bad Request | Log error, raise UnsupportedFormatError |
| 401 | Unauthorized | Check SAPTIVA_API_KEY configuration |
| 413 | Payload Too Large | File exceeds max size (10MB) |
| 429 | Rate Limit | Retry with exponential backoff |
| 500 | Server Error | Retry up to 3 times, then fail |
| 503 | Service Unavailable | Retry with backoff, circuit breaker |

### Retry Strategy

```python
# Exponential backoff with jitter
max_retries = 3
base_delay = 1  # seconds
max_delay = 10  # seconds

for attempt in range(max_retries):
    try:
        response = await make_request()
        if response.status_code in [429, 500, 503]:
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, 0.1 * delay)
            await asyncio.sleep(delay + jitter)
            continue
        return response
    except httpx.TimeoutException:
        if attempt == max_retries - 1:
            raise ExtractionTimeoutError(...)
```

---

## Complete SaptivaExtractor Implementation

```python
"""
Saptiva Native Tools Text Extraction Implementation

Complete implementation for Phase 2 integration.
"""

import os
import asyncio
import random
from typing import Optional, Dict, Any, List

import httpx
import structlog

from .base import (
    TextExtractor,
    MediaType,
    ExtractionError,
    ExtractionTimeoutError,
    UnsupportedFormatError,
)

logger = structlog.get_logger(__name__)


class SaptivaExtractor(TextExtractor):
    """
    Text extractor using Saptiva Native Tools API.

    Supports:
        - PDF text extraction via /v1/extract/pdf
        - Image OCR via /v1/extract/image
        - Automatic retries with exponential backoff
        - Circuit breaker for API failures
        - Detailed observability metrics
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Saptiva extractor.

        Args:
            base_url: Saptiva API base URL (default: from SAPTIVA_BASE_URL env)
            api_key: Saptiva API key (default: from SAPTIVA_API_KEY env)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts for transient errors (default: 3)
        """
        self.base_url = (base_url or os.getenv("SAPTIVA_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("SAPTIVA_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries

        # Circuit breaker state
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_until = 0

        if not self.base_url:
            logger.warning("SAPTIVA_BASE_URL not configured")

        if not self.api_key:
            logger.warning("SAPTIVA_API_KEY not configured")

    async def extract_text(
        self,
        *,
        media_type: MediaType,
        data: bytes,
        mime: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Extract text using Saptiva Native Tools API.

        Args:
            media_type: "pdf" or "image"
            data: Raw document bytes
            mime: MIME type
            filename: Optional filename for API context

        Returns:
            Extracted text as plain string

        Raises:
            ExtractionError: If API call fails
            ExtractionTimeoutError: If request times out
            UnsupportedFormatError: If format not supported
        """
        # Validate configuration
        if not self.base_url or not self.api_key:
            raise ExtractionError(
                "Saptiva API not configured. Set SAPTIVA_BASE_URL and SAPTIVA_API_KEY.",
                media_type=media_type,
            )

        # Check circuit breaker
        if self._is_circuit_open():
            raise ExtractionError(
                "Saptiva API circuit breaker is open (too many failures). Try again later.",
                media_type=media_type,
            )

        # Route to appropriate endpoint
        if media_type == "pdf":
            return await self._extract_pdf(data, mime, filename)
        else:  # media_type == "image"
            return await self._extract_image(data, mime, filename)

    async def _extract_pdf(
        self, data: bytes, mime: str, filename: Optional[str]
    ) -> str:
        """
        Extract text from PDF using Saptiva API.

        Args:
            data: PDF binary data
            mime: MIME type (should be "application/pdf")
            filename: Optional filename

        Returns:
            Concatenated text from all pages (separated by \\n\\n)
        """
        endpoint = f"{self.base_url}/v1/extract/pdf"

        # Prepare request
        files = {"file": (filename or "document.pdf", data, mime)}
        options = {
            "language": "auto",
            "extract_tables": False,
            "extract_images": False,
        }
        data_fields = {"options": httpx._multipart.DataField(str(options))}

        logger.info(
            "Calling Saptiva PDF extraction",
            endpoint=endpoint,
            filename=filename,
            file_size=len(data),
        )

        try:
            response_data = await self._make_request_with_retry(
                endpoint=endpoint,
                files=files,
                data=data_fields,
            )

            # Parse response
            if not response_data.get("success"):
                error = response_data.get("error", {})
                raise ExtractionError(
                    f"Saptiva PDF extraction failed: {error.get('message', 'Unknown error')}",
                    media_type="pdf",
                )

            pages = response_data.get("pages", [])
            if not pages:
                logger.warning("Saptiva returned no pages for PDF", filename=filename)
                return "[PDF sin contenido extraíble]"

            # Concatenate pages with double newline separator
            page_texts = [page.get("text", "").strip() for page in pages]
            result = "\n\n".join(page_texts)

            # Log metrics
            metadata = response_data.get("metadata", {})
            logger.info(
                "Saptiva PDF extraction successful",
                filename=filename,
                pages=len(pages),
                chars=len(result),
                processing_time_ms=metadata.get("processing_time_ms"),
                model_version=metadata.get("model_version"),
            )

            return result

        except httpx.HTTPStatusError as exc:
            self._record_failure()
            raise ExtractionError(
                f"Saptiva API error ({exc.response.status_code}): {exc.response.text}",
                media_type="pdf",
                original_error=exc,
            )

        except httpx.TimeoutException as exc:
            self._record_failure()
            raise ExtractionTimeoutError(
                f"Saptiva API timeout after {self.timeout}s",
                media_type="pdf",
                original_error=exc,
            )

        except Exception as exc:
            self._record_failure()
            raise ExtractionError(
                f"Unexpected Saptiva API error: {str(exc)}",
                media_type="pdf",
                original_error=exc,
            )

    async def _extract_image(
        self, data: bytes, mime: str, filename: Optional[str]
    ) -> str:
        """
        Extract text from image using Saptiva OCR API.

        Args:
            data: Image binary data
            mime: MIME type (e.g., "image/png")
            filename: Optional filename

        Returns:
            OCR-extracted text
        """
        endpoint = f"{self.base_url}/v1/extract/image"

        # Prepare request
        files = {"file": (filename or "image.png", data, mime)}
        options = {
            "language": "auto",
            "preprocessing": "auto",
            "deskew": True,
        }
        data_fields = {"options": httpx._multipart.DataField(str(options))}

        logger.info(
            "Calling Saptiva OCR",
            endpoint=endpoint,
            filename=filename,
            file_size=len(data),
        )

        try:
            response_data = await self._make_request_with_retry(
                endpoint=endpoint,
                files=files,
                data=data_fields,
            )

            # Parse response
            if not response_data.get("success"):
                error = response_data.get("error", {})
                raise ExtractionError(
                    f"Saptiva OCR failed: {error.get('message', 'Unknown error')}",
                    media_type="image",
                )

            text = response_data.get("text", "").strip()
            if not text:
                logger.warning("Saptiva OCR returned empty text", filename=filename)
                return "[Imagen sin texto detectable]"

            # Log metrics
            metadata = response_data.get("metadata", {})
            logger.info(
                "Saptiva OCR successful",
                filename=filename,
                chars=len(text),
                confidence=metadata.get("confidence"),
                language=metadata.get("language"),
                processing_time_ms=metadata.get("processing_time_ms"),
                model_version=metadata.get("model_version"),
            )

            return text

        except httpx.HTTPStatusError as exc:
            self._record_failure()
            raise ExtractionError(
                f"Saptiva API error ({exc.response.status_code}): {exc.response.text}",
                media_type="image",
                original_error=exc,
            )

        except httpx.TimeoutException as exc:
            self._record_failure()
            raise ExtractionTimeoutError(
                f"Saptiva API timeout after {self.timeout}s",
                media_type="image",
                original_error=exc,
            )

        except Exception as exc:
            self._record_failure()
            raise ExtractionError(
                f"Unexpected Saptiva API error: {str(exc)}",
                media_type="image",
                original_error=exc,
            )

    async def _make_request_with_retry(
        self,
        endpoint: str,
        files: Dict[str, Any],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry.

        Args:
            endpoint: Full API endpoint URL
            files: Multipart files dict
            data: Multipart data fields dict

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If request fails after retries
            httpx.TimeoutException: If request times out
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Accept": "application/json",
                        },
                        files=files,
                        data=data,
                    )

                    # Success
                    if response.status_code == 200:
                        self._record_success()
                        return response.json()

                    # Retry on transient errors
                    if response.status_code in [429, 500, 503]:
                        logger.warning(
                            "Saptiva API transient error, retrying",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                        )
                        await self._backoff(attempt)
                        continue

                    # Non-retryable error
                    response.raise_for_status()

            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    "Saptiva API timeout, retrying",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    timeout=self.timeout,
                )
                await self._backoff(attempt)
                continue

            except httpx.HTTPStatusError as exc:
                # Re-raise non-retryable errors
                if exc.response.status_code not in [429, 500, 503]:
                    raise
                last_exception = exc
                await self._backoff(attempt)
                continue

        # All retries exhausted
        if last_exception:
            raise last_exception

        raise ExtractionError("Max retries exhausted without response")

    async def _backoff(self, attempt: int) -> None:
        """
        Exponential backoff with jitter.

        Args:
            attempt: Current retry attempt (0-indexed)
        """
        base_delay = 1  # seconds
        max_delay = 10  # seconds

        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, 0.1 * delay)

        await asyncio.sleep(delay + jitter)

    def _record_success(self) -> None:
        """Record successful API call (reset circuit breaker)."""
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_until = 0

    def _record_failure(self) -> None:
        """Record failed API call (trigger circuit breaker if threshold reached)."""
        self._failure_count += 1

        # Open circuit after 5 consecutive failures
        if self._failure_count >= 5:
            self._circuit_open = True
            self._circuit_open_until = asyncio.get_event_loop().time() + 60  # 1 min
            logger.error(
                "Saptiva API circuit breaker opened",
                failure_count=self._failure_count,
                circuit_open_duration_s=60,
            )

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self._circuit_open:
            return False

        # Check if circuit should reset
        if asyncio.get_event_loop().time() > self._circuit_open_until:
            logger.info("Saptiva API circuit breaker reset")
            self._circuit_open = False
            self._failure_count = 0
            return False

        return True

    async def health_check(self) -> bool:
        """
        Check if Saptiva API is available and healthy.

        Makes a lightweight request to /v1/health endpoint.

        Returns:
            True if API is reachable and healthy, False otherwise
        """
        if not self.base_url or not self.api_key:
            return False

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/v1/health",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.debug(
                        "Saptiva health check passed",
                        status=result.get("status"),
                        version=result.get("version"),
                    )
                    return result.get("status") == "ok"

                return False

        except Exception as exc:
            logger.warning("Saptiva health check failed", error=str(exc))
            return False
```

---

## Testing Strategy

### Unit Tests

```python
# apps/api/tests/unit/test_saptiva_extractor.py

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from src.services.extractors.saptiva import SaptivaExtractor


@pytest.mark.asyncio
async def test_extract_pdf_success():
    """Should extract text from PDF via Saptiva API."""
    extractor = SaptivaExtractor(
        base_url="https://test.saptiva.ai",
        api_key="test-key",
    )

    mock_response = {
        "success": True,
        "pages": [
            {"page_number": 1, "text": "Page 1 text"},
            {"page_number": 2, "text": "Page 2 text"},
        ],
        "metadata": {"total_pages": 2},
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
        )

        text = await extractor.extract_text(
            media_type="pdf",
            data=b"%PDF test",
            mime="application/pdf",
        )

        assert text == "Page 1 text\n\nPage 2 text"


@pytest.mark.asyncio
async def test_extract_image_success():
    """Should extract text from image via Saptiva OCR."""
    extractor = SaptivaExtractor(
        base_url="https://test.saptiva.ai",
        api_key="test-key",
    )

    mock_response = {
        "success": True,
        "text": "OCR extracted text",
        "metadata": {"confidence": 0.95},
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
        )

        text = await extractor.extract_text(
            media_type="image",
            data=b"fake_image",
            mime="image/png",
        )

        assert text == "OCR extracted text"


@pytest.mark.asyncio
async def test_retry_on_transient_error():
    """Should retry on 429/500/503 errors."""
    extractor = SaptivaExtractor(
        base_url="https://test.saptiva.ai",
        api_key="test-key",
        max_retries=3,
    )

    # Mock: Fail twice, then succeed
    responses = [
        AsyncMock(status_code=503),  # Service unavailable
        AsyncMock(status_code=503),  # Service unavailable
        AsyncMock(
            status_code=200,
            json=lambda: {
                "success": True,
                "text": "Success after retries",
                "metadata": {},
            },
        ),
    ]

    with patch("httpx.AsyncClient.post", side_effect=responses):
        text = await extractor.extract_text(
            media_type="image",
            data=b"test",
            mime="image/png",
        )

        assert text == "Success after retries"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Should open circuit breaker after 5 consecutive failures."""
    extractor = SaptivaExtractor(
        base_url="https://test.saptiva.ai",
        api_key="test-key",
    )

    # Trigger 5 failures
    for _ in range(5):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ExtractionTimeoutError):
                await extractor.extract_text(
                    media_type="pdf",
                    data=b"test",
                    mime="application/pdf",
                )

    # 6th call should fail immediately due to circuit breaker
    with pytest.raises(ExtractionError, match="circuit breaker is open"):
        await extractor.extract_text(
            media_type="pdf",
            data=b"test",
            mime="application/pdf",
        )
```

---

## Deployment Checklist

### Environment Variables

```bash
# .env file
EXTRACTOR_PROVIDER=saptiva                      # Switch to Saptiva
SAPTIVA_BASE_URL=https://api.saptiva.com       # Production URL
SAPTIVA_API_KEY=sk_prod_xxxxxxxxxxxxxx         # Production API key
```

### Staging Deployment

1. **Update `.env` in staging:**
   ```bash
   EXTRACTOR_PROVIDER=saptiva
   SAPTIVA_BASE_URL=https://staging-api.saptiva.com
   SAPTIVA_API_KEY=sk_staging_xxxx
   ```

2. **Deploy and test:**
   ```bash
   docker-compose up -d api
   ```

3. **Manual smoke tests:**
   - Upload PDF → Verify extraction
   - Upload image → Verify OCR
   - Check logs for errors

4. **Monitor metrics:**
   - Extraction latency (p50, p95, p99)
   - Error rate
   - API cost per document

### Production Rollout

**Gradual rollout with feature flag:**

1. **Week 1: 5% traffic**
   ```python
   # config.py
   saptiva_rollout_percentage = 5  # 5% of users
   ```

2. **Week 2: 25% traffic**
3. **Week 3: 50% traffic**
4. **Week 4: 100% traffic**

**Monitoring:**
- Compare accuracy (manual sampling)
- Compare latency (p95)
- Compare costs
- Monitor error rates

**Rollback plan:**
```bash
# Instant rollback via environment variable
EXTRACTOR_PROVIDER=third_party
docker-compose restart api
```

---

## Cost Analysis

### Assumptions

- **Uploads per day:** 1,000 documents
- **Average pages per PDF:** 5 pages
- **Saptiva pricing (estimate):**
  - PDF extraction: $0.01 per page
  - Image OCR: $0.02 per image

### Monthly Cost Estimate

```
PDFs:
  800 PDFs/day × 5 pages = 4,000 pages/day
  4,000 pages × $0.01 = $40/day
  $40/day × 30 days = $1,200/month

Images:
  200 images/day × $0.02 = $4/day
  $4/day × 30 days = $120/month

Total: ~$1,320/month
```

**vs. Third-Party Costs:**
- Tesseract: Free (but requires compute)
- pypdf: Free (but limited accuracy)
- **Net cost increase:** $1,320/month

**Justification:**
- Better accuracy → better LLM responses
- Faster extraction → better UX
- No maintenance of OCR infrastructure

---

## Observability

### Key Metrics to Track

```python
# Log extraction metrics
logger.info(
    "extraction_metrics",
    provider="saptiva",
    media_type=media_type,
    file_size_bytes=len(data),
    extraction_time_ms=elapsed_ms,
    text_length=len(text),
    confidence=metadata.get("confidence"),
    api_cost_estimate=calculate_cost(media_type, pages),
)
```

**Dashboards to create:**
- Extraction latency by provider (third_party vs saptiva)
- Error rate by provider
- Cost per extraction
- Documents processed per day
- Circuit breaker triggers

---

## Summary

✅ **Architecture:** Backend-driven extraction at upload time
✅ **API:** POST /v1/extract/pdf and /v1/extract/image
✅ **Response Format:** Structured JSON with pages and metadata
✅ **Error Handling:** Retries + circuit breaker
✅ **Testing:** Unit tests with mocks
✅ **Deployment:** Gradual rollout with feature flag
✅ **Observability:** Comprehensive logging and metrics

**Status:** Ready for Phase 2 implementation 🚀
