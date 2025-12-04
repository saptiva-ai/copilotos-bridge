
import asyncio
import sys
import os
from pathlib import Path

# Add apps/api/src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api/src")))

# Mock settings if needed, or rely on defaults
# We might need to mock get_settings if it relies on env vars that aren't set
from unittest.mock import MagicMock, patch

# Import the function to test
# We need to mock the dependencies that might fail in this standalone script context
# like database connections or complex config loading if they are imported at top level
# But let's try importing directly first.

try:
    from services.document_extraction import extract_text_from_file, _is_text_quality_sufficient
except ImportError as e:
    print(f"Error importing: {e}")
    # Try adjusting path again if needed
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
    from src.services.document_extraction import extract_text_from_file, _is_text_quality_sufficient

async def test_quality_function():
    print("\n--- Testing _is_text_quality_sufficient ---")
    
    good_text = "This is a normal sentence with some numbers 123."
    bad_text = "   123 "
    mixed_text = "Title:  Metadata 123"
    
    print(f"Good text: '{good_text}' -> {_is_text_quality_sufficient(good_text)}")
    print(f"Bad text: '{bad_text}' -> {_is_text_quality_sufficient(bad_text)}")
    print(f"Mixed text: '{mixed_text}' -> {_is_text_quality_sufficient(mixed_text)}")
    
    assert _is_text_quality_sufficient(good_text) == True
    assert _is_text_quality_sufficient(bad_text) == False
    print("Quality function logic verified.")

async def test_pdf_extraction():
    print("\n--- Testing extract_text_from_file ---")
    
    # Path to a scanned PDF
    # Use TEST_PDF env var or default to tests/fixtures/sample.pdf
    import os
    pdf_path = Path(os.getenv("TEST_PDF", "tests/fixtures/sample.pdf"))

    if not pdf_path.exists():
        print(f"PDF not found at {pdf_path}")
        print("Set TEST_PDF environment variable or ensure tests/fixtures/sample.pdf exists")
        return

    print(f"Testing with file: {pdf_path}")
    
    # We need to mock get_settings to ensure we don't need a full .env
    with patch("services.document_extraction.get_settings") as mock_settings:
        mock_settings.return_value.extractor_provider = "third_party"
        mock_settings.return_value.ocr_raster_dpi = 150
        
        # We also need to mock raster_single_page_and_ocr to avoid needing actual Tesseract installed/configured
        # if we just want to verify the LOGIC flow (i.e. that it DECIDES to use OCR).
        # However, seeing the actual OCR output is better. Let's try real execution first.
        # If Tesseract is missing, it will fail or log error.
        
        try:
            pages = await extract_text_from_file(pdf_path, "application/pdf")
            
            for page in pages:
                print(f"\nPage {page.page}:")
                print(f"Length: {len(page.text_md)}")
                print(f"Preview: {page.text_md[:100]}...")
                
                # Check if it looks like OCR was used (clean text) or garbage
                if "[Página" in page.text_md:
                    print("Result: Extraction Failed/Fallback")
                else:
                    print("Result: Text Extracted")
                    
        except Exception as e:
            print(f"Extraction failed with error: {e}")

async def main():
    with open("verification_results.log", "w") as f:
        sys.stdout = f
        sys.stderr = f
        print("Starting verification...")
        await test_quality_function()
        await test_pdf_extraction()
        print("Verification complete.")

if __name__ == "__main__":
    asyncio.run(main())
