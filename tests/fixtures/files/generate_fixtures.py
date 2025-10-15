#!/usr/bin/env python3
"""
Generate test fixtures for Files V1 E2E tests.

Generates:
- small.pdf: Valid PDF < 1MB
- document.pdf: Valid PDF with text content
- large.pdf: PDF > 10MB (for size limit testing)
- fake.exe: Fake executable for MIME validation
"""

import os
from pathlib import Path

# PDF template with actual structure
PDF_HEADER = b"%PDF-1.4\n"
PDF_CATALOG = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
PDF_PAGES = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
PDF_PAGE = b"""3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
"""
PDF_CONTENT = b"""4 0 obj
<< /Length 120 >>
stream
BT
/F1 24 Tf
50 700 Td
(Test PDF Document) Tj
0 -30 Td
(This is a test file for E2E testing.) Tj
ET
endstream
endobj
"""
PDF_FONT = b"""5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
"""
PDF_XREF = b"""xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000062 00000 n
0000000123 00000 n
0000000274 00000 n
0000000441 00000 n
trailer
<< /Root 1 0 R /Size 6 >>
startxref
524
%%EOF
"""


def generate_small_pdf(output_path: Path) -> None:
    """Generate a small valid PDF."""
    with open(output_path, "wb") as f:
        f.write(PDF_HEADER)
        f.write(PDF_CATALOG)
        f.write(PDF_PAGES)
        f.write(PDF_PAGE)
        f.write(PDF_CONTENT)
        f.write(PDF_FONT)
        f.write(PDF_XREF)

    size_kb = output_path.stat().st_size / 1024
    print(f"✓ Generated small.pdf ({size_kb:.2f} KB)")


def generate_document_pdf(output_path: Path) -> None:
    """Generate a PDF with more content."""
    # Same as small but with more text
    content = b"""4 0 obj
<< /Length 350 >>
stream
BT
/F1 18 Tf
50 750 Td
(Technical Documentation) Tj
0 -30 Td
/F1 12 Tf
(This document contains multiple pages and sections.) Tj
0 -25 Td
(Section 1: Introduction) Tj
0 -20 Td
(Lorem ipsum dolor sit amet, consectetur adipiscing elit.) Tj
0 -20 Td
(Section 2: Implementation) Tj
0 -20 Td
(The system processes files in three phases:) Tj
0 -20 Td
(1. Upload and validation) Tj
0 -20 Td
(2. Text extraction) Tj
0 -20 Td
(3. Caching and indexing) Tj
ET
endstream
endobj
"""

    with open(output_path, "wb") as f:
        f.write(PDF_HEADER)
        f.write(PDF_CATALOG)
        f.write(PDF_PAGES)
        f.write(PDF_PAGE)
        f.write(content)
        f.write(PDF_FONT)
        # Adjusted xref for longer content
        xref = b"""xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000062 00000 n
0000000123 00000 n
0000000274 00000 n
0000000681 00000 n
trailer
<< /Root 1 0 R /Size 6 >>
startxref
764
%%EOF
"""
        f.write(xref)

    size_kb = output_path.stat().st_size / 1024
    print(f"✓ Generated document.pdf ({size_kb:.2f} KB)")


def generate_large_pdf(output_path: Path, target_size_mb: int = 11) -> None:
    """Generate a PDF larger than 10MB."""
    target_bytes = target_size_mb * 1024 * 1024

    with open(output_path, "wb") as f:
        # Start with valid PDF structure
        f.write(PDF_HEADER)
        f.write(PDF_CATALOG)
        f.write(PDF_PAGES)
        f.write(PDF_PAGE)

        # Write large content stream
        padding_size = target_bytes - 1000  # Leave space for footer
        content_header = b"4 0 obj\n<< /Length " + str(padding_size).encode() + b" >>\nstream\n"
        f.write(content_header)

        # Fill with null bytes (valid PDF content)
        chunk_size = 1024 * 1024  # 1MB chunks
        for _ in range(padding_size // chunk_size):
            f.write(b"\x00" * chunk_size)
        remaining = padding_size % chunk_size
        if remaining:
            f.write(b"\x00" * remaining)

        f.write(b"\nendstream\nendobj\n")
        f.write(PDF_FONT)
        f.write(PDF_XREF)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Generated large.pdf ({size_mb:.2f} MB)")


def generate_fake_exe(output_path: Path) -> None:
    """Generate a fake executable for MIME validation testing."""
    # MZ header (DOS executable signature)
    exe_header = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xFF\xFF\x00\x00"
    exe_content = b"This is not a real executable, just a test file for MIME validation.\n"
    exe_content += b"DO NOT EXECUTE THIS FILE.\n" * 100  # Make it larger

    with open(output_path, "wb") as f:
        f.write(exe_header)
        f.write(exe_content)

    size_kb = output_path.stat().st_size / 1024
    print(f"✓ Generated fake.exe ({size_kb:.2f} KB)")


def main():
    """Generate all test fixtures."""
    print("Generating Files V1 E2E Test Fixtures")
    print("=" * 50)

    script_dir = Path(__file__).parent

    # Generate fixtures
    generate_small_pdf(script_dir / "small.pdf")
    generate_document_pdf(script_dir / "document.pdf")
    generate_large_pdf(script_dir / "large.pdf", target_size_mb=11)
    generate_fake_exe(script_dir / "fake.exe")

    print("=" * 50)
    print("✓ All fixtures generated successfully")
    print("\nFixtures location:", script_dir)
    print("\nTo regenerate: python generate_fixtures.py")


if __name__ == "__main__":
    main()
