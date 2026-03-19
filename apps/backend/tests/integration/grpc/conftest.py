"""
Pytest configuration for gRPC integration tests.

This conftest is isolated from the main integration conftest to avoid
importing the full app, which requires MinIO, MongoDB, etc.

gRPC tests only need the gRPC client and don't require the FastAPI app.
"""

import os
import pytest
import pytest_asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent.parent / "envs" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set default gRPC connection parameters for tests
os.environ.setdefault("EMBEDDING_SERVICE_GRPC_HOST", "localhost")
os.environ.setdefault("EMBEDDING_SERVICE_GRPC_PORT", "50053")
os.environ.setdefault("FILE_MANAGER_GRPC_HOST", "localhost")
os.environ.setdefault("FILE_MANAGER_GRPC_PORT", "50052")


def is_grpc_service_available(host: str, port: int) -> bool:
    """Check if a gRPC service is available."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def embedding_service_grpc_available():
    """Check if embedding-service gRPC service is available."""
    host = os.getenv("EMBEDDING_SERVICE_GRPC_HOST", "localhost")
    port = int(os.getenv("EMBEDDING_SERVICE_GRPC_PORT", "50053"))
    return is_grpc_service_available(host, port)


@pytest.fixture(scope="session")
def file_manager_grpc_available():
    """Check if file-manager gRPC service is available."""
    host = os.getenv("FILE_MANAGER_GRPC_HOST", "localhost")
    port = int(os.getenv("FILE_MANAGER_GRPC_PORT", "50052"))
    return is_grpc_service_available(host, port)


