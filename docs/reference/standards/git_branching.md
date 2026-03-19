# Estrategia de Branching: Feature de Cliente (Auditoría)

## Problema

Necesitamos mantener el feature de **auditoría de archivos** (COPILOTO_414) separado del código base principal, pero permitir que ambos evolucionen de forma independiente:

- `main`/`upstream`: Código base sin features de cliente
- `develop`: Desarrollo activo sin features de cliente
- `feature/audit-system`: Feature de auditoría que debe sincronizarse con develop

## Solución: Feature Branch Persistente

### Estructura de Branches

```
main (upstream) ← código limpio para clientes genéricos
  ↓
develop ← desarrollo activo sin features de cliente
  ↓
feature/audit-system ← feature de auditoría (branch de larga duración)
```

## Workflow Recomendado

### 1. Setup Inicial (Una sola vez)

```bash
# Crear feature branch desde el estado actual con auditoría
git checkout tool-auditor_archivos
git checkout -b feature/audit-system

# Etiquetar el punto donde se agregó la auditoría
git tag audit-system-base
```

### 2. Eliminar Auditoría de Develop

```bash
git checkout develop

# Identificar archivos del sistema de auditoría
# Backend:
git rm apps/api/src/services/*auditor*.py
git rm apps/api/src/services/validation_*.py
git rm apps/api/src/services/policy_*.py
git rm apps/api/src/services/tools/audit_file_tool.py
git rm apps/api/src/models/validation_report.py
git rm apps/api/src/schemas/audit_message.py
git rm apps/api/src/config/policies.yaml
git rm apps/api/src/config/compliance.yaml
git rm apps/api/tests/unit/test_*audit*.py
git rm apps/api/tests/unit/test_compliance*.py

# Frontend:
git rm -r apps/web/src/components/validation/
git rm -r apps/web/src/components/chat/Audit*.tsx
git rm -r apps/web/src/components/chat/MessageAuditCard.tsx
git rm apps/web/src/types/validation.ts
git rm apps/web/src/lib/stores/audit-store.ts
git rm apps/web/src/hooks/useAudit*.ts

# Docs:
git rm docs/copiloto-414/
git rm docs/AUDIT_SYSTEM_ARCHITECTURE.md

# Commit
git commit -m "refactor: remove audit system from base codebase

This feature is specific to a client and will be maintained
in feature/audit-system branch.

BREAKING CHANGE: Audit endpoints removed from main API"
```

### 3. Workflow de Desarrollo Normal

#### Cuando trabajas en develop (sin auditoría):

```bash
git checkout develop

# Hacer cambios normales
git add .
git commit -m "feat: agregar nueva funcionalidad"

# Push a develop
git push origin develop

# Merge a main cuando esté listo
git checkout main
git merge develop --no-ff
git push origin main
```

#### Cuando necesitas actualizar feature/audit-system con cambios de develop:

```bash
# 1. Actualizar develop
git checkout develop
git pull origin develop

# 2. Ir a feature branch
git checkout feature/audit-system

# 3. Rebase sobre develop (mantiene commits del feature arriba)
git rebase develop

# Si hay conflictos:
# - Resolver conflictos en archivos compartidos
# - git add <archivos-resueltos>
# - git rebase --continue

# 4. Push (requiere force porque reescribimos historia)
git push origin feature/audit-system --force-with-lease
```

#### Cuando trabajas en el feature de auditoría:

```bash
git checkout feature/audit-system

# Hacer cambios en archivos del feature
git add apps/api/src/services/validation_coordinator.py
git commit -m "feat(audit): mejorar detección de disclaimers"

# Push
git push origin feature/audit-system
```

## Archivos del Sistema de Auditoría

### Backend (`apps/api/src/`)

**Servicios:**
- `services/validation_coordinator.py` - Orquestador principal
- `services/compliance_auditor.py` - Auditor de disclaimers
- `services/format_auditor.py` - Auditor de formato (fonts, colors)
- `services/grammar_auditor.py` - Auditor de gramática
- `services/logo_auditor.py` - Auditor de logos
- `services/typography_auditor.py` - Auditor de tipografía
- `services/color_palette_auditor.py` - Auditor de paleta de colores
- `services/semantic_consistency_auditor.py` - Auditor semántico
- `services/entity_consistency_auditor.py` - Auditor de entidades
- `services/policy_manager.py` - Gestor de políticas
- `services/policy_detector.py` - Detector automático de políticas
- `services/validation_context_formatter.py` - Formateador de contexto
- `services/summary_formatter.py` - Formateador de resúmenes
- `services/report_generator.py` - Generador de reportes
- `services/tools/audit_file_tool.py` - Tool handler para auditoría

**Modelos:**
- `models/validation_report.py` - Modelo de reporte de validación

**Schemas:**
- `schemas/audit_message.py` - Schemas para mensajes de auditoría

**Configuración:**
- `config/policies.yaml` - Definición de políticas de clientes
- `config/compliance.yaml` - Reglas de compliance

**Tests:**
- `tests/unit/test_compliance_auditor.py`
- `tests/unit/test_format_numeric.py`
- `tests/unit/test_typography.py`
- `tests/unit/test_color_palette.py`
- `tests/unit/test_entity_consistency.py`
- `tests/unit/test_semantic_consistency.py`

**Routers:**
- Endpoints en `routers/chat.py` para `audit_file` tool
- `routers/reports.py` - Endpoints de reportes de auditoría

### Frontend (`apps/web/src/`)

**Componentes:**
- `components/validation/` - Componentes de validación
  - `ComplianceBadge.tsx`
  - `ValidationFindings.tsx`
- `components/chat/AuditProgress.tsx`
- `components/chat/AuditReportCard.tsx`
- `components/chat/AuditToggle.tsx`
- `components/chat/MessageAuditCard.tsx`
- `components/files/FileAttachmentList.tsx` (parcial - audit toggle)

**Hooks:**
- `hooks/useAuditFile.ts`
- `hooks/useAuditFlow.ts`
- `hooks/__tests__/useAuditFlow.test.ts`

**Stores:**
- `lib/stores/audit-store.ts`

**Types:**
- `types/validation.ts`
- `types/tools.tsx` (parcial - audit tool types)

**Tests:**
- `components/files/__tests__/FileAttachmentList.audit-toggle.test.tsx`

### Documentación

- `docs/copiloto-414/` - Documentación del sistema COPILOTO_414
- `docs/AUDIT_SYSTEM_ARCHITECTURE.md` - Arquitectura del sistema

## Resolución de Conflictos Comunes

### Si un archivo compartido tiene cambios en ambos branches:

**Ejemplo:** `apps/api/src/routers/chat.py`

```bash
# Durante el rebase
git checkout feature/audit-system
git rebase develop

# CONFLICT en chat.py
# Editar manualmente para combinar:
# - Cambios de develop (ej: nuevo endpoint)
# - Cambios de audit (ej: audit_file tool)

# Resolver y continuar
git add apps/api/src/routers/chat.py
git rebase --continue
```

### Si necesitas un cambio específico de develop sin rebase completo:

```bash
git checkout feature/audit-system

# Cherry-pick un commit específico
git cherry-pick <commit-hash>

# O cherry-pick múltiples commits
git cherry-pick <commit1>..<commit2>
```

## Ventajas de Esta Estrategia

✅ **Separación clara**: Código base sin features de cliente
✅ **Sincronización fácil**: Rebase trae cambios de develop automáticamente
✅ **Historia limpia**: Los commits del feature quedan arriba del historial
✅ **Rollback simple**: Puedes volver a develop sin el feature en cualquier momento
✅ **Testing independiente**: Puedes probar el feature sin afectar develop

## Comandos de Referencia Rápida

```bash
# Ver diferencias entre branches
git diff develop..feature/audit-system --name-only

# Ver commits únicos en feature branch
git log develop..feature/audit-system --oneline

# Ver commits que están en develop pero no en feature
git log feature/audit-system..develop --oneline

# Crear branch desde tag (si necesitas volver atrás)
git checkout -b feature/audit-system-old audit-system-base

# Comparar tamaño de código
git diff develop..feature/audit-system --stat
```

## Alternativa: Git Worktrees (Avanzado)

Si trabajas frecuentemente en ambos branches:

```bash
# Crear worktree separado para el feature
git worktree add ../octavios-audit feature/audit-system

# Ahora tienes dos directorios:
# ~/octavios-chat-capital414/ (develop)
# ~/octavios-audit/ (feature/audit-system)

# Puedes trabajar en ambos simultáneamente sin cambiar de branch
```

## Notas Importantes

⚠️ **NUNCA hacer merge de feature/audit-system a develop**
⚠️ **Siempre usar rebase para sincronizar con develop**
⚠️ **Usar --force-with-lease al pushear después de rebase (más seguro que --force)**
⚠️ **Mantener .env local separado si hay configuraciones específicas del feature**

## Deployment del Feature

Cuando necesites deployar el feature de auditoría:

```bash
# Deploy desde feature branch directamente
git checkout feature/audit-system
docker build -t octavios-audit:latest .
docker push octavios-audit:latest

# O crear un tag específico
git tag -a v1.0.0-audit -m "Release with audit system"
git push origin v1.0.0-audit
```
