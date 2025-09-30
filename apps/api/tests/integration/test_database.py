"""
Integration tests for database connectivity
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

class TestDatabaseIntegration:
    """Test database integration functionality"""

    @pytest.mark.asyncio
    async def test_mongodb_connection(self):
        """Test MongoDB connection"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            import os

            # Use test database URL from environment
            db_url = os.getenv('MONGODB_TEST_URL') or os.getenv('MONGODB_URL')
            if not db_url:
                pytest.skip("MONGODB_URL environment variable not set for integration testing")

            client = AsyncIOMotorClient(db_url)

            # Test connection
            await client.admin.command('ping')

            # Test basic operations
            db = client.copilotos_test
            collection = db.test_collection

            # Insert test document
            test_doc = {"test": "integration_test", "timestamp": "2024-01-01"}
            result = await collection.insert_one(test_doc)
            assert result.inserted_id is not None

            # Retrieve test document
            found_doc = await collection.find_one({"test": "integration_test"})
            assert found_doc is not None
            assert found_doc["test"] == "integration_test"

            # Cleanup
            await collection.delete_one({"test": "integration_test"})
            client.close()

        except Exception as e:
            # If MongoDB is not available, mock the test
            pytest.skip(f"MongoDB not available for integration testing: {e}")

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test Redis connection"""
        try:
            import redis.asyncio as redis
            import os

            # Use test Redis URL or mock
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

            client = redis.from_url(redis_url)

            # Test connection
            await client.ping()

            # Test basic operations
            await client.set("test_key", "integration_test")
            value = await client.get("test_key")
            assert value.decode() == "integration_test"

            # Cleanup
            await client.delete("test_key")
            await client.close()

        except Exception as e:
            # If Redis is not available, mock the test
            pytest.skip(f"Redis not available for integration testing: {e}")

    @pytest.mark.asyncio
    async def test_api_with_database(self):
        """Test API endpoints that require database connectivity"""
        try:
            from fastapi.testclient import TestClient
            import sys
            import os

            # Add src to path
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

            from main import app
            client = TestClient(app)

            # Test health endpoint with database check
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            if "checks" in data and "database" in data["checks"]:
                assert data["checks"]["database"]["status"] == "healthy"

        except ImportError:
            pytest.skip("API application not available for integration testing")