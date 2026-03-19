---
id: SEC-2026-01-28__nextjs-15-upgrade-cve
title: Upgrade Next.js 15 - CVE-2025-59471
status: DONE
phase: Validate
priority: medium
scope_in:
  - Actualizar Next.js de 14.x a 15.5.10+
  - 'Migrar APIs de request a async (params, searchParams, headers, cookies)'
  - Actualizar React 18 a React 19
  - Revisar cambios de caching por defecto
  - Actualizar configuracion de next/image si aplica
scope_out:
  - Refactors no relacionados con la migracion
  - Nuevas funcionalidades
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - cd apps/web && pnpm build
  - cd apps/web && pnpm test
  - cd apps/web && pnpm lint
  - make test T=e2e
pr_files:
  - apps/web/package.json
  - apps/web/next.config.js
  - 'apps/web/src/app/chat/[chatId]/page.tsx'
  - 'apps/web/src/app/api/reports/audit/[reportId]/download/route.ts'
  - apps/web/src/app/error.tsx
  - apps/web/src/components/chat/ChatShell.tsx
  - apps/web/src/lib/streaming.ts
test_status: PASS (780/780 unit tests)
---

# Resumen

**Objetivo**: Resolver vulnerabilidad de seguridad CVE-2025-59471 actualizando Next.js a version 15.5.10 o superior.

**Severidad**: Media (DoS via Image Optimizer)

**Constraint**: Requiere actualizacion mayor (14 -> 15) con breaking changes significativos.

---

# Detalles de la Vulnerabilidad

| Campo | Valor |
|-------|-------|
| **CVE** | CVE-2025-59471 |
| **GHSA** | GHSA-9g9p-9gw9-jx7f |
| **Severidad** | Media |
| **Paquete** | next |
| **Version actual** | ^14.2.35 |
| **Version parcheada** | 15.5.10 |
| **Manifest** | pnpm-lock.yaml |

**Descripcion**: Aplicaciones Next.js self-hosted son vulnerables a DoS via configuracion de remotePatterns en Image Optimizer.

**Rango vulnerable**: `>= 10.0.0, < 15.5.10`

---

# Breaking Changes en Next.js 15

## 1. React 19 Requerido
- Next.js 15 requiere React 19
- Revisar compatibilidad de dependencias con React 19

## 2. APIs de Request Asincronas
Las siguientes APIs ahora son `async` y requieren `await`:
- `params` en layouts/pages dinamicos
- `searchParams` en pages
- `headers()`
- `cookies()`

**Ejemplo de migracion**:
```tsx
// Antes (Next.js 14)
export default function Page({ params }: { params: { id: string } }) {
  return <div>{params.id}</div>
}

// Despues (Next.js 15)
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <div>{id}</div>
}
```

## 3. Cambios de Caching
- `fetch()` ya no cachea por defecto
- Revisar estrategia de caching de la aplicacion

## 4. next/image
- Removido `squoosh`, ahora usa `sharp`
- Verificar configuracion de imagenes remotas

---

# Archivos Potencialmente Afectados

Buscar uso de:
- `cookies()` y `headers()` - convertir a async/await
- Paginas con `params` dinamicos
- Uso de `searchParams`
- Configuracion de `next.config.js`

---

# Referencias

- [GitHub Advisory GHSA-9g9p-9gw9-jx7f](https://github.com/advisories/GHSA-9g9p-9gw9-jx7f)
- [Next.js 15 Upgrade Guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)
- [Dependabot Alert #36](../../..)

---

# Actualizaciones

- 2026-01-28 18:30 - Creado desde reporte de Dependabot.
- 2026-01-30 - Research completado. Solo 2 archivos requieren migracion de params async.
- 2026-01-30 - Implementacion completada. Build y tests pasan. CVE resuelto con next@15.5.11.
