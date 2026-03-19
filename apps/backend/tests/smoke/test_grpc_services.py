"""
Smoke tests for gRPC services.

Quick connectivity and health verification tests.
Run with: pytest -m smoke tests/smoke/

These tests are designed to be fast (<5s) and verify:
- Service is reachable
- Health endpoint responds
- Basic functionality works
"""

import os
import socket
import pytest

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.asyncio,
]


def tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    """Quick TCP connectivity check."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


class TestEmbeddingServiceGrpcSmoke:
    """Smoke tests for embedding-service gRPC."""

    GRPC_HOST = os.getenv("EMBEDDING_SERVICE_GRPC_HOST", "localhost")
    GRPC_PORT = int(os.getenv("EMBEDDING_SERVICE_GRPC_PORT", "50053"))

    @pytest.fixture
    def service_available(self):
        """Check if service is available."""
        if not tcp_check(self.GRPC_HOST, self.GRPC_PORT):
            pytest.skip(f"Embedding-service gRPC not available at {self.GRPC_HOST}:{self.GRPC_PORT}")
        return True

    def test_grpc_port_reachable(self, service_available):
        """Verify gRPC port is reachable."""
        assert tcp_check(self.GRPC_HOST, self.GRPC_PORT)

    async def test_grpc_health_check(self, service_available):
        """Verify gRPC health endpoint responds."""
        try:
            from src.clients.embedding_service_grpc import (
                EmbeddingServiceGrpcClient,
                is_grpc_available
            )
        except ImportError:
            pytest.skip("gRPC modules not available")

        if not is_grpc_available():
            pytest.skip("gRPC proto stubs not generated")

        client = EmbeddingServiceGrpcClient(
            host=self.GRPC_HOST,
            port=self.GRPC_PORT
        )

        try:
            result = await client.health_check()
            assert result["status"] in ["healthy", "degraded", "unhealthy"]
        finally:
            await client.close()


class TestFileManagerGrpcSmoke:
    """Smoke tests for file-manager gRPC."""

    GRPC_HOST = os.getenv("FILE_MANAGER_GRPC_HOST", "localhost")
    GRPC_PORT = int(os.getenv("FILE_MANAGER_GRPC_PORT", "50052"))

    @pytest.fixture
    def service_available(self):
        """Check if service is available."""
        if not tcp_check(self.GRPC_HOST, self.GRPC_PORT):
            pytest.skip(f"File-manager gRPC not available at {self.GRPC_HOST}:{self.GRPC_PORT}")
        return True

    def test_grpc_port_reachable(self, service_available):
        """Verify gRPC port is reachable."""
        assert tcp_check(self.GRPC_HOST, self.GRPC_PORT)


class TestAllGrpcServicesSmoke:
    """Comprehensive smoke test for all gRPC services."""

    SERVICES = [
        ("file-manager", os.getenv("FILE_MANAGER_GRPC_HOST", "localhost"), 50052),
        ("embedding-service", os.getenv("EMBEDDING_SERVICE_GRPC_HOST", "localhost"), 50053),
    ]

    def test_all_grpc_ports_summary(self):
        """Summary of all gRPC service availability."""
        results = {}
        for name, host, port in self.SERVICES:
            port = int(os.getenv(f"{name.upper().replace('-', '_')}_GRPC_PORT", str(port)))
            results[name] = {
                "host": host,
                "port": port,
                "available": tcp_check(host, port)
            }

        print("\n=== gRPC Services Status ===")
        for name, info in results.items():
            status = "✓" if info["available"] else "✗"
            print(f"  {status} {name}: {info['host']}:{info['port']}")

        # At least one service should be available in dev environment
        # This is informational, not a hard requirement
        available_count = sum(1 for info in results.values() if info["available"])
        print(f"\n  Total: {available_count}/{len(self.SERVICES)} services available")

        # Don't fail if no services available - this is informational
        # In CI, services may not be running
