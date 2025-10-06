#!/usr/bin/env python3
"""
Test script for Aletheia client with metrics validation
"""

import asyncio
import json
from uuid import uuid4
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.aletheia_client import get_aletheia_client


async def test_aletheia_client():
    """Test Aletheia client functionality and metrics"""

    print("🧪 Testing Aletheia Client...")

    async with await get_aletheia_client() as client:
        # Test health check
        print("\n1. Testing health check...")
        is_healthy = await client.health_check()
        print(f"   Health status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        # Show initial metrics
        print("\n2. Initial metrics:")
        metrics = client.get_metrics()
        print(f"   {json.dumps(metrics, indent=4)}")

        # Test research task
        print("\n3. Testing research task...")
        task_id = str(uuid4())
        user_id = "test-user-123"
        query = "What are the latest developments in AI research?"

        try:
            response = await client.start_research(
                query=query,
                task_id=task_id,
                user_id=user_id,
                params={"max_results": 5},
                context={"source": "test"}
            )

            print(f"   Research Response:")
            print(f"   - Task ID: {response.task_id}")
            print(f"   - Status: {response.status}")
            print(f"   - Message: {response.message}")

            if response.error:
                print(f"   - Error: {response.error}")

        except Exception as e:
            print(f"   ❌ Research task failed: {e}")

        # Test task status
        print("\n4. Testing task status...")
        try:
            status_response = await client.get_task_status(task_id)
            print(f"   Status Response:")
            print(f"   - Task ID: {status_response.task_id}")
            print(f"   - Status: {status_response.status}")
            print(f"   - Message: {status_response.message}")

        except Exception as e:
            print(f"   ❌ Status check failed: {e}")

        # Show final metrics
        print("\n5. Final metrics after tests:")
        final_metrics = client.get_metrics()
        print(f"   {json.dumps(final_metrics, indent=4)}")

        # Test metrics calculations
        print("\n6. Metrics validation:")
        print(f"   - Total requests: {final_metrics['total_requests']}")
        print(f"   - Success rate: {final_metrics['success_rate']}%")
        print(f"   - Failure rate: {final_metrics['failure_rate']}%")
        print(f"   - Average latency: {final_metrics['average_latency_ms']}ms")
        print(f"   - Availability: {final_metrics['availability']}")
        print(f"   - Last health check: {final_metrics['last_health_check']}")

        # Test circuit breaker status
        print("\n7. Circuit breaker status:")
        print(f"   - State: {client.circuit_breaker.state}")
        print(f"   - Failure count: {client.circuit_breaker.failure_count}")
        print(f"   - Last failure: {client.circuit_breaker.last_failure_time}")

    print("\n✅ Aletheia client test completed!")


if __name__ == "__main__":
    asyncio.run(test_aletheia_client())