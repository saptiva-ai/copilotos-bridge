# Research

## Objective
Investigar el flujo actual de creación de conversaciones e identificar la causa raíz del flash "Conversación no encontrada".

## Questions to Answer
1. ¿Dónde se renderiza el mensaje "Conversación no encontrada"?
2. ¿Cómo fluye la navegación al crear una nueva conversación?
3. ¿Existe `loading.tsx` en la ruta `/chat/[id]`?
4. ¿Qué estado management se usa (React Query, SWR, Zustand)?
5. ¿Se usa ruta temporal `temp-*` o se navega después de crear?

---

## Findings

### 1. Componentes que renderizan "Conversación no encontrada"

**Ubicación 1: `apps/web/src/app/chat/[chatId]/not-found.tsx`**
- Renderiza cuando Next.js `notFound()` es llamado
- Mensaje: "Conversación no encontrada"

**Ubicación 2: `apps/web/src/app/chat/_components/ChatView.tsx:1736-1767`**
- Renderiza cuando `chatNotFound && resolvedChatId` es true
- Se setea `chatNotFound = true` en `chat-store.ts:462` cuando hay 404 del backend

### 2. Flujo de navegación al crear conversación

**Flujo actual (`ConversationList.tsx:188-197`):**
```javascript
const optimisticId = await onNewChat(); // Retorna "temp-abc123"
if (optimisticId) {
  router.push(`/chat/${optimisticId}`); // ← PROBLEMA: Navega INMEDIATAMENTE
}
```

**Flujo en `ChatView.handleStartNewChat` (líneas 1525-1647):**
1. Click "Nueva conversación"
2. `createConversationOptimistic("temp-abc")` → crea session optimista
3. `setCurrentChatId(optimisticId)`
4. `router.push(\`/chat/temp-abc\`)` ← desde ConversationList
5. Async: `apiClient.createConversation()` → obtiene UUID real
6. `reconcileConversation(tempId, realSession)`
7. `router.replace(\`/chat/${realId}\`)`

### 3. ROOT CAUSE IDENTIFICADO 🔴

**`apps/web/src/app/chat/[chatId]/page.tsx:16-21`:**
```javascript
function isValidChatId(chatId: string): boolean {
  if (!chatId || chatId === 'new' || chatId.length < 10) return false
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  return uuidRegex.test(chatId) // ← temp-abc123 FALLA este regex
}

export default function ChatRoute({ params }: ChatRouteProps) {
  if (!isValidChatId(chatId)) {
    notFound() // ← Se llama para IDs temp-*
  }
}
```

**Secuencia del bug:**
1. `ConversationList` navega a `/chat/temp-abc123`
2. `page.tsx` valida: `isValidChatId("temp-abc123")` → `false`
3. Se llama `notFound()` → renderiza `not-found.tsx`
4. ~100ms después: backend responde, reconcilia, `router.replace(/chat/uuid)`
5. UUID real pasa validación → chat carga correctamente

### 4. Loading.tsx

**NO EXISTE** `loading.tsx` en `/chat/[chatId]/`

Esto significa que no hay Suspense boundary a nivel de ruta para mostrar skeleton durante la carga.

### 5. Estado Management

- **Zustand:** `chat-store.ts` para mensajes, `history-store.ts` para sesiones
- **React Query:** `useChatMessages.ts` con SWR pattern
- **Guards existentes:**
  - `useChatMessages` tiene `enabled: !chatId.startsWith("temp-")`
  - `ChatView useEffect` tiene guard para `isTempId && isCreatingConversation`

---

## Diagnóstico Final

| Componente | Estado | Problema |
|------------|--------|----------|
| `page.tsx` validation | 🔴 Bug | Regex solo acepta UUIDs, rechaza `temp-*` |
| `loading.tsx` | 🟡 Missing | No existe skeleton de ruta |
| `ChatView guards` | 🟢 OK | Guards funcionan pero page.tsx los bypasea |
| `useChatMessages` | 🟢 OK | No hace fetch para temp-* |

---

## Soluciones Propuestas

### Opción A: Modificar `isValidChatId` para aceptar `temp-*`
```javascript
function isValidChatId(chatId: string): boolean {
  if (!chatId || chatId === 'new' || chatId.length < 10) return false
  if (chatId.startsWith('temp-')) return true // ← Acepta temp-*
  const uuidRegex = /^[0-9a-f]{8}-...$/i
  return uuidRegex.test(chatId)
}
```

### Opción B: No navegar hasta tener UUID real (Recommended)
Modificar `ConversationList.handleCreateNew`:
```javascript
const optimisticId = await onNewChat();
// NO navegar aquí - dejar que handleStartNewChat navegue después de reconciliar
```

### Opción C: Agregar `loading.tsx` + handling de temp-*
Crear `apps/web/src/app/chat/[chatId]/loading.tsx` con skeleton de chat.

---

## Archivos Afectados

| Archivo | Líneas | Rol |
|---------|--------|-----|
| `apps/web/src/app/chat/[chatId]/page.tsx` | 16-29 | Validación de chatId |
| `apps/web/src/components/chat/ConversationList.tsx` | 193-194 | Navegación prematura |
| `apps/web/src/app/chat/[chatId]/not-found.tsx` | 1-20 | UI del error |
| `apps/web/src/app/chat/_components/ChatView.tsx` | 1736-1767 | welcomeComponent |

---

*Research completed: 2026-01-08*
