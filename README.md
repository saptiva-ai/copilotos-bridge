# SAPTIVA Copilot OS — Chat UI + Aletheia Deep Research

> UI conversacional moderna para interactuar con modelos de **Saptiva** y ejecutar **Deep Research** vía el orquestador **Aletheia**.  
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

## 🚀 Deployment Status

### ✅ Producción Activa
- **URL**: http://34.42.214.246
- **Estado**: ✅ Funcionando correctamente
- **API**: ✅ Endpoints operativos
- **Auth**: ✅ Login/Register funcional
- **Nginx**: ✅ Proxy reverse configurado

### 🔧 Credenciales de Prueba
- **Usuario**: `testuser2`
- **Contraseña**: `testpass123`

## Arquitectura (alto nivel)

```mermaid
flowchart LR
  %% --- STYLE FIRST (para motores viejos) ---
  classDef ui fill:#f6f5ff,stroke:#6e56cf,stroke-width:1px,color:#1b1a1f;

  %% --- SUBGRAPHS SIMPLIFICADOS ---
  subgraph UI ["Copilot OS UI"]
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

## 🚀 Comandos Rápidos

```bash
# Ver todos los comandos disponibles
make help

# ⚡ Desarrollo Local
make local                    # Levantar stack completo (con override)
make health                   # Verificar estado de todos los servicios
make logs-follow-all          # Ver logs en tiempo real
make restart                  # Reiniciar servicios rápidamente

# 🔍 Debugging y Monitoreo
make monitor-errors           # Monitor de errores en tiempo real
make logs-search PATTERN='saptiva'  # Buscar en logs
make env-check               # Verificar variables de entorno
make saptiva-test           # Test de integración SAPTIVA

# 🧹 Mantenimiento
make docker-clean           # Limpieza profunda de Docker
make build-rebuild          # Reconstruir stack completo
make logs-export           # Exportar logs a archivos

# 📊 URLs de Desarrollo
# Frontend: http://localhost:3000
# API: http://localhost:8001
# Health: http://localhost:8001/api/health
```

---

## 📁 Archivos Importantes

### Configuración Principal
- `saptiva-chat-fixes-v3.yaml` - Especificación de UI/UX crítica
- `Makefile` - Comandos de desarrollo y producción
- `infra/docker-compose.yml` - Stack principal Docker
- `envs/.env.local` - Variables de entorno desarrollo

### Frontend (Next.js)
- `apps/web/src/app/chat/[chatId]/page.tsx` - Rutas dinámicas de chat
- `apps/web/src/components/chat/ConversationList.tsx` - Sidebar historial
- `apps/web/src/components/chat/ChatInterface.tsx` - Interfaz principal
- `apps/web/src/lib/env-config.ts` - Configuración ENV-only SAPTIVA
- `apps/web/src/styles/tokens.css` - Tokens de diseño SAPTIVA

### Backend (FastAPI)
- `apps/api/src/routers/conversations.py` - API de conversaciones
- `apps/api/src/routers/history.py` - API de historial
- `apps/api/src/routers/chat.py` - API de mensajes
- `apps/api/src/models/chat.py` - Modelos de MongoDB

### DevOps
- `scripts/deploy-local.sh` - Script de desarrollo local
- `scripts/deploy-prod.sh` - Script de producción
- `.github/workflows/` - CI/CD automatizado

---

## Configuración

### Variables de entorno requeridas (`.env`)

```bash
# ========================================
# AUTENTICACIÓN / SEGURIDAD
# ========================================
JWT_SECRET_KEY=change-me-to-secure-random-string
SECRET_KEY=another-secret-string-for-sessions
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

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
MONGODB_URL=mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos
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
ALLOWED_HOSTS=localhost,127.0.0.1,web,api

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

## 🚀 Quickstart - Múltiples Entornos

### 📋 Pre-requisitos
- **Docker** y **Docker Compose** >= 2.0
- **Git** para clonar el repositorio
- **Make** (opcional, para comandos simplificados)

### 🏃‍♂️ Inicio Rápido

**1️⃣ Clonar el repositorio:**
```bash
git clone <repo-url>
cd copilotos-bridge
```

**2️⃣ Configurar entorno local:**
```bash
# Copiar configuración de entorno local
cp envs/.env.local.example envs/.env.local
# Editar envs/.env.local con tu SAPTIVA_API_KEY
```

**3️⃣ Levantar stack completo:**
```bash
# Opción A: Con Make (recomendado)
make local

# Opción B: Con Docker Compose directo
docker compose -f infra/docker-compose.yml up -d
```

**4️⃣ Verificar deployment:**
- 🌐 **Frontend**: http://localhost:3000
- 🔌 **API**: http://localhost:8001/api/health
- 🗄️ **MongoDB**: localhost:27017
- 🔴 **Redis**: localhost:6379

**5️⃣ Login con usuario demo:**
- **Usuario**: `demo_admin`
- **Contraseña**: `ChangeMe123!`

### 🌟 Comandos Rápidos

```bash
# Ver todos los comandos disponibles
make help

# Gestión de entornos
make local     # Desarrollo local
make staging   # Entorno staging (puerto 3001)
make prod      # Producción

# Utilidades
make logs      # Ver logs de todos los servicios
make stop      # Parar todos los servicios
make clean     # Limpiar contenedores y volúmenes
```

### 🔧 Configuración Avanzada

#### Entornos Disponibles

| Entorno | Comando | Frontend | API | Configuración |
|---------|---------|----------|-----|---------------|
| **Local** | `make local` | :3000 | :8001 | `envs/.env.local` |
| **Staging** | `make staging` | :3001 | :8002 | `envs/.env.staging` |
| **Producción** | `make prod` | :3000 | :8001 | `envs/.env.prod` |

#### Estructura de Archivos

```
📁 infra/                          # Infraestructura
├── docker-compose.yml             # Base común
├── docker-compose.override.yml    # Local (auto-carga)
├── docker-compose.staging.yml     # Staging
└── docker-compose.prod.yml        # Producción

📁 envs/                           # Variables de entorno
├── .env.local                     # Desarrollo local
├── .env.staging                   # Staging
├── .env.prod                      # Producción
└── .env.secrets.example           # Template secretos

📁 scripts/                        # Scripts deployment
├── deploy-local.sh
├── deploy-staging.sh
└── deploy-prod.sh
```
cp .env.example .env
cp apps/web/.env.local.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env
# Configurar MongoDB Atlas u otros servicios externos

# 3) Construir shared package
pnpm --filter shared build

# 4) Arrancar servicios en desarrollo
pnpm dev  # Next.js en http://localhost:3000 + API en http://localhost:8001
```

---

## 🚀 **Configuración Para Producción - ACTUALIZADA**

### ✅ **Sistema de URLs Inteligente**

El frontend ahora detecta automáticamente el entorno:

```typescript
// En desarrollo: usa NEXT_PUBLIC_API_URL explícita
// En producción: usa window.location.origin + nginx proxy
```

**No necesitas configurar URLs manualmente en producción.**

### 🔧 **Variables de Entorno Requeridas**

Para usar SAPTIVA real (no modo demo):

```bash
# En envs/.env.prod (producción)
SAPTIVA_API_KEY=tu_saptiva_api_key_real_aqui
NEXT_PUBLIC_API_URL=# Se determina automáticamente

# Opcional - ya configuradas por defecto
SAPTIVA_BASE_URL=https://api.saptiva.com
SAPTIVA_TIMEOUT=30
SAPTIVA_MAX_RETRIES=3
```

### 🚨 **Detección de Modo Demo**

Si ves respuestas como:
- *"Como estoy en modo demo, esta es una respuesta de ejemplo"*
- *"Para respuestas reales, necesito estar conectado a los modelos SAPTIVA"*

**Significa que `SAPTIVA_API_KEY` no está configurada.**

### ✅ **Problemas Resueltos**

1. ✅ **ERR_CONNECTION_REFUSED**: Resuelto con nginx proxy + URLs inteligentes
2. ✅ **Cache divergencia**: Headers anti-cache + localStorage versioning
3. ✅ **Modo incógnito vs normal**: Store persistence mejorada
4. ✅ **Build errors**: TypeScript + Docker build arreglados

### 🔧 **Herramientas de Debug**

```bash
# Nuevos comandos Make disponibles
make test-api-connection      # Test conectividad API
make build-frontend ENV=prod # Build específico de entorno
make nginx-config            # Recargar configuración nginx
make fix-prod               # Fix rápido de contenedores
```

---

## Ambientes de demostración

Para acelerar pruebas, demos con clientes y validaciones internas añadimos plantillas de entorno y un seeder de usuarios.

### API (`apps/api`)

1. Copia la plantilla local y ajústala según tus credenciales:
   ```bash
   cp apps/api/.env.development.sample apps/api/.env
   ```
2. Levanta MongoDB y Redis (por ejemplo `docker compose -f docs/setup/docker-compose.fast.yml up -d mongodb redis`).
3. Ejecuta el seeder para crear un usuario demo (`demo_admin / ChangeMe123!`):
   ```bash
   python apps/api/scripts/seed_demo_data.py
   ```
   > Con Docker en marcha: `docker compose exec api python scripts/seed_demo_data.py`.

También se incluye `.env.production.sample` con campos listos para productivo.

### Web (`apps/web`)

1. Copia la plantilla:
   ```bash
   cp apps/web/.env.local.example apps/web/.env.local
   ```
2. Ajusta `NEXT_PUBLIC_API_URL` si tu API corre en otro host.
3. Inicia el frontend con `pnpm --filter web dev` y autentícate usando el usuario demo.

Con estos pasos tendrás un entorno homogéneo para QA y demostraciones sin exponer secretos reales.

### Verificación del Setup

#### ✅ **Infraestructura y Servicios Base**
- ✅ UI accesible en `http://localhost:3000` y `http://34.42.214.246:3000`
- ✅ Chat interface funcional con estructura completa
- ✅ Páginas Research, History, Reports navegables
- ✅ MongoDB conectada y collections creadas (local Docker + producción)
- ✅ Redis funcionando para cache/sesiones (local Docker + producción)
- ✅ API FastAPI corriendo en `http://localhost:8001` y `http://34.42.214.246:8001`
- ✅ Endpoints básicos funcionando (`/api/health`, `/api/chat`, `/api/sessions`)
- ✅ **Autenticación JWT Funcional**: Login/register UI/UX completamente funcional
- ✅ **Frontend Auth Store**: Zustand store actualizado y errores de hidratación corregidos
- ✅ **Chat API Telemetry**: Métricas de chat implementadas y funcionando
- ✅ **Multi-Environment Docker**: Infraestructura local/staging/prod funcionando
- ✅ CI/CD Pipeline ejecutándose automáticamente
- ✅ Deploy staging funcionando en servidor de producción
- ✅ **Desarrollo Local**: Entorno Docker completo funcionando

#### ⚠️ **SAPTIVA Integration - MODO DEMO**
- ⚠️ **Chat API Structure**: Endpoints funcionando correctamente con fallback inteligente
- ⚠️ **SAPTIVA_API_KEY**: NO configurada - sistema funciona en modo DEMO
- ⚠️ **Respuestas Mock**: "Como estoy en modo demo, esta es una respuesta de ejemplo"
- ⚠️ **Settings Modal**: Existe pero no conectado al backend
- 🔧 **Para Producción**: Configurar `SAPTIVA_API_KEY` en variables de entorno

#### ⏳ **Pendientes Críticos**
- 🔧 Conexión real SAPTIVA API (configurar API key)
- 🔧 Endpoint `/api/settings/saptiva-key` para conectar frontend-backend
- ⏳ Conexión a Aletheia (próxima prioridad)

### Uso Actual

#### 🟢 **Completamente Funcional**
1. **Autenticación**: ✅ **COMPLETA** - Login/register JWT end-to-end funcionando
2. **Chat API**: ✅ **COMPLETA** - Endpoints, telemetría, persistencia con SAPTIVA real
3. **Docker Stack**: ✅ **COMPLETA** - Stack integrado, "Network Error" resuelto
4. **Frontend UI**: ✅ **COMPLETA** - Scroll fix, responsive, SAPTIVA design
5. **Base de Datos**: ✅ **MONGO + REDIS** - Persistencia y cache funcional
6. **SAPTIVA Integration**: ✅ **REAL** - Respuestas reales de modelos SAPTIVA

#### 🟡 **Funcional con Configuración**
7. **Settings Modal**: ⚠️ **UI COMPLETO** - Falta conexión backend para persistir API key
8. **Deep Research**: ⚠️ **MOCK** - Tool integrado pero sin Aletheia real
9. **Streaming**: ⚠️ **SSE BACKEND** - Implementado pero para datos mock

#### 🔴 **Pendiente Implementación**
10. **Aletheia Integration**: ❌ **SIN CONEXIÓN** - Deep research en modo mock
11. **Testing**: ❌ **GAPS CRÍTICOS** - Sin E2E, integration o unit tests
12. **API Key Management**: ❌ **FRONTEND↔BACKEND** - Falta endpoint

---

### Ejecutar el stack completo con Docker Compose

```bash
# Construir imágenes (necesario si cambias variables o dependencias)
docker compose build api web

# Levantar todos los servicios (Mongo, Redis, API, Web)
docker compose up -d

# Revisar el estado y logs
docker compose ps
docker compose logs -f api web
```

**Puntos clave:**
- `API_BASE_URL` apunta al hostname interno `api` para que Next.js haga proxy correcto durante SSR.
- `NEXT_PUBLIC_API_URL` queda expuesto como `http://localhost:8001` para llamadas desde el navegador.
- `ALLOWED_HOSTS` incluye `web` y `api` para que FastAPI acepte las peticiones entre contenedores.
- Si actualizas variables de entorno vuelve a ejecutar `docker compose build web` para regenerar las rewrites.
- Si la UI se ve sin estilos tras un despliegue, ejecuta `docker compose build web` y fuerza un *hard refresh* (Ctrl+Shift+R).

Para tumbar todo:

```bash
docker compose down -v
```

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

### ✅ **Progreso Real (95%) - Actualización Sep 2025**
- **📁 Estructura del monorepo**: Apps (web/api), packages (shared), infra, docs, tests
- **⚙️ Configuración base**: Variables de entorno, TypeScript, Tailwind, FastAPI
- **🗄️ Base de datos**: Modelos MongoDB con Beanie ODM, índices optimizados y funcionando
- **📝 Tipos compartidos**: Interfaces TypeScript + esquemas Zod + Pydantic
- **🐳 Docker Compose**: MongoDB + Redis con healthchecks funcionando
- **🎨 UI Sistema de diseño**: Componentes completos con paleta SAPTIVA
- **💬 Chat Interface**: Funcional con estado global Zustand
- **📱 Páginas principales**: Chat, Research, History, Reports implementadas
- **🔌 Cliente API**: HTTP client para FastAPI con streaming SSE
- **🌐 Frontend completo**: Next.js 14 con identidad visual SAPTIVA
- **🚀 API FastAPI**: Endpoints completos funcionando con routing inteligente
- **🔐 Autenticación JWT**: Middleware JWT con validación y fallback mock
- **⚠️ Manejo de errores**: Exception handlers globales y logging estructurado
- **🔧 CI/CD Pipeline**: GitHub Actions con security scanning, build, tests y deploy automatizado
- **🚀 Deploy Staging**: Servidor de producción funcionando con health checks y rollback automático
- **🛠️ DevOps**: SSH keys configuradas, Docker Compose en servidor, pipeline completo
- **🤖 SAPTIVA Integration**: Cliente HTTP completo, modelos reales funcionando, fallback inteligente
- **🔧 Desarrollo Local**: Docker Compose completo, MongoDB + Redis + API + Frontend funcionando
- **🔗 Conexión End-to-End**: UI → API → SAPTIVA verificada con respuestas reales
- **🧠 Research Coordinator**: Sistema inteligente de routing entre chat y deep research
- **📡 Streaming SSE**: Server-Sent Events implementado con backpressure y fallbacks
- **🔍 Deep Research**: Endpoints completos con integración Aletheia y fallback a mock
- **🎛️ Aletheia Client**: Cliente HTTP robusto con retry logic y circuit breaker
- **⚙️ Configuración Producción**: Variables de entorno, Docker Compose y scripts de deploy completos

### ✅ **Completado Recientemente** 🎉
- ✅ **Autenticación Completa (Sep 2025)**: Login/register UI completamente funcional, auth store corregido, flujo end-to-end validado
- ✅ **Corrección Scroll UI (Sep 2025)**: Problema de scroll cortado solucionado, estructura #message-list implementada, InputBar siempre visible
- ✅ **Docker Stack Completo (Sep 2025)**: Integración completa del stack, resolución "Network Error", autenticación JWT funcionando
- ✅ **Test End-to-End (Sep 2025)**: Flujo completo verificado: registro → login → chat → respuesta SAPTIVA real
- ✅ **Frontend Auth Store Fix**: Resolución de errores de hidratación Zustand y deprecación de APIs
- ✅ **Chat API Telemetry**: Implementación de métricas de chat y corrección de errores MetricsCollector
- ✅ **Multi-Environment Infrastructure**: Docker Compose para local/staging/prod con configuración unificada
- ✅ **Research Coordinator**: Sistema inteligente que decide entre chat simple y deep research basado en complejidad de query
- ✅ **Streaming SSE Real**: `/api/stream/{task_id}` con eventos en tiempo real y manejo de cancelación
- ✅ **Deep Research Endpoints**: `/api/deep-research` completamente funcional con fallback a mock cuando Aletheia no está disponible
- ✅ **Aletheia Integration**: Cliente HTTP completo con manejo de errores, timeouts y retry logic
- ✅ **Configuración Producción**: `.env.production`, `docker-compose.prod.yml`, script de deploy y guía completa
- ✅ **Health Checks**: Endpoints de monitoreo y verificación de estado de servicios
- ✅ **Testing & Validation**: Research logic, API endpoints y search functionality validados (88% success rate)
- ✅ **OpenTelemetry Setup**: Telemetry configuration, metrics collection y observability infrastructure

### 🎨 **Mejoras UI/UX SAPTIVA (Septiembre 2025)**
- ✅ **P0-01: Quick Prompts Funcionales**: Ejemplos envían mensajes automáticamente, solo visibles en conversación vacía, responsive (chips móvil + tarjetas desktop)
- ✅ **P0-07: Selector Modelo Integrado**: Dropdown de modelos en barra ChatInput lado izquierdo, con persistencia por conversación
- ✅ **P0-05: ToolTray en ChatInput**: Deep Research como tool integrado con wrap, contrato Tool→Orquestador→LLM
- ✅ **Docker & CI/CD Simplificado**: Configuración minimalista, pipeline optimizado con pnpm y docker compose moderno
- ✅ **P0-02: UI Responsiva 100dvh**: Layout actualizado con h-screen, overflow correcto, sidebar colapsa ≤1024px
- ✅ **P0-03: Modal API Key Accesible**: Focus-trap, ESC, Cmd/Ctrl+K, localStorage persistence
- ✅ **P0-08: Tokens Tipográficos Lab**: Fuente única Inter, escala 12-40px, radius 12-16px implementado
- ✅ **AUTENTICACIÓN FUNCIONAL**: Login/registro endpoints completamente operativos, serialización UserPreferences solucionada

### 🔧 **En Proceso Final**
- **Monitoring y Observabilidad**: OpenTelemetry configurado, Prometheus y Grafana pending
- **Testing Suite**: Unit tests y E2E tests para flujos críticos
- **History Persistence**: Chat-research mapping completo
- **Report Preview UI**: Modal de preview y descarga de reportes

### **Stack Tecnológico Implementado (COMPLETO)**
```
Frontend:     Next.js 14 + TypeScript + Tailwind CSS + Zustand ✅
UI/UX:        SAPTIVA Design System + Responsive Layout ✅
State:        Zustand store + API client + SSE streaming ✅
Backend:      FastAPI + Pydantic 2.0 + Beanie ODM ✅
Auth:         JWT middleware + validation + error handling ✅
Database:     MongoDB 6.0 + Redis 7 ✅
AI Models:    SAPTIVA API Integration (Cortex/Turbo/Guard) ✅
Research:     Aletheia Integration + Research Coordinator ✅
Streaming:    Server-Sent Events + WebSocket support ✅
Deploy:       Docker Compose + Production scripts ✅
Monitoring:   Health checks + Structured logging ✅
Production:   Complete .env setup + deployment guides ✅
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

#### ❌ Error "Network Error" en el Chat/Login

Si ves un "Network Error" al intentar usar el chat o autenticarse:

**Causa**: El frontend no puede conectarse al backend API.

**Solución Rápida**:
```bash
# 1. Parar cualquier servicio corriendo
make stop
# o manualmente:
docker stop $(docker ps -q --filter "name=copilotos-*")

# 2. Levantar el stack completo con Docker
make local

# 3. Verificar que todos los servicios están corriendo
curl -f http://localhost:8001/api/health
curl -f http://localhost:3000 -I
```

**Verificación de puertos**:
- ✅ **Frontend**: http://localhost:3000
- ✅ **API**: http://localhost:8001/api/health
- ✅ **MongoDB**: localhost:27017
- ✅ **Redis**: localhost:6379

**Si el problema persiste**:
```bash
# Ver logs para diagnosticar
docker logs copilotos-web
docker logs copilotos-api

# Verificar configuración de CORS
grep -r "CORS_ORIGINS" envs/.env.local

# Limpiar y reiniciar
make clean
make local
```

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
# Abrir shell de MongoDB para inspección rápida
docker compose -f docker-compose.yml exec mongodb mongosh -u copilotos_user -p secure_password_change_me
# (Para UI gráfica puedes correr mongo-express manualmente apuntando a la misma red)
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
