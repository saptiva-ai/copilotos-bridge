"""E2E tests for document upload and review SSE endpoints."""

import asyncio
import json
from io import BytesIO

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from jose import jwt
from httpx import AsyncClient, ASGITransport
from fastapi import status

from apps.api.src.main import app
from apps.api.src.models.document import Document, DocumentStatus
from apps.api.src.models.review_job import ReviewJob, ReviewStatus
from apps.api.src.services.storage import storage
from apps.api.src.core.config import get_settings
from apps.api.src.core.database import Database
from apps.api.src.services.auth_service import register_user
from apps.api.src.core.exceptions import ConflictError
from apps.api.src.schemas.user import UserCreate

PDF_BYTES = b"""%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT\n/F1 24 Tf\n72 120 Td\n(Hello PDF) Tj\nET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n \n0000000122 00000 n \n0000000233 00000 n \n0000000333 00000 n \ntrailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n414\n%%EOF\n"""


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app_lifespan():
    await app.router.startup()
    yield
    await app.router.shutdown()


@pytest_asyncio.fixture
async def auth_token() -> str:
    get_settings.cache_clear()
    settings = get_settings()
    if Database.database is None:
        await Database.connect_to_mongo()

    try:
        await register_user(UserCreate(username="test-user", email="test@example.com", password="Demo1234"))
    except ConflictError:
        pass

    now = datetime.utcnow()
    payload = {
        "sub": "test-user",
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=1),
        "username": "test-user",
        "email": "test@example.com",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_upload_idempotency(auth_token):
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-Trace-Id": "test-trace",
        "Idempotency-Key": "demo-key",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        files_payload = [("files", ("sample.pdf", BytesIO(PDF_BYTES), "application/pdf"))]
        response = await client.post("/api/files/upload", headers=headers, files=files_payload)
        assert response.status_code == status.HTTP_201_CREATED
        first_data = response.json()
        first_file = first_data["files"][0]

        # Second request with same idempotency key should return identical payload
        files_payload = [("files", ("sample.pdf", BytesIO(PDF_BYTES), "application/pdf"))]
        response = await client.post("/api/files/upload", headers=headers, files=files_payload)
        assert response.status_code == status.HTTP_201_CREATED
        second_data = response.json()
        second_file = second_data["files"][0]

        assert first_file["file_id"] == second_file["file_id"]


@pytest.mark.asyncio
async def test_sse_requires_authorization(auth_token):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        # Without auth header should fail fast
        response = await client.get("/api/files/events/missing")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Create file + job owned by the authenticated user
        doc_id = "test-doc-sse"
        temp_path = storage.config.root / doc_id / "sample.pdf"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(PDF_BYTES)

        document = Document(
            id=doc_id,
            filename="sample.pdf",
            content_type="application/pdf",
            size_bytes=len(PDF_BYTES),
            minio_key=str(temp_path),
            minio_bucket="temp",
            status=DocumentStatus.READY,
            user_id="test-user",
        )
        await document.insert()

        job_id = "test-job-sse"
        job = ReviewJob(
            job_id=job_id,
            doc_id=str(document.id),
            user_id="test-user",
            status=ReviewStatus.RECEIVED,
        )
        await job.insert()

        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            async with client.stream("GET", f"/api/files/events/{job_id}", headers=headers) as response:
                assert response.status_code == status.HTTP_200_OK
                event_iter = response.aiter_lines()
                first_line = await asyncio.wait_for(event_iter.__anext__(), timeout=2)
                assert first_line.startswith("event: meta")
                data_line = await asyncio.wait_for(event_iter.__anext__(), timeout=2)
                assert data_line.startswith("data:")
                meta = json.loads(data_line.split("data:", 1)[1].strip())
                assert meta["status"] == "meta"
        finally:
            await ReviewJob.find_one(ReviewJob.job_id == job_id).delete()
            await Document.find_one(Document.id == document.id).delete()
            storage.delete_document(str(document.id))
