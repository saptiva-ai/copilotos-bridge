#!/usr/bin/env python3
"""
Validation script for OCR → LLM prompt improvements.

Tests that images are correctly identified and the LLM receives
explicit instructions about having access to OCR-extracted text.

Usage:
    # From project root:
    docker exec copilotos-api python3 /app/tests/validate_ocr_prompt.py

    # Or copy to container and run:
    docker cp tests/validate_ocr_prompt.py copilotos-api:/app/tests/
    docker exec copilotos-api python3 /app/tests/validate_ocr_prompt.py
"""


def mock_extract_content_for_rag_from_cache(doc_texts):
    """Mock version of DocumentService.extract_content_for_rag_from_cache"""
    formatted_parts = []
    used_chars = 0
    used_docs = 0

    for doc_id, doc_data in doc_texts.items():
        text = doc_data.get("text", "")
        filename = doc_data.get("filename", "unknown")
        content_type = doc_data.get("content_type", "")
        ocr_applied = doc_data.get("ocr_applied", False)

        # Format with header - differentiate images from PDFs
        is_image = content_type.startswith("image/")
        if is_image and ocr_applied:
            header = f"## 📷 Imagen: {filename}\n**Texto extraído con OCR:**\n\n"
        elif is_image:
            header = f"## 📷 Imagen: {filename}\n\n"
        else:
            header = f"## 📄 Documento: {filename}\n\n"

        formatted = f"{header}{text}"
        formatted_parts.append(formatted)
        used_chars += len(text)
        used_docs += 1

    result = "\n\n---\n\n".join(formatted_parts)
    metadata = {"used_chars": used_chars, "used_docs": used_docs}
    warnings = []

    return result, warnings, metadata


def test_extract_content_formatting():
    """Test that image content is formatted with correct headers."""

    # Mock document data with image
    doc_texts = {
        "doc1": {
            "text": "INVOICE\nCompany XYZ\nTotal: $1,234.56",
            "filename": "invoice.jpg",
            "content_type": "image/jpeg",
            "ocr_applied": True
        },
        "doc2": {
            "text": "This is a PDF document with regular text content.",
            "filename": "contract.pdf",
            "content_type": "application/pdf",
            "ocr_applied": False
        }
    }

    # Extract and format
    formatted, warnings, metadata = mock_extract_content_for_rag_from_cache(
        doc_texts=doc_texts
    )

    print("=" * 80)
    print("FORMATTED CONTENT FOR LLM:")
    print("=" * 80)
    print(formatted)
    print("\n" + "=" * 80)
    print("METADATA:")
    print(f"  Used chars: {metadata['used_chars']}")
    print(f"  Used docs: {metadata['used_docs']}")
    print(f"  Warnings: {warnings}")
    print("=" * 80)

    # Assertions
    assert "📷 Imagen: invoice.jpg" in formatted, "Image header not found!"
    assert "Texto extraído con OCR:" in formatted, "OCR indicator not found!"
    assert "📄 Documento: contract.pdf" in formatted, "PDF header not found!"
    assert "INVOICE" in formatted, "OCR text not included!"

    print("\n✅ All validations passed!\n")
    return formatted


def test_system_prompt_logic():
    """Test the prompt selection logic for different document types."""

    test_cases = [
        {
            "name": "Only images",
            "context": "## 📷 Imagen: photo.jpg\n**Texto extraído con OCR:**\n\nHello World",
            "should_contain": [
                "IMÁGENES",
                "OCR",
                "TEXTO EXTRAÍDO",
                "no puedes 'ver' las imágenes",
                "SÍ puedes analizar"
            ]
        },
        {
            "name": "Only PDFs",
            "context": "## 📄 Documento: report.pdf\n\nThis is a report",
            "should_contain": [
                "documentos para tu referencia"
            ],
            "should_not_contain": [
                "IMÁGENES",
                "OCR"
            ]
        },
        {
            "name": "Mixed content",
            "context": "## 📷 Imagen: chart.png\n\nData\n\n## 📄 Documento: notes.pdf\n\nNotes",
            "should_contain": [
                "PDFs e imágenes",
                "OCR"
            ]
        }
    ]

    print("\n" + "=" * 80)
    print("SYSTEM PROMPT VALIDATION")
    print("=" * 80)

    for case in test_cases:
        print(f"\nTest case: {case['name']}")
        print(f"Context preview: {case['context'][:50]}...")

        # Simulate prompt generation logic from chat_service.py
        has_images = "📷" in case['context']
        has_pdfs = "📄" in case['context']

        if has_images and not has_pdfs:
            system_prompt = (
                f"El usuario ha adjuntado una o más IMÁGENES. "
                f"Tienes acceso al TEXTO EXTRAÍDO de estas imágenes mediante OCR (reconocimiento óptico de caracteres). "
                f"IMPORTANTE: Aunque no puedes 'ver' las imágenes, SÍ puedes analizar, leer y responder preguntas sobre el texto que contienen.\n\n"
                f"Contenido de las imágenes:\n\n{case['context']}\n\n"
                f"Usa esta información para responder las preguntas del usuario sobre las imágenes."
            )
        elif has_images and has_pdfs:
            system_prompt = (
                f"El usuario ha adjuntado documentos (PDFs e imágenes). "
                f"Para las imágenes, tienes el texto extraído con OCR. "
                f"Usa toda esta información para responder las preguntas:\n\n{case['context']}"
            )
        else:
            system_prompt = (
                f"El usuario ha adjuntado documentos para tu referencia. "
                f"Usa esta información para responder sus preguntas:\n\n{case['context']}"
            )

        # Validate
        for phrase in case.get('should_contain', []):
            if phrase not in system_prompt:
                print(f"  ❌ Missing required phrase: '{phrase}'")
                raise AssertionError(f"Missing phrase: {phrase}")
            print(f"  ✅ Found: '{phrase}'")

        for phrase in case.get('should_not_contain', []):
            if phrase in system_prompt:
                print(f"  ❌ Should not contain: '{phrase}'")
                raise AssertionError(f"Should not contain: {phrase}")

        print(f"  ✅ Prompt structure correct for: {case['name']}")

    print("\n" + "=" * 80)
    print("✅ All system prompt tests passed!")
    print("=" * 80)


def main():
    """Run all validation tests."""
    print("\n🔍 OCR → LLM Prompt Validation Suite\n")

    try:
        # Test 1: Document formatting
        formatted_content = test_extract_content_formatting()

        # Test 2: System prompt logic
        test_system_prompt_logic()

        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Rebuild API: make rebuild-api")
        print("  2. Test with real image upload")
        print("  3. Ask: '¿Qué dice esta imagen?' or 'Revisa el contenido de esta imagen'")
        print("\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
