---
id: "ISSUE-004-2026-01-08-1535-ux-frontend-conv-notfound"
title: "Fix 'Conversación no encontrada' flash on new conversation"
status: "DONE"
phase: "Complete"
priority: "P1"
scope_in:
  - "Fix UI flash/flicker when creating new conversation"
  - "Implement proper loading states in /chat/[id] route"
  - "Separate 'loading' from 'not found' states"
scope_out:
  - "Backend conversation creation changes"
  - "New conversation routing architecture"
  - "Animation/transition improvements (nice-to-have)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
  issue: issue.md
plan_phase: 0
validation_commands:
  - "make dev"
  - "Manual: Create new conversation, verify no 'not found' flash"
pr_files: []
test_status: ""
---

# Summary

**Bug:** Al crear una nueva conversación, la UI muestra brevemente (~100ms) la pantalla "Conversación no encontrada" antes de cargar el chat real. Es un flicker/glitch visual causado por un estado intermedio mal modelado donde `!conversation` se interpreta como "no existe" en lugar de "cargando".

**Impacto:**
- UX degradada: sensación de app "glitchy"
- Pérdida de confianza del usuario
- Riesgo de quedarse en 404 si hay latencia real

**Root Cause Hipótesis:**
1. Ruta temporal `temp-<uuid>` + render de NotFound por datos `null`
2. Race condition: GET ejecuta antes de que POST termine commit
3. Next.js App Router: uso agresivo de `notFound()` en page.tsx
4. React Query/SWR: cambio de query key causa `data=undefined` por 1 frame

**Solución Propuesta:** Modelar estados correctamente:
- `loading` → Skeleton/loader
- `notFound` → Solo cuando backend confirma 404 definitivo
- `creating` → Estado específico para provisioning

# Acceptance Criteria

- [ ] Al crear conversación, **nunca** aparece "Conversación no encontrada" en flujos normales
- [ ] Si el backend tarda, se ve un estado neutral (skeleton/loader), no error
- [ ] La transición conversación vieja → nueva es suave (no flash)

# Updates

- 2026-01-08 15:35 - Issue created with detailed analysis.
- 2026-01-08 - Card and plan created for tracking.
- 2026-01-08 - **Research completed.** Root cause identified:
  - `page.tsx:isValidChatId()` regex only accepts UUIDs, rejects `temp-*` IDs
  - `ConversationList.tsx:193` navigates to `/chat/temp-*` before UUID is ready
  - Missing `loading.tsx` in `/chat/[chatId]`
  - Fix: Modify regex to accept `temp-*` + add loading skeleton
- 2026-01-08 - **Phase 2 implemented:**
  - Modified `page.tsx:isValidChatId()` to accept `temp-*` IDs
  - Created `loading.tsx` with spinner skeleton
  - Lint passes ✅
- 2026-01-08 - **Docker infra fixed (bonus):**
  - Added `dev` stage to `apps/web/Dockerfile` with bun
  - Updated `docker-compose.dev.yml` to use bun instead of pnpm
  - Fixed volume permissions for `.next` cache
- 2026-01-08 - **Phase 3 validated:**
  - `/chat/temp-*` returns 200 ✅ (previously 404 flash)
  - `/chat/invalid` shows 404 page ✅
  - Docker web container working with hot-reload ✅
