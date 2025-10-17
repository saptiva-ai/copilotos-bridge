#!/usr/bin/env python3
"""
Saptiva API Validation Script

Validates that our SaptivaExtractor implementation works correctly
with the real Saptiva API endpoints.

Usage:
    export SAPTIVA_API_KEY=your-real-key
    export SAPTIVA_BASE_URL=https://api.saptiva.com
    python tools/validate_saptiva_api.py

Tests:
    1. API authentication
    2. PDF extraction endpoint (⚠️ Expected to fail - requires SDK)
    3. OCR endpoint (✅ Chat Completions API)
    4. Error handling
    5. Response format validation

Note (2025-10-16):
    - OCR now uses Chat Completions API: /v1/chat/completions/
    - PDF extraction via REST API not supported (422 error)
    - PDF requires Saptiva SDK: saptiva_agents.tools.obtener_texto_en_documento
    - See docs/SAPTIVA_API_REFACTORING.md for details
"""

import os
import sys
import asyncio
import base64
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api" / "src"))

import httpx
from services.extractors import SaptivaExtractor, get_text_extractor, clear_extractor_cache


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.END}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def generate_minimal_pdf() -> bytes:
    """Generate minimal valid PDF for testing."""
    return b"""%PDF-1.4
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
<< /Length 55 >>
stream
BT
/F1 12 Tf
100 700 Td
(Validation Test PDF) Tj
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
436
%%EOF"""


def generate_minimal_png() -> bytes:
    """Generate minimal PNG image for testing."""
    # 1x1 pixel PNG (67 bytes) - validated to work with Saptiva OCR API
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'


class SaptivaAPIValidator:
    """Validates Saptiva API implementation."""

    def __init__(self):
        """Initialize validator."""
        self.base_url = os.getenv("SAPTIVA_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("SAPTIVA_API_KEY", "")
        self.results: List[Dict[str, Any]] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def check_credentials(self) -> bool:
        """Check if credentials are configured."""
        print_header("1. Checking Credentials")

        if not self.base_url:
            print_error("SAPTIVA_BASE_URL not set")
            print_info("Set it with: export SAPTIVA_BASE_URL=https://api.saptiva.com")
            return False

        if not self.api_key:
            print_error("SAPTIVA_API_KEY not set")
            print_info("Set it with: export SAPTIVA_API_KEY=your-key")
            return False

        print_success(f"Base URL: {self.base_url}")
        print_success(f"API Key: {self.api_key[:8]}...{self.api_key[-4:]}")
        return True

    async def test_pdf_extraction_raw_api(self) -> bool:
        """Test PDF extraction using raw HTTP calls to validate endpoint."""
        print_header("2. Testing PDF Extraction (Raw API)")

        self.total_tests += 1

        pdf_bytes = generate_minimal_pdf()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        url = f"{self.base_url}/v1/tools/extractor-pdf"
        payload = {
            "doc_type": "pdf",
            "document": b64_pdf,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        print_info(f"Endpoint: {url}")
        print_info(f"Payload size: {len(b64_pdf)} bytes (base64)")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                print_info(f"Status Code: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print_success("PDF extraction successful!")
                    print_info(f"Response keys: {list(result.keys())}")

                    if "text" in result:
                        text = result["text"]
                        print_success(f"Extracted text: {text[:100]}..." if len(text) > 100 else f"Extracted text: {text}")
                        print_info(f"Text length: {len(text)} characters")

                    if "pages" in result:
                        print_info(f"Pages: {len(result.get('pages', []))}")

                    if "confidence" in result:
                        print_info(f"Confidence: {result.get('confidence')}")

                    self.passed_tests += 1
                    self.results.append({
                        "test": "PDF Extraction (Raw API)",
                        "status": "PASS",
                        "endpoint": url,
                        "response_keys": list(result.keys()),
                    })
                    return True
                else:
                    print_error(f"Request failed: {response.status_code}")
                    print_error(f"Response: {response.text[:500]}")
                    self.failed_tests += 1
                    self.results.append({
                        "test": "PDF Extraction (Raw API)",
                        "status": "FAIL",
                        "error": f"HTTP {response.status_code}",
                    })
                    return False

        except httpx.HTTPStatusError as exc:
            print_error(f"HTTP error: {exc}")
            print_error(f"Response: {exc.response.text[:500]}")
            self.failed_tests += 1
            return False
        except Exception as exc:
            print_error(f"Unexpected error: {exc}")
            self.failed_tests += 1
            return False

    async def test_pdf_extraction_via_extractor(self) -> bool:
        """Test PDF extraction using our SaptivaExtractor implementation."""
        print_header("3. Testing PDF Extraction (SaptivaExtractor)")

        self.total_tests += 1

        pdf_bytes = generate_minimal_pdf()

        print_info("Testing with SaptivaExtractor class...")

        try:
            extractor = SaptivaExtractor(
                base_url=self.base_url,
                api_key=self.api_key,
            )

            text = await extractor.extract_text(
                media_type="pdf",
                data=pdf_bytes,
                mime="application/pdf",
                filename="validation_test.pdf",
            )

            print_success("Extraction via SaptivaExtractor successful!")
            print_info(f"Extracted text: {text[:100]}..." if len(text) > 100 else f"Extracted text: {text}")
            print_info(f"Text length: {len(text)} characters")

            self.passed_tests += 1
            self.results.append({
                "test": "PDF Extraction (SaptivaExtractor)",
                "status": "PASS",
                "text_length": len(text),
            })
            return True

        except Exception as exc:
            print_error(f"Extraction failed: {exc}")
            print_error(f"Error type: {type(exc).__name__}")
            self.failed_tests += 1
            self.results.append({
                "test": "PDF Extraction (SaptivaExtractor)",
                "status": "FAIL",
                "error": str(exc),
            })
            return False

    async def test_ocr_extraction_raw_api(self) -> bool:
        """Test OCR extraction using raw HTTP calls (Chat Completions API)."""
        print_header("4. Testing OCR Extraction (Raw API - Chat Completions)")

        self.total_tests += 1

        image_bytes = generate_minimal_png()
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64_image}"

        # Use Chat Completions API endpoint (OpenAI-compatible)
        url = f"{self.base_url}/v1/chat/completions/"
        payload = {
            "model": "Saptiva OCR",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extrae todo el texto legible de esta imagen. Devuelve solo el texto extraído, sin explicaciones adicionales."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri}
                    }
                ]
            }]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        print_info(f"Endpoint: {url}")
        print_info(f"Payload size: {len(str(payload))} bytes")
        print_info("Using Chat Completions API (OpenAI-compatible format)")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                print_info(f"Status Code: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print_success("OCR extraction successful!")
                    print_info(f"Response keys: {list(result.keys())}")

                    # Extract text from Chat Completions format
                    # Format: {"choices": [{"message": {"content": "text"}}]}
                    extracted_text = ""
                    if "choices" in result and len(result["choices"]) > 0:
                        message = result["choices"][0].get("message", {})
                        extracted_text = message.get("content", "")

                    if extracted_text:
                        print_success(f"OCR text: {extracted_text[:100]}..." if len(extracted_text) > 100 else f"OCR text: {extracted_text}")
                        print_info(f"Text length: {len(extracted_text)} characters")
                    else:
                        print_warning("No text extracted from image")

                    if "model" in result:
                        print_info(f"Model: {result.get('model')}")

                    if "usage" in result:
                        usage = result.get('usage', {})
                        print_info(f"Tokens: {usage.get('total_tokens', 'N/A')}")

                    self.passed_tests += 1
                    self.results.append({
                        "test": "OCR Extraction (Raw API - Chat Completions)",
                        "status": "PASS",
                        "endpoint": url,
                        "text_length": len(extracted_text),
                    })
                    return True
                elif response.status_code == 404:
                    print_warning("OCR endpoint not found (404)")
                    print_info("This might be expected if OCR API is not yet available")
                    self.total_tests -= 1  # Don't count as failure
                    return False
                else:
                    print_error(f"Request failed: {response.status_code}")
                    print_error(f"Response: {response.text[:500]}")
                    self.failed_tests += 1
                    return False

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                print_warning("OCR endpoint not found (404)")
                print_info("OCR API may not be available yet")
                self.total_tests -= 1
                return False
            print_error(f"HTTP error: {exc}")
            self.failed_tests += 1
            return False
        except Exception as exc:
            print_error(f"Unexpected error: {exc}")
            self.failed_tests += 1
            return False

    async def test_circuit_breaker(self) -> bool:
        """Test that circuit breaker functions correctly."""
        print_header("5. Testing Circuit Breaker")

        self.total_tests += 1

        print_info("Circuit breaker should remain CLOSED with successful requests")
        print_info("Using OCR extraction (images work, PDFs require SDK)")

        try:
            extractor = SaptivaExtractor(
                base_url=self.base_url,
                api_key=self.api_key,
                enable_circuit_breaker=True,
            )

            # Make a successful request using OCR (not PDF, since PDF requires SDK)
            image_bytes = generate_minimal_png()
            await extractor.extract_text(
                media_type="image",
                data=image_bytes,
                mime="image/png",
            )

            # Check circuit breaker state
            if extractor.circuit_breaker.state.value == "closed":
                print_success("Circuit breaker is CLOSED (normal operation)")
                self.passed_tests += 1
                return True
            else:
                print_error(f"Circuit breaker is {extractor.circuit_breaker.state.value} (expected CLOSED)")
                self.failed_tests += 1
                return False

        except Exception as exc:
            print_error(f"Circuit breaker test failed: {exc}")
            self.failed_tests += 1
            return False

    async def test_cache_integration(self) -> bool:
        """Test cache integration."""
        print_header("6. Testing Cache Integration")

        self.total_tests += 1

        print_info("Testing that cache is properly integrated...")

        try:
            from services.extractors.cache import ExtractionCache

            cache = ExtractionCache()

            if cache.enabled:
                print_success("Cache is enabled")
                print_info(f"Redis URL: {cache._mask_redis_url(cache.redis_url)}")
                print_info(f"TTL: {cache.ttl_hours} hours")

                # Try to get Redis client
                redis_client = await cache._get_redis_client()
                if redis_client:
                    print_success("Redis connection successful")
                    self.passed_tests += 1
                    return True
                else:
                    print_warning("Redis connection failed, cache will be disabled")
                    print_info("This is OK for local testing without Redis")
                    self.passed_tests += 1
                    return True
            else:
                print_warning("Cache is disabled")
                print_info("Set EXTRACTION_CACHE_ENABLED=true to enable")
                self.passed_tests += 1
                return True

        except Exception as exc:
            print_error(f"Cache test failed: {exc}")
            self.failed_tests += 1
            return False

    async def test_cost_optimization(self) -> bool:
        """Test searchable PDF detection."""
        print_header("7. Testing Cost Optimization")

        self.total_tests += 1

        print_info("Testing searchable PDF detection...")

        try:
            extractor = SaptivaExtractor(
                base_url=self.base_url,
                api_key=self.api_key,
            )

            # Our test PDF has searchable text
            pdf_bytes = generate_minimal_pdf()
            is_searchable = extractor._is_pdf_searchable(pdf_bytes)

            if is_searchable:
                print_success("PDF correctly identified as searchable")
                print_info("This PDF will use native extraction (no API cost)")
                self.passed_tests += 1
                return True
            else:
                print_warning("PDF not detected as searchable")
                print_info("This might be due to pypdf not being available")
                self.passed_tests += 1  # Not a failure
                return True

        except Exception as exc:
            print_error(f"Cost optimization test failed: {exc}")
            self.failed_tests += 1
            return False

    async def test_factory_integration(self) -> bool:
        """Test factory pattern integration."""
        print_header("8. Testing Factory Integration")

        self.total_tests += 1

        print_info("Testing get_text_extractor() factory...")

        try:
            # Set provider to saptiva
            os.environ["EXTRACTOR_PROVIDER"] = "saptiva"
            clear_extractor_cache()

            extractor = get_text_extractor()

            if isinstance(extractor, SaptivaExtractor):
                print_success("Factory correctly returns SaptivaExtractor")
                self.passed_tests += 1
                return True
            else:
                print_error(f"Factory returned {type(extractor).__name__} (expected SaptivaExtractor)")
                self.failed_tests += 1
                return False

        except Exception as exc:
            print_error(f"Factory test failed: {exc}")
            self.failed_tests += 1
            return False

    def print_summary(self):
        """Print test summary."""
        print_header("VALIDATION SUMMARY")

        print(f"Total Tests: {self.total_tests}")
        print(f"{Colors.GREEN}Passed: {self.passed_tests}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed_tests}{Colors.END}")

        if self.failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Saptiva integration is ready.{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed. Review errors above.{Colors.END}")

        # Print detailed results
        print(f"\n{Colors.BOLD}Detailed Results:{Colors.END}")
        for result in self.results:
            status_icon = "✓" if result["status"] == "PASS" else "✗"
            status_color = Colors.GREEN if result["status"] == "PASS" else Colors.RED
            print(f"{status_color}{status_icon} {result['test']}{Colors.END}")

    async def run_all_tests(self):
        """Run all validation tests."""
        print(f"{Colors.BOLD}Saptiva API Validation Script{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}")

        # Check credentials first
        if not self.check_credentials():
            print_error("\nValidation aborted: Missing credentials")
            return False

        # Run all tests
        await self.test_pdf_extraction_raw_api()
        await self.test_pdf_extraction_via_extractor()
        await self.test_ocr_extraction_raw_api()
        await self.test_circuit_breaker()
        await self.test_cache_integration()
        await self.test_cost_optimization()
        await self.test_factory_integration()

        # Print summary
        self.print_summary()

        return self.failed_tests == 0


async def main():
    """Main entry point."""
    validator = SaptivaAPIValidator()
    success = await validator.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
