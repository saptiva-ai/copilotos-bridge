# Copilot OS API

FastAPI backend for the Copilot OS chat and deep research platform.

## Features

- 🚀 **FastAPI** with async/await support
- 🗄️ **MongoDB** with Beanie ODM for data persistence
- ⚡ **Redis** for caching and session management
- 🔐 **JWT Authentication** with refresh tokens
- 🔄 **Server-Sent Events (SSE)** for real-time streaming
- 📊 **OpenTelemetry** instrumentation for observability
- 🛡️ **Rate limiting** and security middleware
- 🔌 **Aletheia integration** with circuit breaker pattern
- 🤖 **System Prompts por Modelo** con orquestación de LLMs y telemetría

## Quick Start

### Prerequisites

- Python 3.10+
- MongoDB 6.0+
- Redis 6.2+
- Aletheia orchestrator (optional for full functionality)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit configuration
nano .env

# Run the API
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Development with Docker

```bash
# Start database services
docker compose -f ../../infra/docker-compose.yml up -d mongodb redis

# Run API
python -m uvicorn src.main:app --reload
```

## API Endpoints

### Health & System

#### `GET /api/health`
Comprehensive health check including database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "0.1.0",
  "uptime_seconds": 123.45,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 12.5,
      "connected": true
    }
  }
}
```

#### `GET /api/health/live`
Kubernetes liveness probe.

#### `GET /api/health/ready`
Kubernetes readiness probe.

### Chat Operations

#### `POST /api/chat`
Send a chat message and get AI response.

**Request:**
```json
{
  "message": "What is artificial intelligence?",
  "chat_id": "optional-existing-chat-id",
  "model": "SAPTIVA_CORTEX",
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false,
  "tools_enabled": {
    "web_search": false,
    "deep_research": false
  }
}
```

**Response:**
```json
{
  "chat_id": "chat-uuid",
  "message_id": "msg-uuid", 
  "content": "AI response content...",
  "role": "assistant",
  "model": "SAPTIVA_CORTEX",
  "created_at": "2024-01-01T12:00:00Z",
  "tokens": 150,
  "latency_ms": 1250,
  "finish_reason": "completed"
}
```

#### `GET /api/history/{chat_id}`
Get chat history for a session.

**Query Parameters:**
- `limit` (int): Number of messages (default: 50, max: 200)
- `offset` (int): Pagination offset (default: 0)
- `include_system` (bool): Include system messages (default: false)

#### `GET /api/sessions`
Get user's chat sessions.

**Query Parameters:**
- `limit` (int): Number of sessions (default: 20, max: 100)
- `offset` (int): Pagination offset (default: 0)

#### `DELETE /api/sessions/{chat_id}`
Delete a chat session and all messages.

### Deep Research

#### `POST /api/deep-research`
Start a deep research task.

**Request:**
```json
{
  "query": "Latest developments in quantum computing",
  "research_type": "deep_research",
  "chat_id": "optional-chat-id",
  "stream": true,
  "params": {
    "budget": 10.0,
    "max_iterations": 5,
    "scope": "comprehensive",
    "sources_limit": 20,
    "depth_level": "deep",
    "focus_areas": ["quantum algorithms", "quantum hardware"],
    "language": "en",
    "include_citations": true
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "running",
  "message": "Deep research task started successfully",
  "progress": 0.0,
  "created_at": "2024-01-01T12:00:00Z",
  "stream_url": "/api/stream/task-uuid"
}
```

#### `GET /api/deep-research/{task_id}`
Get research task status and results.

#### `POST /api/deep-research/{task_id}/cancel`
Cancel a running research task.

#### `GET /api/tasks`
Get user's research tasks.

**Query Parameters:**
- `limit` (int): Number of tasks (default: 20)
- `offset` (int): Pagination offset
- `status_filter` (str): Filter by status (pending, running, completed, failed, cancelled)

### Real-time Streaming

#### `GET /api/stream/{task_id}`
Server-Sent Events stream for research progress.

**Event Types:**
- `connection_established`
- `task_started`
- `search_started`
- `sources_found`
- `processing_sources`
- `evidence_extraction`
- `synthesis_started`
- `task_completed`
- `stream_error`
- `task_cancelled`

**Event Format:**
```
data: {"event_type": "sources_found", "task_id": "task-uuid", "timestamp": "2024-01-01T12:00:00Z", "data": {"message": "Found 15 relevant sources", "sources_count": 15}, "progress": 0.3}
```

#### `GET /api/stream/{task_id}/status`
Get streaming task status without opening SSE connection.

### History & Analytics

#### `GET /api/history`
Get chat session history overview.

**Query Parameters:**
- `search` (str): Search in session titles
- `date_from` (datetime): Filter from date
- `date_to` (datetime): Filter to date
- `limit`, `offset`: Pagination

#### `GET /api/history/{chat_id}/export`
Export chat history in various formats.

**Query Parameters:**
- `format` (str): Export format (json, csv, txt)
- `include_metadata` (bool): Include technical metadata

#### `GET /api/history/stats`
Get user chat usage statistics.

**Query Parameters:**
- `days` (int): Analysis period in days (default: 30, max: 365)

### Research Reports

#### `GET /api/report/{task_id}`
Download research report in specified format.

**Query Parameters:**
- `format` (str): Report format (md, html, pdf)
- `include_sources` (bool): Include source references (default: true)

#### `GET /api/report/{task_id}/preview`
Preview research report without downloading.

#### `GET /api/report/{task_id}/metadata`
Get report metadata and availability.

#### `DELETE /api/report/{task_id}`
Delete research report and artifacts.

## Authentication

The API uses JWT bearer tokens for authentication:

```http
Authorization: Bearer <jwt-token>
```

**Public endpoints** (no authentication required):
- `/api/health/*`
- `/docs`, `/redoc`, `/openapi.json`

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {...},
    "trace_id": "req-uuid"
  }
}
```

**Common HTTP Status Codes:**
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `502` - Bad Gateway (Aletheia unavailable)

## Rate Limiting

Default limits (configurable):
- **100 requests per minute** per IP address
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## Monitoring & Observability

### OpenTelemetry Tracing
Automatic instrumentation for:
- HTTP requests/responses
- Database operations
- External API calls
- Custom business logic spans

### Health Checks
- **Liveness**: Service is running
- **Readiness**: Service can accept traffic
- **Comprehensive**: Includes dependency checks

### Metrics
Exported via Prometheus format at `/metrics`:
- Request count/duration
- Database connection pool
- Rate limiting
- Custom business metrics

## Configuration

All configuration via environment variables. See `.env.example` for full list.

**Key settings:**

```bash
# Database
MONGODB_URL=mongodb://localhost:27017/copilotos
REDIS_URL=redis://localhost:6379/0

# Aletheia Integration
ALETHEIA_BASE_URL=http://localhost:8000
ALETHEIA_API_KEY=your-api-key

# Security
JWT_SECRET_KEY=your-jwt-secret
RATE_LIMIT_CALLS=100

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires MongoDB/Redis)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Linting
flake8 src/
black --check src/
isort --check-only src/

# Type checking
mypy src/
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Architecture

```
src/
├── core/           # Core infrastructure
│   ├── config.py   # Settings management
│   ├── database.py # MongoDB connection
│   ├── logging.py  # Structured logging
│   └── telemetry.py # OpenTelemetry setup
├── models/         # Database models (Beanie)
├── schemas/        # Pydantic schemas
├── routers/        # FastAPI route handlers
├── services/       # Business logic
├── middleware/     # Custom middleware
└── main.py         # Application entry point
```

## System Prompts por Modelo

El sistema de **prompts por modelo** permite configurar system prompts específicos, parámetros de generación y herramientas disponibles para cada modelo de Saptiva, con versionado y telemetría integrada.

### Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  Chat Request (message, model, channel, context, tools)     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  build_payload()                                             │
│  ├── Carga PromptRegistry desde YAML                        │
│  ├── Resuelve system prompt (placeholders + addendums)      │
│  ├── Inyecta herramientas disponibles                       │
│  ├── Aplica parámetros por modelo y canal                   │
│  └── Genera metadata (hash, version, request_id)            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Payload completo:                                           │
│  {                                                           │
│    "messages": [                                             │
│      {"role": "system", "content": "..."},                   │
│      {"role": "user", "content": "..."}                      │
│    ],                                                        │
│    "temperature": 0.25,  # Por modelo                        │
│    "max_tokens": 1200,   # Por canal                         │
│    "tools": [...]        # Function-calling schemas          │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Configuración de Prompts

Los prompts se definen en **`prompts/registry.yaml`**:

```yaml
version: v1
copilot_name: CopilotOS
org_name: Saptiva

models:
  default:
    system_base: |
      Eres {CopilotOS} de {Saptiva}...
      Herramientas disponibles:
      {TOOLS}
    params:
      temperature: 0.3
      top_p: 0.9
      frequency_penalty: 0.2

  "Saptiva Turbo":
    system_base: |
      [System prompt base...]
    addendum: |
      Optimiza por brevedad y latencia.
      Responde en ≤6 bullets.
    params:
      temperature: 0.25
      frequency_penalty: 0.1
```

### Placeholders

- **`{CopilotOS}`** → Nombre del copiloto (configurable)
- **`{Saptiva}`** → Nombre de la organización
- **`{TOOLS}`** → Descripción de herramientas disponibles (inyectado dinámicamente)

### Parámetros por Canal

El sistema ajusta `max_tokens` según el canal de comunicación:

| Canal      | Max Tokens | Uso                           |
|------------|------------|-------------------------------|
| `chat`     | 1200       | Conversación normal          |
| `report`   | 3500       | Reportes largos              |
| `title`    | 64         | Títulos y encabezados        |
| `summary`  | 256        | Resúmenes concisos           |
| `code`     | 2048       | Generación de código         |

### Uso desde el API

**Request con canal y contexto:**

```json
{
  "message": "Dame 3 bullets sobre capacidades de IA",
  "model": "Saptiva Turbo",
  "channel": "chat",
  "context": {
    "session_id": "abc-123",
    "user_preferences": {"language": "es"}
  },
  "tools_enabled": {
    "web_search": true,
    "calculator": false
  }
}
```

**Payload generado internamente:**

```json
{
  "model": "Saptiva Turbo",
  "messages": [
    {
      "role": "system",
      "content": "Eres CopilotOS de Saptiva...\n\nHerramientas disponibles:\n* **web_search** — Buscar información...\n\n---\nOptimiza por brevedad y latencia..."
    },
    {
      "role": "user",
      "content": "Contexto:\n- session_id: abc-123\n...\n\nSolicitud:\nDame 3 bullets sobre capacidades de IA"
    }
  ],
  "temperature": 0.25,
  "max_tokens": 1200,
  "tools": [{"type": "function", "function": {...}}]
}
```

### Telemetría

Cada request genera metadata **sin loguear el contenido del prompt**:

```json
{
  "request_id": "uuid-here",
  "model": "Saptiva Turbo",
  "channel": "chat",
  "prompt_version": "v1",
  "system_hash": "a3f5b2c1d4e6f7a8",  // SHA256 (primeros 16 chars)
  "has_addendum": true,
  "has_tools": true
}
```

**Logs de telemetría:**
```
INFO Saptiva request metadata request_id=uuid model=Saptiva_Turbo
     system_hash=a3f5b2c1 prompt_version=v1 channel=chat has_tools=true
```

### Agregar Nuevo Modelo

1. **Editar `prompts/registry.yaml`:**

```yaml
models:
  "My Custom Model":
    system_base: |
      Tu prompt base aquí con {CopilotOS} y {TOOLS}
    addendum: |
      Instrucciones específicas del modelo
    params:
      temperature: 0.4
      top_p: 0.95
      frequency_penalty: 0.25
```

2. **El sistema automáticamente:**
   - Cargará el nuevo modelo
   - Aplicará parámetros específicos
   - Generará hash único para telemetría

3. **Usar desde el frontend:**

```typescript
await sendChat({
  message: "Test",
  model: "My Custom Model",
  channel: "chat"
});
```

### Feature Flag

Control del sistema mediante variable de entorno:

```bash
# Habilitar (default)
ENABLE_MODEL_SYSTEM_PROMPT=true

# Deshabilitar (fallback a comportamiento legacy)
ENABLE_MODEL_SYSTEM_PROMPT=false
```

### Testing

**Tests unitarios:**
```bash
pytest tests/test_prompt_registry.py -v
```

**Smoke test manual:**
```bash
python apps/api/smoke_test_prompts.py
```

### Rollout Seguro

1. **Staging**: `ENABLE_MODEL_SYSTEM_PROMPT=true`
2. **Canary**: 10% → 50% → 100%
3. **Monitoreo**: Latencia, tasa de tool-calls, system_hash consistency
4. **Rollback**: `ENABLE_MODEL_SYSTEM_PROMPT=false` (instantáneo)

### Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `prompts/registry.yaml` | Configuración de prompts por modelo |
| `src/core/prompt_registry.py` | Carga y resolución de prompts |
| `src/services/tools.py` | Helpers para herramientas |
| `src/services/saptiva_client.py` | Builder de payloads |
| `src/routers/chat.py` | Integración en endpoints |
| `tests/test_prompt_registry.py` | Tests unitarios |

---

## Contributing

1. Follow existing code style (Black, isort)
2. Add tests for new features
3. Update documentation
4. Ensure all health checks pass
5. Add appropriate logging and tracing

## License

MIT License - see LICENSE file for details.
