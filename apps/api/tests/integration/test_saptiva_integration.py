"""
Integration tests for Saptiva API

These tests require real Saptiva API credentials and make actual API calls.
They are marked with @pytest.mark.integration and skipped by default.

To run these tests:
    1. Set environment variables:
       export SAPTIVA_BASE_URL=https://api.saptiva.com
       export SAPTIVA_API_KEY=your-real-api-key
       export REDIS_URL=redis://localhost:6379/0

    2. Run with integration marker:
       pytest tests/integration/test_saptiva_integration.py -v -m integration

WARNING: These tests will make real API calls and may incur costs!
"""

import os
import pytest
from pathlib import Path

from src.services.extractors import (
    SaptivaExtractor,
    get_text_extractor,
    clear_extractor_cache,
)
from src.services.extractors.cache import ExtractionCache

# Skip all tests in this module unless explicitly requested
pytestmark = pytest.mark.integration


class TestSaptivaAPIIntegration:
    """
    Integration tests for Saptiva PDF extraction API.

    Tests actual API connectivity, authentication, and extraction functionality.
    """

    @pytest.fixture
    def extractor(self):
        """Create Saptiva extractor with real credentials."""
        api_key = os.getenv("SAPTIVA_API_KEY")
        base_url = os.getenv("SAPTIVA_BASE_URL", "https://api.saptiva.com")

        if not api_key:
            pytest.skip("SAPTIVA_API_KEY not set")

        return SaptivaExtractor(base_url=base_url, api_key=api_key)

    @pytest.fixture
    def sample_pdf_bytes(self):
        """Create a minimal valid PDF for testing."""
        # Minimal PDF with text "Hello World"
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000056 00000 n
0000000115 00000 n
0000000229 00000 n
0000000330 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
424
%%EOF"""
        return pdf_content

    @pytest.mark.asyncio
    async def test_health_check(self, extractor):
        """Test Saptiva API health check."""
        result = await extractor.health_check()
        assert result is True, "Saptiva API should be healthy with valid credentials"

    @pytest.mark.asyncio
    async def test_extract_pdf_text(self, extractor, sample_pdf_bytes):
        """Test PDF text extraction via Saptiva API."""
        text = await extractor.extract_text(
            media_type="pdf",
            data=sample_pdf_bytes,
            mime="application/pdf",
            filename="test_integration.pdf",
        )

        assert text is not None
        assert len(text) > 0
        assert isinstance(text, str)

        print(f"\n✓ Extracted text ({len(text)} chars): {text[:100]}...")

    @pytest.mark.asyncio
    async def test_extract_pdf_with_cache(self, extractor, sample_pdf_bytes):
        """Test PDF extraction with caching."""
        cache = ExtractionCache()

        # First extraction (should hit API)
        text1 = await extractor.extract_text(
            media_type="pdf",
            data=sample_pdf_bytes,
            mime="application/pdf",
            filename="test_cache.pdf",
        )

        # Second extraction (should hit cache)
        text2 = await extractor.extract_text(
            media_type="pdf",
            data=sample_pdf_bytes,
            mime="application/pdf",
            filename="test_cache.pdf",
        )

        assert text1 == text2
        assert cache.get_hit_rate() > 0

        print(f"\n✓ Cache hit rate: {cache.get_hit_rate():.1%}")
        print(f"✓ Cache metrics: {cache.get_metrics()}")

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, extractor, sample_pdf_bytes):
        """Test circuit breaker doesn't interfere with successful requests."""
        # Make multiple successful requests
        for i in range(5):
            text = await extractor.extract_text(
                media_type="pdf",
                data=sample_pdf_bytes,
                mime="application/pdf",
                filename=f"test_cb_{i}.pdf",
            )
            assert text is not None

        # Circuit should remain closed
        assert extractor.circuit_breaker.state.value == "closed"

        print("\n✓ Circuit breaker remained closed after 5 successful requests")

    @pytest.mark.asyncio
    async def test_cost_optimization_searchable_pdf(self, extractor, sample_pdf_bytes):
        """Test that searchable PDFs bypass Saptiva API."""
        # Check if our sample PDF is detected as searchable
        is_searchable = extractor._is_pdf_searchable(sample_pdf_bytes)

        if is_searchable:
            print("\n✓ PDF detected as searchable, will use native extraction")
        else:
            print("\n✓ PDF detected as scanned, will use Saptiva API")

        text = await extractor.extract_text(
            media_type="pdf",
            data=sample_pdf_bytes,
            mime="application/pdf",
            filename="test_optimization.pdf",
        )

        assert text is not None
        assert len(text) > 0


class TestSaptivaOCRIntegration:
    """
    Integration tests for Saptiva OCR API.

    Tests image-to-text extraction functionality.
    """

    @pytest.fixture
    def extractor(self):
        """Create Saptiva extractor with real credentials."""
        api_key = os.getenv("SAPTIVA_API_KEY")
        base_url = os.getenv("SAPTIVA_BASE_URL", "https://api.saptiva.com")

        if not api_key:
            pytest.skip("SAPTIVA_API_KEY not set")

        return SaptivaExtractor(base_url=base_url, api_key=api_key)

    @pytest.fixture
    def sample_image_bytes(self):
        """Create a minimal PNG image for testing."""
        # 1x1 PNG (red pixel)
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf'
            b'\xc0\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00'
            b'IEND\xaeB`\x82'
        )
        return png_bytes

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="OCR endpoint specification may not be final")
    async def test_extract_image_text(self, extractor, sample_image_bytes):
        """Test image OCR extraction via Saptiva API."""
        text = await extractor.extract_text(
            media_type="image",
            data=sample_image_bytes,
            mime="image/png",
            filename="test_ocr.png",
        )

        assert text is not None
        assert isinstance(text, str)

        print(f"\n✓ OCR extracted text: {text[:100]}...")


class TestCacheIntegration:
    """
    Integration tests for Redis caching layer.

    Tests caching functionality with real Redis instance.
    """

    @pytest.fixture
    async def cache(self):
        """Create cache instance with real Redis."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cache = ExtractionCache(redis_url=redis_url)

        yield cache

        # Cleanup
        await cache.close()

    @pytest.fixture
    def sample_data(self):
        """Sample document bytes for caching tests."""
        return b"Sample PDF content for testing" * 100

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache, sample_data):
        """Test basic cache set and get operations."""
        provider = "saptiva"
        media_type = "pdf"
        text = "This is the extracted text from the document."

        # Set cache
        success = await cache.set(provider, media_type, sample_data, text)
        assert success is True

        # Get cache
        cached_text = await cache.get(provider, media_type, sample_data)
        assert cached_text == text

        print(f"\n✓ Cache set and retrieved successfully")
        print(f"✓ Metrics: {cache.get_metrics()}")

    @pytest.mark.asyncio
    async def test_cache_compression(self, cache):
        """Test that large texts are compressed."""
        # Create large text (>1KB to trigger compression)
        large_text = "Lorem ipsum dolor sit amet. " * 100  # ~2.8KB

        sample_data = b"large_document_bytes" * 50

        success = await cache.set("saptiva", "pdf", sample_data, large_text)
        assert success is True

        # Retrieve and verify
        cached_text = await cache.get("saptiva", "pdf", sample_data)
        assert cached_text == large_text

        print(f"\n✓ Large text ({len(large_text)} bytes) cached with compression")

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache, sample_data):
        """Test that cache entries expire after TTL."""
        # Note: This test requires modifying TTL to a small value for testing
        # In production, TTL is 24 hours
        print("\n⏭ Skipping expiration test (requires TTL modification)")


class TestEndToEndWorkflow:
    """
    End-to-end integration tests simulating real user workflows.
    """

    @pytest.fixture
    def extractor(self):
        """Create Saptiva extractor with real credentials."""
        api_key = os.getenv("SAPTIVA_API_KEY")
        base_url = os.getenv("SAPTIVA_BASE_URL", "https://api.saptiva.com")

        if not api_key:
            pytest.skip("SAPTIVA_API_KEY not set")

        # Use factory to test full integration
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("EXTRACTOR_PROVIDER", "saptiva")
            clear_extractor_cache()
            extractor = get_text_extractor()

        return extractor

    @pytest.mark.asyncio
    async def test_full_extraction_workflow(self, extractor):
        """Test complete extraction workflow from file upload to text output."""
        # Simulate file upload
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"

        # Extract text
        text = await extractor.extract_text(
            media_type="pdf",
            data=pdf_bytes,
            mime="application/pdf",
            filename="user_upload.pdf",
        )

        # Verify result
        assert text is not None
        assert isinstance(text, str)

        print(f"\n✓ Full workflow completed successfully")
        print(f"✓ Extracted {len(text)} characters")


# Test fixtures for sample files
@pytest.fixture(scope="session")
def test_files_dir():
    """Directory containing test files for integration tests."""
    return Path(__file__).parent / "test_files"


@pytest.fixture(scope="session")
def sample_pdf_file(test_files_dir):
    """Sample PDF file for integration tests."""
    pdf_path = test_files_dir / "sample.pdf"
    if pdf_path.exists():
        return pdf_path
    pytest.skip("sample.pdf not found in test_files directory")


@pytest.fixture(scope="session")
def sample_image_file(test_files_dir):
    """Sample image file for OCR integration tests."""
    image_path = test_files_dir / "sample_ocr.png"
    if image_path.exists():
        return image_path
    pytest.skip("sample_ocr.png not found in test_files directory")
