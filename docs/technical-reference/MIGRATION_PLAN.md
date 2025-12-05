# Plan de Migración: Arquitectura Plugin-First (Micro-Kernel)

> **Versión**: 2.0 (Plugin-First)
> **Fecha**: 2025-11-25
> **Status**: Ready for Implementation
> **Objetivo**: Transformar OctaviOS de monolito a Micro-Kernel con plugins públicos y privados

---

## Executive Summary

Esta migración transforma OctaviOS en una arquitectura **Micro-Kernel**:

| Capa | Responsabilidad | Visibilidad |
|------|-----------------|-------------|
| **Core (Kernel)** | Chat, Auth, Orquestación | Open Source |
| **Plugins Públicos** | File Manager, Web Browsing | Open Source |
| **Plugins Privados** | Capital414, Bank Advisor | Propietario |

**Beneficio clave**: Otros desarrolladores podrán crear sus propios "File Managers" (ej. Google Drive, AWS S3) y simplemente intercambiarlos.

---

## Arquitectura Objetivo

```
octavios-repo/
├── apps/
│   └── backend/                 # CORE (Orquestador ligero)
│       └── src/
│           ├── routers/         # Auth + proxy endpoints
│           ├── middleware/      # JWT, rate limiting
│           ├── clients/         # HTTP clients para plugins
│           └── domain/          # Chat logic only
│
├── plugins/
│   ├── public/                  # OPEN SOURCE
│   │   └── file-manager/        # Procesador de archivos (REST + MCP)
│   │   │   ├── src/
│   │   │   │   ├── services/    # MinIO, OCR, extraction
│   │   │   │   ├── routers/     # /upload, /download
│   │   │   │   └── mcp/         # read_file_text, extract_metadata
│   │   │   ├── Dockerfile
│   │   │   └── requirements.txt
│   │   └── deep-research/        # DeepReseach API(REST + MCP)
│   │   │   ├── src/
│   │   │   │   ├── services/    # Taavily
│   │   │   │   ├── routers/     # /research, /deepresearch
│   │   │   │   └── mcp/         # research, deepreseach
│   │   │   ├── Dockerfile
│   │   │   └── requirements.txt
│   │
│   └── private/                 # PROPIETARIO (gitignored/submódulos)
│       └── capital414/          
│       └── bajaware_invex/
│
├── apps/web/                    # Frontend (sin cambios)
└── infra/
    ├── docker-compose.yml
    └── nginx/
        └── nginx.dev.conf       # Ruteo: /api/v1/files/* → file-manager
```

---

## Estado Actual (Pre-Migración)

### Lo que YA EXISTE ✅

| Componente | Ubicación | Estado |
|------------|-----------|--------|
| Plugin Capital414 | `plugins/capital414-private/` | ✅ Completamente funcional |
| Backend monolito | `apps/api/` | 🟡 Contiene lógica de archivos |
| Docker Compose | `infra/docker-compose.yml` | ✅ 10 servicios |
| Red Docker | `octavios-network` | ✅ Configurada |

### Lo que SE DEBE MIGRAR

| Origen | Destino | Líneas |
|--------|---------|--------|
| `apps/api/src/services/storage.py` | `plugins/public/file-manager/` | 172 |
| `apps/api/src/services/minio_service.py` | `plugins/public/file-manager/` | 239 |
| `apps/api/src/services/minio_storage.py` | `plugins/public/file-manager/` | 632 |
| `apps/api/src/services/document_extraction.py` | `plugins/public/file-manager/` | 461 |
| `apps/api/src/services/file_ingest.py` | `plugins/public/file-manager/` | 593 |
| `apps/api/src/services/file_events.py` | `plugins/public/file-manager/` | 120 |
| `apps/api/src/services/ocr_service.py` | `plugins/public/file-manager/` | 150 |
| `apps/api/src/services/extractors/` | `plugins/public/file-manager/` | 363+ |
| **TOTAL** | | **~2,730** |

---

## FASE 1: Renombrar Core (apps/api → apps/backend)

### Objetivo
Estandarizar nomenclatura y preparar para arquitectura de plugins.

### Archivos a Modificar

```bash
# 1. Renombrar directorio
mv apps/api apps/backend

# 2. Actualizar Docker Compose
sed -i 's|apps/api|apps/backend|g' infra/docker-compose.yml
sed -i 's|apps/api|apps/backend|g' infra/docker-compose.dev.yml

# 3. Actualizar CI/CD
sed -i 's|apps/api|apps/backend|g' .github/workflows/*.yml

# 4. Actualizar Makefile
sed -i 's|apps/api|apps/backend|g' Makefile

# 5. Actualizar documentación
sed -i 's|apps/api|apps/backend|g' CLAUDE.md README.md
```

### Nota Importante
**Mantener el nombre del servicio Docker como `api`** para no romper:
- Nginx upstream: `server api:8001`
- Frontend proxy: `API_BASE_URL=http://api:8001`
- Inter-service networking

### Validación
```bash
make dev
make health
curl http://localhost:8001/api/health
```

---

## FASE 2: Crear Plugin Público "File Manager"

### 2.1 Estructura del Plugin

```
plugins/public/file-manager/
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI + FastMCP server
│   ├── config.py                   # Settings
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py              # ← Migrado
│   │   ├── minio_service.py        # ← Migrado
│   │   ├── minio_storage.py        # ← Migrado
│   │   ├── document_extraction.py  # ← Migrado
│   │   ├── file_ingest.py          # ← Migrado
│   │   ├── file_events.py          # ← Migrado
│   │   └── ocr_service.py          # ← Migrado
│   │
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py        # ← Migrado
│   │   ├── image_extractor.py      # ← Migrado
│   │   └── pdf_raster_ocr.py       # ← Migrado
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── upload.py               # POST /upload
│   │   ├── download.py             # GET /download/{id}
│   │   ├── metadata.py             # GET /metadata/{id}
│   │   └── health.py               # GET /health
│   │
│   └── mcp/
│       ├── __init__.py
│       ├── server.py               # FastMCP server
│       └── tools/
│           ├── __init__.py
│           ├── read_file_text.py   # Tool: read_file_text(file_id)
│           ├── extract_metadata.py # Tool: extract_metadata(file_id)
│           └── list_files.py       # Tool: list_user_files(user_id)
│
├── tests/
│   ├── __init__.py
│   ├── test_upload.py
│   ├── test_download.py
│   ├── test_extraction.py
│   └── test_mcp_tools.py
│
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

### 2.2 API del File Manager

#### REST Endpoints (Puerto 8001)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `POST` | `/upload` | Subir archivo | JWT forwarded |
| `GET` | `/download/{file_id}` | Descargar archivo | JWT forwarded |
| `GET` | `/metadata/{file_id}` | Obtener metadatos | JWT forwarded |
| `DELETE` | `/files/{file_id}` | Eliminar archivo | JWT forwarded |
| `POST` | `/extract` | Extraer texto | JWT forwarded |
| `GET` | `/health` | Health check | None |

#### MCP Tools (SSE)

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `read_file_text` | Extraer texto de documento | `file_id`, `pages?` |
| `extract_metadata` | Obtener metadatos | `file_id` |
| `list_user_files` | Listar archivos del usuario | `user_id`, `session_id?` |

### 2.3 main.py del File Manager

```python
# plugins/public/file-manager/src/main.py
"""
OctaviOS File Manager Plugin
Microservicio híbrido REST + MCP para gestión de archivos.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from .config import settings
from .routers import upload, download, metadata, health
from .services.minio_service import init_minio_client
from .mcp.server import mcp_app

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y cleanup del servicio."""
    logger.info("Starting File Manager plugin", port=settings.PORT)

    # Inicializar cliente MinIO
    await init_minio_client()

    yield

    logger.info("Shutting down File Manager plugin")


app = FastAPI(
    title="OctaviOS File Manager",
    description="Plugin público para gestión de archivos (REST + MCP)",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers REST
app.include_router(health.router, tags=["Health"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(download.router, prefix="/download", tags=["Download"])
app.include_router(metadata.router, prefix="/metadata", tags=["Metadata"])

# Montar MCP server
app.mount("/mcp", mcp_app)


@app.get("/")
async def root():
    return {
        "service": "file-manager",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "rest": "/docs",
            "mcp": "/mcp/sse",
            "health": "/health",
        }
    }
```

### 2.4 Dockerfile del File Manager

```dockerfile
# plugins/public/file-manager/Dockerfile
FROM python:3.11-slim

# Metadatos
LABEL maintainer="Saptiva Team"
LABEL description="OctaviOS File Manager Plugin"
LABEL version="1.0.0"

# Dependencias del sistema para OCR/PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/

# Variables de entorno
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Comando de inicio
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 2.5 requirements.txt del File Manager

```
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Storage
minio>=7.2.0
redis>=5.0.0

# File Processing
pypdf>=4.0.0
PyMuPDF>=1.23.0
python-magic>=0.4.27
pillow>=10.0.0
pytesseract>=0.3.10

# MCP
fastmcp>=0.1.0

# HTTP Client
httpx>=0.26.0

# Utilities
structlog>=24.1.0
python-multipart>=0.0.6
aiofiles>=23.2.0
```

---

## FASE 3: Refactorizar Core (Backend)

### 3.1 Crear FileManagerClient

```python
# apps/backend/src/clients/file_manager.py
"""
Cliente HTTP para comunicarse con el plugin file-manager.
Permite al Core delegar todas las operaciones de archivos.
"""
import httpx
from typing import Optional, BinaryIO, Dict, Any
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)


class FileMetadata(BaseModel):
    """Modelo de metadatos de archivo."""
    id: str
    filename: str
    size: int
    mime_type: str
    extracted_text: Optional[str] = None
    pages: Optional[int] = None
    user_id: str
    session_id: Optional[str] = None


class FileManagerClient:
    """Cliente HTTP para el plugin file-manager."""

    def __init__(self, base_url: str = "http://file-manager:8001"):
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,  # Uploads pueden ser lentos
            )
        return self._client

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        user_id: str,
        session_id: str,
        jwt_token: str,
    ) -> FileMetadata:
        """Subir archivo al File Manager."""
        client = await self._get_client()

        headers = {"Authorization": f"Bearer {jwt_token}"}
        files = {"file": (filename, file)}
        data = {"user_id": user_id, "session_id": session_id}

        logger.info("Uploading file to file-manager", filename=filename, user_id=user_id)

        response = await client.post(
            "/upload",
            files=files,
            data=data,
            headers=headers,
        )
        response.raise_for_status()

        return FileMetadata(**response.json())

    async def download(self, file_id: str, jwt_token: str) -> bytes:
        """Descargar archivo del File Manager."""
        client = await self._get_client()

        headers = {"Authorization": f"Bearer {jwt_token}"}

        logger.info("Downloading file from file-manager", file_id=file_id)

        response = await client.get(
            f"/download/{file_id}",
            headers=headers,
        )
        response.raise_for_status()

        return response.content

    async def get_metadata(self, file_id: str, jwt_token: str) -> FileMetadata:
        """Obtener metadatos del archivo."""
        client = await self._get_client()

        headers = {"Authorization": f"Bearer {jwt_token}"}

        response = await client.get(
            f"/metadata/{file_id}",
            headers=headers,
        )
        response.raise_for_status()

        return FileMetadata(**response.json())

    async def extract_text(self, file_id: str, jwt_token: str) -> str:
        """Extraer texto de un documento."""
        client = await self._get_client()

        headers = {"Authorization": f"Bearer {jwt_token}"}

        response = await client.post(
            "/extract",
            json={"file_id": file_id},
            headers=headers,
        )
        response.raise_for_status()

        return response.json().get("text", "")

    async def delete(self, file_id: str, jwt_token: str) -> None:
        """Eliminar archivo."""
        client = await self._get_client()

        headers = {"Authorization": f"Bearer {jwt_token}"}

        logger.info("Deleting file from file-manager", file_id=file_id)

        response = await client.delete(
            f"/files/{file_id}",
            headers=headers,
        )
        response.raise_for_status()

    async def close(self):
        """Cerrar cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton para inyección de dependencias
_client: Optional[FileManagerClient] = None


async def get_file_manager() -> FileManagerClient:
    """Obtener instancia del cliente."""
    global _client
    if _client is None:
        from ..core.config import settings
        _client = FileManagerClient(
            base_url=settings.FILE_MANAGER_URL
        )
    return _client
```

### 3.2 Archivos a Refactorizar en el Core

| Archivo | Cambio |
|---------|--------|
| `routers/files.py` | Usar `FileManagerClient` para upload/download |
| `routers/documents.py` | Usar `FileManagerClient` para operaciones |
| `mcp/tools/audit_file.py` | Descargar archivo via HTTP antes de auditar |
| `mcp/tools/document_extraction_tool.py` | Delegar a File Manager |
| `mcp/tools/ingest_files.py` | Delegar a File Manager |
| `domain/audit_handler.py` | Actualizar `materialize_document()` |

### 3.3 Ejemplo: Refactorizar audit_file.py

```python
# apps/backend/src/mcp/tools/audit_file.py

# ANTES (tight coupling)
from ...services.minio_storage import get_minio_storage

minio_storage = get_minio_storage()
pdf_path, is_temp = minio_storage.materialize_document(
    document.minio_key,
    filename=document.filename,
)

# DESPUÉS (decoupled via HTTP)
from ...clients.file_manager import get_file_manager
import tempfile
from pathlib import Path

file_manager = await get_file_manager()

# Descargar archivo desde el plugin
file_bytes = await file_manager.download(document.id, jwt_token)

# Escribir a archivo temporal para el auditor
with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
    tmp.write(file_bytes)
    pdf_path = Path(tmp.name)
    is_temp = True

logger.info(
    "Downloaded file via file-manager HTTP",
    file_id=document.id,
    path=str(pdf_path),
)
```

### 3.4 Eliminar del Core Post-Migración

```bash
# Archivos a eliminar después de verificar que todo funciona
rm apps/backend/src/services/storage.py
rm apps/backend/src/services/minio_service.py
rm apps/backend/src/services/minio_storage.py
rm apps/backend/src/services/document_extraction.py
rm apps/backend/src/services/file_ingest.py
rm apps/backend/src/services/file_events.py
rm apps/backend/src/services/ocr_service.py
rm -rf apps/backend/src/services/extractors/
```

**Dependencias a eliminar de requirements.txt:**
- `pypdf`
- `PyMuPDF`
- `pytesseract`
- `python-magic`

---

## FASE 4: Actualizar Docker Compose

### 4.1 docker-compose.yml Actualizado

```yaml
version: "3.8"

services:
  # ════════════════════════════════════════════════════════════════
  # INFRASTRUCTURE
  # ════════════════════════════════════════════════════════════════
  mongodb:
    image: mongo:7.0
    container_name: ${PROJECT_NAME:-octavios}-mongodb
    volumes:
      - mongodb_data:/data/db
    networks:
      - octavios-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ${PROJECT_NAME:-octavios}-redis
    volumes:
      - redis_data:/data
    networks:
      - octavios-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:RELEASE.2024-11-07T00-52-20Z
    container_name: ${PROJECT_NAME:-octavios}-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - octavios-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.12.5
    container_name: ${PROJECT_NAME:-octavios}-qdrant
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
    networks:
      - octavios-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  languagetool:
    image: erikvl87/languagetool:6.3
    container_name: ${PROJECT_NAME:-octavios}-languagetool
    ports:
      - "8010:8010"
    networks:
      - octavios-network

  # ════════════════════════════════════════════════════════════════
  # CORE (Kernel) - Solo orquestación y chat
  # ════════════════════════════════════════════════════════════════
  api:
    build:
      context: ../apps/backend
      dockerfile: Dockerfile
    container_name: ${PROJECT_NAME:-octavios}-backend
    environment:
      # URLs de plugins
      - FILE_MANAGER_URL=http://file-manager:8001
      - CAPITAL414_URL=http://capital414-auditor:8002
    env_file:
      - ../envs/.env
    volumes:
      - ../apps/backend/src:/app/src:ro
    ports:
      - "8001:8001"
    networks:
      - octavios-network
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
      file-manager:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ════════════════════════════════════════════════════════════════
  # PLUGINS PÚBLICOS (Open Source)
  # ════════════════════════════════════════════════════════════════
  file-manager:
    build:
      context: ../plugins/public/file-manager
      dockerfile: Dockerfile
    container_name: ${PROJECT_NAME:-octavios}-file-manager
    env_file:
      - ../envs/.env
    environment:
      - MINIO_ENDPOINT=minio:9000
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ../plugins/public/file-manager/src:/app/src:ro
      - file_manager_temp:/tmp/uploads
    ports:
      - "8001:8001"
    networks:
      - octavios-network
    depends_on:
      minio:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ════════════════════════════════════════════════════════════════
  # PLUGINS PRIVADOS (Propietario)
  # ════════════════════════════════════════════════════════════════
  capital414-auditor:
    build:
      context: ../plugins/capital414-private
      dockerfile: Dockerfile
    container_name: ${PROJECT_NAME:-octavios}-capital414
    environment:
      # Consume archivos desde el plugin público
      - FILE_MANAGER_URL=http://file-manager:8001
    env_file:
      - ../envs/.env
    volumes:
      - ../plugins/capital414-private/src:/app/src:ro
      - /tmp/capital414-reports:/tmp/reports
    ports:
      - "8002:8002"
    networks:
      - octavios-network
    depends_on:
      file-manager:
        condition: service_healthy
      languagetool:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ════════════════════════════════════════════════════════════════
  # FRONTEND
  # ════════════════════════════════════════════════════════════════
  web:
    build:
      context: ../apps/web
      dockerfile: Dockerfile.dev
    container_name: ${PROJECT_NAME:-octavios}-web
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8001
    volumes:
      - ../apps/web:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    networks:
      - octavios-network
    depends_on:
      api:
        condition: service_healthy

  # ════════════════════════════════════════════════════════════════
  # API GATEWAY (Development)
  # ════════════════════════════════════════════════════════════════
  nginx:
    image: nginx:1.25-alpine
    container_name: ${PROJECT_NAME:-octavios}-nginx
    volumes:
      - ./nginx/nginx.dev.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    networks:
      - octavios-network
    depends_on:
      - api
      - web
      - file-manager
    profiles:
      - gateway

networks:
  octavios-network:
    driver: bridge

volumes:
  mongodb_data:
  redis_data:
  minio_data:
  qdrant_data:
  file_manager_temp:
```

### 4.2 nginx.dev.conf

```nginx
# infra/nginx/nginx.dev.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Upstreams
    upstream backend {
        server api:8001;
    }

    upstream file_manager {
        server file-manager:8001;
    }

    upstream frontend {
        server web:3000;
    }

    server {
        listen 80;
        server_name localhost;

        # ════════════════════════════════════════════════════════════
        # FILE OPERATIONS → File Manager Plugin (DIRECTO)
        # ════════════════════════════════════════════════════════════
        location /api/v1/files/ {
            # El frontend sube archivos directamente al plugin
            proxy_pass http://file_manager/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # Límites para uploads grandes
            client_max_body_size 100M;
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;
        }

        # ════════════════════════════════════════════════════════════
        # CORE API → Backend (Chat, Auth, MCP)
        # ════════════════════════════════════════════════════════════
        location /api/ {
            proxy_pass http://backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # SSE support para streaming
            proxy_buffering off;
            proxy_cache off;
            proxy_set_header Connection '';
            proxy_http_version 1.1;
            chunked_transfer_encoding off;
        }

        # ════════════════════════════════════════════════════════════
        # FRONTEND → Next.js
        # ════════════════════════════════════════════════════════════
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;

            # WebSocket support para HMR
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

---

## FASE 5: Actualizar Plugin Capital414

### 5.1 Crear FileManagerClient en Capital414

El plugin Capital414 debe consumir archivos desde el File Manager en lugar de acceder directamente a MinIO.

```python
# plugins/capital414-private/src/clients/file_manager.py
"""
Cliente HTTP para consumir archivos desde el plugin file-manager.
"""
import httpx
from pathlib import Path
import tempfile
import structlog

logger = structlog.get_logger(__name__)


class FileManagerClient:
    """Cliente para descargar archivos desde file-manager."""

    def __init__(self, base_url: str = "http://file-manager:8001"):
        self.base_url = base_url

    async def download_to_temp(self, file_id: str, jwt_token: str) -> Path:
        """
        Descarga un archivo a un directorio temporal.

        Args:
            file_id: ID del archivo en el sistema
            jwt_token: Token JWT para autenticación

        Returns:
            Path al archivo temporal descargado
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {"Authorization": f"Bearer {jwt_token}"}

            logger.info("Downloading file for audit", file_id=file_id)

            response = await client.get(
                f"{self.base_url}/download/{file_id}",
                headers=headers,
            )
            response.raise_for_status()

            # Obtener extensión del header o usar .pdf por defecto
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = "document.pdf"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')

            suffix = Path(filename).suffix or ".pdf"

            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                dir="/tmp/reports"
            ) as f:
                f.write(response.content)
                temp_path = Path(f.name)

            logger.info(
                "File downloaded for audit",
                file_id=file_id,
                path=str(temp_path),
                size=len(response.content),
            )

            return temp_path

    async def get_extracted_text(self, file_id: str, jwt_token: str) -> str:
        """Obtener texto ya extraído del archivo."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {"Authorization": f"Bearer {jwt_token}"}

            response = await client.get(
                f"{self.base_url}/metadata/{file_id}",
                headers=headers,
            )
            response.raise_for_status()

            return response.json().get("extracted_text", "")
```

### 5.2 Actualizar Coordinator

```python
# plugins/capital414-private/src/audit_engine/coordinator.py

# Importar el nuevo cliente
from ..clients.file_manager import FileManagerClient

async def validate_document(
    document_id: str,
    jwt_token: str,
    policy: PolicyConfig,
    ...
):
    """
    Ejecuta auditoría completa sobre un documento.

    CAMBIO: Ahora descarga el archivo desde file-manager en lugar de MinIO directo.
    """
    file_client = FileManagerClient()

    # Descargar archivo desde el plugin público
    pdf_path = await file_client.download_to_temp(document_id, jwt_token)

    try:
        # Ejecutar auditores en paralelo
        findings = await asyncio.gather(
            audit_disclaimers(pdf_path, policy),
            audit_format(pdf_path, policy),
            audit_typography(pdf_path, policy),
            audit_grammar(pdf_path, policy),
            audit_logo(pdf_path, policy),
            audit_color(pdf_path, policy),
            audit_entities(pdf_path, policy),
            audit_semantic(pdf_path, policy),
        )

        return ValidationReport(findings=findings)

    finally:
        # Limpiar archivo temporal
        if pdf_path.exists():
            pdf_path.unlink()
```

---

## Cronograma de Implementación

| Fase | Duración | Tareas Principales |
|------|----------|-------------------|
| **Fase 1** | 1 día | Renombrar apps/api → apps/backend |
| **Fase 2** | 3 días | Crear plugin file-manager completo |
| **Fase 3** | 2 días | Refactorizar Core con FileManagerClient |
| **Fase 4** | 1 día | Actualizar Docker Compose + Nginx |
| **Fase 5** | 1 día | Actualizar Capital414 |
| **Testing** | 2 días | Tests E2E, integración, validación |
| **TOTAL** | **10 días** | |

---

## Validación Post-Migración

### Checklist

- [ ] `make dev` inicia todos los servicios
- [ ] `curl http://localhost:8001/health` responde OK (file-manager)
- [ ] `curl http://localhost:8001/api/health` responde OK (backend)
- [ ] `curl http://localhost:8002/health` responde OK (capital414)
- [ ] Upload de archivos funciona: `POST /api/v1/files/upload`
- [ ] Descarga funciona: `GET /api/v1/files/download/{id}`
- [ ] Auditoría E2E: "Auditar archivo: test.pdf" completa correctamente
- [ ] MCP tools responden: `read_file_text`, `extract_metadata`
- [ ] No hay imports de pypdf/minio en Core: `grep -r "pypdf\|minio" apps/backend/src/`
- [ ] Tests pasan: `make test`

### Comandos de Validación

```bash
# 1. Health checks
make health

# 2. Test file-manager directo
curl -X POST http://localhost:8001/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf" \
  -F "user_id=demo"

# 3. Test upload via nginx (producción-like)
curl -X POST http://localhost/api/v1/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"

# 4. Test auditoría completa
curl -X POST http://localhost:8001/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Auditar archivo: test.pdf", "session_id": "test-session"}'

# 5. Verificar Core limpio
grep -r "pypdf\|minio\|tesseract" apps/backend/src/services/ && echo "❌ Core aún tiene dependencias" || echo "✅ Core limpio"
```

---

## Rollback Plan

### Si Fase 1 falla (renombrado)
```bash
mv apps/backend apps/api
git checkout infra/ .github/ Makefile CLAUDE.md README.md
make dev
```

### Si Fase 2-5 fallan (plugins)
```bash
# Detener nuevo servicio
docker compose stop file-manager

# Restaurar Core original
git checkout apps/backend/src/services/
git checkout apps/backend/src/mcp/tools/audit_file.py

# Reiniciar
make restart
```

---

## Beneficios de la Arquitectura Plugin-First

| Beneficio | Descripción |
|-----------|-------------|
| **Escalabilidad** | File Manager escala independientemente del Core |
| **Reusabilidad** | Otros plugins consumen archivos sin duplicar código |
| **Mantenibilidad** | Cambios en OCR/PDF no afectan al Core |
| **Testing** | Cada plugin se testea aisladamente |
| **Open Source Ready** | File Manager público, Capital414 privado |
| **Intercambiabilidad** | Fácil cambiar MinIO por S3, GCS, etc. |
| **Comunidad** | Desarrolladores pueden crear sus propios "File Managers" |

---

## Diagrama de Arquitectura Final

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Navegador / Cliente                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Nginx (API Gateway)                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ /api/v1/files/* → file-manager:8001                            │ │
│  │ /api/*          → backend:8001                                 │ │
│  │ /               → web:3000                                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ↓                     ↓                     ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Next.js 14    │  │  Backend Core   │  │  File Manager   │
│   (web:3000)    │  │ (backend:8001)  │  │  (8001)         │
│                 │  │                 │  │                 │
│  • UI/UX        │  │  • Auth/JWT     │  │  • Upload       │
│  • Chat View    │  │  • Chat Logic   │  │  • Download     │
│  • Canvas       │  │  • MCP Router   │  │  • OCR/PDF      │
│  • SSE Handler  │  │  • Rate Limit   │  │  • MCP Tools    │
└─────────────────┘  └────────┬────────┘  └────────┬────────┘
                              │                     │
                              │   HTTP Client       │
                              │──────────────────→  │
                              │                     │
                              ↓                     ↓
                    ┌─────────────────┐   ┌─────────────────┐
                    │ Capital414      │   │   MinIO S3      │
                    │ (8002)          │←──│   Redis Cache   │
                    │                 │   └─────────────────┘
                    │  • 8 Auditors   │
                    │  • PDF Analysis │
                    │  • Compliance   │
                    └─────────────────┘
```

---

*Documento actualizado: 2025-11-25 | Versión 2.0 (Plugin-First Architecture)*
