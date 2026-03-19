# Plan: Separación de Despliegues por Entorno/Tenant

## Objective
Habilitar despliegues independientes por tenant (demo vs invex) desde un solo pipeline de GitHub Actions, separando claramente la dimensión de environment (dev/staging/prod) de la dimensión de tenant (demo/invex/futuro-cliente).

## Scope
### In
- GitHub Environments con secrets per-tenant
- CD workflow con matrix de deploy targets
- Perfil `demo.yaml` para bank-advisor
- Parametrización de NGINX y Next.js
- Env file templates por tenant
- Smoke tests por tenant
- Checklist de validación anti-mezcla

### Out
- Tenant resolution dinámico por dominio (Fase 3 futura)
- API `/api/tenant/config` runtime (Fase 4 futura)
- Renombrar Docker images (cosmético, alto costo)
- Multi-tenancy a nivel DB
- Kubernetes / IaC

## Phases

### Phase 1: GitHub Environments + Secrets per-Tenant (1-2 días)
**Impacto:** Alto | **Riesgo:** Bajo

- [ ] Crear GitHub Environment `production-demo` con secrets del servidor actual
- [ ] Crear GitHub Environment `production-invex` con secrets del nuevo servidor
- [ ] Agregar variables de environment (no-secret):
  - `DEPLOYMENT_PROFILE` = `demo` | `invex`
  - `PUBLIC_BASE_URL` = URL pública del frontend
  - `PUBLIC_API_URL` = URL pública del API
  - `TENANT_DOMAIN` = dominio principal
  - `NGINX_CONFIG` = nombre del archivo NGINX a usar
- [ ] Modificar `cd.yml`:
  - Agregar input `deploy_targets` (default: `"all"`, opciones: `demo`, `invex`, `all`)
  - Agregar step `Resolve deploy targets` que genera JSON array
  - Cambiar job `deploy` a usar `matrix.target` con `environment: production-${{ matrix.target }}`
  - Cada step de deploy usa `secrets.PROD_HOST` (resuelto por environment)
- [ ] Mover secrets actuales (`PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY`, `PROD_PATH`) de repo-level a environment-level
- [ ] Mantener `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `PAT_PUSH_MAIN` a nivel de repo (compartidos)

#### Phase 1 Files
- `.github/workflows/cd.yml`

#### Phase 1 — Estructura de Secrets

```
Repository Secrets (compartidos):
├── DOCKERHUB_USERNAME
├── DOCKERHUB_TOKEN
└── PAT_PUSH_MAIN

GitHub Environment: production-demo
├── Secrets:
│   ├── PROD_HOST          = <IP servidor demo>
│   ├── PROD_USER          = <usuario SSH>
│   ├── PROD_SSH_KEY       = <key SSH>
│   └── PROD_PATH          = /opt/octavios-demo
└── Variables:
    ├── DEPLOYMENT_PROFILE = demo
    ├── PUBLIC_BASE_URL    = https://bankadvisor.saptiva.com
    ├── PUBLIC_API_URL     = https://back-bankadvisor.saptiva.com
    ├── TENANT_DOMAIN      = bankadvisor.saptiva.com
    └── NGINX_CONFIG       = nginx.bankadvisor.conf

GitHub Environment: production-invex
├── Secrets:
│   ├── PROD_HOST          = <IP servidor invex>
│   ├── PROD_USER          = <usuario SSH>
│   ├── PROD_SSH_KEY       = <key SSH>
│   └── PROD_PATH          = /opt/octavios-invex
└── Variables:
    ├── DEPLOYMENT_PROFILE = invex
    ├── PUBLIC_BASE_URL    = https://invex.saptiva.com
    ├── PUBLIC_API_URL     = https://back-invex.saptiva.com
    ├── TENANT_DOMAIN      = invex.saptiva.com
    └── NGINX_CONFIG       = nginx.invex.conf
```

#### Phase 1 — CD Workflow Changes (pseudo-YAML)

```yaml
on:
  workflow_dispatch:
    inputs:
      deploy_targets:
        description: 'Deploy targets (demo,invex or all)'
        default: 'all'
        type: string
      # ... inputs existentes ...

jobs:
  detect-changes:
    steps:
      - name: Resolve deploy targets
        id: targets
        run: |
          INPUT="${{ github.event.inputs.deploy_targets }}"
          if [[ "$INPUT" == "all" || -z "$INPUT" ]]; then
            echo 'deploy_targets=["demo","invex"]' >> $GITHUB_OUTPUT
          else
            TARGETS=$(echo "$INPUT" | jq -R 'split(",") | map(gsub("\\s";""))')
            echo "deploy_targets=$TARGETS" >> $GITHUB_OUTPUT
          fi

  deploy:
    needs: [build, backup]
    strategy:
      fail-fast: false
      matrix:
        target: ${{ fromJson(needs.detect-changes.outputs.deploy_targets) }}
    environment: production-${{ matrix.target }}
    steps:
      - name: Deploy to ${{ matrix.target }}
        env:
          DEPLOYMENT_PROFILE: ${{ vars.DEPLOYMENT_PROFILE }}
        run: |
          ssh ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} << 'DEPLOY_EOF'
            cd ${{ secrets.PROD_PATH }}
            git pull origin main
            # Inyectar perfil de tenant en env
            sed -i 's/^BANKADVISOR_PROFILE=.*/BANKADVISOR_PROFILE=${{ vars.DEPLOYMENT_PROFILE }}/' envs/.env
            docker compose -f infra/docker-compose.yml \
              -f infra/docker-compose.images.yml \
              -f infra/docker-compose.production.yml \
              --env-file envs/.env \
              up -d --force-recreate $SERVICES
          DEPLOY_EOF

  smoke-tests:
    needs: [deploy]
    strategy:
      matrix:
        target: ${{ fromJson(needs.detect-changes.outputs.deploy_targets) }}
    environment: production-${{ matrix.target }}
    steps:
      - name: Verify tenant identity
        run: |
          ssh ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} << 'EOF'
            # Health check
            curl -sf http://localhost:8000/api/health | jq .status
            # Verify BANKADVISOR_PROFILE matches expected
            docker exec backend printenv BANKADVISOR_PROFILE
          EOF
```

---

### Phase 2: Perfil demo.yaml + Parametrizar NGINX y Next.js (2-3 días)
**Impacto:** Alto | **Riesgo:** Medio

- [ ] Crear `plugins/bank-advisor-private/config/profiles/demo.yaml`:
  ```yaml
  profile:
    name: "DEMO"
    version: "1.0.0"
    description: "Configuration for general demo / multi-bank analytics"
  banks:
    primary: ""  # No default bank — triggers clarification
    aggregates: ["SISTEMA", "SECTOR", "MERCADO"]
  defaults:
    apply_bank_default: false
  visualization:
    colors:
      primary: "#2DD4BF"  # Saptiva mint (neutral branding)
    branding:
      title_prefix: "OctaviOS"
      logo_url: null
  tenant:
    locked: false  # Multi-bank mode — no lock
  ```
- [ ] Crear `infra/nginx/nginx.invex.conf` (copia de bankadvisor.conf con dominios cambiados):
  - `server_name invex.saptiva.com;`
  - `server_name back-invex.saptiva.com;`
  - SSL cert paths para `invex.saptiva.com`
- [ ] Parametrizar `apps/web/next.config.js` allowedOrigins:
  ```javascript
  const extraOrigins = (process.env.ALLOWED_ORIGINS || '').split(',').filter(Boolean);
  allowedOrigins: [
    'localhost:3000',
    '127.0.0.1:3000',
    '*.localhost:3000',
    '*.saptiva.com',
    ...extraOrigins,
  ],
  ```
- [ ] Crear `envs/.env.invex.example` con variables específicas:
  ```bash
  BANKADVISOR_PROFILE=invex
  CORS_ORIGINS=["https://invex.saptiva.com"]
  ALLOWED_HOSTS=["invex.saptiva.com","back-invex.saptiva.com"]
  PASSWORD_RESET_URL=https://invex.saptiva.com
  MAIL_FROM_NAME=INVEX Analytics
  ```
- [ ] Crear `envs/.env.demo.example` con variables demo:
  ```bash
  BANKADVISOR_PROFILE=demo
  CORS_ORIGINS=["https://bankadvisor.saptiva.com"]
  ALLOWED_HOSTS=["bankadvisor.saptiva.com","back-bankadvisor.saptiva.com"]
  PASSWORD_RESET_URL=https://bankadvisor.saptiva.com
  MAIL_FROM_NAME=OctaviOS Support
  ```
- [ ] Fix: Unificar registry user en `scripts/deploy/validate-deploy.sh` (cambiar `jazielflores1998` → `saptivaai`)

#### Phase 2 Files
- `plugins/bank-advisor-private/config/profiles/demo.yaml`
- `infra/nginx/nginx.invex.conf`
- `apps/web/next.config.js`
- `envs/.env.invex.example`
- `envs/.env.demo.example`
- `scripts/deploy/validate-deploy.sh`

---

### Phase 3: Host-Based Tenant Resolution (3-5 días) — FUTURO
**Impacto:** Medio-Alto | **Riesgo:** Medio

> **Nota:** Esta fase se ejecuta cuando haya 3+ clientes o cuando se necesite
> branding dinámico sin rebuild.

- [ ] Crear `apps/web/src/lib/tenant-config.ts` con resolución por hostname
- [ ] Crear `TenantProvider` React context
- [ ] Backend: header `X-Tenant-ID` o resolución por `Origin`
- [ ] Conectar bank-advisor `active_profile` con tenant ID

#### Phase 3 Files
- `apps/web/src/lib/tenant-config.ts`
- `apps/web/src/providers/TenantProvider.tsx`
- `apps/backend/src/middleware/tenant.py`

---

### Phase 4: Runtime Config por Tenant (5-8 días) — FUTURO
**Impacto:** Medio | **Riesgo:** Medio-Alto

> **Nota:** Esta fase se ejecuta cuando se necesiten cambios de config sin redeploy.

- [ ] Endpoint `GET /api/tenant/config` que devuelve config dinámica
- [ ] Fuente inicial: YAML profiles existentes
- [ ] Frontend consume al cargar, cachea en sessionStorage
- [ ] Migración gradual a MongoDB/Redis para edición en caliente

#### Phase 4 Files
- `apps/backend/src/routers/tenant.py`
- `apps/backend/src/services/tenant_config_service.py`

---

## Deploy-Time vs Runtime — Tabla de Decisión

| Config | Deploy-Time | Runtime | Justificación |
|--------|:-----------:|:-------:|---------------|
| `PROD_HOST`, SSH keys | X | | Infra, seguridad |
| `DEPLOYMENT_PROFILE` | X | | Identifica el tenant |
| `PUBLIC_BASE_URL` | X | | URL pública (DNS) |
| `CORS_ORIGINS` | X | | Seguridad web |
| `JWT_SECRET_KEY` | X | | Criptografía |
| Banco default | | X | Config de negocio |
| Branding (colores, logo) | | X | UX per-client |
| Feature flags | | X | Toggles de producto |
| Prompts/system messages | | X | NLP behavior |
| `FEATURED_BANKS` | | X | Config de negocio |

---

## Convenciones de Nombres

### Workflows
```
ci.yml                    # (sin cambio)
cd.yml                    # (agregar matrix + environments)
```

### GitHub Environments
```
production-demo           # bankadvisor.saptiva.com
production-invex          # invex.saptiva.com
staging-demo              # (futuro)
staging-invex             # (futuro)
```

### Secrets Pattern
```
PROD_HOST                 # Per-environment (sin sufijo de tenant)
PROD_USER                 # Per-environment
DEPLOYMENT_PROFILE        # Variable (no secret), per-environment
PUBLIC_BASE_URL            # Variable (no secret), per-environment
```

### Env Files
```
envs/.env                 # Base / desarrollo local
envs/.env.demo            # Producción demo (gitignored)
envs/.env.invex           # Producción invex (gitignored)
envs/.env.demo.example    # Template demo (committed)
envs/.env.invex.example   # Template invex (committed)
```

### Bank-Advisor Profiles
```
config/profiles/
├── demo.yaml             # Demo general (multi-banco, neutral)
├── invex.yaml            # INVEX (tenant locked, branding rojo)
├── template.yaml         # Template para nuevos clientes
└── <cliente>.yaml        # Futuro: bbva.yaml, banorte.yaml, etc.
```

---

## Validation Commands

```bash
# Phase 1 — Verificar environments configurados
gh api repos/{owner}/{repo}/environments | jq '.environments[].name'

# Phase 1 — Verificar workflow acepta deploy_targets
grep deploy_targets .github/workflows/cd.yml

# Phase 2 — Verificar demo.yaml existe
cat plugins/bank-advisor-private/config/profiles/demo.yaml

# Phase 2 — Verificar NGINX invex config
grep server_name infra/nginx/nginx.invex.conf

# Phase 2 — Verificar allowedOrigins parametrizado
grep ALLOWED_ORIGINS apps/web/next.config.js

# Phase 2 — Verificar registry user unificado
grep -r jazielflores scripts/deploy/ # debería devolver 0 resultados

# Post-deploy — Verificar tenant identity
ssh $PROD_USER@$PROD_HOST "docker exec backend printenv BANKADVISOR_PROFILE"
```

## Success Criteria

### Phase 1
- [ ] `workflow_dispatch` de CD acepta `deploy_targets` input
- [ ] Deploy a `production-demo` usa secrets de ese environment
- [ ] Deploy a `production-invex` usa secrets de ese environment
- [ ] `deploy_targets=all` despliega a ambos en paralelo (matrix)
- [ ] `deploy_targets=invex` despliega solo a invex
- [ ] Smoke tests verifican tenant identity post-deploy

### Phase 2
- [ ] `demo.yaml` existe y bank-advisor lo carga con `BANKADVISOR_PROFILE=demo`
- [ ] `nginx.invex.conf` existe con dominios `invex.saptiva.com`
- [ ] `next.config.js` acepta `ALLOWED_ORIGINS` env var
- [ ] `validate-deploy.sh` usa `saptivaai` (no `jazielflores1998`)
- [ ] Templates de env existen: `.env.demo.example`, `.env.invex.example`

### General
- [ ] No hay mezcla de secrets entre environments
- [ ] Deploy a un tenant no afecta al otro
- [ ] Rollback funciona per-tenant
- [ ] Documentación de convenciones actualizada

---

## Checklist de Validación Anti-Mezcla de Tenants

### Pre-Deploy
- [ ] GitHub Environment correcto seleccionado en workflow dispatch
- [ ] `DEPLOYMENT_PROFILE` matchea target (demo ≠ invex)
- [ ] `PROD_HOST` apunta al servidor correcto para ese tenant
- [ ] `envs/.env` en servidor tiene `CORS_ORIGINS` para el dominio correcto
- [ ] `BANKADVISOR_PROFILE` en `.env` matchea el perfil YAML

### Post-Deploy
- [ ] `curl https://<TENANT_DOMAIN>/api/health` → `status: healthy`
- [ ] NGINX `server_name` matchea el dominio esperado
- [ ] `docker exec backend printenv BANKADVISOR_PROFILE` → tenant correcto
- [ ] Query "ranking de bancos" → NO defaultea a banco específico en demo
- [ ] Query "mi cartera" en invex → usa perfil INVEX (si tenant.locked)
- [ ] Redis flush completado (no hay cache cruzada)
- [ ] Logs no muestran errores de CORS

### Smoke Test Automatizado (integrar en cd.yml)
- [ ] `GET /api/health` → JSON con status healthy
- [ ] `GET /` → HTTP 200 o 307
- [ ] `POST /api/chat` → no error de CORS
- [ ] `docker exec backend printenv BANKADVISOR_PROFILE` == `$DEPLOYMENT_PROFILE`
