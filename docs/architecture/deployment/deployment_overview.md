# Deployment Architecture Overview

## System Components

The OctaviOS Chat system consists of the following Docker services:

- **Web (Next.js)**: Frontend UI (Port 3000)
- **Backend (FastAPI)**: Core API and orchestration (Port 8000)
- **Bank Advisor (FastAPI)**: Specialized RAG & NL2SQL service (Port 8002)
- **MongoDB**: Chat history and user data
- **Redis**: Caching and session management
- **Weaviate**: Vector database (Cloud managed, or local fallback)

## Infrastructure Reference

For detailed architectural diagrams and specifications, please refer to:

- [System Architecture](../../../00_architecture/2025-12-01_system_architecture.md)
- [GCP Postgres Schema](../../../00_architecture/2025-12-04_gcp_postgres_schema.md)
- [Observability Design](../../../00_architecture/2025-12-01_observability_design.md)

## Deployment Flow

1. **Local Build**: Code is built into Docker images locally or via CI.
2. **Registry**: Images are pushed to Docker Hub (`jazielflores1998/octavios-invex-*`).
3. **Production**: Server pulls images and restarts containers via Docker Compose.
