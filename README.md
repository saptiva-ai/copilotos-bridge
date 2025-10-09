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

---

## 🚀 Quick Start for New Developers

**First time here?** Check out our comprehensive getting started guide:

👉 **[Getting Started Guide](docs/GETTING_STARTED.md)** - Complete step-by-step setup guide (5 minutes to running stack)

This guide includes:
- ✅ Prerequisites checklist
- ✅ Interactive setup (recommended)
- ✅ Manual configuration options
- ✅ Common troubleshooting
- ✅ Useful development commands

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
│   ├── security-audit.sh            # Security validation
│   ├── test-docker-permissions.sh   # Permission testing
│   ├── docker-cleanup.sh            # Docker resource cleanup
│   └── create-demo-user.py          # Demo user creation
├── docs/
│   ├── DEPLOYMENT.md                        # Production deployment guide
│   ├── TOKEN_EXPIRATION_HANDLING.md         # JWT expiration & session management
│   ├── RESOURCE_OPTIMIZATION.md             # Docker resource optimization strategies
│   ├── MAKEFILE_RESOURCE_COMMANDS.md        # Resource command reference
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

**Optimized Builds:**
```bash
make build-optimized        # Build with inline cache, multi-stage optimization
                           # Results in 30-50% smaller images

make deploy-optimized       # Complete workflow: cleanup → optimized build → deploy → post-cleanup
                           # Recommended for production deployments
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
# Option 1: Quick deploy (if recent builds are good)
make deploy-quick

# Option 2: Optimized deploy (recommended for releases)
make deploy-optimized       # 15-20 min, includes cleanup + optimizations

# Option 3: Clean build (guaranteed fresh)
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


### Deployment Options

#### Option A: Automated Tar Deployment (Recommended)

```bash
# One-command deployment (no registry needed)
make deploy-tar
```

**Advantages:**
- No Docker Registry setup required
- Full automation (12 min total)
- Proper image tagging handled automatically
- Built-in verification steps

**See:** [`docs/archive/DEPLOYMENT-TAR-GUIDE.md`](docs/archive/DEPLOYMENT-TAR-GUIDE.md) for details

#### Option B: Docker Registry Deployment (Faster)

```bash
# Setup GitHub Packages (one-time)
export GITHUB_TOKEN=ghp_your_token

# Deploy (3 min total)
make deploy-prod
```

**Advantages:**
- Fastest deployment (~3 min)
- Build once, deploy many times
- Version management built-in

**See:** [`scripts/README-DEPLOY.md`](scripts/README-DEPLOY.md) for setup

#### Option C: Manual Build (Legacy)

```bash
# Fix Docker permissions
./scripts/fix-docker-permissions.sh

# Build production images
cd infra
export UID=$(id -u)
export GID=$(id -g)
docker-compose --profile production build --no-cache

# Start services (without nginx initially)
docker-compose up -d mongodb redis api
```

### Nginx & SSL Setup

```bash
# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/copilotos > /dev/null << 'EOF'
server {
    server_name your-domain.com;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=web:10m rate=300r/m;

    # API Backend (with rate limiting)
    location /api/ {
        limit_req zone=api burst=20 nodelay;

        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Timeouts for long-running requests
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Frontend Application
    location / {
        limit_req zone=web burst=50 nodelay;

        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Disable buffering for real-time features
        proxy_buffering off;
        proxy_cache off;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }

    listen 80;
}
EOF

# Replace your-domain.com with actual domain
sudo sed -i 's/your-domain.com/actual-domain.com/g' /etc/nginx/sites-available/copilotos

# Enable site
sudo ln -s /etc/nginx/sites-available/copilotos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com --non-interactive --agree-tos --email admin@your-domain.com
```

### Start Production Services

```bash
# Start web service
cd /opt/copilotos-bridge/infra
docker-compose --profile production up -d web

# Start nginx reverse proxy
docker-compose --profile production up -d nginx

# Verify all services are running
docker-compose ps
```

### Production Health Verification

```bash
# Check all containers
docker ps

# Test API health
curl -s https://your-domain.com/api/health | jq

# Test web application
curl -s -o /dev/null -w "%{http_code}" https://your-domain.com

# Monitor logs
docker-compose logs -f --tail=50

# Check SSL certificate
curl -vI https://your-domain.com 2>&1 | grep -A 2 "SSL certificate"
```

### Zero-Downtime Updates

```bash
# 1. Prepare update
cd /opt/copilotos-bridge
git pull origin main

# 2. Test configuration
./scripts/validate-config.sh

# 3. Build new images with versioning
docker-compose --profile production build --no-cache
docker tag copilotos-web:latest copilotos-web:backup

# 4. Rolling update
docker-compose --profile production up -d --no-deps web

# 5. Health check
sleep 30
curl -f https://your-domain.com/api/health

# 6. Rollback if needed (only if health check fails)
# docker-compose --profile production stop web
# docker tag copilotos-web:backup copilotos-web:latest
# docker-compose --profile production up -d web
```

### Monitoring & Maintenance

```bash
# Real-time monitoring
docker-compose logs -f --tail=100

# System health dashboard
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Database health
docker exec copilotos-mongodb mongosh --eval "db.runCommand('ping')"
docker exec copilotos-redis redis-cli -a "$REDIS_PASSWORD" ping

# Storage monitoring
df -h
docker system df

# Log rotation (setup cron job)
echo "0 2 * * * docker system prune -f --filter until=72h" | sudo crontab -

# SSL certificate renewal (automatic with certbot)
sudo certbot renew --dry-run
```

### Production Troubleshooting

```bash
# Container health check
docker-compose ps
docker-compose logs api web nginx

# Network connectivity
docker exec copilotos-web curl -f http://api:8001/api/health
docker exec copilotos-api curl -f http://mongodb:27017

# Database debugging
docker exec -it copilotos-mongodb mongosh
docker exec -it copilotos-redis redis-cli -a "$REDIS_PASSWORD"

# Performance monitoring
htop
iotop
nethogs

# Emergency restart
docker-compose --profile production restart
```


###  Backup & Disaster Recovery

```bash
# Database backup script
#!/bin/bash
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
docker exec copilotos-mongodb mongodump \
  --authenticationDatabase admin \
  --username copilotos_user \
  --password "$MONGODB_PASSWORD" \
  --out /backup/mongodb_$BACKUP_DATE

# Automated backup cron job
echo "0 3 * * * /opt/copilotos-bridge/scripts/backup.sh" | sudo crontab -

# Restore from backup
docker exec copilotos-mongodb mongorestore \
  --authenticationDatabase admin \
  --username copilotos_user \
  --password "$MONGODB_PASSWORD" \
  /backup/mongodb_20240101_030000

# Configuration backup
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  envs/ scripts/ infra/docker-compose.yml
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
