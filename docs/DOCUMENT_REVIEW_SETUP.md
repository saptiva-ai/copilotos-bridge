# Document Review System - Setup Guide

Quick setup guide for the document review system external dependencies.

## Prerequisites

- Docker and Docker Compose installed
- Ports 8010 (LanguageTool) and 9000-9001 (MinIO) available

## 1. Setup External Services

### Option A: Docker Compose (Recommended)

Create `docker-compose.services.yml` in project root:

```yaml
version: '3.8'

services:
  # LanguageTool - Grammar and Spelling Checker
  languagetool:
    image: erikvl87/languagetool:latest
    container_name: copilotos-languagetool
    ports:
      - "8010:8010"
    environment:
      - langtool_languageModel=/ngrams
      - Java_Xms=512m
      - Java_Xmx=1g
    volumes:
      - languagetool-ngrams:/ngrams
    restart: unless-stopped

  # MinIO - S3-Compatible Object Storage
  minio:
    image: minio/minio:latest
    container_name: copilotos-minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  languagetool-ngrams:
  minio-data:
```

Start services:
```bash
docker compose -f docker-compose.services.yml up -d
```

### Option B: Standalone Docker

**LanguageTool:**
```bash
docker run -d \
  --name languagetool \
  -p 8010:8010 \
  -e langtool_languageModel=/ngrams \
  erikvl87/languagetool:latest
```

**MinIO:**
```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

## 2. Configure MinIO

### Create Bucket

**Option 1: MinIO Console (UI)**
1. Open http://localhost:9001
2. Login: minioadmin / minioadmin
3. Click "Buckets" → "Create Bucket"
4. Name: `documents`
5. Click "Create Bucket"

**Option 2: MinIO Client (mc)**
```bash
# Install mc
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure alias
mc alias set local http://localhost:9000 minioadmin minioadmin

# Create bucket
mc mb local/documents

# Verify
mc ls local
```

**Option 3: Python Script**
```python
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# Create bucket if not exists
if not client.bucket_exists("documents"):
    client.make_bucket("documents")
    print("✓ Bucket 'documents' created")
else:
    print("✓ Bucket 'documents' already exists")
```

## 3. Configure Environment Variables

Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
```

Verify these variables in `.env`:
```env
# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_DOCUMENTS=documents

# LanguageTool
LANGUAGETOOL_URL=http://localhost:8010

# Feature Flags
FEATURE_DOCUMENT_REVIEW_ENABLED=true
NEXT_PUBLIC_FEATURE_DOCUMENT_REVIEW=true
```

## 4. Install Python Dependencies

```bash
cd apps/api
pip install -r requirements.txt
```

This will install:
- `minio>=7.2.0` - MinIO client
- `httpx>=0.25.2` - HTTP client (already installed)
- `sse-starlette>=1.8.2` - SSE support (already installed)

## 5. Verify Setup

### Check LanguageTool

```bash
curl http://localhost:8010/v2/check \
  -d "text=Hola mundo" \
  -d "language=es"
```

Expected: JSON response with language analysis

### Check MinIO

```bash
curl http://localhost:9000/minio/health/live
```

Expected: Empty 200 OK response

### Check MinIO Console

Open: http://localhost:9001
- Username: minioadmin
- Password: minioadmin

Should see MinIO dashboard with `documents` bucket

## 6. Test Document Review API

### Upload Document

```bash
TOKEN="your-jwt-token"

curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"
```

Expected response:
```json
{
  "doc_id": "abc123...",
  "filename": "test.pdf",
  "total_pages": 3,
  "status": "ready"
}
```

### Start Review

```bash
curl -X POST http://localhost:8000/api/review/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "abc123...",
    "model": "Saptiva Turbo"
  }'
```

Expected response:
```json
{
  "job_id": "rev-xyz...",
  "status": "QUEUED"
}
```

### Monitor Progress (SSE)

```bash
curl http://localhost:8000/api/review/events/rev-xyz... \
  -H "Authorization: Bearer $TOKEN"
```

Expected: Stream of SSE events with status updates

### Get Report

```bash
curl http://localhost:8000/api/review/report/abc123... \
  -H "Authorization: Bearer $TOKEN"
```

Expected: JSON with spelling, grammar, style, rewrites, and color audit results

## 7. Troubleshooting

### LanguageTool Not Responding

**Check container:**
```bash
docker logs languagetool
```

**Common issues:**
- Out of memory: Increase Java heap size
- Port conflict: Change 8010 to another port
- Language model missing: Pull ngrams volume

**Fix:**
```bash
docker restart languagetool
```

### MinIO Connection Failed

**Check container:**
```bash
docker logs minio
```

**Common issues:**
- Bucket doesn't exist: Create `documents` bucket
- Wrong credentials: Check MINIO_ACCESS_KEY/SECRET_KEY
- Port conflict: Change 9000/9001 to other ports

**Fix:**
```bash
docker restart minio
```

### Upload Fails with 413 (File Too Large)

**Backend**: Check MAX_UPLOAD_SIZE_MB in .env (default: 50MB)

**Nginx/Proxy**: Add `client_max_body_size 50M;`

### Review Fails at LT_GRAMMAR Stage

**Check LanguageTool:**
```bash
curl http://localhost:8010/v2/languages
```

Should return list of supported languages including Spanish (`es`)

### MinIO Presigned URLs Fail

**Issue**: URL not accessible from frontend

**Solution**: Update MINIO_ENDPOINT to use external IP instead of localhost
```env
MINIO_ENDPOINT=192.168.1.100:9000
```

## 8. Production Considerations

### Security

1. **Change default credentials:**
   ```env
   MINIO_ACCESS_KEY=your-secure-access-key
   MINIO_SECRET_KEY=your-secure-secret-key-min-32-chars
   ```

2. **Enable TLS:**
   ```env
   MINIO_SECURE=true
   ```

3. **Add bucket policy:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {"AWS": ["*"]},
         "Action": ["s3:GetObject"],
         "Resource": ["arn:aws:s3:::documents/*"]
       }
     ]
   }
   ```

### Performance

1. **LanguageTool**: Increase Java heap for large documents
   ```yaml
   environment:
     - Java_Xms=1g
     - Java_Xmx=4g
   ```

2. **MinIO**: Use dedicated volumes with SSDs
   ```yaml
   volumes:
     - /mnt/fast-storage/minio:/data
   ```

3. **Caching**: Enable Redis caching for review results

### Monitoring

1. **Health checks:**
   - LanguageTool: http://localhost:8010/v2/languages
   - MinIO: http://localhost:9000/minio/health/live

2. **Metrics:**
   - MinIO Prometheus: http://localhost:9000/minio/v2/metrics/cluster
   - Add to Prometheus scrape targets

3. **Alerts:**
   - Disk space < 20%
   - Service unavailable > 1 min
   - Error rate > 5%

## 9. Uninstall

```bash
# Stop and remove containers
docker compose -f docker-compose.services.yml down

# Remove volumes (CAUTION: deletes all documents)
docker volume rm copilotos-bridge_minio-data
docker volume rm copilotos-bridge_languagetool-ngrams
```

## 10. Alternative Deployments

### Using Managed Services

**MinIO**: Use AWS S3, Google Cloud Storage, or Azure Blob
**LanguageTool**: Deploy on dedicated server or use LanguageTool Cloud

Update environment variables accordingly.

## Support

- Backend API docs: http://localhost:8000/docs
- Full API documentation: `apps/api/src/routers/document_review_README.md`
- Issues: GitHub Issues
- Questions: #copilotos-dev Slack channel
