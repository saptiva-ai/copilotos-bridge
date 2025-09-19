#!/usr/bin/env python3
"""
Test script for CopilotOS Bridge integration.
Tests all major endpoints and functionality.
"""

import asyncio
import json
import time
from typing import Dict, Any

import httpx


class IntegrationTester:
    """Integration test suite for CopilotOS Bridge"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results: Dict[str, Any] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def test_health_endpoint(self) -> bool:
        """Test the health endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/api/health")
            success = response.status_code == 200 and "healthy" in response.text
            self.test_results["health_check"] = {
                "success": success,
                "status_code": response.status_code,
                "response": response.json() if success else response.text
            }
            return success
        except Exception as e:
            self.test_results["health_check"] = {
                "success": False,
                "error": str(e)
            }
            return False

    async def test_chat_endpoint(self) -> bool:
        """Test the chat endpoint"""
        try:
            payload = {
                "message": "Hello, this is a test message",
                "model": "SAPTIVA_CORTEX",
                "temperature": 0.7,
                "stream": False
            }
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )

            success = response.status_code == 200
            result = response.json() if success else {"error": response.text}

            self.test_results["chat_endpoint"] = {
                "success": success,
                "status_code": response.status_code,
                "response": result
            }
            return success
        except Exception as e:
            self.test_results["chat_endpoint"] = {
                "success": False,
                "error": str(e)
            }
            return False

    async def test_deep_research_endpoint(self) -> bool:
        """Test the deep research endpoint"""
        try:
            payload = {
                "query": "What are the latest developments in AI language models?",
                "research_type": "deep_research",
                "stream": True,
                "params": {
                    "max_iterations": 2,
                    "budget": 5,
                    "depth_level": "medium"
                }
            }
            response = await self.client.post(
                f"{self.base_url}/api/deep-research",
                json=payload
            )

            success = response.status_code == 200
            result = response.json() if success else {"error": response.text}

            # If successful, also test task status
            task_id = None
            if success and "task_id" in result:
                task_id = result["task_id"]
                # Wait a moment and check task status
                await asyncio.sleep(1)
                status_response = await self.client.get(
                    f"{self.base_url}/api/deep-research/{task_id}"
                )
                result["status_check"] = {
                    "status_code": status_response.status_code,
                    "response": status_response.json() if status_response.status_code == 200 else status_response.text
                }

            self.test_results["deep_research_endpoint"] = {
                "success": success,
                "status_code": response.status_code,
                "response": result,
                "task_id": task_id
            }
            return success
        except Exception as e:
            self.test_results["deep_research_endpoint"] = {
                "success": False,
                "error": str(e)
            }
            return False

    async def test_streaming_endpoint(self) -> bool:
        """Test the streaming endpoint with mock data"""
        try:
            # First create a task
            task_creation_success = await self.test_deep_research_endpoint()
            if not task_creation_success:
                return False

            task_id = self.test_results["deep_research_endpoint"]["task_id"]
            if not task_id:
                return False

            # Test streaming with mock data
            async with self.client.stream(
                "GET",
                f"{self.base_url}/api/stream/{task_id}?use_mock=true",
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status_code != 200:
                    self.test_results["streaming_endpoint"] = {
                        "success": False,
                        "status_code": response.status_code,
                        "error": "Failed to start stream"
                    }
                    return False

                # Read first few events
                events = []
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        events.append(chunk.strip())
                        if len(events) >= 3:  # Just test first 3 events
                            break

                self.test_results["streaming_endpoint"] = {
                    "success": True,
                    "status_code": response.status_code,
                    "events_received": len(events),
                    "sample_events": events[:2]  # Store first 2 events as sample
                }
                return True

        except Exception as e:
            self.test_results["streaming_endpoint"] = {
                "success": False,
                "error": str(e)
            }
            return False

    async def test_sessions_endpoint(self) -> bool:
        """Test the sessions/history endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/api/sessions")
            success = response.status_code == 200
            result = response.json() if success else {"error": response.text}

            self.test_results["sessions_endpoint"] = {
                "success": success,
                "status_code": response.status_code,
                "response": result
            }
            return success
        except Exception as e:
            self.test_results["sessions_endpoint"] = {
                "success": False,
                "error": str(e)
            }
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        print("🧪 Starting CopilotOS Bridge Integration Tests...")

        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Chat Endpoint", self.test_chat_endpoint),
            ("Deep Research Endpoint", self.test_deep_research_endpoint),
            ("Streaming Endpoint", self.test_streaming_endpoint),
            ("Sessions Endpoint", self.test_sessions_endpoint),
        ]

        results = {
            "total_tests": len(tests),
            "passed": 0,
            "failed": 0,
            "tests": {}
        }

        for test_name, test_func in tests:
            print(f"🔍 Running {test_name}...")
            success = await test_func()

            if success:
                print(f"✅ {test_name} PASSED")
                results["passed"] += 1
            else:
                print(f"❌ {test_name} FAILED")
                results["failed"] += 1

            results["tests"][test_name] = self.test_results.get(
                test_name.lower().replace(" ", "_"),
                {"success": success}
            )

        # Calculate summary
        results["success_rate"] = (results["passed"] / results["total_tests"]) * 100
        results["overall_success"] = results["failed"] == 0

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "="*60)
        print("🧪 INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")

        if results["overall_success"]:
            print("\n🎉 ALL TESTS PASSED! Integration is working correctly.")
        else:
            print(f"\n⚠️  {results['failed']} test(s) failed. Check the details below:")

            for test_name, test_data in results["tests"].items():
                if not test_data.get("success", False):
                    print(f"\n❌ {test_name}:")
                    if "error" in test_data:
                        print(f"   Error: {test_data['error']}")
                    if "status_code" in test_data:
                        print(f"   Status Code: {test_data['status_code']}")


async def main():
    """Main test function"""
    # Test both local and production
    environments = [
        ("Production", "http://34.42.214.246:8001"),
        ("Local", "http://localhost:8001")
    ]

    for env_name, base_url in environments:
        print(f"\n{'='*20} TESTING {env_name.upper()} {'='*20}")

        async with IntegrationTester(base_url) as tester:
            results = await tester.run_all_tests()
            tester.print_summary(results)

            # Save results to file
            with open(f"integration_test_results_{env_name.lower()}.json", "w") as f:
                json.dump(results, f, indent=2, default=str)

            print(f"📁 Results saved to integration_test_results_{env_name.lower()}.json")


if __name__ == "__main__":
    asyncio.run(main())