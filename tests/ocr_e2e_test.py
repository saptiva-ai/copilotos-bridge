#!/usr/bin/env python3
"""
End-to-End OCR Test Script

Tests the complete flow:
1. Generate test image with clear text
2. Upload to document API
3. Send chat message asking about content
4. Verify LLM receives and uses OCR context

Usage:
    python tests/ocr_e2e_test.py
"""

import asyncio
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

# Test configuration
API_BASE_URL = "http://localhost:3001/api"
TEST_TEXT = "TESTING OCR EXTRACTION\nThis is a test document for validating OCR integration.\nModel: Saptiva CopilotOS\nDate: 2025-10-16"
TEST_IMAGE_PATH = "/tmp/ocr_test_image.png"
TEST_QUESTION = "¿Qué dice exactamente el texto de la imagen? Cita el contenido textual completo."

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_step(step: str, status: str = "info"):
    """Print colored step information."""
    color = {"info": BLUE, "success": GREEN, "error": RED, "warning": YELLOW}.get(status, RESET)
    print(f"{color}[{status.upper()}]{RESET} {step}")


def create_test_image(text: str, output_path: str) -> None:
    """Create a test image with clear text for OCR."""
    print_step(f"Creating test image: {output_path}", "info")

    # Create image with white background
    width, height = 800, 400
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Use default font (PIL will use a built-in font)
    try:
        # Try to use a better font if available
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        # Fallback to default font
        font = ImageFont.load_default()

    # Draw text in black
    y_offset = 50
    for line in text.split('\n'):
        draw.text((50, y_offset), line, fill='black', font=font)
        y_offset += 60

    # Save image
    image.save(output_path)
    print_step(f"✓ Image created: {width}x{height}px", "success")


async def register_test_user() -> dict:
    """Register a test user and return credentials."""
    print_step("Registering test user", "info")

    username = f"ocr-test-{int(time.time())}"
    email = f"{username}@test.local"
    password = "TestPass123!"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            },
            timeout=30.0
        )

        if response.status_code != 201:
            print_step(f"Failed to register user: {response.text}", "error")
            sys.exit(1)

        data = response.json()
        print_step(f"✓ User registered: {username}", "success")
        return {
            "username": username,
            "email": email,
            "password": password,
            "token": data["data"]["access_token"]
        }


async def upload_image(token: str, image_path: str) -> dict:
    """Upload test image to document API."""
    print_step(f"Uploading image: {image_path}", "info")

    async with httpx.AsyncClient() as client:
        with open(image_path, 'rb') as f:
            files = {'file': ('ocr_test.png', f, 'image/png')}
            headers = {'Authorization': f'Bearer {token}'}

            response = await client.post(
                f"{API_BASE_URL}/files/upload",
                files=files,
                headers=headers,
                timeout=60.0
            )

        if response.status_code != 201:
            print_step(f"Failed to upload image: {response.text}", "error")
            sys.exit(1)

        data = response.json()
        file_id = data.get("file_id") or data.get("doc_id")
        print_step(f"✓ Image uploaded: {file_id}", "success")
        print_step(f"  Status: {data.get('status')}", "info")
        print_step(f"  Pages: {data.get('pages')}", "info")

        return data


async def send_chat_message(token: str, file_id: str, message: str) -> dict:
    """Send chat message with file context."""
    print_step(f"Sending chat message with file context", "info")

    async with httpx.AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}

        response = await client.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "file_ids": [file_id],
                "model": "Saptiva Turbo"
            },
            headers=headers,
            timeout=60.0
        )

        if response.status_code != 200:
            print_step(f"Failed to send chat message: {response.text}", "error")
            sys.exit(1)

        data = response.json()
        print_step(f"✓ Chat response received", "success")
        return data


async def verify_redis_cache(file_id: str) -> bool:
    """Verify OCR text is in Redis cache."""
    print_step(f"Verifying Redis cache for file: {file_id}", "info")

    # Run redis-cli command in docker
    cmd = f'docker exec copilotos-redis redis-cli GET "doc:text:{file_id}"'

    import subprocess
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "(nil)":
        cached_text = result.stdout.strip()
        print_step(f"✓ Redis cache found: {len(cached_text)} chars", "success")
        print_step(f"  Preview: {cached_text[:100]}...", "info")
        return True
    else:
        print_step(f"✗ Redis cache not found or empty", "error")
        return False


def validate_llm_response(response_data: dict, expected_keywords: list) -> bool:
    """Validate that LLM response contains expected keywords from OCR."""
    print_step("Validating LLM response", "info")

    content = response_data.get("content", "")

    print_step(f"Response length: {len(content)} chars", "info")
    print_step(f"Response preview:\n{content[:500]}...", "info")

    found_keywords = []
    missing_keywords = []

    for keyword in expected_keywords:
        if keyword.lower() in content.lower():
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    if found_keywords:
        print_step(f"✓ Found keywords: {', '.join(found_keywords)}", "success")

    if missing_keywords:
        print_step(f"⚠ Missing keywords: {', '.join(missing_keywords)}", "warning")

    # Consider test passed if at least 50% of keywords are found
    success_rate = len(found_keywords) / len(expected_keywords) if expected_keywords else 0

    if success_rate >= 0.5:
        print_step(f"✓ Validation passed: {success_rate*100:.0f}% keywords found", "success")
        return True
    else:
        print_step(f"✗ Validation failed: only {success_rate*100:.0f}% keywords found", "error")
        return False


async def main():
    """Run end-to-end OCR test."""
    print("\n" + "="*80)
    print(f"{BLUE}OCR END-TO-END TEST{RESET}")
    print("="*80 + "\n")

    try:
        # Step 1: Create test image
        create_test_image(TEST_TEXT, TEST_IMAGE_PATH)

        # Wait a bit to ensure file is written
        await asyncio.sleep(0.5)

        # Step 2: Register test user
        user = await register_test_user()

        # Step 3: Upload image
        upload_result = await upload_image(user["token"], TEST_IMAGE_PATH)
        file_id = upload_result.get("file_id") or upload_result.get("doc_id")

        # Wait for processing
        print_step("Waiting for OCR processing (3s)...", "info")
        await asyncio.sleep(3)

        # Step 4: Verify Redis cache
        cache_ok = await verify_redis_cache(file_id)

        # Step 5: Send chat message
        chat_response = await send_chat_message(user["token"], file_id, TEST_QUESTION)

        # Step 6: Validate LLM response
        expected_keywords = ["TESTING", "OCR", "EXTRACTION", "Saptiva", "CopilotOS"]
        llm_ok = validate_llm_response(chat_response, expected_keywords)

        # Summary
        print("\n" + "="*80)
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print("="*80)
        print(f"{'Image Creation:':<30} {GREEN}✓ PASS{RESET}")
        print(f"{'User Registration:':<30} {GREEN}✓ PASS{RESET}")
        print(f"{'Image Upload:':<30} {GREEN}✓ PASS{RESET}")
        print(f"{'Redis Cache:':<30} {GREEN if cache_ok else RED}{'✓ PASS' if cache_ok else '✗ FAIL'}{RESET}")
        print(f"{'LLM Response:':<30} {GREEN if llm_ok else RED}{'✓ PASS' if llm_ok else '✗ FAIL'}{RESET}")

        if cache_ok and llm_ok:
            print(f"\n{GREEN}✓ ALL TESTS PASSED{RESET}")
            print(f"\n{GREEN}OCR → Redis → LLM pipeline is working correctly!{RESET}\n")
            return 0
        else:
            print(f"\n{RED}✗ SOME TESTS FAILED{RESET}\n")
            return 1

    except Exception as e:
        print_step(f"Test failed with error: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if Path(TEST_IMAGE_PATH).exists():
            Path(TEST_IMAGE_PATH).unlink()
            print_step(f"Cleaned up test image: {TEST_IMAGE_PATH}", "info")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
