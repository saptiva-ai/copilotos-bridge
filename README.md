# CopilotOS Bridge — Chat UI + Aletheia Deep Research

> UI estilo ChatGPT para interactuar con modelos de **Saptiva** y ejecutar **Deep Research** vía el orquestador **Aletheia**.  
> Filosofía operativa: *veracidad + trazabilidad + control de lo controlable* (estoicismo aplicado al stack).

---

## Objetivo

Unificar una **UI conversacional** (chat) con:
- **LLM directo** (mensajes rápidos) y
- **Deep Research** (pipeline iterativo con evidencia, citaciones y telemetría).

La UI debe permitir:
- Elegir modelo de Saptiva
- Lanzar **websearch** o **deep-research**
- Ver **streaming** de respuestas en tiempo real
- Mantener **histórico** de conversaciones y resultados (por `chat_id` / `task_id`)
- Descargar reporte final (MD/HTML/PDF) con metadatos
- Control granular de parámetros de investigación (budget, iteraciones, scope)

## Requisitos del Sistema

- **Node.js** >= 18.0.0
- **Python** >= 3.10
- **MongoDB** >= 6.0 (or MongoDB Atlas)
- **Redis** >= 6.2
- **Docker** y Docker Compose (para desarrollo local)
- **pnpm** >= 8.0 (recomendado) o npm/yarn

---

## Arquitectura (alto nivel)

```mermaid
flowchart LR
  %% --- STYLE FIRST (para motores viejos) ---
  classDef ui fill:#f6f5ff,stroke:#6e56cf,stroke-width:1px,color:#1b1a1f;

  %% --- SUBGRAPHS SIMPLIFICADOS ---
  subgraph UI ["CopilotOS UI"]
    C[Chat UI]:::ui
    M[Model Picker]:::ui
    T[Tools]
  end

  subgraph API ["Gateway Proxy FastAPI"]
    S[Session and History Service]
    E[SSE and WebSocket Streamer]
    A[Auth JWT]
    DB[MongoDB ODM Beanie]
  end

  subgraph ORCH ["DeepResearch API (Aletheia)"]
    R1[POST research]
    R2[POST deep research]
    TR[(OTel Spans and NDJSON Events)]
  end

  subgraph SVCS ["Servicios"]
    SA[Saptiva Models]
    TA[Tavily]
    WV[Weaviate Vector DB]
    MI[MinIO or S3 Artifacts]
    JG[Jaeger Tracing]
    GD[Guard Policies]
  end

  subgraph DATA ["Datos"]
    MG[(MongoDB)]
    RD[(Redis)]
  end

  %% --- FLUJOS SIN LABELS ---
  C --> S
  S --> ORCH

  DB --> MG
  S  --> RD

  ORCH --> SA
  ORCH --> TA
  ORCH --> WV
  ORCH --> MI
  ORCH --> JG
  ORCH --> GD

  E --> C
  E --> TR
```

---

## Contratos y Mapping

### Endpoints (este repo)
- `POST /api/chat` → Mensaje directo al LLM (usa Saptiva).  
- `POST /api/deep-research` → Inicia investigación; devuelve `task_id`.  
- `GET  /api/stream/{task_id}` → **SSE**: puentea eventos parciales desde Aletheia.  
- `GET  /api/report/{task_id}` → Descarga el reporte final/artefactos.  
- `GET  /api/history/{chat_id}` → Histórico de la conversación y sus `task_id`.

### Handoff a Aletheia
- Proxy a `POST /research` y `POST /deep-research` con los parámetros del UI.  
- Lectura de `runs/<task_id>/events.ndjson` para emitir *stream* SSE.  
- Descarga de `report.md`, `sources.bib` y métricas para el usuario.

---

## Datos y Persistencia

- **MongoDB**: `users`, `chat_sessions`, `messages`, `tasks` (mapea `chat_id` ↔ `task_id`), `research_sources`, `evidence`.  
- **Redis**: sesiones y caché de respuestas parciales.  
- **MinIO/S3** (Aletheia): almacenamiento de artefactos (reportes/evidencia).

---

## Configuración

### Variables de entorno requeridas (`.env`)

```bash
# ========================================
# AUTENTICACIÓN
# ========================================
AUTH_JWT_SECRET=change-me-to-secure-random-string
AUTH_JWT_EXPIRY_HOURS=24

# ========================================
# ALETHEIA ORCHESTRATOR
# ========================================
ALETHEIA_BASE_URL=http://localhost:8000
ALETHEIA_API_KEY=optional-if-required
ALETHEIA_TIMEOUT_SECONDS=120
ALETHEIA_MAX_RETRIES=3

# ========================================
# STREAMING Y PERFORMANCE
# ========================================
STREAM_BACKPRESSURE_MAX=1000
STREAM_HEARTBEAT_INTERVAL_MS=5000
SSE_KEEP_ALIVE_TIMEOUT_MS=30000

# ========================================
# BASE DE DATOS
# ========================================
POSTGRES_URL=postgresql://user:pass@localhost:5432/copilotos
REDIS_URL=redis://localhost:6379/0
DB_POOL_SIZE=10
DB_CONNECTION_TIMEOUT_MS=5000

# ========================================
# LÍMITES Y SEGURIDAD
# ========================================
RATE_LIMIT_REQUESTS_PER_MINUTE=100
MAX_PROMPT_LENGTH=10000
MAX_UPLOAD_SIZE_MB=10
CORS_ORIGINS=http://localhost:3000,https://app.domain.com

# ========================================
# OBSERVABILIDAD
# ========================================
LOG_LEVEL=info
OTEL_SERVICE_NAME=copilotos-bridge
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

Variables de Aletheia (colócalas en su propio .env):

```bash
SAPTIVA_API_KEY=...
SAPTIVA_MODEL_PLANNER=SAPTIVA_OPS
SAPTIVA_MODEL_WRITER=SAPTIVA_CORTEX
TAVILY_API_KEY=...
VECTOR_BACKEND=weaviate
WEAVIATE_HOST=http://localhost:8080
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
ARTIFACTS_DIR=./runs
```

---

## Quickstart (local)

### Pre-requisitos
1) **Levantar Aletheia** (API + Weaviate + MinIO + Jaeger) siguiendo su repo
2) **Configurar bases de datos con Docker Compose** (recomendado):
```bash
# Iniciar MongoDB + Redis con configuración predefinida
docker compose -f infra/docker/docker-compose.yml up -d

# Verificar que los servicios están corriendo
docker compose -f infra/docker/docker-compose.yml ps

# Ver logs si hay problemas
docker compose -f infra/docker/docker-compose.yml logs mongodb redis
```

**Alternativa manual:**
```bash
# MongoDB standalone
docker run -d --name mongodb -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=copilotos_user \
  -e MONGO_INITDB_ROOT_PASSWORD=secure_password_change_me \
  mongo:6.0

# Redis standalone  
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Instalación y Configuración
```bash
# 1) Clonar e instalar dependencias
git clone <repo-url>
cd copilotos-bridge
pnpm install  # o npm install / yarn install

# 2) Configurar variables de entorno
cp .env.example .env
cp apps/web/.env.local.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env
# Editar archivos .env con tus credenciales

# 3) Construir shared package
pnpm --filter shared build

# 4) Verificar conexión a MongoDB (opcional)
python scripts/test-mongodb.py

# 5) Arrancar servicios en desarrollo
pnpm dev  # Next.js en http://localhost:3000 + API en http://localhost:8000
```

### Verificación del Setup
- ✅ UI accesible en `http://localhost:3000`
- ✅ API respondiendo en `/api/health` (cuando se implemente)
- ✅ MongoDB conectada y collections creadas
- ✅ Redis funcionando para cache/sesiones
- ✅ Conexión a Aletheia OK (cuando se configure)

### Uso Básico
1. **Chat directo**: Envía mensaje y selecciona modelo
2. **Deep Research**: Activa "Investigar a fondo" y observa el streaming
3. **Historial**: Navega conversaciones anteriores
4. **Reportes**: Descarga resultados en formato deseado

---

## Tests & Quality

- **E2E** con Playwright (flujo chat + deep research).  
- **Contract tests** del proxy contra Aletheia.  
- **Tracing Assertions**: verifica presencia de spans clave.  
- **Feature flags**: activar/desactivar herramientas por entorno.

---

##  Roadmap corto (v1 → v1.1)

- v1: Chat + Deep Research (SSE), histórico básico, descarga de reporte.  
- v1.1: edición de prompts, renombrar/congelar conversaciones, compartir enlace de reporte, *retry* inteligente de pasos fallidos.

---

##  Estado Actual del Proyecto

### ✅ **Completado (25%)**
- **📁 Estructura del monorepo**: Apps (web/api), packages (shared), infra, docs, tests
- **⚙️ Configuración base**: Variables de entorno, TypeScript, Tailwind, FastAPI
- **🗄️ Base de datos**: Modelos MongoDB con Beanie ODM, índices optimizados
- **📝 Tipos compartidos**: Interfaces TypeScript + esquemas Zod + Pydantic
- **🐳 Docker Compose**: MongoDB + Redis con healthchecks

### 🚧 **En Progreso**
- **Docker stack completo**: Faltan Dockerfiles para apps web/api

### **Próximamente (prioridad crítica)**
1. **Endpoints FastAPI**: `/api/chat`, `/api/deep-research`, `/api/health`
2. **Componentes UI base**: Sistema de diseño, chat interface
3. **Autenticación JWT**: Login, middleware, sesiones
4. **Seguridad**: Rate limiting, validación, CORS

### **Stack Tecnológico Final**
```
Frontend:  Next.js 14 + TypeScript + Tailwind CSS + Zustand
Backend:   FastAPI + Pydantic 2.0 + Beanie ODM
Database:  MongoDB 6.0 + Redis 7
Deploy:    Docker Compose + (futuro: Kubernetes)
Monitoring: OpenTelemetry + Jaeger + Prometheus
```

---

##  Principios de diseño

- **Veracidad y trazabilidad primero**: toda afirmación importante debe poder vincularse a evidencia.  
- **Separación de preocupaciones**: UI ↔ Proxy ↔ Orquestador; puertos/adapters intercambiables.  
- **Observabilidad obligatoria**: spans + eventos estructurados; fallas visibles y depurables.  
- **Estoicismo aplicado**: centrarse en lo controlable (inputs, límites, telemetría) y no en el azar externo (latencia/red).

---

## Estructura del Proyecto

```
copilotos-bridge/
├─ apps/
│  ├─ web/                   # Next.js 14+ (UI React/TypeScript)
│  │  ├─ src/
│  │  │  ├─ components/      # Componentes UI reutilizables
│  │  │  ├─ pages/api/       # API Routes de Next.js (proxy)
│  │  │  ├─ hooks/           # Custom React hooks
│  │  │  ├─ stores/          # Estado global (Zustand/Redux)
│  │  │  └─ types/           # Tipos TypeScript específicos del UI
│  │  ├─ public/
│  │  └─ package.json
│  └─ api/                   # FastAPI (alternativa al proxy de Next.js)
│     ├─ src/
│     │  ├─ routers/         # Endpoints organizados por dominio
│     │  ├─ services/        # Lógica de negocio
│     │  ├─ models/          # Modelos SQLAlchemy
│     │  └─ middleware/      # Auth, CORS, rate limiting
│     └─ requirements.txt
├─ packages/
│  └─ shared/                # Contratos y tipos compartidos
│     ├─ src/
│     │  ├─ types/           # Interfaces TypeScript
│     │  ├─ schemas/         # Esquemas de validación (Zod/Pydantic)
│     │  └─ constants/       # Constantes compartidas
│     └─ package.json
├─ infra/
│  ├─ docker/                # Configuración Docker
│  │  ├─ docker-compose.yml
│  │  ├─ docker-compose.dev.yml
│  │  └─ Dockerfiles/
│  └─ k8s/                   # Manifiestos Kubernetes (opcional)
├─ docs/
│  ├─ architecture/          # ADRs y diagramas de arquitectura
│  ├─ api/                   # Documentación de endpoints
│  └─ deployment/            # Guías de despliegue
├─ tests/
│  ├─ e2e/                   # Tests end-to-end (Playwright)
│  ├─ integration/           # Tests de integración
│  └─ contract/              # Contract tests con Aletheia
├─ scripts/                  # Scripts de automatización
├─ .env.example
├─ .env.local.example
├─ pnpm-workspace.yaml
└─ package.json
```

---

## Seguridad

- Sanitizar entradas y limitar tamaño de prompts/archivos.  
- **Guard** en entrada/salida a través de Aletheia.  
- Rate limiting por IP/usuario y *circuit breakers* en el proxy.

---

## Troubleshooting

### Problemas Comunes

#### Error de conexión a MongoDB
```bash
# Verificar que MongoDB esté corriendo
docker ps | grep mongodb
docker logs copilotos-mongodb

# Probar conexión manualmente
python scripts/test-mongodb.py

# Conectar con MongoDB shell
docker exec -it copilotos-mongodb mongosh -u copilotos_user -p secure_password_change_me

# Ver base de datos web UI (opcional)
docker compose -f infra/docker/docker-compose.yml --profile tools up -d mongo-express
# http://localhost:8081 (admin/admin123)
```

#### Error de conexión a Aletheia
```bash
# Verificar que Aletheia esté corriendo
curl -f http://localhost:8000/health

# Revisar logs
docker logs aletheia-api
```

#### Streaming interrumpido
- Verificar `STREAM_BACKPRESSURE_MAX` y ajustar según carga
- Revisar conexión de red y timeouts
- Comprobar logs del navegador para errores de EventSource

#### Redis no conecta
```bash
# Verificar Redis
redis-cli ping
# o con Docker:
docker exec copilotos-redis redis-cli ping

# Ver configuración Redis
docker exec copilotos-redis redis-cli CONFIG GET "*"
```

#### Performance lenta
- Revisar `DB_POOL_SIZE` y ajustar para tu carga
- Monitorear métricas en Jaeger
- Verificar índices de base de datos

### Logs y Debugging
```bash
# Logs detallados
export LOG_LEVEL=debug
pnpm dev

# Trazas distribuidas
# Abrir Jaeger UI en http://localhost:16686
```

## 📝 Licencia

MIT (propuesta).
