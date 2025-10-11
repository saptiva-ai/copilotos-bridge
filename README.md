# Saptiva CopilotOS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Security](https://img.shields.io/badge/Security-Enterprise-red.svg)](#security-architecture)

Copiloto provides a production-ready conversational interface for SAPTIVA language models with integrated deep-research orchestration and enterprise-grade security.

## Overview

Copilotos Bridge delivers a ChatGPT-style experience tailored to SAPTIVA deployments while preserving the observability, governance, and hardening requirements of enterprise environments.

### Key Features
- Chat workspace with model selector, conversation history, streaming responses, and keyboard shortcuts.
- Direct SAPTIVA API integration with end-to-end tracing and real production responses.
- Deep research orchestrated through Aletheia with source attribution and progress streaming.
- Security-first design with JWT authentication, rate limiting, secrets management, and container hardening.
- Accessibility-first UI with ARIA labeling, full keyboard control, and responsive layouts.
- Docker-first deployment that aligns local development and production releases.


## Quick Start for New Developers

**First time here?** Check out our comprehensive getting started guide:

➤ **[Getting Started Guide](docs/GETTING_STARTED.md)** - Complete step-by-step setup guide (5 minutes to running stack)

This guide includes:
- ✔ Prerequisites checklist
- ✔ Interactive setup (recommended)
- ✔ Manual configuration options
- ✔ Common troubleshooting
- ✔ Useful development commands

**TL;DR - Three commands to start:**
```bash
make setup          # Interactive configuration (asks for API key)
make dev            # Starts all services
make create-demo-user  # Creates test user (demo/Demo1234)
```

Then visit: http://localhost:3000

---

## Requirements

### System
- Docker and Docker Compose 20.10+
- Node.js 18+
- Python 3.10+
- pnpm 8+ (or npm)

### Frontend (Next.js 14)
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript with strict configuration
- **Styling**: Tailwind CSS with custom design system
- **State Management**: Zustand for global state
- **UI Components**: Custom React components with accessibility
- **Build**: Standalone output for containerization

### Backend (FastAPI)
- **Framework**: FastAPI with async/await
- **Language**: Python 3.10+ with type hints
- **Database ODM**: Beanie (async MongoDB ODM)
- **Validation**: Pydantic v2 with advanced validation
- **Authentication**: JWT with Redis session storage
- **API Documentation**: Auto-generated OpenAPI/Swagger

### Databases
- **Primary**: MongoDB 7.0 (document store)
- **Cache**: Redis 7.0 (in-memory cache)
- **Search**: Integrated vector search capabilities
  
## Project Structure

```
copilotos-bridge/
├── apps/
│   ├── web/                # Next.js frontend application
│   │   ├── deployment/     # Standalone Docker build assets
│   │   ├── src/components/ # React components & UI library
│   │   ├── src/lib/        # Utilities, hooks & configuration
│   │   ├── src/styles/     # Design system & Tailwind config
│   │   ├── Dockerfile      # Multi-stage container build
│   │   └── next.config.js  # Next.js configuration
│   └── api/                # FastAPI backend application
│       ├── src/routers/    # API route handlers
│       ├── src/models/     # Database models (Beanie ODM)
│       ├── src/services/   # Business logic & integrations
│       ├── src/core/       # Core utilities & configuration
│       │   ├── config.py   # Application configuration
│       │   └── secrets.py  # Secrets management system
│       └── Dockerfile      # Production API container
├── infra/
│   ├── docker-compose.yml  # Complete service orchestration
│   └── nginx/              # Production reverse proxy config
├── envs/
│   ├── .env.local.example  # Development environment template
│   ├── .env.prod.example   # Production environment template
│   └── .env.local          # Local environment (gitignored)
├── scripts/
│   ├── generate-production-secrets.sh # Secure credential generation
│   ├── rotate-mongo-credentials.sh   # Safe MongoDB password rotation
│   ├── rotate-redis-credentials.sh   # Safe Redis password rotation
│   ├── validate-production-readiness.sh # Pre-rotation validation (10 checks)
│   ├── test-credential-rotation.sh   # Automated credential rotation testing
│   ├── security-audit.sh            # Security validation
│   ├── test-docker-permissions.sh   # Permission testing
│   ├── docker-cleanup.sh            # Docker resource cleanup
│   └── create-demo-user.py          # Demo user creation
├── docs/
│   ├── DEPLOYMENT.md                        # Production deployment guide
│   ├── TOKEN_EXPIRATION_HANDLING.md         # JWT expiration & session management
│   ├── RESOURCE_OPTIMIZATION.md             # Docker resource optimization strategies
│   ├── MAKEFILE_RESOURCE_COMMANDS.md        # Resource command reference
│   ├── PRODUCTION_CREDENTIAL_ROTATION.md    # Production credential rotation procedures
│   ├── CREDENTIAL_MANAGEMENT.md             # Credential policies & best practices
│   ├── DOCKER_ENV_FILE_CONFIGURATION.md     # Docker env_file technical guide
│   ├── MAKEFILE_CREDENTIAL_COMMANDS.md      # Credential command reference
│   ├── arquitectura/                        # LLM architecture documentation
│   ├── evidencias/                          # Reproducible evidence files
│   └── guides/                              # Quick start & developer guides
├── Makefile                        # Development automation & resource tools
└── README.md                       # This file
```

### Services (Docker Compose Profiles)
- MongoDB 7+ with replica set support
- Redis 7+ with AOF persistence
- Nginx 1.25+ for production reverse proxying

### External Dependencies
- SAPTIVA API key (required)
- Domain and TLS certificate for production deployments

## Architecture

The bridge combines a Next.js conversation client, a FastAPI orchestration layer, and supporting AI providers. Redis accelerates hot paths such as session management, rate limiting, and streaming cursors, while MongoDB stores chats, research runs, and audit history.

```mermaid
%%{init: {'theme':'neutral','flowchart':{'curve':'basis'}}}%%
flowchart TB
  subgraph Client["Frontend · Next.js"]
    UI["Chat Interface\n(React components)"]
    State["State Stores & Hooks\n(Zustand, custom hooks)"]
    Streamer["Streaming Bridge\n(SSE listeners)"]
    UI --> State
    State --> Streamer
  end

  subgraph Gateway["Backend · FastAPI"]
    Auth["Auth & Rate Limit Middleware"]
    Router["REST & SSE Routers"]
    Coordinator["Research Coordinator\n(SAPTIVA ⇄ Aletheia)"]
    History["History Service\n(Chat · Research timeline)"]
    CacheSvc["Redis Cache Client"]
    Router --> Coordinator
    Router --> History
    History --> CacheSvc
  end

  subgraph Data["Persistence"]
    Mongo[("MongoDB\nBeanie ODM")]
    Redis[("Redis\nCaching · Rate limits")]
  end

  subgraph External["External AI & Search"]
    Saptiva["SAPTIVA LLM API"]
    Aletheia["Aletheia Orchestrator"]
    Tavily["Tavily Search"]
    Weaviate["Weaviate Vector DB"]
  end

  Client -->|HTTP /api| Gateway
  Gateway -->|JWT + SSE| Client
  Gateway --> Mongo
  Gateway --> Redis
  Coordinator --> Saptiva
  Coordinator --> Aletheia
  Aletheia --> Tavily
  Aletheia --> Weaviate
  Aletheia --> Saptiva

  classDef client fill:#3358ff,stroke:#1c2f73,color:#ffffff;
  classDef gateway fill:#2f9e44,stroke:#186429,color:#ffffff;
  classDef data fill:#fab005,stroke:#c47a02,color:#111111;
  classDef external fill:#868e96,stroke:#495057,color:#ffffff,stroke-dasharray: 4 3;
  class UI,State,Streamer client;
  class Auth,Router,Coordinator,History,CacheSvc gateway;
  class Mongo,Redis data;
  class Saptiva,Aletheia,Tavily,Weaviate external;
```

### Conversation and Research Flow

The sequence below shows how a user message is processed, routed between SAPTIVA chat and Aletheia deep research, and streamed back to the client.

```mermaid
%%{init: {'theme':'neutral'}}%%
sequenceDiagram
    autonumber
    participant User
    participant Web as Next.js UI
    participant Store as Client State
    participant API as FastAPI /api/chat
    participant Coord as Research Coordinator
    participant Cache as Redis Cache
    participant DB as MongoDB
    participant Saptiva as SAPTIVA API
    participant Aletheia as Aletheia Orchestrator

    User->>Web: Compose message & choose tools
    Web->>Store: Persist draft + context
    Web->>API: POST /api/chat
    API->>Coord: analyze_query()
    Coord->>Cache: hydrate recent context
    alt Lightweight prompt
        Coord->>Saptiva: chatCompletion()
        Saptiva-->>Coord: streaming chunks
        Coord->>DB: upsert ChatMessage + HistoryEvent
        Coord->>Cache: invalidate chat cache
        Coord-->>API: Chat reply payload
    else Research escalation
        Coord->>Aletheia: start_deep_research()
        Aletheia-->>Coord: task_id + stream_url
        Coord->>DB: persist Task + HistoryEvent
        Coord->>Cache: invalidate research tasks cache
        Coord-->>API: Deep-research acknowledgement
    end
    API-->>Web: JSON response
    Web->>Store: Update timeline/state
    Web-->>User: Render assistant reply or research task status
    API-->>Web: SSE /api/stream/{task_id}
    Web->>Store: Merge streaming progress + report
    Store-->>User: Live status, evidence, and report links
```

### Data Persistence Map

MongoDB collections capture chats, research tasks, and unified history, while Redis holds ephemeral indices referenced by the services above.

```mermaid
erDiagram
    USERS {
        string _id "ObjectId"
        string username
        string email
        bool is_active
        datetime created_at
    }
    CHAT_SESSIONS {
        string _id "UUID"
        string title
        string user_id
        int message_count
        datetime created_at
    }
    CHAT_MESSAGES {
        string _id "UUID"
        string chat_id
        enum role
        string content
        enum status
        datetime created_at
    }
    HISTORY_EVENTS {
        string _id "UUID"
        string chat_id
        string user_id
        enum event_type
        datetime timestamp
    }
    TASKS {
        string _id "UUID"
        string user_id
        string chat_id
        string task_type
        enum status
        float progress
        datetime created_at
    }
    DEEP_RESEARCH_TASKS {
        string _id "UUID"
        string query
        int sources_found
        string report_url
    }
    RESEARCH_SOURCES {
        string _id "UUID"
        string task_id
        string url
        float relevance_score
        float credibility_score
    }
    EVIDENCE {
        string _id "UUID"
        string task_id
        string claim
        enum support_level
        float confidence
    }

    USERS ||--o{ CHAT_SESSIONS : "owns"
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : "contains"
    USERS ||--o{ HISTORY_EVENTS : "generates"
    CHAT_SESSIONS ||--o{ HISTORY_EVENTS : "timeline"
    USERS ||--o{ TASKS : "launches"
    CHAT_SESSIONS ||--o{ TASKS : "initiates"
    TASKS ||--o{ DEEP_RESEARCH_TASKS : "specializes"
    TASKS ||--o{ RESEARCH_SOURCES : "collects"
    TASKS ||--o{ EVIDENCE : "produces"
    TASKS ||--o{ HISTORY_EVENTS : "updates"
```

### Deployment Topology

Local development uses Docker Compose, while production combines a standalone web image behind Nginx with FastAPI services running through Compose profiles or managed infrastructure.

```mermaid
%%{init: {'theme':'neutral','flowchart':{'curve':'basis'}}}%%
flowchart LR
  subgraph Dev["Local Development (make dev)"]
    subgraph Compose["Docker Compose"]
      WebDev["web (Next.js runner)"]
      ApiDev["api (FastAPI)"]
      MongoDev[("MongoDB 7\nvolume: mongodb_data")]
      RedisDev[("Redis 7\nAOF enabled")]
    end
    WebDev --> ApiDev
    ApiDev --> MongoDev
    ApiDev --> RedisDev
  end

  subgraph Prod["Production"]
    Nginx["Nginx reverse proxy\nTLS + routing"]
    WebProd["Standalone web image\n(Dockerfile.local)"]
    ApiProd["copilotos-api service\n(compose profile)"]
    MongoProd[("Managed MongoDB / Atlas")]
    RedisProd[("Managed Redis")]
  end

  Nginx --> WebProd
  Nginx --> ApiProd
  ApiProd --> MongoProd
  ApiProd --> RedisProd

  subgraph External["External Providers"]
    SaptivaExt["SAPTIVA API"]
    AletheiaExt["Aletheia Orchestrator"]
  end

  ApiDev -.-> SaptivaExt
  ApiDev -.-> AletheiaExt
  ApiProd -.-> SaptivaExt
  ApiProd -.-> AletheiaExt

  classDef infra fill:#1864ab,stroke:#0b284f,color:#ffffff;
  classDef data fill:#f08c00,stroke:#9c5900,color:#111111;
  classDef external fill:#868e96,stroke:#495057,color:#ffffff,stroke-dasharray: 4 3;
  class WebDev,ApiDev,WebProd,ApiProd,Nginx infra;
  class MongoDev,RedisDev,MongoProd,RedisProd data;
  class SaptivaExt,AletheiaExt external;
```

### Security Architecture

- JWT-authenticated API backed by refresh flows and audit logging.
- Strict cache headers, rate limiting, and session management enforced through Redis.
- Secrets managed through `.env` templates with Docker secrets compatibility for production.
- Deep research kill switch to isolate SAPTIVA-only operation modes when needed.
- Hardened Dockerfiles that run services as non-root users with minimal base images.

## System Prompts Architecture

The bridge implements a **model-specific system prompting system** that allows customizing LLM behavior per model without code changes. This ensures consistent, optimized responses across different SAPTIVA models.

### How It Works

**3-Layer Architecture:**
1. **Configuration Layer** (`apps/api/prompts/registry.yaml`) - Defines prompts, addendums, and parameters per model
2. **Registry Layer** (`apps/api/src/core/prompt_registry.py`) - Loads, validates, and resolves prompts with dynamic placeholders
3. **Integration Layer** (`apps/api/src/services/saptiva_client.py`) - Injects prompts into every SAPTIVA API call

### Key Features

- **Dynamic Placeholders**: `{CopilotOS}`, `{Saptiva}`, `{TOOLS}` automatically replaced at runtime
- **Model Addendums**: Specialized instructions per model (e.g., "Turbo: respond in ≤6 bullets")
- **Channel-Based Limits**: Different max\_tokens for `chat` (1200), `report` (3500), `code` (2048), etc.
- **DRY Principle**: Shared base prompt with model-specific overrides
- **Feature Flag**: `ENABLE_MODEL_SYSTEM_PROMPT=true` allows safe rollback
- **Telemetry**: Each request includes system prompt hash for tracking

### Configuration Example

```yaml
# apps/api/prompts/registry.yaml
models:
  "Saptiva Turbo":
    system_base: |
      You are {CopilotOS}, assistant for {Saptiva}...
      Available tools: {TOOLS}
    addendum: |
      Optimize for speed. Respond in ≤6 bullets.
    params:
      temperature: 0.25
      top_p: 0.9
      max_tokens: 1200  # Overridden by channel
```

### Request Flow

```mermaid
sequenceDiagram
    participant Router as Chat Router
    participant Builder as build_payload()
    participant Registry as PromptRegistry
    participant API as SAPTIVA API

    Router->>Builder: build_payload(model, message, channel)
    Builder->>Registry: resolve(model, tools, channel)
    Registry->>Registry: 1. Get model config<br/>2. Replace placeholders<br/>3. Add addendum<br/>4. Set max_tokens
    Registry-->>Builder: system_text + params
    Builder->>Builder: Construct messages array
    Builder-->>Router: payload + metadata
    Router->>API: POST /v1/chat/completions
```

### Configured Models

| Model | Temperature | Specialization | Max Tokens (chat) |
|-------|-------------|----------------|-------------------|
| **Saptiva Turbo** | 0.25 | Speed & brevity | 1200 |
| **Saptiva Cortex** | 0.35 | Rigor & reasoning | 1200 |
| **Saptiva Ops** | 0.20 | Code & DevOps | 1200 |
| **Saptiva Coder** | 0.20 | Clean code | 1200 |
| **default** | 0.30 | Fallback | 1200 |

### Adding a New Model

1. **Edit** `apps/api/prompts/registry.yaml`:
   ```yaml
   "Saptiva Vision":
     system_base: |
       [base prompt with placeholders]
     addendum: |
       Optimize for visual reasoning.
     params:
       temperature: 0.3
   ```

2. **No code changes needed** - Registry auto-loads on startup
3. **Test** with `make test-all`

### Benefits

- **Consistency**: One change affects all endpoints
- **Traceability**: Hash of system prompt logged per request
- **Flexibility**: Add models without touching Python code
- **Performance**: Singleton cache avoids repeated YAML reads
- **Safety**: Automatic fallback to default if model not found

### Testing

The project includes a comprehensive test suite covering both backend (Python/pytest) and frontend (TypeScript/Jest) with **137 individual tests** across **6 test suites**.

#### Quick Start

```bash
# Run complete test suite (recommended before commits)
make test-all

# Run containerized tests (faster for quick checks)
make test
```

#### Test Suite Overview

**Backend (API) - 52 tests**
- **Prompt Registry** (`test_prompt_registry.py`) - 19 tests
  - Model parameter validation (temperature, top\_p, penalties)
  - YAML configuration loading and parsing
  - Placeholder substitution (`{CopilotOS}`, `{Saptiva}`, `{TOOLS}`)
  - Addendum injection per model
  - Channel-based max\_tokens limits (chat: 1200, report: 3500, title: 64)
  - System prompt hashing for telemetry

- **Registry Configuration E2E** (`test_registry_configuration.py`) - 26 tests
  - Production registry validation (`prompts/registry.yaml`)
  - All 4 models (Turbo, Cortex, Ops, Coder) configuration
  - Parameter consistency and defaults
  - Prompt resolution with real tool descriptions
  - Metadata tracking and versioning

- **Health Check** (`test_health.py`) - 7 tests
  - API liveness and readiness endpoints
  - Database connectivity verification
  - Redis connection validation
  - Service dependencies health status

**Frontend (Web) - 85 tests**
- **Model Mapping** (`modelMap.test.ts`) - 41 tests
  - Backend model ID → UI model slug mapping
  - Fuzzy matching with case-insensitive aliases
  - Default model resolution
  - Model availability handling
  - Integration with model catalog

- **Chat API** (`chatAPI.test.ts`) - 10 tests
  - HTTP client request/response validation
  - Error handling (401 Unauthorized, 422 Validation, Network errors)
  - Channel-specific requests (chat, title, report)
  - Tools enablement payload structure
  - Model selection for all supported models

- **Model Selector** (`modelSelector.test.tsx`) - 34 tests
  - Model catalog structure validation
  - Display metadata (displayName, description, badges)
  - Alias patterns for fuzzy matching
  - Helper functions (getModelBySlug, getAllModels)
  - Badge configuration (CORE, FAST, REASONING, CHAT)

#### Running Specific Tests

```bash
# Backend tests (requires .venv activation)
cd apps/api
source .venv/bin/activate

# Individual test suites
pytest tests/test_prompt_registry.py -v
pytest tests/e2e/test_registry_configuration.py -v
pytest tests/test_health.py -v

# With coverage report
pytest --cov=src --cov-report=html

# Frontend tests
cd apps/web

# All tests
npm test

# Specific test suites
npm test -- __tests__/modelMap.test.ts
npm test -- __tests__/chatAPI.test.ts
npm test -- __tests__/modelSelector.test.tsx

# Watch mode for development
npm test -- --watch
```

#### Test Structure

```
apps/api/tests/
├── test_prompt_registry.py       # Unit tests for prompt system
├── test_health.py                # Health check endpoints
└── e2e/
    └── test_registry_configuration.py  # E2E registry validation

apps/web/__tests__/
├── modelMap.test.ts              # Model mapping logic
├── chatAPI.test.ts               # API client integration
└── modelSelector.test.tsx        # UI model catalog
```

#### Common Issues and Solutions

**Issue**: `ModuleNotFoundError: No module named 'fastapi'`
**Solution**: Reinstall backend dependencies
```bash
cd apps/api && source .venv/bin/activate && pip install -r requirements.txt
```

**Issue**: Jest configuration conflicts
**Solution**: Ensure only one `jest.config.js` exists (not both `.js` and `.cjs`)

**Issue**: `vi is not defined` in frontend tests
**Solution**: Tests should use `jest.fn()` not `vi.fn()` (Jest, not Vitest)

#### Adding New Tests

**Backend (pytest)**:
```python
# apps/api/tests/test_new_feature.py
import pytest

def test_feature_behavior():
    """Test that new feature behaves correctly"""
    result = my_function()
    assert result == expected_value
```

**Frontend (Jest)**:
```typescript
// apps/web/__tests__/newFeature.test.ts
import { describe, it, expect } from '@jest/globals'

describe('New Feature', () => {
  it('should work correctly', () => {
    const result = myFunction()
    expect(result).toBe(expectedValue)
  })
})
```

#### Test Coverage Goals

- **Backend**: Maintain >80% coverage for core modules (prompt\_registry, services)
- **Frontend**: Focus on business logic (model mapping, API clients) over UI components
- **E2E**: Cover critical user flows and integration points

#### CI/CD Integration

The test suite is designed for CI/CD pipelines:
- Fast execution: ~5-10 seconds total
- Exit code 0 on success, 1 on any failure
- Detailed test results with failure diagnostics
- Compatible with GitHub Actions, GitLab CI, Jenkins

## Documentation

### Complete Documentation Index

**Architecture & Features:**
- Arquitectura de LLM y herramientas: `docs/arquitectura/`
- Evidencias reproducibles: `docs/evidencias/llm-tools.md`
- Token expiration handling system: **`docs/TOKEN_EXPIRATION_HANDLING.md`** _(520 lines)_
  Technical specification for JWT token expiration detection, refresh strategies, WebSocket handling, and session preservation.

**Deployment & Operations:**
- Production deployment guide: **`docs/DEPLOYMENT.md`**
- Quick deploy scripts: `docs/QUICK-DEPLOY.md`
- Resource optimization guide: **`docs/RESOURCE_OPTIMIZATION.md`** _(580 lines)_
  Comprehensive guide covering Docker resource analysis, cleanup strategies, Dockerfile optimization, monitoring, and automation.

**Security & Credentials:**
- Production credential rotation: **`docs/PRODUCTION_CREDENTIAL_ROTATION.md`** _(443 lines)_
  Complete step-by-step procedures for safely rotating credentials in production without data loss. Includes critical warnings, rollback plans, and troubleshooting.
- Credential management policies: **`docs/CREDENTIAL_MANAGEMENT.md`**
  Security best practices, rotation schedules, and credential lifecycle management.
- Docker env_file configuration: **`docs/DOCKER_ENV_FILE_CONFIGURATION.md`**
  Technical deep-dive explaining why env_file is critical for credential synchronization and common pitfalls.
- Makefile credential commands: **`docs/MAKEFILE_CREDENTIAL_COMMANDS.md`**
  Reference guide for all credential-related make commands with examples.

**Developer Guides:**
- Quick start guide: `docs/guides/QUICK_START.md`
- Makefile resource commands reference: **`docs/MAKEFILE_RESOURCE_COMMANDS.md`** _(450 lines)_
  User guide for resource monitoring, cleanup commands, deployment workflows, and best practices.

## Getting Started

### Environment Setup

```bash
git clone https://github.com/saptiva-ai/copilotos-bridge
cd copilotos-bridge
make setup                # Creates env files, installs dependencies, prepares .venv
make dev                  # Starts web, API, MongoDB, and Redis containers
make create-demo-user     # Seeds demo credentials for local testing
```

Edit `envs/.env` or `envs/.env.local` to add your SAPTIVA API key before connecting to production resources.

### Useful Commands

- `make help` lists every available task.
- `make logs` tails combined service logs.
- `make test`, `make lint`, and `make security` keep code quality in check.
- `make clean` stops and removes containers.
- `make shell-api` or `make shell-web` opens interactive shells inside containers.

### Demo & Testing Scripts

The project includes a comprehensive suite of demo scripts for rapid testing of chat flows, auto-titling with AI, and conversation management. These scripts provide an automated way to verify the message-first pattern implementation and AI-powered title generation.

#### Demo User Credentials

The demo scripts use a dedicated test user:

```
Username: demo_admin
Email:    demo@saptiva.ai
Password: ChangeMe123!
```

Token storage: `/tmp/demo_token.txt` (automatically managed by scripts)

#### Available Demo Commands

**Quick Test (Recommended):**
```bash
make demo-quick          # Complete automated test: create user + full flow + verification
                         # Perfect for CI/CD or quick smoke tests
```

**User Management:**
```bash
make demo-create-user    # Create demo_admin user via API (idempotent)
make demo-login          # Login and save JWT token to /tmp/demo_token.txt
```

**Conversation Operations:**
```bash
make demo-list-chats     # List all conversations with titles, models, and pin status
                         # Example output:
                         #  1. [abc123...] Optimización consultas SQL
                         #     Modelo: saptiva-turbo

make demo-send-message CHAT_ID=abc123 MSG="Your message"
                         # Send message to existing conversation
```

**Testing Features:**
```bash
make demo-test-autotitle # Test AI auto-titling feature
                         # Creates conversation → sends message → waits 3s
                         # → verifies title updated with AI-generated one

make demo-test-flow      # Complete test flow with colored output
                         # ✓ Authentication
                         # ✓ List conversations
                         # ✓ Create + send message
                         # ✓ Verify auto-titling

make demo-check-models   # Display available models for demo user
```

**Documentation:**
```bash
make demo-help           # Show complete demo scripts documentation
                         # Includes examples, troubleshooting, and advanced usage
```

#### Example Workflow

**Scenario 1: Quick Verification**
```bash
# Verify entire system is working (authentication, API, auto-titling)
make demo-quick

# Output:
# ╔════════════════════════════════════════════════════════════╗
# ║   Test Flow: Message-First + Auto-Titling con IA          ║
# ╚════════════════════════════════════════════════════════════╝
#
# ============================================================
# Paso 1: Autenticación con usuario demo
# ============================================================
# ✓ Login exitoso
# ℹ Usuario: demo_admin (demo@saptiva.ai)
# ...
```

**Scenario 2: Test Auto-Titling**
```bash
# Test that AI generates intelligent titles from messages
make demo-create-user
make demo-test-autotitle

# Verifies:
# 1. Temporary title: "Quiero aprender a optimizar consultas SQL..."
# 2. AI title (after 2-3s): "Optimización consultas PostgreSQL"
```

**Scenario 3: Development Workflow**
```bash
# After making changes to auto-titling code
make rebuild-web         # Rebuild web container
make demo-test-flow      # Verify changes work correctly
make demo-list-chats     # Inspect conversation titles
```

**Scenario 4: Manual Testing**
```bash
# Create user and get token
make demo-create-user
make demo-login

# List existing conversations
make demo-list-chats
# Output: Total de conversaciones: 5

# Send message to conversation
make demo-send-message CHAT_ID=2464b7ce MSG="Explícame índices en PostgreSQL"
```

#### Testing Auto-Titling Feature

The auto-titling system implements a **two-phase progressive enhancement pattern**:

1. **Immediate temporary title**: First line of message (70 chars max)
2. **AI-generated title**: Improved title via `/api/title` endpoint (~2 seconds)

**Verification Steps:**

1. **Browser Test** (Visual):
   ```
   1. Open http://localhost:3000
   2. Login: demo_admin / ChangeMe123!
   3. Click "+" to create conversation
   4. Send long message: "Quiero aprender a optimizar consultas SQL..."
   5. Watch history sidebar - title updates automatically after ~2 seconds
   ```

2. **Automated Test** (CI/CD):
   ```bash
   make demo-test-autotitle
   # Checks:
   # - Temporary title set immediately
   # - AI title different from temporary
   # - Update happens within 5 seconds
   ```

3. **Debug Mode** (Development):
   ```bash
   # Run test flow and watch browser console (F12)
   make demo-test-flow

   # Look for logs:
   # "Auto-titled message-first conversation"
   # originalTitle: "Quiero aprender..."
   # aiTitle: "Optimización consultas SQL"
   ```

#### Script Locations

All demo scripts are in `/tmp/` for easy access:

| Script | Purpose |
|--------|---------|
| `/tmp/create_demo_user.py` | Create demo user via API |
| `/tmp/demo_login.sh` | Login and save token |
| `/tmp/demo_list_chats.sh` | List conversations |
| `/tmp/demo_send_message.sh` | Send message to chat |
| `/tmp/demo_test_autotitle.sh` | Test auto-titling feature |
| `/tmp/demo_test_flow.py` | Complete test flow (Python, colored) |
| `/tmp/check_models.py` | List available models |
| `/tmp/DEMO_SCRIPTS_README.md` | Full documentation |

#### Integration with CI/CD

The demo scripts are designed for automated testing pipelines:

```yaml
# Example GitHub Actions workflow
- name: Test Auto-Titling Feature
  run: |
    make setup
    make dev
    sleep 30  # Wait for services
    make demo-quick || exit 1
```

**Exit Codes:**
- `0`: All tests passed
- `1`: Authentication failed
- `1`: API error or network issue
- `1`: Auto-titling verification failed

#### Troubleshooting Demo Scripts

**Issue: Token expired or invalid**
```bash
# Solution: Get fresh token
make demo-login
```

**Issue: "No demo user found"**
```bash
# Solution: Create user first
make demo-create-user
```

**Issue: "Auto-titling not detected"**
```bash
# Possible causes:
# 1. AI API key not configured
# 2. Network latency >5 seconds
# 3. /api/title endpoint error

# Debug:
docker logs copilotos-api | grep -i "title\|error"
make demo-check-models  # Verify models available
```

**Issue: Scripts not found in `/tmp/`**
```bash
# Scripts are created on-demand. Run once:
make demo-help  # This ensures all scripts exist
```

#### Advanced Usage

**Custom Test Message:**
```bash
# Edit /tmp/demo_test_flow.py line 200
test_message = "Your custom test message here..."
python3 /tmp/demo_test_flow.py
```

**Use Different Model:**
```bash
# Edit /tmp/demo_test_flow.py line 113
default_model = {"id": "saptiva-cortex", "name": "Saptiva Cortex"}
```

**Adjust Auto-Title Wait Time:**
```bash
# Edit /tmp/demo_test_autotitle.sh line 69
sleep 5  # Wait 5 seconds instead of 3
```

For complete documentation with examples and troubleshooting, run:
```bash
make demo-help
```

### Common Issue: Code Changes Not Reflected in Containers?

**Problem:** Docker caches image layers for faster builds. When you modify code or change environment variables, a simple `docker compose up` or `docker restart` won't pick up the changes because:

1. **Docker Build Cache**: Uses cached layers from previous builds
2. **Restart vs Recreate**: `docker restart` keeps the same container with old code
3. **Environment Variables**: `restart` doesn't reload env vars from `.env` files

**Solution:**

```bash
# For code changes in API:
make rebuild-api      # Builds with --no-cache, then down/up to recreate container

# For env var changes or major updates:
make rebuild-all      # Rebuilds all containers without cache

# Alternative manual approach:
docker compose -f infra/docker-compose.yml --env-file envs/.env build --no-cache api
docker compose -f infra/docker-compose.yml --env-file envs/.env down api
docker compose -f infra/docker-compose.yml --env-file envs/.env up -d api
```

**Why `--no-cache` + `down`/`up`?**
- `--no-cache`: Forces Docker to rebuild all layers (ignores cache)
- `down` + `up`: Destroys old container and creates fresh one with new code + env vars
- `restart` alone: Keeps old container, old code, old env vars

**Quick Check:**
```bash
# Verify code is synced
make debug-file-sync

# Check if env vars loaded
docker exec copilotos-api env | grep YOUR_VAR_NAME
```

## Resource Optimization & Maintenance

The project includes comprehensive resource monitoring and cleanup tools to optimize Docker resource usage, reduce disk space consumption, and maintain system performance.

### Quick Resource Commands

**Monitor Resources:**
```bash
make resources              # Show Docker disk usage, container stats, and system memory
make resources-monitor      # Real-time monitoring (updates every 2s, Ctrl+C to exit)
```

**Cleanup Commands:**
```bash
make docker-cleanup         # Safe cleanup: removes build cache >7 days, dangling images, stopped containers
                           # Interactive confirmation for orphaned volumes
                           # Safe to run weekly

make docker-cleanup-aggressive  # Deep cleanup: removes ALL unused images, volumes, and build cache
                               # Requires explicit confirmation: type "yes"
                               # Only use for major cleanup (monthly/as-needed)
```

### When to Use Each Command

**Daily Development Workflow:**
```bash
# Check resource usage before starting work
make resources

# If "RECLAIMABLE" column shows >10 GB:
make docker-cleanup
```

**Weekly Maintenance:**
```bash
# Every Friday or weekend
make docker-cleanup         # Frees 5-15 GB typically
make resources              # Verify cleanup results
```

**Monthly Deep Clean:**
```bash
# Before major releases or when disk is filling up
make docker-cleanup-aggressive  # Frees 50-70 GB typically
make dev-build                  # Rebuild cache (takes 5-10 min first time)
```

**Production Deployment:**
```bash
# Option 1: Fast deployment (incremental build, 3-5 min)
make deploy-fast

# Option 2: Regular deployment (recommended default, 8-12 min)
make deploy

# Option 3: Clean deployment (guaranteed fresh, 12-15 min)
make deploy-clean
```

### Resource Limits Configuration

Optional resource limits can be enabled to prevent memory leaks and ensure stable operation:

```bash
# Add resource limits to development
COMPOSE_RESOURCES=1 make dev

# Production with limits (recommended)
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.resources.yml \
               up -d
```

**Configured Limits:**
| Service  | CPU Max  | RAM Max | RAM Min |
|----------|----------|---------|---------|
| API      | 1 core   | 512 MB  | 128 MB  |
| Web      | 1 core   | 1 GB    | 256 MB  |
| MongoDB  | 1 core   | 512 MB  | 256 MB  |
| Redis    | 0.5 core | 128 MB  | 32 MB   |

**Benefits:**
- Prevents memory leaks from consuming all system RAM
- Fair resource distribution across services
- Easier debugging with clear resource boundaries
- Allows running more services on same hardware

### Typical Cleanup Results

**After `make docker-cleanup`:**
```
Before:  35 GB Docker usage (20 GB reclaimable)
After:   15 GB Docker usage (0.5 GB reclaimable)
Freed:   20 GB (57% reduction)
```

**After `make docker-cleanup-aggressive`:**
```
Before:  75 GB Docker usage (55 GB reclaimable)
After:   4.5 GB Docker usage (0 GB reclaimable)
Freed:   70.5 GB (94% reduction)
```

### Documentation

- **Quick reference:** [`docs/MAKEFILE_RESOURCE_COMMANDS.md`](docs/MAKEFILE_RESOURCE_COMMANDS.md) - All commands with examples
- **Deep dive:** [`docs/RESOURCE_OPTIMIZATION.md`](docs/RESOURCE_OPTIMIZATION.md) - Technical optimization strategies
- **Configuration:** [`infra/docker-compose.resources.yml`](infra/docker-compose.resources.yml) - Resource limits

---

## Credential Management & Security

The project includes comprehensive credential rotation tools that allow safe password changes **WITHOUT data loss**. This prevents the common mistake of deleting volumes (and losing production data) when credentials need to be updated.

### Quick Credential Commands

**Generate Secure Passwords:**
```bash
make generate-credentials    # Creates 32-char passwords and 64-char JWT secrets
                            # Copy the generated values to envs/.env or envs/.env.prod
```

**Rotate Passwords Safely (No Data Loss):**
```bash
make rotate-mongo-password   # Interactive MongoDB password rotation
                            # Uses db.changeUserPassword() - preserves all data

make rotate-redis-password   # Interactive Redis password rotation
                            # Uses CONFIG SET requirepass - preserves cache data
```

**Production Validation:**
```bash
make validate-production     # Pre-rotation safety checks
                            # Validates: env_file config, credential sync, backups, scripts
                            # Run BEFORE any production credential rotation
```

**Development Reset (Deletes Data):**
```bash
make reset                   # ▲ Complete environment reset
                            # Stops containers → deletes volumes → generates new credentials → restarts
                            # ONLY for development - NEVER in production!
```

### Credential Rotation Workflow

**Local Development Rotation:**
```bash
# 1. Generate new password
make generate-credentials

# 2. Rotate MongoDB (interactive, prompts for old/new passwords)
make rotate-mongo-password
# Enter old password: <current_password>
# Enter new password: <paste_generated_password>

# 3. Update .env file
nano envs/.env
# Change: MONGODB_PASSWORD=<new_password>

# 4. Recreate containers (IMPORTANT: down+up, NOT restart)
docker compose -f infra/docker-compose.yml down api
docker compose -f infra/docker-compose.yml up -d api

# 5. Verify
curl http://localhost:8001/api/health
```

**Production Rotation (Safe):**
```bash
# 1. ALWAYS validate before rotating in production
make validate-production

# 2. Create backup BEFORE rotation
make backup-mongodb-prod     # or appropriate backup command

# 3. Follow the detailed production guide
# See: docs/PRODUCTION_CREDENTIAL_ROTATION.md
```

### Critical: Why Restart Doesn't Work

**Common Mistake:**
```bash
# ✖ WRONG - This doesn't reload environment variables!
docker compose restart api
```

**Problem:** `docker compose restart` keeps the same container with OLD environment variables from when it was created.

**Correct Approach:**
```bash
# ✔ CORRECT - Recreates container with NEW environment variables
docker compose down api
docker compose up -d api
```

### Security Best Practices

**Rotation Schedule (Recommended):**
- **MongoDB Password**: Every 3 months
- **Redis Password**: Every 3 months
- **JWT Secret Key**: Every 6 months
- **SAPTIVA API Key**: Per provider's security policy

**Always:**
- ✔ Test rotation in DEV before PROD
- ✔ Create backup before rotating in PROD
- ✔ Run `make validate-production` before PROD rotation
- ✔ Use different credentials for DEV vs PROD
- ✔ Store PROD credentials in secure vault (1Password, AWS Secrets Manager, etc.)

**Never:**
- ✖ Use `docker compose restart` after credential changes
- ✖ Delete volumes to "fix" credential mismatches
- ✖ Run `make reset` in production
- ✖ Commit credentials to git
- ✖ Reuse DEV credentials in PROD

### Testing Credential Rotation

The project includes a comprehensive test suite to verify credential rotation works correctly:

```bash
# Run complete credential rotation test
./scripts/test-credential-rotation.sh

# Tests performed:
# ✓ Create test user and conversation
# ✓ Rotate MongoDB password (verifies data preserved)
# ✓ Rotate Redis password (verifies cache preserved)
# ✓ Create backup before/after rotation
# ✓ Test backup restore functionality
# ✓ Verify user can still login after both rotations
```

### Troubleshooting Credentials

**Issue: "Authentication failed" after rotation**

**Diagnosis:**
```bash
# Compare password in .env vs container
echo "Password in .env:"
grep MONGODB_PASSWORD envs/.env

echo "Password in container:"
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' | grep MONGO_INITDB_ROOT_PASSWORD
```

**Cause:** Used `restart` instead of `down`+`up`

**Solution:**
```bash
docker compose -f infra/docker-compose.yml down api mongodb redis
docker compose -f infra/docker-compose.yml up -d api mongodb redis
```

**Issue: Credential mismatch between services**

**Validation:**
```bash
# Run comprehensive validation
make validate-production

# Look for:
# ✖ MongoDB password MISMATCH between .env and container!
# ✖ Redis password MISMATCH between .env and container!
```

**Solution:** Recreate containers (see above)

### Documentation

**Complete Guides:**
- **Production rotation:** [`docs/PRODUCTION_CREDENTIAL_ROTATION.md`](docs/PRODUCTION_CREDENTIAL_ROTATION.md) - Step-by-step production procedures (443 lines)
- **General management:** [`docs/CREDENTIAL_MANAGEMENT.md`](docs/CREDENTIAL_MANAGEMENT.md) - Credential policies and workflows
- **Technical details:** [`docs/DOCKER_ENV_FILE_CONFIGURATION.md`](docs/DOCKER_ENV_FILE_CONFIGURATION.md) - Why env_file is critical
- **Command reference:** [`docs/MAKEFILE_CREDENTIAL_COMMANDS.md`](docs/MAKEFILE_CREDENTIAL_COMMANDS.md) - All commands with examples

**Scripts:**
- `scripts/rotate-mongo-credentials.sh` - Safe MongoDB rotation (uses db.changeUserPassword)
- `scripts/rotate-redis-credentials.sh` - Safe Redis rotation (uses CONFIG SET)
- `scripts/validate-production-readiness.sh` - Pre-rotation validation (10 checks)
- `scripts/test-credential-rotation.sh` - Automated testing suite

### Production Checklist

Before rotating credentials in production:

- [ ] **Validation passed**: `make validate-production` shows ✔
- [ ] **Backup created**: Recent backup < 24 hours old
- [ ] **Backup verified**: Backup file exists and size > 0
- [ ] **Tested in staging**: Rotation tested in non-prod first
- [ ] **Maintenance window**: Team notified, low-traffic period scheduled
- [ ] **Rollback plan**: Documented procedure to revert if needed
- [ ] **Monitoring ready**: Logs/metrics dashboard open for verification
- [ ] **Credentials stored**: New passwords saved in vault BEFORE rotation
- [ ] **Documentation**: `docs/PRODUCTION_CREDENTIAL_ROTATION.md` reviewed

**After rotation:**
- [ ] Health check passing: `make health`
- [ ] Users can login successfully
- [ ] Post-rotation backup created
- [ ] Secrets manager updated with new credentials
- [ ] Team notified of successful rotation
- [ ] Rotation calendar updated

---

## ▸ Lessons Learned from Production Issues

This section documents critical lessons learned from real production debugging sessions. These insights will help future developers avoid common pitfalls and understand why certain patterns are required.

### 1. Docker Compose `restart` Does NOT Reload Environment Variables

**The Problem:**
After updating credentials in `.env` and running `docker compose restart`, authentication failures occur because containers still use OLD environment variables.

**Why It Happens:**
- `docker compose restart` only stops and starts the process inside the existing container
- It does NOT recreate the container or reload environment variables from `.env`
- The container keeps the environment variables it had when it was created

**Real-World Impact:**
- **Symptom**: "Cargando conversaciones..." stuck loading indefinitely
- **Symptom**: Chat responses hang at "Generando respuesta..."
- **Symptom**: Redis WRONGPASS errors in logs
- **Symptom**: MongoDB authentication failures

**The Solution:**
```bash
# ✖ WRONG - Does NOT reload env vars
docker compose restart api

# ✔ CORRECT - Recreates container with new env vars
docker compose down api
docker compose up -d api
```

**Commands Affected:**
- `make restart` - Now uses `down` + `up` pattern (fixed)
- `make rotate-mongo-password` - Instructs to use `down` + `up`
- `make rotate-redis-password` - Instructs to use `down` + `up`

**Prevention:**
- Always use `make restart` instead of `docker compose restart` directly
- After updating `.env`, always recreate containers with `down` + `up`
- Never assume `restart` will pick up configuration changes

### 2. env_file Directive is Critical for Credential Synchronization

**The Problem:**
Without `env_file` in `docker-compose.yml`, services don't automatically load variables from `.env`, causing credential desynchronization.

**Required Configuration:**
```yaml
services:
  api:
    env_file:
      - ../envs/.env  # ← CRITICAL - Without this, .env is ignored
    environment:
      MONGODB_PASSWORD: ${MONGODB_PASSWORD}
```

**What Happens Without It:**
- Services use hardcoded defaults or shell environment variables
- Changes to `.env` file are completely ignored
- Credential rotation scripts fail silently
- Container environment != `.env` file contents

**Verification:**
```bash
# Check if .env matches container
grep MONGODB_PASSWORD envs/.env
docker inspect copilotos-mongodb --format='{{range .Config.Env}}{{println .}}{{end}}' | grep MONGO_INITDB

# If they don't match → missing env_file or need container recreation
```

### 3. Saptiva API Integration Requirements

Through extensive debugging, we discovered specific requirements for integrating with the Saptiva API:

**Endpoint Format:**
```bash
# ✖ WRONG - Returns 307 redirect or 404
POST https://api.saptiva.com/v1/chat/completions

# ✔ CORRECT - Must have trailing slash
POST https://api.saptiva.com/v1/chat/completions/
```

**Model Name Capitalization:**
```python
# ✖ WRONG - Returns 404 "Model not found"
{"model": "saptiva-turbo"}
{"model": "SAPTIVA_TURBO"}

# ✔ CORRECT - Must use exact capitalization
{"model": "Saptiva Turbo"}
{"model": "Saptiva Cortex"}
```

**Redirect Handling:**
```python
# ✔ REQUIRED - Saptiva uses 307 redirects for slash normalization
client = httpx.AsyncClient(
    follow_redirects=True,  # ← Must be enabled
    http2=True
)
```

**Solution Implemented:**
- Added model name mapping: `"saptiva-turbo"` → `"Saptiva Turbo"`
- Updated endpoint to include trailing slash
- Enabled `follow_redirects=True` in httpx client
- See: `apps/api/src/services/saptiva_client.py:187-200`

### 4. Credential Desynchronization is the #1 Cause of Runtime Failures

**Common Symptoms:**
- Conversations endpoint returns 500 error
- Chat endpoint hangs or fails
- "Cargando conversaciones..." never completes
- "Generando respuesta..." shows but nothing happens

**Root Cause Pattern:**
1. Developer updates password in `.env` file
2. Developer runs `docker compose restart` (wrong!)
3. Container keeps old password, `.env` has new password
4. API tries to connect with new password from `.env`
5. Database rejects connection (still has old password)

**Diagnostic Commands:**
```bash
# Step 1: Check what password .env file has
grep REDIS_PASSWORD envs/.env

# Step 2: Check what password container is actually using
docker inspect copilotos-redis --format='{{range .Config.Env}}{{println .}}{{end}}' | grep REDIS_PASSWORD

# Step 3: If they don't match → credential desync
# Solution: Recreate container
docker compose down redis api
docker compose up -d redis api
```

**Prevention Checklist:**
- [ ] Always use `make restart` after credential changes
- [ ] Never use `docker compose restart` for configuration changes
- [ ] Run `make validate-production` before production changes
- [ ] Test credential rotation in DEV before PROD

### 5. Health Checks Are Essential After Configuration Changes

**The Problem:**
Scripts would declare success before services were actually ready, causing subsequent operations to fail.

**Example from `make reset`:**
```bash
# ✖ OLD - No verification
make dev
echo "Reset complete!"  # Too early!

# ✔ NEW - Wait for readiness
make dev
sleep 5
MAX_ATTEMPTS=30
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
        echo "✓ Services ready!"
        break
    fi
    sleep 2
done
```

**Where Applied:**
- `make reset` - Waits for health check after environment recreation
- `make restart` - Checks API health after container restart
- `scripts/test-credential-rotation.sh` - Validates services between rotations

### 6. Common Troubleshooting Patterns

**Pattern 1: Service Won't Start**
```bash
# Diagnosis sequence
docker logs copilotos-<service>  # Check for errors
make resources                   # Check disk space
docker system df                  # Check Docker resources
make docker-cleanup              # Free up space if needed
```

**Pattern 2: Authentication Errors**
```bash
# Diagnosis sequence
make validate-production         # Check credential sync
docker compose down <service>    # Recreate with fresh env
docker compose up -d <service>
curl http://localhost:8001/api/health  # Verify
```

**Pattern 3: Changes Not Reflected**
```bash
# For code changes
make rebuild-api                 # Rebuilds with --no-cache

# For env var changes
make restart                     # Uses down+up, not restart

# For major changes
make rebuild-all                 # Complete rebuild
```

### Quick Reference: Critical Commands

```bash
# ✔ SAFE - Use these
make restart                     # Recreates containers (reloads env)
make rebuild-api                 # Rebuilds API with fresh code
docker compose down && up        # Properly recreates containers

# ✖ UNSAFE - Avoid these
docker compose restart           # Does NOT reload env vars!
docker volume rm <vol>           # Deletes data permanently!
make reset  (in prod)           # NEVER in production!
```

### Documentation References

For deeper understanding of these issues:
- **Credential Management**: [docs/PRODUCTION_CREDENTIAL_ROTATION.md](docs/PRODUCTION_CREDENTIAL_ROTATION.md)
- **Docker Configuration**: [docs/DOCKER_ENV_FILE_CONFIGURATION.md](docs/DOCKER_ENV_FILE_CONFIGURATION.md)
- **Makefile Commands**: See comments in `Makefile` CREDENTIAL MANAGEMENT section
- **Test Scripts**: `scripts/test-credential-rotation.sh` validates these patterns

---

### Default Development Credentials

```
Username: demo
Password: Demo1234
Email:    demo@example.com
MongoDB:  mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos
Redis:    redis://:redis_password_change_me@localhost:6379
```

Change these values for any shared or production environment.

### Troubleshooting

- Use `make logs` followed by `make clean` and `make dev` to recover from container errors.
- Clear Next.js artifacts with `make clean-next` if the frontend fails to compile.

## Contributing

We welcome contributions of any size. Please open an issue before large changes so we can help align scope and security requirements.

### Development Workflow

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Run validations
make test
make lint
make security

# Commit with conventional messages
git commit -m "feat: describe change"
```

## Docker & Permission Issues

#### Docker Permission Problems (Most Common)
```bash
# Problem: .next directory owned by root
sudo rm -rf apps/web/.next

# Solution: Run permission fix
./scripts/fix-docker-permissions.sh

# Verify fix worked
./scripts/test-docker-permissions.sh

# For future builds
./scripts/docker-build.sh web
```

#### Container Startup Issues
```bash
# Check service status
make status
docker ps -a

# View service logs
make logs
docker logs copilotos-api
docker logs copilotos-web

# Restart services
make restart

# Complete reset
make clean && make dev
```
### Security & Authentication Issues

#### Missing or Invalid API Keys
```bash
# Check configuration
./scripts/validate-config.sh

# Regenerate secrets
./scripts/generate-production-secrets.sh

# Verify SAPTIVA API key
curl -H "Authorization: Bearer $SAPTIVA_API_KEY" \
  https://api.saptiva.com/health
```

#### Authentication Failures
```bash
# Test login endpoint
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier": "demo_admin", "password": "ChangeMe123!"}'

# Check user exists
make list-users

# Reset demo user
make delete-demo-user && make create-demo-user

# Check JWT configuration
grep JWT_SECRET_KEY envs/.env.local
```

### Database Connection Issues

#### MongoDB Connection Problems
```bash
# Check MongoDB service
docker logs copilotos-mongodb
make shell-db

# Test connectivity
docker exec copilotos-mongodb mongosh \
  "mongodb://copilotos_user:password@localhost:27017/copilotos?authSource=admin"

# Reset database
docker volume rm copilotos_mongodb_data
make dev
```

#### Redis Connection Issues
```bash
# Check Redis service
docker logs copilotos-redis
make shell-redis

# Test connectivity
docker exec copilotos-redis redis-cli \
  -a "your-redis-password" ping

# Clear Redis cache
docker exec copilotos-redis redis-cli \
  -a "your-redis-password" FLUSHALL
```

### Network & API Issues

#### API Connection Errors
```bash
# Check API health
curl http://localhost:8001/api/health

# Check API logs
docker logs copilotos-api

# Test internal connectivity
docker exec copilotos-web curl http://api:8001/api/health

# Verify port bindings
docker port copilotos-api
docker port copilotos-web
```

#### Frontend Build Issues
```bash
# Permission-related build failures
./scripts/fix-docker-permissions.sh

# Clear build cache
docker system prune -f
make clean
make build

# Check Next.js configuration
cat apps/web/next.config.js | grep distDir
```

#### Test Authentication Flow
```python
# Register new user (password requirements: 8+ chars, uppercase, lowercase, number/symbol)
import requests

response = requests.post(
    "http://localhost:8001/api/auth/register",
    json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",  # Must have uppercase!
        "name": "Test User"
    }
)
print(f"Register: {response.status_code}")
print(response.json())

# Login (returns access_token, refresh_token, expires_in, user)
response = requests.post(
    "http://localhost:8001/api/auth/login",
    json={
        "identifier": "testuser",  # Can be username or email
        "password": "TestPass123!"
    }
)
token = response.json()["access_token"]
print(f"Token: {token[:50]}...")
```

#### Test Chat with Saptiva
```python
# Chat endpoint schema: /api/chat
# Request: {"message": str, "model": str, "stream": bool, "chat_id": str (optional)}
# Response: {"chat_id": str, "message_id": str, "content": str, "model": str, "created_at": datetime}

response = requests.post(
    "http://localhost:8001/api/chat",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "message": "Hello",
        "model": "Saptiva Turbo",  # IMPORTANT: Use exact case!
        "stream": False
    }
)
print(f"Chat: {response.status_code}")
print(response.json()["content"])
```

#### Verify Saptiva API Configuration
```bash
# Check API key is loaded in container
docker exec copilotos-api printenv | grep SAPTIVA_API_KEY

# Test models endpoint (public, no auth required)
curl http://localhost:8001/api/models

# Check API logs for Saptiva errors
docker logs copilotos-api | grep -i saptiva
```

#### Common Saptiva API Issues

**Issue: "Model not found" (404)**
- **Cause**: Model name case sensitivity
- **Solution**: Use exact case: `"Saptiva Turbo"`, `"Saptiva Cortex"`, etc.
- **NOT**: `"saptiva turbo"` or `"SAPTIVA_TURBO"`

**Issue: SAPTIVA_API_KEY empty in container**
- **Cause**: Docker Compose variable substitution reads from shell, not env_file
- **Solution**: Remove `${SAPTIVA_API_KEY}` from docker-compose.yml, let env_file load it

**Issue: "Connection refused" to Saptiva**
- **Cause**: API key not configured or invalid
- **Solution**: Verify API key in `envs/.env`:
```bash
# Correct format (no quotes, no spaces around =)
SAPTIVA_API_KEY=va-ai-xxxxx...
SAPTIVA_BASE_URL=https://api.saptiva.com
```

#### Available Endpoints Reference
```bash
# Public endpoints (no auth required)
GET  /api/health           # Health check
GET  /api/models           # List available models
GET  /api/feature-flags    # Feature toggles

# Auth endpoints
POST /api/auth/register    # Register user
POST /api/auth/login       # Login (returns tokens)
POST /api/auth/refresh     # Refresh access token
GET  /api/auth/me          # Get current user
POST /api/auth/logout      # Logout

# Chat endpoints (require auth)
POST /api/chat             # Send message
GET  /api/chat/history     # Get chat history
GET  /api/conversations    # List conversations

# Research endpoints (require auth)
POST /api/deep-research    # Start research task
GET  /api/report/{id}      # Get research report
```


## Production Deployment

For complete production deployment instructions, including:
- Security pre-flight checks
- Multiple deployment methods (TAR transfer, Docker Registry, Manual)
- Step-by-step deployment process
- Post-deployment verification
- Troubleshooting
- Rollback procedures
- Monitoring & maintenance
- Backup & disaster recovery

➤ **See: [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md)**

### Quick Deploy Commands

```bash
# Regular deployment (recommended)
make deploy           # Full build with cache (8-12 min)

# Quick fixes
make deploy-fast      # Incremental build (3-5 min)

# Clean rebuild
make deploy-clean     # No-cache rebuild (12-15 min)

# Check deployment status
make deploy-status    # Verify production server
```

---

## Contributing

We welcome contributions of any size. Please open an issue before large changes so we can help align scope and security requirements.

### Development Workflow

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Run validations
make test
make lint
make security

# Commit with conventional messages
git commit -m "feat: describe change"
```

### Contribution Guidelines
- Do not commit secrets or production credentials.
- Add or update tests alongside new features and fixes.
- Update documentation when behavior or configuration changes.
- Follow existing coding patterns and formatting rules.
- Expect every pull request to receive a security review.

### Project Areas
- Frontend: React/Next.js components and the conversation experience.
- Backend: FastAPI endpoints, orchestrators, and service integrations.
- Infrastructure: Dockerfiles, Compose profiles, and deployment automation.
- Security: Authentication, authorization, and hardening improvements.
- Documentation: Technical writing, diagrams, and troubleshooting guides.

### Reporting Issues
1. Search existing issues before creating a new report.
2. Use the issue templates and include reproduction steps whenever possible.
3. Share logs, system details, and screenshots that help triage the problem.

### Requesting Features
1. Review the roadmap to avoid duplicate requests.
2. Describe the business value and success criteria.
3. Outline potential implementation considerations or constraints.



## Support

- Documentation: consult the sections in `docs/`
- Issues: [GitHub Issues](https://github.com/your-org/copilotos-bridge/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/copilotos-bridge/discussions)
- Security reports: notify [security@your-domain.com]

## Acknowledgments

- SAPTIVA for the primary LLM integration.
- Aletheia for the deep-research orchestration layer.
- Next.js and FastAPI for the foundation of the web and API stacks.
- Docker for the consistent development and deployment workflows.

## License

```
MIT License

Copyright (c) 2024 Copilotos Bridge Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
