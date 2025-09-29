# 🤖 Copilotos Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Security](https://img.shields.io/badge/Security-Enterprise-red.svg)](#-security-architecture)

> **Production-ready ChatGPT-style conversational interface for SAPTIVA language models with integrated Deep Research capabilities and enterprise-grade security.**

## 🚀 Overview

**🎯 Core Features:**
- **🎨 ChatGPT-Style UX**: Complete interface with hierarchical model selector, conversation history, and modern interactions
- **🔗 Real SAPTIVA Integration**: Direct connection to SAPTIVA language models (production-ready, no mock responses)
- **💬 Advanced Chat Features**: File attachments, message actions (copy, regenerate), streaming responses, keyboard shortcuts
- **🔍 Deep Research**: Integrated Aletheia orchestrator for comprehensive research with source traceability
- **🔒 Enterprise Security**: Multi-layer security with JWT authentication, secrets management, and Docker hardening
- **♿ Full Accessibility**: Complete keyboard navigation, ARIA labels, and responsive design
- **🐳 Docker Optimized**: Production-ready containers with proper permission handling and security

## 🧰 Requirements

### System Requirements
- **Docker & Docker Compose** (20.10+ recommended)
- **Node.js** >= 18.0.0 (for local development)
- **Python** >= 3.10 (for local development)
- **pnpm** >= 8.0 (recommended) or npm

### Services (Included in Docker Compose)
- **MongoDB** >= 7.0 (with replica set support)
- **Redis** >= 7.0 (with AOF persistence)
- **Nginx** 1.25+ (for production reverse proxy)

### External Dependencies
- **SAPTIVA API Key** (required - no demo mode)
- **Domain & SSL Certificate** (for production deployment)

## 🏗️ Architecture

The bridge combines a Next.js conversation client, a FastAPI orchestration layer, and AI/research providers. Redis accelerates hot paths (sessions, rate limiting, streaming cursors) while MongoDB stores durable chat, research, and audit history.

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

### 🔄 Conversation & Research Flow

The following sequence shows how a user message is processed, routed between SAPTIVA chat and Aletheia deep research, and streamed back to the client.

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

### 🗄️ Data Persistence Map

MongoDB collections and their relationships capture chats, research tasks, and unified history; Redis holds ephemeral indices referenced by the services above.

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

### 🚢 Deployment Topology

Two deployment paths coexist: local development via Docker Compose and production releases using the standalone web image fronted by Nginx while the API continues to run under Compose profiles or managed infrastructure.

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

## 🏁 Quick Start

> **⚡ Want to get started in 5 minutes?** Check out [QUICK_START.md](docs/guides/QUICK_START.md) for a streamlined guide!

### TL;DR - Fast Track

```bash
# Clone repository
git clone https://github.com/saptiva-ai/copilotos-bridge
cd copilotos-bridge

# One-command setup (creates .env, installs deps, sets up .venv)
make setup

# Start development services
make dev

# Create demo user (username: demo, password: Demo1234)
make create-demo-user

# Open browser
open http://localhost:3000
```

**Login with:** `demo` / `Demo1234`

---

### 📚 Detailed Setup

<details>
<summary><b>Step 1: Clone Repository</b></summary>

```bash
git clone https://github.com/saptiva-ai/copilotos-bridge
cd copilotos-bridge
```
</details>

<details>
<summary><b>Step 2: Initial Setup (First Time Only)</b></summary>

```bash
# Automated setup: creates env files, .venv, installs dependencies
make setup
```

This creates:
- `envs/.env` (environment configuration)
- `.venv/` (Python virtual environment)
- Installs all necessary dependencies

**Optional:** Edit `envs/.env` to add your SAPTIVA API key:
```bash
nano envs/.env  # or use your preferred editor
```
</details>

<details>
<summary><b>Step 3: Start Development Environment</b></summary>

```bash
# Start all services (web, api, mongodb, redis)
make dev
```

This will:
- ✅ Start Next.js frontend (http://localhost:3000)
- ✅ Start FastAPI backend (http://localhost:8001)
- ✅ Start MongoDB database
- ✅ Start Redis cache
- ✅ Enable hot reload for development

**Wait 30-60 seconds** for services to become healthy on first run.
</details>

<details>
<summary><b>Step 4: Create Demo User</b></summary>

```bash
# Create demo user account
make create-demo-user
```

**Credentials created:**
- Username: `demo`
- Password: `Demo1234`
- Email: `demo@example.com`
</details>

<details>
<summary><b>Step 5: Access Application</b></summary>

**Application URLs:**
- 🌐 **Frontend**: http://localhost:3000
- ⚡ **API**: http://localhost:8001
- 📚 **API Docs**: http://localhost:8001/docs
- 🩺 **Health Check**: http://localhost:8001/api/health

**Login with:**
- Username: `demo`
- Password: `Demo1234`
</details>

---

### 🎯 Common Development Commands

```bash
# View all available commands
make help

# Development
make dev          # Start services
make stop         # Stop services
make restart      # Restart services
make logs         # View logs (all services)
make logs-api     # View API logs only
make health       # Check service health

# Users & Authentication
make create-demo-user  # Create demo user
make delete-demo-user  # Delete demo user
make list-users        # List all users
make test-login        # Test login credentials
make clear-cache       # Clear Redis cache
make get-token    # Get JWT token for API testing

# Container Access
make shell-api    # Shell into API container
make shell-web    # Shell into web container
make shell-db     # MongoDB shell
make shell-redis  # Redis CLI

# Testing
make test         # Run all tests
make test-api     # Run API tests
make test-e2e     # Run E2E tests
make verify       # Full verification

# Code Quality
make lint         # Run linters
make lint-fix     # Auto-fix issues

# Cleanup
make clean        # Stop and remove containers
```

---

### 🔐 Default Credentials

**Demo User:**
```
Username: demo
Password: Demo1234
Email:    demo@example.com
```

**Database (Development):**
```
MongoDB:  mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos
Redis:    redis://:redis_password_change_me@localhost:6379
```

**⚠️ Important:** Change these credentials for production! See `envs/.env.local.example` for configuration.

---

### 🆘 Quick Troubleshooting

**Services won't start?**
```bash
make logs        # Check error messages
make clean       # Clean up
make dev-build   # Rebuild and start
```

**Can't login?**
```bash
make health            # Check services are healthy
make clear-cache       # Clear Redis cache (important!)
make delete-demo-user  # Delete demo user
make create-demo-user  # Recreate demo user
make test-login        # Test login
```

**Port conflicts?**
```bash
# Edit envs/.env to change ports
WEB_PORT=3001
API_PORT=8002
```

**Need to reset everything?**
```bash
make clean-all   # ⚠️ Deletes all data
make setup
make dev
make create-demo-user
```

---

### 📖 Documentation Index

#### 🚀 Getting Started
- **[Quick Start Guide](docs/guides/QUICK_START.md)** - Get up and running in 5 minutes
- **[Credentials Reference](docs/guides/CREDENTIALS.md)** - Default credentials and API keys
- **[System Requirements](Makefile)** - Check requirements with `make help`
- **[Installation Guide](docs/guides/QUICK_START.md#step-by-step-guide)** - Detailed setup instructions

#### 💻 Development
- **[Makefile Commands](Makefile)** - Run `make help` for all available commands
- **[Development Workflow](docs/development/)** - Daily development guides
- **[API Documentation](http://localhost:8001/docs)** - Interactive API docs (Swagger UI)
- **[Manual Testing Guide](docs/testing/)** - Browser testing checklist

#### 🚀 Deployment & Production
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment walkthrough
- **[Docker Guide](docs/DOCKER_PERMISSIONS_FIX.md)** - Docker setup and permissions
- **[System Verification](docs/SYSTEM_VERIFICATION_REPORT.md)** - System health report

#### 🔒 Security
- **[Security Guide](docs/SECURITY.md)** - Security architecture and best practices
- **[Authentication](docs/security/)** - Auth implementation details
- **[Secrets Management](docs/SECURITY.md#multi-layer-security-implementation)** - Handling sensitive data

#### 📚 Additional Resources
- **[Architecture Documentation](docs/architecture/)** - System architecture details
- **[Historical Changes](docs/archive/)** - Archived improvements and fixes
- **[UX Documentation](docs/UX-Auth-And-Tools.md)** - User experience features

## 🔒 Security Architecture

### 🛡️ Multi-Layer Security Implementation

**1. Secrets Management**
- **Docker Secrets**: Production-grade secret distribution
- **Environment Variables**: Development and local testing
- **Secure Files**: File-based secrets with proper permissions
- **Validation**: Automatic secret strength validation and rotation

**2. Container Security**
- **Non-Root Containers**: All services run as non-privileged users
- **User Namespace Mapping**: Host UID/GID mapping prevents permission issues
- **Named Volumes**: Isolated storage prevents host filesystem contamination
- **Security Scanning**: Automated vulnerability scanning in CI/CD

**3. Authentication & Authorization**
- **JWT Tokens**: Cryptographically signed with configurable expiration
- **Session Management**: Redis-backed session storage with automatic cleanup
- **Rate Limiting**: Configurable per-user and global rate limiting
- **CORS Protection**: Strict origin validation

**4. Network Security**
- **TLS Termination**: Nginx with Let's Encrypt certificates
- **Internal Networks**: Docker network isolation
- **Security Headers**: Comprehensive security headers (HSTS, CSP, etc.)
- **API Gateway**: Centralized request routing and validation

### 🔧 Security Configuration Files

- `apps/api/src/core/secrets.py` - Multi-source secrets manager
- `production-secrets.txt` - Generated secure credentials (gitignored)
- `scripts/security-audit.sh` - Security validation script
- `scripts/fix-docker-permissions.sh` - Container hardening

> **⚠️ Important**: Never commit secrets to version control. Use the provided scripts for secure credential management.

## 📡 API Endpoints

### 🔐 Authentication
- `POST /api/auth/login` - User authentication with JWT tokens
- `POST /api/auth/register` - User registration with validation
- `POST /api/auth/refresh` - Token refresh mechanism
- `DELETE /api/auth/logout` - Secure session termination

### 💬 Chat & Research
- `POST /api/chat` - Send message to LLM with streaming support
- `POST /api/deep-research` - Start research task, returns task_id
- `GET /api/stream/{task_id}` - Server-Sent Events for task progress
- `GET /api/report/{task_id}` - Download research report and artifacts
- `GET /api/history/{chat_id}` - Retrieve conversation history

### 🔧 System
- `GET /api/health` - System health check with dependency status
- `GET /api/status` - Detailed system status and metrics
- `POST /api/intent` - Intent analysis and routing

## 🛠️ Development Commands

```bash
# View all available commands
make help

# 🚀 Development
make dev                     # Start development environment
make dev-detached           # Start in background
make logs                    # View service logs
make status                  # Check service status
make stop                    # Stop all services
make restart                 # Restart all services
make clean                   # Clean Docker resources

# 🧪 Testing & Quality
make test                    # Run all tests
make test-unit              # Run unit tests
make test-integration       # Run integration tests
make test-e2e               # Run end-to-end tests
make lint                    # Run code linters
make security               # Run security scans
make audit                   # Full security audit

# 🔐 Security & Setup
make generate-secrets       # Generate production secrets
make fix-permissions        # Fix Docker permissions
make security-scan          # Container vulnerability scan
make validate-config        # Validate configuration

# 👤 User Management
make create-demo-user       # Create demo user for testing
make list-users             # List all database users
make delete-demo-user       # Remove demo user
make reset-user-password    # Reset user password

# 🐳 Container Management
make shell-api              # Access API container shell
make shell-web              # Access web container shell
make shell-db               # Access MongoDB shell
make shell-redis            # Access Redis CLI

# 📦 Build & Deploy
make build                  # Build all images
make build-web-standalone   # Build standalone web image
make package-web            # Package web for deployment
make push                   # Push images to registry
```

### 🔧 Docker Permission Management

```bash
# Fix permission issues (run once per machine)
./scripts/fix-docker-permissions.sh

# For future builds with correct permissions
./scripts/docker-build.sh web

# Test permission fix
./scripts/test-docker-permissions.sh
```

## 📁 Project Structure

```
copilotos-bridge/
├── 🌐 apps/
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
│       │   └── secrets.py  # 🔒 Secrets management system
│       └── Dockerfile      # Production API container
├── 🏗️ infra/
│   ├── docker-compose.yml  # Complete service orchestration
│   └── nginx/              # Production reverse proxy config
├── 🔐 envs/
│   ├── .env.local.example  # Development environment template
│   ├── .env.prod.example   # Production environment template
│   └── .env.local          # Local environment (gitignored)
├── 📜 scripts/
│   ├── fix-docker-permissions.sh    # 🐳 Docker user mapping fix
│   ├── generate-production-secrets.sh # 🔑 Secure credential generation
│   ├── security-audit.sh            # 🛡️ Security validation
│   ├── test-docker-permissions.sh   # 🧪 Permission testing
│   └── create-demo-user.py          # 👤 Demo user creation
├── 📚 docs/
│   ├── DOCKER_PERMISSIONS_FIX.md    # Docker permission solution
│   ├── SECURITY.md                  # Security architecture guide
│   └── DEPLOYMENT.md               # Production deployment guide
├── production-secrets.txt           # 🔒 Generated secrets (gitignored)
├── Makefile                        # Development automation
└── README.md                       # This file
```

### 🔑 Key Configuration Files

- **`apps/api/src/core/secrets.py`** - Enterprise secrets management
- **`apps/web/Dockerfile`** - Multi-stage build with non-root user
- **`infra/docker-compose.yml`** - Production-ready service definitions
- **`production-secrets.txt`** - Auto-generated secure credentials
- **`scripts/fix-docker-permissions.sh`** - Solves Docker permission issues

## 💾 Data Storage & Security

### 🗄️ Primary Databases
- **MongoDB 7.0+**: User accounts, chat sessions, messages, task tracking
  - Replica set configuration for high availability
  - Automatic authentication with secure credentials
  - Indexed collections for optimal performance

- **Redis 7.0+**: Session management, caching, and real-time data
  - AOF persistence enabled
  - Password-protected access
  - Memory optimization with LRU eviction

### 🗂️ External Storage
- **MinIO/S3**: Research artifacts and reports (via Aletheia)
- **Named Docker Volumes**: Persistent data with proper permissions
- **Backup Strategy**: Automated backup scripts included

### 🔐 Data Security
- **Encryption at Rest**: Database encryption enabled
- **Secure Connections**: TLS/SSL for all database connections
- **Access Control**: Role-based database access
- **Audit Logging**: Complete audit trail for security events

## 🛠️ Technology Stack

### 🎨 Frontend (Next.js 14)
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript with strict configuration
- **Styling**: Tailwind CSS with custom design system
- **State Management**: Zustand for global state
- **UI Components**: Custom React components with accessibility
- **Build**: Standalone output for containerization

### ⚡ Backend (FastAPI)
- **Framework**: FastAPI with async/await
- **Language**: Python 3.10+ with type hints
- **Database ODM**: Beanie (async MongoDB ODM)
- **Validation**: Pydantic v2 with advanced validation
- **Authentication**: JWT with Redis session storage
- **API Documentation**: Auto-generated OpenAPI/Swagger

### 🗄️ Databases
- **Primary**: MongoDB 7.0 (document store)
- **Cache**: Redis 7.0 (in-memory cache)
- **Search**: Integrated vector search capabilities

### 🤖 AI & Research
- **Language Models**: SAPTIVA API (production)
- **Research Engine**: Aletheia orchestrator
- **Vector Search**: Weaviate integration
- **Web Search**: Tavily search API

### 🏗️ Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose with profiles
- **Reverse Proxy**: Nginx with SSL termination
- **Monitoring**: Health checks and logging

### 🧪 Testing & Quality
- **E2E Testing**: Playwright with TypeScript
- **Unit Testing**: pytest with async support
- **API Testing**: FastAPI TestClient
- **Linting**: ESLint, Prettier, Black, isort
- **Type Checking**: TypeScript, mypy
- **Security**: Bandit, Safety, Docker scanning

## 🔧 Troubleshooting

### 🐳 Docker & Permission Issues

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

### 🔐 Security & Authentication Issues

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

### 🗄️ Database Connection Issues

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

### 🌐 Network & API Issues

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

### 🛡️ Security Debugging

#### Run Complete Security Audit
```bash
./scripts/security-audit.sh
```

#### Check for Hardcoded Secrets
```bash
grep -r "password" --include="*.py" --include="*.js" --include="*.ts" apps/
grep -r "secret" --include="*.py" --include="*.js" --include="*.ts" apps/
```

#### Validate Configuration
```bash
# Check for missing required variables
./scripts/validate-config.sh

# Test secrets loading
python -c "from apps.api.src.core.secrets import SecretsManager; sm = SecretsManager(); print('OK')"
```

### 🆘 Emergency Recovery

#### Complete System Reset
```bash
# Stop everything
make stop
docker system prune -a -f

# Remove all volumes (⚠️ DATA LOSS)
docker volume prune -f

# Regenerate secrets
./scripts/generate-production-secrets.sh

# Fix permissions
./scripts/fix-docker-permissions.sh

# Restart
make dev
```

#### Get Help
```bash
# View available commands
make help

# Check system requirements
docker --version
docker-compose --version
node --version
python3 --version
```

### ⚠️ Production Requirements

**🔴 CRITICAL**: This system requires valid SAPTIVA API credentials. No demo mode available.

#### 🔑 Required Configuration
- **SAPTIVA_API_KEY**: Valid API key from SAPTIVA platform
- **JWT_SECRET_KEY**: Cryptographically secure secret (32+ characters)
- **Database Credentials**: Strong passwords for MongoDB and Redis
- **Domain Configuration**: Valid domain for production deployment

#### 🔒 Security Validation
```bash
# Validate all security requirements
./scripts/security-audit.sh

# Check configuration completeness
./scripts/validate-config.sh
```

#### 📊 API Key Configuration Priority
1. **🔒 Docker Secrets** - Highest priority (production)
2. **📁 Secure Files** - File-based secrets with 600 permissions
3. **🌍 Environment Variables** - Development and testing
4. **❌ No Fallback** - System fails fast without valid configuration

#### 🚀 Production Deployment
See detailed production deployment guide below.

## 🎨 User Experience Features

This application implements a comprehensive ChatGPT-style user experience:

### UX-001: Hierarchical Model Selector
- **Smart Organization**: Models grouped by Provider → Family → Variant
- **Quick Access**: Presets for Rapid, Accurate, and Creative workflows
- **Search**: Global model search with `Cmd/Ctrl+K`
- **Compact Design**: Pill format showing "Provider/Model (context) ▾"

### UX-002: Advanced Conversation Management
- **Sidebar Toggle**: `Cmd/Ctrl+B` to collapse/expand
- **Hover Actions**: Rename, pin, and delete conversations on hover
- **Inline Editing**: Click to rename conversations directly
- **Smart Organization**: Pinned conversations stay at top

### UX-003: Integrated Composer Actions
- **One-Click Tools**: Access 6 integrated actions via '+' button
- **Keyboard Shortcut**: `Alt+N` to open actions menu
- **Smart Menu**: Contextual actions (files, research, analysis, connectors)
- **Quick Access**: Upload files, trigger deep research, analyze documents

### UX-004: File Attachment System
- **Drag & Drop**: Natural file attachment workflow
- **Format Support**: PDF, images, documents, code files, notebooks
- **Progress Tracking**: Real-time upload progress with validation
- **Smart Limits**: 20MB per file, 5 files max, with clear error messaging

### UX-005: Message Enhancement
- **Streaming Cursor**: Animated cursor during AI response generation
- **Action Buttons**: Copy, regenerate, and stop streaming on hover
- **Rich Metadata**: Token count, latency, and model information
- **Research Integration**: Direct access to research reports and sources

### UX-006: Full Accessibility
- **Keyboard Navigation**: Complete keyboard-only operation support
- **Screen Reader**: Comprehensive ARIA labels and semantic markup
- **Focus Management**: Proper focus handling and visual indicators
- **Shortcuts**: All major functions accessible via keyboard shortcuts

## 🚀 Production Deployment

### 🔐 Security-First Production Setup

**Prerequisites:**
- 🐧 Linux server (Ubuntu 20.04+ recommended)
- 🐳 Docker Engine 20.10+ and Docker Compose V2
- 🌐 Domain name with DNS configured
- 🔒 SSL certificate capability (Let's Encrypt)
- 💾 Minimum 4GB RAM, 20GB storage

### 1. 🏗️ Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose V2
sudo apt install docker-compose-plugin

# Logout and login to apply docker group
exit
```

### 2. 📥 Repository Setup

```bash
# Clone repository
git clone <repository-url> /opt/copilotos-bridge
cd /opt/copilotos-bridge

# Set proper permissions
sudo chown -R $USER:$USER /opt/copilotos-bridge
chmod +x scripts/*.sh
```

### 3. 🔐 Security Configuration

```bash
# Generate production secrets
./scripts/generate-production-secrets.sh

# Review generated secrets
cat production-secrets.txt

# Configure production environment
cp envs/.env.prod.example envs/.env.prod
nano envs/.env.prod  # Edit with your values
```

**🔑 Required Production Variables:**
```bash
# Domain Configuration
DOMAIN=your-domain.com
NEXT_PUBLIC_API_URL=https://your-domain.com/api

# Security (Use generated values from production-secrets.txt)
JWT_SECRET_KEY=<generated-secure-key>
SECRET_KEY=<generated-secure-key>
MONGODB_PASSWORD=<generated-password>
REDIS_PASSWORD=<generated-password>

# SAPTIVA Integration
SAPTIVA_API_KEY=<your-saptiva-api-key>
SAPTIVA_BASE_URL=https://api.saptiva.com
```

### 4. 🐳 Docker Production Build

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

### 5. 🌐 Nginx & SSL Setup

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

### 6. 🚀 Start Production Services

```bash
# Start web service
cd /opt/copilotos-bridge/infra
docker-compose --profile production up -d web

# Start nginx reverse proxy
docker-compose --profile production up -d nginx

# Verify all services are running
docker-compose ps
```

### 7. ✅ Production Health Verification

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

### 8. 🔄 Zero-Downtime Updates

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

### 9. 📊 Monitoring & Maintenance

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

### 10. 🚨 Production Troubleshooting

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

### 11. 🔐 Docker Security Best Practices

This deployment implements comprehensive Docker security:

**🛡️ Container Hardening:**
- ✅ Non-root user execution (`USER app` in Dockerfiles)
- ✅ User namespace mapping (`UID/GID` configuration)
- ✅ Minimal base images (Alpine Linux)
- ✅ Multi-stage builds (smaller attack surface)
- ✅ Named volumes (isolated storage)
- ✅ Security scanning integrated

**🔒 Network Security:**
- ✅ Internal Docker networks (isolated communication)
- ✅ TLS termination at reverse proxy
- ✅ Rate limiting and DDoS protection
- ✅ Security headers (HSTS, CSP, etc.)

**🔑 Secrets Management:**
- ✅ Docker secrets for production
- ✅ Environment-based configuration
- ✅ Automatic secret rotation capability
- ✅ No secrets in images or logs

### 12. 📈 Performance Optimization

**⚡ Production Performance Tips:**

```bash
# Enable Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1

# Use Docker layer caching
docker-compose build --parallel

# Monitor performance
docker stats --no-stream
curl -s https://your-domain.com/api/health | jq '.performance'

# Optimize database
docker exec copilotos-mongodb mongosh --eval "db.runCommand({collStats: 'chatSessions'})"

# Cache warming (optional)
curl -s https://your-domain.com > /dev/null
```

**🎯 Scaling Considerations:**
- Horizontal scaling with Docker Swarm or Kubernetes
- Database replication for read scaling
- CDN integration for static assets
- Load balancer configuration
- Auto-scaling based on metrics

### 13. 🔄 Backup & Disaster Recovery

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

## 🤝 Contributing

We welcome contributions! Please follow these steps:

### 🚀 Development Setup
```bash
# 1. Fork and clone
git clone https://github.com/your-username/copilotos-bridge.git
cd copilotos-bridge

# 2. Setup development environment
./scripts/fix-docker-permissions.sh
cp envs/.env.local.example envs/.env.local
# Edit envs/.env.local with your development keys

# 3. Start development environment
make dev
```

### 🔄 Development Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes, then test
make test                # Run all tests
make lint               # Check code style
make security           # Security scan

# Commit with conventional format
git commit -m "feat: add new feature description"

# Push and create pull request
git push origin feature/your-feature-name
```

### 📋 Contribution Guidelines
- **🔒 Security First**: Never commit secrets or credentials
- **✅ Test Coverage**: Add tests for new features
- **📝 Documentation**: Update relevant documentation
- **🎨 Code Style**: Follow existing patterns and conventions
- **🔍 Security Review**: All PRs undergo security review

### 🏗️ Project Areas
- **Frontend**: React/Next.js components and UX improvements
- **Backend**: FastAPI endpoints and business logic
- **Infrastructure**: Docker, deployment, and DevOps improvements
- **Security**: Authentication, authorization, and security hardening
- **Documentation**: Technical writing and user guides

### 🐛 Bug Reports
1. Search existing issues first
2. Use the bug report template
3. Include reproduction steps
4. Provide system information and logs

### 💡 Feature Requests
1. Check the roadmap and existing issues
2. Use the feature request template
3. Describe the use case and business value
4. Consider implementation complexity

## 📊 Project Status

- **🟢 Active Development**: Regular updates and maintenance
- **🔒 Security-Focused**: Enterprise-grade security implementation
- **🐳 Production-Ready**: Docker-optimized with proper user permissions
- **📈 Performance-Optimized**: Caching, compression, and optimization
- **♿ Accessibility-First**: Full keyboard navigation and screen reader support

## 🗓️ Roadmap

- [ ] **Multi-model Support**: Additional LLM provider integrations
- [ ] **Advanced Analytics**: Usage metrics and performance dashboards
- [ ] **Team Collaboration**: Shared workspaces and conversation management
- [ ] **API Extensions**: Public API for third-party integrations
- [ ] **Mobile Optimization**: Progressive Web App enhancements

## 📞 Support

- **📖 Documentation**: Check the troubleshooting section above
- **🐛 Issues**: [GitHub Issues](https://github.com/your-org/copilotos-bridge/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/your-org/copilotos-bridge/discussions)
- **🔒 Security**: Report security issues privately to [security@your-domain.com]

## 🏆 Acknowledgments

- **SAPTIVA**: AI/LLM platform integration
- **Aletheia**: Research orchestration capabilities
- **Next.js**: Modern web framework
- **FastAPI**: High-performance API framework
- **Docker**: Containerization and deployment

## 📄 License

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

---

<div align="center">

**🚀 Built with security, performance, and accessibility in mind**

[⭐ Star this project](https://github.com/your-org/copilotos-bridge) • [🐛 Report Issues](https://github.com/your-org/copilotos-bridge/issues) • [💡 Request Features](https://github.com/your-org/copilotos-bridge/discussions)

</div>
