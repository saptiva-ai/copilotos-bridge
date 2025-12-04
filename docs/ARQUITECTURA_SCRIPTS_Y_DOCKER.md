# Arquitectura de Scripts y Docker Compose

**Fecha:** 3 de Diciembre 2025
**Versión:** 1.0

---

## 📋 Tabla de Contenidos

1. [Docker Compose - Arquitectura de Overlays](#docker-compose---arquitectura-de-overlays)
2. [Organización Actual de Scripts](#organización-actual-de-scripts)
3. [Scripts en Uso vs Obsoletos](#scripts-en-uso-vs-obsoletos)
4. [Propuesta de Limpieza](#propuesta-de-limpieza)
5. [Comandos de Deploy Recomendados](#comandos-de-deploy-recomendados)

---

## 🐳 Docker Compose - Arquitectura de Overlays

### Estructura de Archivos

El proyecto usa una arquitectura de **overlays** (capas) de Docker Compose, donde archivos específicos sobrescriben configuraciones base:

```
infra/
├── docker-compose.yml            # 📦 BASE (19KB) - Configuración canónica
├── docker-compose.dev.yml        # 🔧 DEV (2.4KB) - Override para desarrollo
├── docker-compose.production.yml # 🚀 PROD (2.5KB) - Override para producción
└── docker-compose.registry.yml   # 📦 REGISTRY (953B) - Override para Docker Hub
```

---

### 1. `docker-compose.yml` - BASE (Canónico)

**Propósito:** Configuración base compartida por todos los entornos.

**Servicios Definidos:**
- **Infraestructura:**
  - `mongodb` - MongoDB 7.0 (puerto 27018)
  - `redis` - Redis 7-alpine (puerto 6380)
  - `postgres` - PostgreSQL 15 (puerto 5433)
  - `qdrant` - Qdrant vector DB (puerto 6333)
  - `minio` - S3-compatible storage (puertos 9000/9001)

- **Aplicación:**
  - `backend` - FastAPI backend (puerto 8000)
  - `web` - Next.js frontend (puerto 3000)
  - `bank-advisor` - Bank Advisor plugin (puerto 8002)
  - `file-manager` - File Manager plugin (puerto 8001)

**Características Clave:**
```yaml
# Name (CRÍTICO: debe coincidir con producción para reusar volúmenes)
name: ${COMPOSE_PROJECT_NAME:-octavios-chat-bajaware_invex}

# Env file compartido
env_file:
  - ../envs/.env

# Health checks para todos los servicios
healthcheck:
  test: [...]
  interval: 30s
  timeout: 10s
  retries: 3
```

**Volúmenes Persistentes:**
```yaml
volumes:
  mongodb_data:        # Datos de MongoDB (usuarios, chats)
  mongodb_config:      # Configuración de MongoDB
  redis_data:          # Caché de Redis
  postgres_data:       # Datos de PostgreSQL (Bank Advisor)
  qdrant_storage:      # Vectores de Qdrant (RAG)
  minio_data:          # Archivos S3 (documentos)
```

**Red:**
```yaml
networks:
  octavios-network:
    driver: bridge
```

---

### 2. `docker-compose.dev.yml` - DEV Override

**Propósito:** Habilitar **hot reload** y herramientas de desarrollo.

**Uso:**
```bash
# Desarrollo (con hot reload)
make dev
# O manualmente:
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.dev.yml \
               up -d
```

**Cambios Aplicados:**

#### Backend (FastAPI)
```yaml
backend:
  user: "${UID:-1000}:${GID:-1000}"  # Permisos del host
  build:
    target: development  # Stage con pytest y tools
  volumes:
    - ../apps/backend/src:/app/src              # Hot reload
    - ../apps/backend/tests:/app/tests:ro       # Tests
  environment:
    - PYTHONPATH=/usr/local/lib/python3.11/site-packages:/app/src
    - COVERAGE_FILE=/tmp/.coverage
```

#### Web (Next.js)
```yaml
web:
  user: "${UID:-1000}:${GID:-1000}"
  build:
    target: dev
  command: |
    pnpm install --frozen-lockfile
    cd apps/web && pnpm dev --hostname 0.0.0.0
  environment:
    - NODE_ENV=development
    - CI=true  # Para evitar warning de pnpm
  volumes:
    - ../pnpm-lock.yaml:/app/pnpm-lock.yaml:ro
    - ../packages:/app/packages
    - ../apps/web:/app/apps/web
    - web_node_modules:/app/apps/web/node_modules  # Named volume
    - /app/apps/web/.next  # Anonymous volume para build
```

#### Bank Advisor
```yaml
bank-advisor:
  volumes:
    - ../plugins/bank-advisor-private/src:/app/src  # Hot reload
    - ../plugins/bank-advisor-private/data:/app/data:ro
    - ../apps/backend/src:/backend_shared/src:ro  # SAPTIVA client
```

#### File Manager
```yaml
file-manager:
  volumes:
    - ../plugins/public/file-manager/src:/app/src  # Hot reload
```

**Características:**
- ✅ Hot reload habilitado (cambios en código → auto-recarga)
- ✅ Tests disponibles (pytest, jest)
- ✅ Permisos del host user (evita problemas de permisos)
- ✅ node_modules en volumen named (evita conflictos)
- ⚠️ **NO usar en producción** (monta código fuente)

---

### 3. `docker-compose.production.yml` - PROD Override

**Propósito:** Deshabilitar explícitamente características de desarrollo.

**Uso:**
```bash
# Producción (build local)
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               up -d --build

# Producción (con registry)
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               -f infra/docker-compose.registry.yml \
               up -d
```

**Cambios Aplicados:**

#### Backend
```yaml
backend:
  build:
    target: production  # Stage optimizado sin dev tools
  environment:
    - NODE_ENV=production
    - DEBUG=false
    - LOG_LEVEL=info
    - RATE_LIMIT_ENABLED=true
    - DEEP_RESEARCH_KILL_SWITCH=true
    - DEEP_RESEARCH_ENABLED=false
  user: ""  # Container user (mejor seguridad)
  # SIN volúmenes de código fuente
```

#### Web
```yaml
web:
  build:
    target: runner  # Next.js production build
  environment:
    - NODE_ENV=production
    - DEEP_RESEARCH_ENABLED=false
  user: "${UID:-1000}:${GID:-1000}"  # Mantiene user para permisos
  command: []  # Usa CMD del Dockerfile (node server.js)
  # SIN volúmenes de código fuente
```

#### Bank Advisor & File Manager
```yaml
bank-advisor:
  environment:
    - LOG_LEVEL=INFO
  user: ""
  # SIN volúmenes de código fuente

file-manager:
  environment:
    - LOG_LEVEL=INFO
  user: ""
  # SIN volúmenes de código fuente
```

**Características:**
- ✅ Sin hot reload (no monta código fuente)
- ✅ Build targets de producción optimizados
- ✅ Logs en nivel INFO (menos verbose)
- ✅ Rate limiting habilitado
- ✅ Deep research deshabilitado (kill switch)
- ✅ Container user (mejor seguridad)
- ⚠️ **Requiere build** (más lento en servidor)

---

### 4. `docker-compose.registry.yml` - REGISTRY Override

**Propósito:** Usar imágenes pre-construidas desde **Docker Hub** en vez de build local.

**Uso:**
```bash
# Producción con registry (RECOMENDADO)
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.production.yml \
               -f infra/docker-compose.registry.yml \
               up -d --no-build
```

**Cambios Aplicados:**

```yaml
services:
  backend:
    image: jazielflores1998/octavios-invex-backend:0.1.2
    build: null  # Deshabilita build local

  web:
    image: jazielflores1998/octavios-invex-web:0.1.2
    build: null

  file-manager:
    image: jazielflores1998/octavios-invex-file-manager:0.1.2
    build: null

  bank-advisor:
    image: jazielflores1998/octavios-invex-bank-advisor:0.1.2
    build: null
```

**Características:**
- ✅ **Muy rápido** (solo pull, sin build)
- ✅ Imágenes consistentes (build en PC potente)
- ✅ Versionado explícito (0.1.2)
- ✅ Ideal para producción
- ⚠️ **Requiere push previo** a Docker Hub

**Workflow con Registry:**
```bash
# 1. LOCAL: Build y push a Docker Hub
make deploy-registry VERSION=0.1.3

# 2. SERVIDOR: Pull y deploy
ssh servidor "cd proyecto && \
  sed -i 's/:0.1.2/:0.1.3/g' infra/docker-compose.registry.yml && \
  docker compose -f infra/docker-compose.yml \
                 -f infra/docker-compose.production.yml \
                 -f infra/docker-compose.registry.yml \
                 up -d"
```

---

## 🔧 Comparación de Modos

| Aspecto | DEV | PRODUCTION | REGISTRY |
|---------|-----|------------|----------|
| **Hot Reload** | ✅ Sí | ❌ No | ❌ No |
| **Build** | Dev target | Production target | Sin build (pull) |
| **Volúmenes Código** | ✅ Montados | ❌ No | ❌ No |
| **NODE_ENV** | development | production | production |
| **LOG_LEVEL** | DEBUG | INFO | INFO |
| **User** | Host UID/GID | Container | Container |
| **Velocidad Deploy** | Rápido (no build) | Lento (47+ min) | **Muy rápido (5 min)** |
| **Uso** | Desarrollo local | Build en servidor | **Deploy producción** |
| **Comando** | `make dev` | `make prod` | `REGISTRY=1 make prod` |

**Recomendación:**
- 🔧 **Desarrollo:** `make dev` (docker-compose.yml + dev.yml)
- 🚀 **Producción:** `REGISTRY=1 make prod` (base + production + registry)

---

## 📁 Organización Actual de Scripts

### Estado Actual (Antes de Limpieza)

```
scripts/
├── 📁 ci/                          # CI/CD scripts
├── 📁 database/                    # Database management (13 scripts)
├── 📁 fixtures/                    # Test fixtures
├── 📁 git-hooks/                   # Git hooks
├── 📁 legacy/                      # Scripts obsoletos
│   ├── deploy_archive/            # ✅ NUEVO: 18 deploys archivados
│   └── manual-deploy-prod.sh
├── 📁 legacy_archive/              # Archivo antiguo
├── 📁 maintenance/                 # Mantenimiento (11 scripts)
├── 📁 migrations/                  # DB migrations
├── 📁 security/                    # Security audits (5 scripts)
├── 📁 setup/                       # Setup scripts (12 scripts)
├── 📁 testing/                     # Testing scripts (27 scripts)
├── 📁 tests/                       # Test suites (e2e, smoke)
└── 📁 validation/                  # Validation scripts

# Scripts en root (total: 103 archivos)
├── ⚠️ DUPLICADOS (eliminados):
│   ├── deployment/ (16 scripts)  ✅ ELIMINADA
│   ├── database duplicates (12)  ✅ ELIMINADOS
│   └── setup duplicates (12)     ⚠️ PENDIENTE
│
├── ✅ ACTIVOS (en uso):
│   ├── deploy-to-production.sh   ⭐ NUEVO (registry deploy)
│   ├── push-dockerhub.sh         Registry helpers
│   ├── tag-dockerhub.sh
│   ├── tag-images.sh
│   ├── start-production.sh
│   ├── git-secrets-check.sh      Pre-commit hook
│   ├── cleanup-python-cache.sh   Pre-commit hook
│   ├── init-bankadvisor-db.sh    Bank Advisor init
│   ├── init_bank_advisor_data.sh Bank Advisor data
│   └── db-manager.sh             DB management
│
└── ⚠️ OBSOLETOS (archivados):
    └── legacy/deploy_archive/    ✅ 18 scripts movidos
```

### Scripts Archivados en `legacy/deploy_archive/`

Los siguientes 18 scripts de deploy fueron movidos a `legacy/deploy_archive/`:

1. `DEPLOY-NOW.sh` - Nombre poco descriptivo
2. `deploy-production-v3.sh` - Reemplazado por registry strategy
3. `deploy-production-v2.sh` - Versión antigua
4. `deploy-production-safe.sh` - Versión antigua
5. `deploy-production.sh` - Genérico obsoleto
6. `deploy-registry.sh` - Reemplazado por deploy-to-production.sh
7. `deploy-from-registry.sh` - Para otro proyecto (Copilotos Bridge)
8. `deploy-api-only.sh` - Deploy parcial no recomendado
9. `deploy-web-only.sh` - Deploy parcial no recomendado
10. `deploy-full-pipeline.sh` - Pipeline complejo
11. `deploy-on-server.sh` - Método obsoleto
12. `deploy-manager.sh` - Orquestador innecesario
13. `deploy-with-tar.sh` - Método de tar obsoleto
14. `deploy.sh` - Genérico
15. `deploy-staging.sh` - Staging no existe
16. `deploy-vercel.sh` - Vercel no se usa
17. `deploy-prod.sh` - Duplicado
18. `deploy-local.sh` - Solo para dev

**Razón:** Todos reemplazados por `deploy-to-production.sh` que usa registry strategy.

---

## 🔍 Scripts en Uso vs Obsoletos

### Scripts ACTIVOS (Mantener)

#### Deploy y Registry
```bash
scripts/
├── deploy-to-production.sh    # ⭐ Script principal de deploy
├── push-dockerhub.sh          # Push imágenes a Docker Hub
├── tag-dockerhub.sh           # Tag imágenes para Docker Hub
├── tag-images.sh              # Tag imágenes locales
└── start-production.sh        # Start servicios en producción
```

**Referenciados en:**
- `docs/DEPLOY_ANALISIS_Y_GUIA.md`
- `Makefile` (make deploy-registry)

---

#### Git Hooks (Pre-commit)
```bash
scripts/
├── git-secrets-check.sh       # Detecta secrets antes de commit
└── cleanup-python-cache.sh    # Limpia cache Python
```

**Referenciados en:**
- `apps/web/.husky/pre-commit`
- Ejecutados automáticamente en cada commit

---

#### Bank Advisor
```bash
scripts/
├── init-bankadvisor-db.sh        # Inicializa DB + ETL
├── init_bank_advisor_data.sh     # Carga datos iniciales
├── test_bank_query_detection.py  # Tests de detección
└── test_bank_query_hybrid.py     # Tests híbridos
```

**Referenciados en:**
- `Makefile` (make init-bank-advisor)
- `plugins/bank-advisor-private/README.md`

---

#### Database Management
```bash
scripts/db-manager.sh              # CLI para DB operations
scripts/database/
├── backup-mongodb.sh              # Backup automático
├── restore-mongodb.sh             # Restore desde backup
├── migrate-*.py                   # Migraciones de datos
└── rotate-*-credentials.sh        # Rotación de credentials
```

**Referenciados en:**
- `Makefile` (make db CMD=backup)

---

#### Testing
```bash
scripts/
├── test-runner.sh                 # Runner principal de tests
├── test-auth-and-chat.py          # Tests de auth + chat
├── test_password_reset.sh         # Tests de password reset
└── testing/
    ├── test_integration.py        # Tests de integración
    ├── validate-*.sh              # Validaciones
    └── verify-*.sh                # Verificaciones
```

**Referenciados en:**
- `Makefile` (make test)
- `scripts/README.md`

---

### Scripts OBSOLETOS / DUPLICADOS

#### ✅ Ya Eliminados
- `scripts/deployment/` - **16 scripts** (todos duplicados exactos)
- `scripts/legacy/deploy_archive/` - **18 scripts** de deploy obsoletos
- Duplicados de `database/` - **12 scripts** en root

#### ⚠️ Pendientes de Revisar

##### Setup Scripts (posibles duplicados)
```bash
scripts/
├── create-demo-user.py        }
├── create-demo-user.sh        } Duplicados con setup/
├── env-checker.sh             }
├── env-manager.sh             }
├── fix-docker-permissions.sh  }
├── fix-env-server.sh          }
├── fix_demo_user.py           }
├── generate-secrets.py        }
├── interactive-env-setup.sh   }
├── setup-dev.sh               }
├── setup-docker-secrets.sh    }
└── setup.sh                   }
```

**Acción Sugerida:** Verificar si están referenciados en Makefile. Si no, eliminar duplicados de root.

---

##### Maintenance Scripts (posibles duplicados)
```bash
scripts/
├── analyze-chunk-optimization.py  }
├── cleanup-duplicate-drafts.py    } Duplicados con maintenance/
├── clear-server-cache.sh          }
├── dev-troubleshoot.sh            }
├── diagnose-nginx-413.sh          }
├── docker-cleanup.sh              }
├── health-check.sh                }
├── monitor-backups.sh             }
├── prod-health-check.sh           }
├── quick-diagnostic.sh            }
└── repro_second_image.sh          }
```

**Acción Sugerida:** Eliminar duplicados de root, mantener solo en `maintenance/`.

---

##### Security Scripts (posibles duplicados)
```bash
scripts/
├── security-audit-focused.sh      }
├── security-audit-precise.sh      } Duplicados con security/
├── security-audit.sh              }
├── security-check.sh              }
└── remove-audit-system.sh         }
```

**Acción Sugerida:** Eliminar duplicados de root, mantener solo en `security/`.

---

##### Testing Scripts (muchos duplicados)
```bash
scripts/
├── test-all-models.py             }
├── test-auth-and-chat.py          }
├── test-auth-logging.py           }
├── test-backup-system.sh          } Duplicados con testing/
├── test-credential-rotation.sh    }
├── test-mongodb.py                }
├── test-rag-ingestion.py          }
├── test-rag-wrapper.sh            }
├── test-semantic-search.py        }
├── test_mcp_audit.py              }
├── test_mcp_tools.sh              }
├── test_validation.sh             }
├── validate-config.sh             }
├── validate-env-server.sh         }
├── validate-mvp.sh                }
├── validate-production-readiness.sh}
├── validate-setup.sh              }
├── validate_saptiva_api.py        }
├── verify-deployment.sh           }
├── verify-deps.sh                 }
└── verify.sh                      }
```

**Acción Sugerida:** Eliminar duplicados de root, mantener solo en `testing/`.

---

##### Scripts Únicos a Categorizar
```bash
scripts/
├── audit-production-state.sh      → maintenance/?
├── blue-green-switch.sh           → legacy? (no se usa blue-green)
├── build-frontend.sh              → setup/?
├── fix-nginx-413.sh               → maintenance/
├── fix-orphaned-drafts.py         → database/
├── init-blue-green.sh             → legacy?
├── migrate-prod-to-octavios.sh    → database/
├── push-to-registry.sh            → ¿duplicado de push-dockerhub.sh?
├── rollback.sh                    → deployment/ (si se crea)
├── sanitize.sh                    → security/?
├── setup-demo-server.sh           → setup/
├── setup-ssl-414.sh               → setup/
├── verify_pdf_extraction.py       → testing/
└── reproduce_golden_case.py       → testing/
```

---

## 🧹 Propuesta de Limpieza

### Fase 1: Eliminar Duplicados Obvios (✅ COMPLETADO)

```bash
✅ rm -rf scripts/deployment/                    # 16 duplicados exactos
✅ mv scripts/deploy-*.sh scripts/legacy/deploy_archive/  # 18 obsoletos
✅ rm scripts/{apply-draft,apply-email,backup-docker,...}  # 12 de database/
```

**Resultado:** -46 scripts

---

### Fase 2: Organizar Scripts Restantes (PENDIENTE)

#### Opción A: Eliminar duplicados de root (RECOMENDADO)

```bash
# Mantener solo en subcarpetas organizadas
rm scripts/{security-audit,security-check}*.sh         # En security/
rm scripts/{test,validate,verify}*.{sh,py}             # En testing/
rm scripts/{cleanup,diagnose,health-check}*.sh         # En maintenance/
rm scripts/{create-demo,env-checker,setup}*.{sh,py}    # En setup/
```

**Ventajas:**
- ✅ Organización clara por categoría
- ✅ Menos archivos en root (más limpio)
- ✅ Fácil encontrar scripts

**Desventajas:**
- ⚠️ Rutas más largas (`scripts/testing/test-auth.py` vs `scripts/test-auth.py`)

---

#### Opción B: Mantener scripts activos en root (ALTERNATIVA)

```bash
# Root: Solo scripts de uso diario
scripts/
├── deploy-to-production.sh       # Deploy principal
├── db-manager.sh                 # DB management
├── test-runner.sh                # Test runner
├── git-secrets-check.sh          # Pre-commit
└── ... (10-15 scripts core)

# Subcarpetas: Scripts especializados
scripts/{database,testing,security,setup,maintenance}/
```

**Ventajas:**
- ✅ Scripts comunes fácil acceso
- ✅ Rutas cortas para lo frecuente

**Desventajas:**
- ⚠️ Aún hay duplicados (mantener sincronizados)

---

### Fase 3: Crear Índice de Scripts

Crear `scripts/README.md` con tabla de todos los scripts:

```markdown
# Scripts Directory

## Quick Reference

| Script | Categoría | Propósito | Uso |
|--------|-----------|-----------|-----|
| `deploy-to-production.sh` | Deploy | Deploy completo a producción | `./scripts/deploy-to-production.sh 0.1.3` |
| `db-manager.sh` | Database | CLI para operaciones DB | `./scripts/db-manager.sh backup` |
| `git-secrets-check.sh` | Security | Detecta secrets | Pre-commit (automático) |
...
```

---

## 📊 Resumen de Limpieza Ejecutada

### Acciones Completadas

| Acción | Cantidad | Ubicación |
|--------|----------|-----------|
| ✅ Carpeta deployment/ eliminada | 16 scripts | `scripts/deployment/` |
| ✅ Scripts de deploy archivados | 18 scripts | `scripts/legacy/deploy_archive/` |
| ✅ Duplicados database eliminados | 12 scripts | `scripts/{backup,migrate,...}` |
| ⚠️ Setup duplicados NO eliminados | 12 scripts | `scripts/{env-checker,setup}*` (pendiente review) |

**Total eliminado hasta ahora:** 46 scripts

---

### Acciones Pendientes

| Acción | Cantidad Estimada | Impacto |
|--------|-------------------|---------|
| Eliminar duplicados de testing/ | ~19 scripts | Limpieza root |
| Eliminar duplicados de maintenance/ | ~11 scripts | Limpieza root |
| Eliminar duplicados de security/ | ~5 scripts | Limpieza root |
| Eliminar duplicados de setup/ | ~12 scripts | ⚠️ **Verificar Makefile primero** |
| Categorizar scripts únicos | ~15 scripts | Mejor organización |

**Total potencial:** -62 scripts adicionales

---

## 🚀 Comandos de Deploy Recomendados

### Desarrollo Local
```bash
# Iniciar entorno de desarrollo (hot reload)
make dev

# O manualmente:
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.dev.yml \
               up -d
```

---

### Testing
```bash
# Run all tests
make test

# Run specific tests
make test T=api       # API tests
make test T=web       # Web tests
make test T=e2e       # E2E tests
```

---

### Deploy a Producción (Registry Strategy) ⭐

```bash
# === EN PC LOCAL (build potente) ===
# 1. Build imágenes y push a Docker Hub
make deploy-registry VERSION=0.1.4

# Desglose interno:
#   docker compose -f infra/docker-compose.yml \
#                  -f infra/docker-compose.production.yml \
#                  build backend web bank-advisor file-manager
#
#   ./scripts/tag-dockerhub.sh 0.1.4
#   ./scripts/push-dockerhub.sh

# === EN SERVIDOR (producción) ===
# 2. Deploy usando script automatizado
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  ./scripts/deploy-to-production.sh 0.1.4"

# O manualmente:
ssh jf@34.28.92.134 "cd octavios-chat-bajaware_invex && \
  git pull origin main && \
  sed -i 's/:0\.1\.[0-9]/:0.1.4/g' infra/docker-compose.registry.yml && \
  source envs/.env && export SECRET_KEY JWT_SECRET_KEY && \
  docker compose -f infra/docker-compose.yml \
                 -f infra/docker-compose.production.yml \
                 -f infra/docker-compose.registry.yml \
                 pull && \
  docker compose -f infra/docker-compose.yml \
                 -f infra/docker-compose.production.yml \
                 -f infra/docker-compose.registry.yml \
                 up -d --force-recreate --no-build"
```

**Tiempo:** ~15 minutos total (5 min build local + 5 min pull + 5 min restart)

---

### Deploy Legacy (Build en Servidor) - NO RECOMENDADO

```bash
# Deploy con build en servidor (LENTO: 47+ min)
ssh servidor "cd proyecto && \
  docker compose -f infra/docker-compose.yml \
                 -f infra/docker-compose.production.yml \
                 up -d --build"
```

**⚠️ Problema:** Servidor con recursos limitados, build muy lento.

---

## 📖 Referencias

- **Deploy Guide:** `docs/DEPLOY_ANALISIS_Y_GUIA.md`
- **Production Deployment:** `docs/PRODUCTION_DEPLOYMENT.md`
- **Makefile:** `Makefile` (comandos make)
- **Docker Hub:** https://hub.docker.com/u/jazielflores1998

---

**Última actualización:** 3 de Diciembre 2025
**Mantenido por:** Equipo Saptiva AI
