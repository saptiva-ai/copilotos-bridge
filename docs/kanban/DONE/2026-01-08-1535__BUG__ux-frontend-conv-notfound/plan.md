# Plan

## Objective
Eliminar el flash de "Conversación no encontrada" al crear nuevas conversaciones.

**Root Cause:** `page.tsx` tiene un regex que solo acepta UUIDs. Cuando `ConversationList` navega a `/chat/temp-abc123`, el regex falla y se llama `notFound()`.

## Scope
### In
- Modificar validación en `page.tsx` para aceptar IDs temporales `temp-*`
- Crear `loading.tsx` para mostrar skeleton durante carga
- Verificar que guards existentes funcionan correctamente

### Out
- Cambios en backend (POST /conversations)
- Refactor de arquitectura de routing
- Animaciones/transiciones avanzadas

## Phases

### Phase 1: Research ✅ COMPLETADO
- [x] Identificar componente que renderiza "Conversación no encontrada"
- [x] Trazar flujo de navegación al crear nueva conversación
- [x] Verificar si existe `loading.tsx` en `/chat/[chatId]`
- [x] Revisar cómo se maneja el estado en React Query/SWR/Zustand
- [x] Documentar findings en research.md

**Findings:**
- Root cause: `isValidChatId()` en `page.tsx` rechaza IDs `temp-*`
- `ConversationList.tsx:193` navega a `/chat/temp-*` antes de tener UUID real
- No existe `loading.tsx` en `/chat/[chatId]`

### Phase 2: Fix Validation + Loading ✅ COMPLETADO
- [x] Modificar `isValidChatId()` para aceptar IDs `temp-*`
- [x] Crear `loading.tsx` con skeleton de chat
- [x] Lint passes sin errores

#### Phase 2 Files
```
apps/web/src/app/chat/[chatId]/page.tsx      # Modificar isValidChatId
apps/web/src/app/chat/[chatId]/loading.tsx   # Crear nuevo
```

#### Phase 2 Changes

**2.1 Modificar `page.tsx:16-21`:**
```javascript
function isValidChatId(chatId: string): boolean {
  if (!chatId || chatId === 'new' || chatId.length < 10) return false
  // Accept temporary IDs during optimistic creation
  if (chatId.startsWith('temp-')) return true
  // Standard UUID validation
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  return uuidRegex.test(chatId)
}
```

**2.2 Crear `loading.tsx`:**
```tsx
export default function Loading() {
  return (
    <div className="flex h-screen items-center justify-center bg-saptiva-dark">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-saptiva-blue" />
        <p className="text-saptiva-light/70">Cargando conversación...</p>
      </div>
    </div>
  )
}
```

### Phase 3: Validate ✅ COMPLETADO
- [x] Test: `/chat/temp-*` returns 200 (previously 404 flash)
- [x] Test: `/chat/invalid` shows 404 page correctly
- [x] Docker web container working with hot-reload

#### Phase 3 Files
- docs/kanban/.../validate.md

## Validation Commands
```bash
make dev                    # Start services

# Test 1: Normal creation
# 1. Open http://localhost:3000/chat
# 2. Click "Nueva conversación"
# 3. Verify NO flash of "Conversación no encontrada"

# Test 2: Real 404
# 1. Navigate to http://localhost:3000/chat/invalid-id
# 2. Verify "Conversación no encontrada" appears (expected)

# Test 3: Throttled network
# 1. Open DevTools > Network > Slow 3G
# 2. Click "Nueva conversación"
# 3. Verify loading skeleton or smooth transition
```

## Success Criteria
- [ ] Cero flashes de "not found" durante creación normal
- [ ] Loading skeleton visible durante carga
- [ ] 404 real sigue funcionando para IDs inválidos (no temp-*, no UUID)
- [ ] No regresiones en flujo de chat existente
