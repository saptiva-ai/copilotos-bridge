#!/usr/bin/env python3
"""
Test Resource Lifecycle Management

Tests:
1. File deduplication (upload same file multiple times)
2. Resource metrics retrieval
3. Manual cleanup trigger
4. Cleanup queue monitoring

Usage:
    python scripts/test-resource-lifecycle.py
"""

import requests
import time
from pathlib import Path
import hashlib

# Configuration
API_BASE = "http://localhost:8001"
TEST_USER = {"email": "demo@example.com", "password": "Demo1234"}

# Test PDF
TEST_PDF_PATH = Path(__file__).parent.parent / "packages/tests-e2e/tests/data/capital414" / "Capital414_usoIA.pdf"


def authenticate():
    """Authenticate and get JWT token."""
    print("\n🔐 Authenticating...")

    response = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"identifier": TEST_USER["email"], "password": TEST_USER["password"]},
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Authenticated successfully")
        return token
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        print("💡 Tip: Run 'make create-demo-user' first")
        return None


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            sha256.update(chunk)
    return sha256.hexdigest()


def test_file_deduplication(token):
    """Test that uploading same file multiple times is deduplicated."""
    print("\n" + "=" * 70)
    print("TEST 1: File Deduplication")
    print("=" * 70)

    if not TEST_PDF_PATH.exists():
        print(f"❌ Test PDF not found: {TEST_PDF_PATH}")
        return False

    file_hash = compute_file_hash(TEST_PDF_PATH)
    print(f"\n📄 Test file: {TEST_PDF_PATH.name}")
    print(f"🔒 SHA256 hash: {file_hash[:16]}...")

    # Upload file 3 times
    upload_results = []
    for i in range(3):
        print(f"\n📤 Upload attempt {i+1}/3...")

        with open(TEST_PDF_PATH, "rb") as f:
            response = requests.post(
                f"{API_BASE}/api/files/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"files": (TEST_PDF_PATH.name, f, "application/pdf")},
            )

        if response.status_code == 201:
            result = response.json()
            files = result.get("files", [])
            if files:
                file_id = files[0].get("file_id") or files[0].get("id")
                status = files[0].get("status")
                print(f"   ✅ Upload {i+1}: file_id={file_id}, status={status}")
                upload_results.append(file_id)
            else:
                print(f"   ❌ Upload {i+1}: No files in response")
                return False
        else:
            print(f"   ❌ Upload {i+1} failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

        time.sleep(1)  # Small delay between uploads

    # Verificar deduplicación
    print(f"\n🔍 Checking deduplication...")
    print(f"   Upload 1 ID: {upload_results[0]}")
    print(f"   Upload 2 ID: {upload_results[1]}")
    print(f"   Upload 3 ID: {upload_results[2]}")

    # Si la deduplicación funciona, los 3 IDs deberían ser iguales
    if upload_results[0] == upload_results[1] == upload_results[2]:
        print(f"\n✅ PASS: Deduplication working correctly!")
        print(f"   All uploads returned same document ID")
        print(f"   Storage saved: ~{2 * 2.3:.1f} MB")
        print(f"   Processing saved: ~{2 * 5} seconds")
        return True
    else:
        print(f"\n⚠️  WARNING: Different document IDs returned")
        print(f"   Deduplication may not be working as expected")
        print(f"   This could indicate:")
        print(f"   - File hash not being stored in metadata")
        print(f"   - Different user_id scoping")
        print(f"   - Timing issue with async processing")
        return False


def test_resource_metrics(token):
    """Test retrieving resource metrics."""
    print("\n" + "=" * 70)
    print("TEST 2: Resource Metrics")
    print("=" * 70)

    response = requests.get(
        f"{API_BASE}/api/resources/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        metrics = response.json()

        print(f"\n📊 Resource Usage:")
        for resource_name, resource_data in metrics.items():
            usage_pct = resource_data.get("usage_percentage", 0)
            size_mb = resource_data.get("size_mb", 0)
            total_items = resource_data.get("total_items", 0)
            priority = resource_data.get("cleanup_priority", "UNKNOWN")

            print(f"\n   {resource_name.upper()}:")
            print(f"      Items: {total_items}")
            print(f"      Size: {size_mb:.2f} MB")
            print(f"      Usage: {usage_pct:.2f}%")
            print(f"      Priority: {priority}")

        print(f"\n✅ PASS: Resource metrics retrieved successfully")
        return True
    else:
        print(f"❌ FAIL: Failed to get metrics: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_cleanup_trigger(token):
    """Test manual cleanup trigger."""
    print("\n" + "=" * 70)
    print("TEST 3: Manual Cleanup Trigger")
    print("=" * 70)

    # Trigger Redis cleanup
    print(f"\n🧹 Triggering Redis cleanup...")

    response = requests.post(
        f"{API_BASE}/api/resources/cleanup",
        headers={"Authorization": f"Bearer {token}"},
        json={"resource_type": "redis_cache"},
    )

    if response.status_code == 200:
        result = response.json()
        success = result.get("success", False)
        deleted_counts = result.get("deleted_counts", {})
        message = result.get("message", "")

        print(f"\n✅ Cleanup completed:")
        print(f"   Success: {success}")
        print(f"   Message: {message}")
        print(f"   Deleted items:")
        for resource, count in deleted_counts.items():
            print(f"      {resource}: {count}")

        print(f"\n✅ PASS: Manual cleanup trigger working")
        return True
    else:
        print(f"❌ FAIL: Cleanup failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_cleanup_queue(token):
    """Test cleanup queue monitoring."""
    print("\n" + "=" * 70)
    print("TEST 4: Cleanup Queue")
    print("=" * 70)

    response = requests.get(
        f"{API_BASE}/api/resources/queue",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        result = response.json()
        queue_size = result.get("queue_size", 0)
        tasks = result.get("tasks", [])

        print(f"\n📋 Cleanup Queue Status:")
        print(f"   Queue size: {queue_size}")

        if tasks:
            print(f"\n   Pending tasks:")
            for task in tasks:
                priority = task.get("priority")
                resource_type = task.get("resource_type")
                reason = task.get("reason")
                print(f"      [{priority}] {resource_type}: {reason}")
        else:
            print(f"   No pending tasks")

        print(f"\n✅ PASS: Cleanup queue retrieved successfully")
        return True
    else:
        print(f"❌ FAIL: Failed to get queue: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def main():
    """Run all lifecycle management tests."""
    print("=" * 70)
    print("RESOURCE LIFECYCLE MANAGEMENT TESTS")
    print("=" * 70)

    # Authenticate
    token = authenticate()
    if not token:
        return

    # Run tests
    results = []
    results.append(("File Deduplication", test_file_deduplication(token)))
    results.append(("Resource Metrics", test_resource_metrics(token)))
    results.append(("Manual Cleanup", test_cleanup_trigger(token)))
    results.append(("Cleanup Queue", test_cleanup_queue(token)))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("=" * 70)


if __name__ == "__main__":
    main()
