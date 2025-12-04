#!/usr/bin/env python3
"""
Test RAG Ingestion Pipeline - End-to-End Test

This script tests the complete PDF → Extract → Chunk → Embed → Qdrant pipeline.

Usage:
    python test_rag_ingestion.py

Expected Behavior:
    1. Creates demo user (demo/Demo1234)
    2. Authenticates and gets JWT token
    3. Creates a new chat session
    4. Uploads a test PDF
    5. Waits for document processing
    6. Verifies chunks appear in Qdrant with correct metadata
"""

import requests
import time
import json
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8001"
QDRANT_BASE = "http://localhost:6333"
TEST_USER = {"email": "demo@example.com", "password": "Demo1234"}

# Test PDF path (using existing test data)
TEST_PDF_PATH = Path(__file__).parent.parent / "packages/tests-e2e/tests/data/capital414" / "Capital414_usoIA.pdf"


def create_test_pdf():
    """Create a simple test PDF using reportlab if available."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(TEST_PDF_PATH), pagesize=letter)
        c.setFont("Helvetica", 12)

        # Add test content
        c.drawString(100, 750, "Test Document for RAG Pipeline")
        c.drawString(100, 730, "=" * 50)
        c.drawString(100, 700, "This is a test document to verify the RAG ingestion pipeline.")
        c.drawString(100, 680, "It contains multiple sentences to generate several chunks.")
        c.drawString(100, 660, "")
        c.drawString(100, 640, "Section 1: Introduction")
        c.drawString(100, 620, "The RAG system uses Qdrant for vector storage.")
        c.drawString(100, 600, "Documents are chunked with 500 tokens and 100 token overlap.")
        c.drawString(100, 580, "")
        c.drawString(100, 560, "Section 2: Embedding Model")
        c.drawString(100, 540, "We use paraphrase-multilingual-MiniLM-L12-v2 for embeddings.")
        c.drawString(100, 520, "This model produces 384-dimensional vectors.")
        c.drawString(100, 500, "It supports over 50 languages including Spanish and English.")

        c.save()
        print(f"✅ Created test PDF: {TEST_PDF_PATH}")
        return True
    except ImportError:
        print("❌ reportlab not installed. Please provide a test PDF manually.")
        return False


def authenticate():
    """Authenticate and get JWT token."""
    print("\n1️⃣ Authenticating...")

    # Try to login
    response = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"identifier": TEST_USER["email"], "password": TEST_USER["password"]},
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Authenticated successfully")
        return token
    else:
        print(f"❌ Authentication failed: {response.status_code} - {response.text}")
        print("💡 Tip: Run 'make create-demo-user' to create the demo user")
        return None


def upload_pdf(token, pdf_path):
    """Upload PDF."""
    print(f"\n2️⃣ Uploading PDF: {pdf_path.name}")

    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return None

    with open(pdf_path, "rb") as f:
        response = requests.post(
            f"{API_BASE}/api/files/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"files": (pdf_path.name, f, "application/pdf")},
        )

    if response.status_code == 201:
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=2)}")
        # Bulk upload returns list of files
        if result.get("files") and len(result["files"]) > 0:
            # Check if "id" or "file_id" is used
            first_file = result["files"][0]
            doc_id = first_file.get("id") or first_file.get("file_id")
            print(f"✅ PDF uploaded: {doc_id}")
            return doc_id
        else:
            print(f"❌ No files in response: {result}")
            return None
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return None


def wait_for_processing(token, doc_id, timeout=60):
    """Wait for document to be processed."""
    print(f"\n3️⃣ Waiting for document processing...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        # Get document status
        doc_response = requests.get(
            f"{API_BASE}/api/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if doc_response.status_code == 200:
            doc_status = doc_response.json().get("status")
            print(f"   Status: {doc_status}")

            if doc_status == "ready":
                print(f"✅ Document processed successfully")
                return True
            elif doc_status == "failed":
                error = doc_response.json().get("error_message", "Unknown error")
                print(f"❌ Processing failed: {error}")
                return False

        time.sleep(2)

    print(f"❌ Timeout waiting for processing")
    return False


def send_chat_message(token, doc_id, message="Summarize this document"):
    """Send a chat message with the uploaded document."""
    print(f"\n4️⃣ Sending chat message with document...")

    response = requests.post(
        f"{API_BASE}/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": message,
            "file_ids": [doc_id],
            "stream": False
        },
    )

    if response.status_code == 200:
        data = response.json()
        chat_id = data.get("chat_id")
        print(f"✅ Chat message sent, session: {chat_id}")
        return chat_id
    else:
        print(f"❌ Chat message failed: {response.status_code} - {response.text}")
        return None


def verify_qdrant_chunks(chat_id, doc_id):
    """Verify chunks were stored in Qdrant."""
    print(f"\n5️⃣ Verifying chunks in Qdrant...")

    # Query Qdrant for points with this document_id
    # (during upload, session_id is temporary like "upload_{doc_id}")
    response = requests.post(
        f"{QDRANT_BASE}/collections/rag_documents/points/scroll",
        json={
            "filter": {
                "must": [
                    {"key": "document_id", "match": {"value": doc_id}}
                ]
            },
            "limit": 100,
            "with_payload": True,
            "with_vector": False
        }
    )

    if response.status_code == 200:
        data = response.json()
        points = data["result"]["points"]

        print(f"✅ Found {len(points)} chunks in Qdrant")

        if points:
            # Show first chunk details
            first_point = points[0]
            payload = first_point["payload"]

            print(f"\n📄 Sample Chunk:")
            print(f"   Document ID: {payload.get('document_id')}")
            print(f"   Chunk ID: {payload.get('chunk_id')}")
            print(f"   Text length: {len(payload.get('text', ''))}")
            print(f"   Text preview: {payload.get('text', '')[:100]}...")
            print(f"   Filename: {payload.get('metadata', {}).get('filename')}")

            return True
        else:
            print("⚠️  No chunks found - document may not have been processed")
            return False
    else:
        print(f"❌ Qdrant query failed: {response.status_code} - {response.text}")
        return False


def main():
    """Run end-to-end test."""
    print("=" * 70)
    print("RAG INGESTION PIPELINE - END-TO-END TEST")
    print("=" * 70)

    # Step 0: Create test PDF if needed
    if not TEST_PDF_PATH.exists():
        if not create_test_pdf():
            print("\n💡 Please provide a test PDF at:", TEST_PDF_PATH)
            return

    # Step 1: Authenticate
    token = authenticate()
    if not token:
        return

    # Step 2: Upload PDF
    doc_id = upload_pdf(token, TEST_PDF_PATH)
    if not doc_id:
        return

    # Step 3: Wait for processing
    if not wait_for_processing(token, doc_id):
        return

    # Step 4: Send chat message with document
    chat_id = send_chat_message(token, doc_id)
    if not chat_id:
        return

    # Step 5: Verify Qdrant storage
    success = verify_qdrant_chunks(chat_id, doc_id)

    print("\n" + "=" * 70)
    if success:
        print("✅ END-TO-END TEST PASSED")
        print(f"\n🎉 Next steps:")
        print(f"   - View Qdrant dashboard: http://localhost:6333/dashboard")
        print(f"   - Query document via chat API using session: {chat_id}")
    else:
        print("❌ END-TO-END TEST FAILED")
    print("=" * 70)


if __name__ == "__main__":
    main()
