# Saptiva Copiloto

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
│   ├── generate-production-secrets.sh # 🔑 Secure credential generation
│   ├── security-audit.sh            # 🛡️ Security validation
│   ├── test-docker-permissions.sh   # 🧪 Permission testing
│   └── create-demo-user.py          # 👤 Demo user creation
├── 📚 docs/
│   └── DEPLOYMENT.md               # Production deployment guide
├── Makefile                        # Development automation
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

## Documentation

- Arquitectura de LLM y herramientas: `docs/arquitectura/`
- Evidencias reproducibles: `docs/evidencias/llm-tools.md`
- Guías de despliegue: `docs/DEPLOYMENT.md`, `docs/QUICK-DEPLOY.md`
- Guía rápida de inicio: `docs/guides/QUICK_START.md`

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
- ✅ No Docker Registry setup required
- ✅ Full automation (12 min total)
- ✅ Proper image tagging handled automatically
- ✅ Built-in verification steps

**See:** [`docs/archive/DEPLOYMENT-TAR-GUIDE.md`](docs/archive/DEPLOYMENT-TAR-GUIDE.md) for details

#### Option B: Docker Registry Deployment (Faster)

```bash
# Setup GitHub Packages (one-time)
export GITHUB_TOKEN=ghp_your_token

# Deploy (3 min total)
make deploy-prod
```

**Advantages:**
- ✅ Fastest deployment (~3 min)
- ✅ Build once, deploy many times
- ✅ Version management built-in

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
