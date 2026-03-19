# Research: Separación de Despliegues por Entorno/Tenant

> **Fecha de investigación:** 2026-02-23
> **Método:** Análisis exhaustivo de workflows, scripts, configs, frontend, backend e infra
> **Alcance:** `.github/workflows/`, `scripts/deploy/`, `infra/`, `apps/web/`, `apps/backend/`, `plugins/`

---

## 1. GitHub Actions — Estado Actual

### 1.1 CI Pipeline (`ci.yml`)

**Triggers:** PR a `main`, `workflow_dispatch` manual.

**Jobs (10):**
1. `detect-changes` — `dorny/paths-filter@v3` detecta qué servicios cambiaron
2. `test-backend` — Python 3.11, uv, ruff lint, pytest unit
3. `test-web` — Bun 1.3.4, typecheck, lint, tests
4. `test-bank-advisor` — pytest regression
5. `test-file-manager` — pytest smoke+unit+regression
6. `test-regression` — MongoDB 7.0 + Redis 7 como services
7. `test-backend-integration-smoke` — auth flow tests
8. `test-web-e2e-smoke` — Playwright chromium
9. `no-changes` — informativo
10. `ci-gate` — required status check, evalúa todos los results

**Secrets usados:** Ninguno (solo tests).
**Environments:** Ninguno.
**Separación de tenant:** Ninguna.
**Concurrency:** `cancel-in-progress: true` (cancela runs previos).

### 1.2 CD Pipeline (`cd.yml`)

**Triggers:**
- Push a `main`
- Tags `v*`
- `workflow_dispatch` con inputs: `services`, `deploy` (bool), `no_cache` (bool), `run_smoke_tests` (bool), `rollback_version`

**Jobs (9):**
1. `detect-changes` — misma lógica de CI + version auto-increment + `should_deploy` flag
2. `security` — Trivy filesystem scan (CRITICAL, HIGH) → SARIF upload
3. `build` — matrix por servicio, Docker Buildx, push a Docker Hub
4. `update-compose` — actualiza `docker-compose.images.yml` con nueva versión
5. `backup` — MongoDB dump pre-deploy
6. `deploy` — SSH a producción, `docker compose up -d --force-recreate`
7. `smoke-tests` — health checks post-deploy via SSH
8. `rollback` — manual, restaura versión anterior
9. `no-changes` — informativo

**Secrets usados (7):**

| Secret | Scope | Propósito |
|--------|-------|-----------|
| `DOCKERHUB_USERNAME` | Repo | Registry auth |
| `DOCKERHUB_TOKEN` | Repo | Registry auth |
| `PAT_PUSH_MAIN` | Repo | Push commits a main |
| `PROD_HOST` | Repo (debería ser per-env) | IP del servidor |
| `PROD_USER` | Repo (debería ser per-env) | Usuario SSH |
| `PROD_SSH_KEY` | Repo (debería ser per-env) | Llave privada SSH |
| `PROD_PATH` | Repo (debería ser per-env) | Path de deploy |

**GitHub Environments:** Solo `production` (sin variables, solo para approval gates).

**Deploy decision logic:**
```bash
SHOULD_DEPLOY=$([[ "${{ github.event.inputs.deploy }}" == "true" ||
                   "$IS_RELEASE" == "true" ||
                   "$GITHUB_REF" == "refs/heads/main" ]] && echo "true" || echo "false")
```

**Concurrency:** `cancel-in-progress: false` (no cancela deploys en progreso).

**Hallazgo clave:** No hay forma de elegir A DÓNDE se despliega. Todo va al mismo `PROD_HOST`.

### 1.3 Valores Hardcodeados en Workflows

| Valor | Ubicación | Impacto |
|-------|-----------|---------|
| Python 3.11 | CI/CD | Bajo — versión correcta |
| Bun 1.3.4 | CI/CD | Bajo — versión correcta |
| `saptivaai/octavios-invex-*` | CD build/push | Medio — prefijo "invex" en nombre de imagen |
| `mongodb:7.0`, `redis:7-alpine` | CI services | Bajo |
| `http://localhost:8000/api/health` | CD smoke tests | Bajo — puertos internos |
| `github-actions[bot]` | CD update-compose | Bajo |
| `octavios-chat-bajaware_invex_backend_shared` | CD deploy | Bajo — nombre de volumen |

### 1.4 Reusable Workflows
**No existen.** CI y CD son standalone. Para multi-tenant, se beneficiarían de `workflow_call` para reusar lógica de deploy.

---

## 2. Scripts de Deploy

### 2.1 `scripts/deploy/build.sh`
- Docker Hub user: `saptivaai` (hardcoded)
- Project prefix: `octavios-invex` (hardcoded)
- Image tag: `saptivaai/octavios-invex-<service>:<version>`
- Build targets: backend→`production`, web→`runner`
- Tagging: `<version>`, `<version>-<DATETIME>`, `latest`

### 2.2 `scripts/deploy/push.sh`
- Docker Hub user: `saptivaai` (hardcoded)
- Login detection: `~/.docker/config.json` + `docker info`
- Retry: 3 intentos, 5s delay

### 2.3 `scripts/deploy/update-images.sh`
- Modifica `infra/docker-compose.images.yml` con `sed`
- Dashboard version track independiente (1.0.x vs 1.4.x)
- Backup automático del archivo antes de editar

### 2.4 `scripts/deploy/validate-deploy.sh`
- **INCONSISTENCIA:** Registry user `jazielflores1998` (debería ser `saptivaai`)
- Valida: SECRET_KEY, JWT_SECRET_KEY, Docker Hub images, git status, SSH

### 2.5 `scripts/deploy/detect-changes.sh`
- Service-to-path mapping: backend→`apps/backend`, web→`apps/web`, etc.
- Shared paths (trigger all): `infra/`, `docker-compose`, `.env`, `Makefile`
- Output: JSON + GitHub Actions outputs

---

## 3. Configuración de Infraestructura

### 3.1 Docker Compose Files

| Archivo | Propósito | Líneas |
|---------|-----------|--------|
| `infra/docker-compose.yml` | Base — todos los servicios | 661 |
| `infra/docker-compose.dev.yml` | Dev — hot reload, bind mounts | 106 |
| `infra/docker-compose.production.yml` | Prod — no debug, rate limits, no volumes | ~50 |
| `infra/docker-compose.images.yml` | Versiones pinned (v1.4.53, dashboard v1.0.25) | 395 |
| `infra/docker-compose.registry.yml` | Legacy registry (deprecated) | 31 |
| `infra/docker-compose.production-postgres.yml` | GCP PostgreSQL override | 31 |
| `infra/docker-compose.tidewave.yml` | Testing aislado con Playwright MCP | 124 |

**Composición:**
```
Development:  base + dev
Production:   base + production + images
Registry:     base + production + registry (deprecated)
```

### 3.2 Makefile — ENV support (ya existe)

```makefile
ENV ?=
ENV_CANDIDATE := $(if $(ENV),envs/.env.$(ENV),envs/.env)
ENV_FILE := $(if $(wildcard $(ENV_CANDIDATE)),$(ENV_CANDIDATE),envs/.env)

COMPOSE_PROD_CMD = $(COMPOSE_CMD) -f $(COMPOSE_PROD) $(if $(filter 1,$(REGISTRY)),-f $(COMPOSE_REGISTRY),)
```

Esto permite: `make prod ENV=invex` → usa `envs/.env.invex`.

### 3.3 NGINX Configs

| Archivo | Dominio | SSL | Estado |
|---------|---------|-----|--------|
| `infra/nginx/nginx.bankadvisor.conf` | `bankadvisor.saptiva.com` + `back-bankadvisor.saptiva.com` | Let's Encrypt | Activo en prod |
| `infra/nginx/nginx.conf` | `${PROD_SERVER_IP}` (IP GCP) | No | Legacy |
| `infra/nginx/dev.conf` | `_` (wildcard) | No | Solo dev |

**Hallazgo:** `nginx.bankadvisor.conf` hardcodea:
- `server_name bankadvisor.saptiva.com;`
- `server_name back-bankadvisor.saptiva.com;`
- `ssl_certificate /etc/letsencrypt/live/back-bankadvisor.saptiva.com/fullchain.pem;`
- Rate limiting: `10r/s` API, `30r/s` web
- Security headers: HSTS, X-Frame-Options, etc.

No hay `envsubst` ni templating. Para `invex.saptiva.com` se necesita una config separada.

### 3.4 Environment Files

| Archivo | Existe | Committed |
|---------|--------|-----------|
| `envs/.env.example` | Si | Si |
| `envs/.env.production.example` | Si | Si |
| `envs/.env.development.example` | Si | Si |
| `envs/.env.secrets.example` | Si | Si |
| `envs/.env` | Si (gitignored) | No |
| `envs/.env.invex` | **NO** | — |
| `envs/.env.demo` | **NO** | — |

---

## 4. Frontend — Hallazgos de Tenant/Config

### 4.1 Dominios Hardcodeados

**`apps/web/next.config.js` — allowedOrigins:**
```javascript
allowedOrigins: [
  'localhost:3000',
  '127.0.0.1:3000',
  '*.localhost:3000',
  'invex.saptiva.com',        // ← HARDCODED
  'back-invex.saptiva.com',    // ← HARDCODED
  '*.saptiva.com',             // ← Wildcard (cubre demo + invex)
],
```

### 4.2 Feature Flags (bien diseñados)

**`apps/web/src/lib/feature-flags.ts`:**
```typescript
export const featureFlags = {
  webSearch: toBool(process.env.NEXT_PUBLIC_FEATURE_WEB_SEARCH, false),
  deepResearch: toBool(process.env.NEXT_PUBLIC_FEATURE_DEEP_RESEARCH, false),
  bankAdvisor: toBool(process.env.NEXT_PUBLIC_FEATURE_BANK_ADVISOR, false),
  mic: toBool(process.env.NEXT_PUBLIC_FEATURE_MIC, false),
  // ... 12 flags total
};
```

### 4.3 Branding Saptiva

- **Tailwind config:** Colores `saptiva.mint`, `saptiva.blue`, etc.
- **Font:** IBM Plex Sans (Saptiva Lab token system)
- **Metadata:** `title: "Saptiva OctaviOS Chat"`, icon: `/saptiva_ai_logo.jpg`
- **Logos en public/:** OctaviOS, Saptiva, Bajaware (INVEX partner) — todos mezclados
- **Build arg:** `NEXT_PUBLIC_APP_NAME="Saptiva Copilot OS"` (baked en imagen)

### 4.4 API Client

**`apps/web/src/lib/api-client.ts`:**
- Server-side default: `http://localhost:8000`
- Client-side: empty string (usa proxy Next.js)
- Configurable via `NEXT_PUBLIC_API_URL`

### 4.5 Sin Tenant Resolution

- **No hay** subdomain-based routing
- **No hay** `TenantProvider` o context
- **No hay** middleware de tenant en `middleware.ts` (solo auth + redirect)
- Toda la app asume single-tenant

---

## 5. Backend — Hallazgos de Tenant/Config

### 5.1 Settings (Pydantic BaseSettings)

**`apps/backend/src/core/config.py`:**
- `app_name: str = Field(default="Copilot OS API")`
- `saptiva_api_base_url: str = Field(default="https://api.saptiva.com")`
- `mail_from_email: str = Field(default="support@saptiva.com")`
- `mail_from_name: str = Field(default="Octavios Support")`
- `password_reset_base_url: str = Field(default="http://localhost:3000")`
- `chat_default_model: str = Field(default="Saptiva Turbo")`
- `CORS_ORIGINS` cargado de env var (bien)

### 5.2 Bank-Advisor Profile System (ya existente)

**`plugins/bank-advisor-private/config/bankadvisor.yaml`:**
```yaml
active_profile: "invex"           # ← Seleccionable via BANKADVISOR_PROFILE
banks:
  primary: ""                      # ← Vacío: triggers clarification
defaults:
  apply_bank_default: false        # ← Fix previo (DONE task)
```

**`plugins/bank-advisor-private/config/profiles/invex.yaml`:**
```yaml
profile:
  name: "INVEX"
  version: "1.0.0"
banks:
  primary: ""                      # ← Vacío incluso en perfil INVEX
visualization:
  colors:
    primary: "#E45756"             # ← INVEX red
  branding:
    title_prefix: "INVEX"
tenant:
  locked: true                     # ← Tenant locked
  display_notice: "Mostrando datos de INVEX (cambiar banco)"
```

**`plugins/bank-advisor-private/config/profiles/template.yaml`:**
```yaml
profile:
  name: "<CLIENT_NAME>"
  version: "1.0.0"
tenant:
  locked: false                    # ← Multi-tenant por default
```

### 5.3 Bank Rules

**`plugins/bank-advisor-private/src/bankadvisor/config/bank_rules.py`:**
- `FEATURED_BANKS = ["INVEX"]` — solo INVEX marcado como featured
- `MAJOR_BANKS = [BBVA, BANORTE, SANTANDER, CITIBANAMEX, HSBC, SCOTIABANK, INBURSA]`

### 5.4 Sin Middleware de Tenant

- No hay `X-Tenant-ID` header handling
- No hay domain-based resolution
- Single MongoDB per deployment
- Single Redis per deployment (no namespace)

---

## 6. Docker Images

**Registry:** `docker.io/saptivaai`

**Naming actual:**
```
saptivaai/octavios-invex-backend:1.4.53
saptivaai/octavios-invex-web:1.4.53
saptivaai/octavios-invex-bank-advisor:1.4.53
saptivaai/octavios-invex-file-manager:1.4.53
saptivaai/octavios-invex-dashboard:1.0.25
```

**Problema:** El prefijo `invex` en el nombre de imagen es cosmético pero confuso para despliegues multi-tenant. Las mismas imágenes sirven para demo e invex (el tenant se configura via env vars, no via código diferente).

---

## 7. Resumen de Hallazgos por Categoría

### Deploy-Time Config (requiere rebuild/redeploy)

| Variable | Estado | Problema |
|----------|--------|----------|
| `PROD_HOST` | 1 valor para todo | Necesita ser per-environment |
| `PROD_SSH_KEY` | 1 valor para todo | Necesita ser per-environment |
| `NGINX config` | Hardcoded | Necesita config por tenant |
| `NEXT_PUBLIC_APP_NAME` | Baked en build | Necesita ser build arg |
| `allowedOrigins` | Hardcoded | Necesita env var |

### Runtime Config (editable sin redeploy)

| Variable | Estado | Problema |
|----------|--------|----------|
| `BANKADVISOR_PROFILE` | Soportado | Falta `demo.yaml` |
| Feature flags | Soportados via env | Sin separación por tenant |
| Branding (colores) | En tailwind config | No es dinámico |
| `FEATURED_BANKS` | Hardcoded `["INVEX"]` | Debería venir del perfil |
| `CORS_ORIGINS` | Env var | OK — configurar por deploy |

### Anti-Patterns Confirmados

1. **Single deployment target** — blocker para multi-tenant
2. **NGINX sin templating** — requiere duplicación manual
3. **Docker image naming** — confuso pero no blocker
4. **Registry user inconsistente** — `jazielflores1998` en validate-deploy.sh
5. **No staging environment** — deploy directo a prod
6. **Branding acoplado a código** — colores/logos en Tailwind/public

---

## 8. Conclusiones

### Lo que existe y se puede reusar (80% del trabajo)
- Makefile con `ENV=` selector
- Bank-advisor profile system (YAML)
- Feature flags frontend (`NEXT_PUBLIC_FEATURE_*`)
- Docker compose overlay pattern
- `template.yaml` para nuevos clientes

### Lo que falta (20% — la parte de infra/CI)
- GitHub Environments con secrets per-target
- Matrix strategy en CD workflow
- `demo.yaml` profile
- NGINX config para `invex.saptiva.com`
- Env file templates por tenant
- Smoke tests que validen tenant identity

### Precedente
Task `2025-12-04__TASK__invex-generalization-multi-tenant` (DONE) eliminó hardcodes de INVEX en código. Este task completa el ciclo separando la capa de **deployment**.

---

## 9. Referencias

- `.github/workflows/ci.yml` — CI pipeline
- `.github/workflows/cd.yml` — CD pipeline
- `scripts/deploy/build.sh` — Docker build script
- `scripts/deploy/push.sh` — Docker push script
- `scripts/deploy/validate-deploy.sh` — Pre-deploy validation
- `infra/nginx/nginx.bankadvisor.conf` — Production NGINX
- `apps/web/next.config.js` — Next.js config (allowedOrigins)
- `apps/web/src/lib/feature-flags.ts` — Feature flags
- `plugins/bank-advisor-private/config/bankadvisor.yaml` — BA config
- `plugins/bank-advisor-private/config/profiles/invex.yaml` — INVEX profile
- `plugins/bank-advisor-private/config/profiles/template.yaml` — Client template
- `apps/backend/src/core/config.py` — Backend settings
- `envs/.env.example` — Dev env template
- `envs/.env.production.example` — Prod env template
