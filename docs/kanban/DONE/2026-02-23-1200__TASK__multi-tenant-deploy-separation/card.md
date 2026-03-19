---
id: "TASK-2026-02-23-1200__multi-tenant-deploy-separation"
title: "Separar despliegues por entorno/tenant en GitHub Actions (demo vs invex)"
status: "DONE"
phase: "Validate"
priority: "P1"
scope_in:
  - "Crear GitHub Environments (production-demo, production-invex) con secrets separados"
  - "Agregar deploy_targets input al workflow CD con matrix strategy"
  - "Crear perfil demo.yaml para bank-advisor (basado en template.yaml)"
  - "Parametrizar NGINX config y Next.js allowedOrigins"
  - "Crear envs/.env.invex template con BANKADVISOR_PROFILE=invex"
  - "Agregar smoke tests por tenant al pipeline CD"
  - "Documentar convenciones de nombres para environments, secrets y profiles"
scope_out:
  - "Tenant resolution dinámico por dominio en runtime (Fase 3 — futuro)"
  - "API endpoint /api/tenant/config con config runtime (Fase 4 — futuro)"
  - "Renombrar Docker images de octavios-invex-* a octavios-* (bajo impacto, alto costo)"
  - "Multi-tenancy a nivel de base de datos (row-level isolation)"
  - "BankSelector component en frontend (requiere cambios en estado de conversación)"
  - "Kubernetes / IaC migration"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "gh workflow view cd.yml"
  - "cat plugins/bank-advisor-private/config/profiles/demo.yaml"
  - "grep DEPLOYMENT_PROFILE .github/workflows/cd.yml"
  - "grep deploy_targets .github/workflows/cd.yml"
pr_files:
  - ".github/workflows/cd.yml"
  - "plugins/bank-advisor-private/config/profiles/demo.yaml"
  - "infra/nginx/nginx.invex.conf"
  - "apps/web/next.config.js"
  - "envs/.env.invex.example"
test_status: ""
related:
  - "2025-12-04__TASK__invex-generalization-multi-tenant (DONE — eliminó hardcodes de INVEX en código)"
---

# Summary

- **Objective:** Separar los despliegues por entorno técnico (dev/staging/prod) y por tenant/cliente (demo/invex) en GitHub Actions, usando GitHub Environments con secrets independientes y una matrix strategy en el workflow CD. Esto permite desplegar `bankadvisor.saptiva.com` (demo) e `invex.saptiva.com` (INVEX) de forma independiente desde el mismo pipeline.

- **Constraints:**
  - No sobre-ingeniar: profile-per-deployment (no multi-tenant-per-instance)
  - Reusar el sistema de perfiles YAML que ya existe en bank-advisor
  - `NEXT_PUBLIC_*` se bake en build-time — requiere parametrización de build args
  - NGINX configs actualmente hardcodeadas — requieren templating o duplicación
  - Mantener retrocompatibilidad total con el deploy actual de producción

# Contexto de Producto

| URL | Tipo | Propósito |
|-----|------|-----------|
| `bankadvisor.saptiva.com` | Demo general | Multicliente, demos de ventas, sin banco default |
| `invex.saptiva.com` | Tenant INVEX | Branding INVEX, tenant locked, features específicos |

# Modelo Conceptual

```
┌─────────────────────────────────────────────────┐
│              DIMENSIÓN ENVIRONMENT               │
│         (infra, secrets, servidores)             │
│   dev ──── staging ──── prod                     │
└─────────────────────────────────────────────────┘
                    ×
┌─────────────────────────────────────────────────┐
│               DIMENSIÓN TENANT                   │
│    (branding, banco default, features, data)     │
│   demo ──── invex ──── [futuro cliente]          │
└─────────────────────────────────────────────────┘
```

Combinaciones: `prod+demo`, `prod+invex`, `staging+demo`, etc.

# Diagnóstico Actual

## Estado de GitHub Actions
- **CI** (`ci.yml`): PR a main → tests → ci-gate. Sin deploy. OK.
- **CD** (`cd.yml`): Push a main/tags → build → deploy a **un solo servidor** via SSH.
- **Secrets**: `PROD_HOST`, `PROD_USER`, `PROD_SSH_KEY`, `PROD_PATH` — un solo target.
- **GitHub Environments**: No configurados.
- **Reusable workflows**: No existen.

## Anti-Patterns Detectados
1. **Single point of deployment** — solo 1 set de secrets, 1 servidor.
2. **Dominios hardcodeados en NGINX** — `bankadvisor.saptiva.com` en `nginx.bankadvisor.conf`.
3. **Dominios hardcodeados en Next.js** — `invex.saptiva.com` en `next.config.js:allowedOrigins`.
4. **`NEXT_PUBLIC_*` baked en build** — un build no puede servir 2 tenants con branding diferente.
5. **Docker images con prefijo "invex"** — `saptivaai/octavios-invex-backend:1.4.53`.
6. **CORS no parametrizado** — defaults hardcodeados en `config.py`.
7. **Inconsistencia en registry user** — `saptivaai` (build/push) vs `jazielflores1998` (validate-deploy).

## Lo que Ya Funciona Bien
- `Makefile` soporta `ENV=` para seleccionar env file (`envs/.env.$(ENV)`)
- Bank-advisor tiene sistema de perfiles YAML (`config/profiles/invex.yaml`, `template.yaml`)
- `active_profile` es configurable via `BANKADVISOR_PROFILE` env var
- Feature flags en frontend via `NEXT_PUBLIC_FEATURE_*`
- Docker compose overlay pattern (base + dev/prod)
- `apply_bank_default: false` ya es el default (fix previo)

# Archivos Clave Involucrados

| Archivo | Qué tiene hoy | Qué necesita |
|---------|---------------|--------------|
| `.github/workflows/cd.yml` | Deploy a 1 servidor | Matrix de targets + environments |
| `infra/nginx/nginx.bankadvisor.conf` | Dominio hardcodeado | Template o config por tenant |
| `apps/web/next.config.js` | `invex.saptiva.com` en allowedOrigins | Parametrizar via env var |
| `plugins/bank-advisor-private/config/profiles/` | Solo `invex.yaml` + `template.yaml` | Agregar `demo.yaml` |
| `envs/` | Solo `.env`, `.env.example`, `.env.production.example` | Agregar `.env.invex.example` |
| `scripts/deploy/validate-deploy.sh` | Registry user hardcodeado `jazielflores1998` | Unificar a `saptivaai` |

# Riesgos Principales

| Riesgo | Mitigación |
|--------|------------|
| Mezcla de datos entre tenants (MongoDB compartido) | Servidores separados (Fase 1) |
| Build web con branding incorrecto | Validar post-build, parametrizar build args (Fase 2) |
| NGINX apuntando al dominio equivocado | Checklist + smoke test por dominio |
| Deploy accidental al tenant equivocado | GitHub Environment protection rules |
| Feature flags inconsistentes | Config centralizada servida por API (Fase 4) |

# Updates
- 2026-02-23 12:00 - Creado. Research completa con análisis de 5 frentes (workflows, scripts, frontend, backend, infra).
- 2026-02-23 - Implementación completa. 4 archivos nuevos + 4 modificados. Pendiente: setup manual de GitHub Environments.
