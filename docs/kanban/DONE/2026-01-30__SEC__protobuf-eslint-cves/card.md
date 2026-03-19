---
id: "SEC-2026-01-30__protobuf-eslint-cves"
title: "Fix CVE-2026-0994 (protobuf) and CVE-2025-50537 (eslint)"
status: "DONE"
phase: "Validate"
priority: "high"
scope_in:
  - "Actualizar protobuf en backend"
  - "Actualizar eslint en web y shared"
  - "Remover saptiva-agents (bloqueaba protobuf upgrade)"
scope_out:
  - "Cambios no relacionados con seguridad"
artifacts:
  card: card.md
plan_phase: 1
validation_commands:
  - "cd apps/backend && uv pip list | grep protobuf"
  - "cd apps/web && bun pm ls eslint"
  - "gh api repos/saptiva-ai/octavios-chat-bajaware_invex/dependabot/alerts?state=open"
pr_files:
  - "apps/backend/requirements.txt"
  - "apps/backend/requirements-runtime.txt"
  - "apps/backend/pyproject.toml"
  - "apps/backend/uv.lock"
  - "apps/web/package.json"
  - "packages/shared/package.json"
  - "bun.lock"
test_status: "PASS - CI green, 0 Dependabot alerts"
---

# Resumen

**Objetivo**: Resolver 2 CVEs pendientes en Dependabot.

**Resultado**: ✅ Completado - Todas las vulnerabilidades resueltas.

---

# Vulnerabilidades Resueltas

## CVE-2026-0994 (HIGH) - protobuf

| Campo | Valor |
|-------|-------|
| **Package** | protobuf |
| **Severity** | High |
| **Issue** | JSON recursion depth bypass |
| **Version** | 5.29.x → 6.33.5 |
| **Status** | ✅ Fixed |

**Solución**: Removimos `saptiva-agents` (que bloqueaba upgrade) ya que PDF extraction ahora usa file-manager gRPC.

## CVE-2025-50537 (MEDIUM) - eslint

| Campo | Valor |
|-------|-------|
| **Package** | eslint |
| **Severity** | Medium |
| **Issue** | Stack Overflow with circular references |
| **Version** | 8.x → 9.39.2 |
| **Status** | ✅ Fixed |

---

# Commits

- `45961663` - fix(security): resolve CVE-2026-0994 and CVE-2025-50537
- `6ba04044` - fix(backend): remove saptiva-agents, upgrade protobuf to 6.33.5

---

# Actualizaciones

- 2026-01-30 - Creado desde Dependabot alerts.
- 2026-01-30 - eslint actualizado a 9.39.2.
- 2026-01-30 - protobuf bloqueado por autogen-core (saptiva-agents dep).
- 2026-01-30 - Removido saptiva-agents, protobuf actualizado a 6.33.5.
- 2026-01-30 - ✅ Completado. 0 alertas Dependabot abiertas.
