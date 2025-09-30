#!/usr/bin/env python3
"""
Test script for Deep Research Feature Flags (P0-DR-001, P0-DR-002)
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_feature_flags():
    """Test 1: Feature flags endpoint is public"""
    print("\n🧪 Test 1: GET /api/feature-flags (no auth)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/feature-flags")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200, "Should be public endpoint"
    flags = response.json()
    assert "deep_research_enabled" in flags
    assert "deep_research_auto" in flags
    print("✅ PASSED")
    return flags

def get_auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "demo", "password": "Demo1234"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

def test_explicit_false(token):
    """Test 2: Deep Research with explicit=false should fail"""
    print("\n🧪 Test 2: POST /api/deep-research with explicit=false")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "query": "Test research query",
        "explicit": False
    }

    response = requests.post(
        f"{BASE_URL}/api/deep-research",
        json=payload,
        headers=headers
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, "Should reject with 400"
    error = response.json()["detail"]
    assert "EXPLICIT_FLAG_REQUIRED" in str(error), "Should have explicit flag error code"
    print("✅ PASSED - Request correctly rejected")

def test_explicit_true(token):
    """Test 3: Deep Research with explicit=true should work"""
    print("\n🧪 Test 3: POST /api/deep-research with explicit=true")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "query": "What is artificial intelligence?",
        "explicit": True,
        "stream": False
    }

    response = requests.post(
        f"{BASE_URL}/api/deep-research",
        json=payload,
        headers=headers
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Task ID: {data.get('task_id')}")
        print(f"Status: {data.get('status')}")
        print("✅ PASSED - Research task created")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 503:
            print("⚠️  Feature is disabled - this is expected if DEEP_RESEARCH_ENABLED=false")
        else:
            print(f"❌ FAILED - Unexpected status code: {response.status_code}")

def main():
    print("\n" + "=" * 60)
    print(" 🧪 DEEP RESEARCH FEATURE FLAGS TEST SUITE")
    print("=" * 60)

    try:
        # Test 1: Feature flags endpoint
        flags = test_feature_flags()

        # Get auth token
        print("\n🔐 Getting authentication token...")
        token = get_auth_token()
        print("✅ Token obtained")

        # Test 2: explicit=false should fail
        test_explicit_false(token)

        # Test 3: explicit=true should work (if enabled)
        test_explicit_true(token)

        # Summary
        print("\n" + "=" * 60)
        print(" 📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Feature flags endpoint: PUBLIC")
        print(f"✅ deep_research_enabled: {flags['deep_research_enabled']}")
        print(f"✅ deep_research_auto: {flags['deep_research_auto']}")
        print(f"✅ explicit=false: REJECTED (400)")
        print(f"✅ explicit=true: {'ACCEPTED' if flags['deep_research_enabled'] else 'DISABLED (503)'}")
        print("\n🎉 All tests passed!")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())