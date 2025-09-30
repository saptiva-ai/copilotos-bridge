# Plan Detallado: UX Historial de Chats - Feedback Vivo + Densidad

**Fecha:** 2025-09-30
**Versión:** 1.0
**Estado:** ✅ Aprobado - En Implementación

---

## 📋 Resumen Ejecutivo

**Objetivo:** Mejorar la experiencia de usuario del historial de chats con feedback inmediato, señales visuales claras y densidad optimizada.

**Filosofía Estoica:** "Controla lo controlable" - Mostrar estados intermedios reduce la incertidumbre del usuario y mejora la percepción de velocidad.

**Enfoque:** Implementación por fases (P0 → P1 → P2) con documentación y testing incremental.

**Archivos a modificar:** 7 archivos + 3 nuevos componentes

**Tiempo estimado:** 3-4 días de desarrollo

---

## 🎯 FASE 1: P0 - Funcionalidad Crítica (Día 1-2)

### P0-UX-HIST-001: Nueva conversación con feedback inmediato

**Prioridad:** P0 (Crítica)
**Tiempo estimado:** 4-6 horas
**Archivos:** `store.ts`, `ConversationList.tsx`, `ChatView.tsx`, `types.ts`

#### Cambios en types.ts
```typescript
export interface ChatSessionOptimistic extends ChatSession {
  isOptimistic?: boolean  // ID temporal, aún no confirmado por servidor
  isNew?: boolean         // Recién creada, mostrar badge
  tempId?: string         // ID temporal para reconciliación
  realId?: string         // ID real del servidor (tras reconciliación)
}

export interface UXState {
  isCreatingConversation: boolean
  isRevalidating: boolean
  renamingSessionId: string | null
  pinningSessionId: string | null
  deletingSessionId: string | null
}
```

#### Cambios en store.ts
```typescript
interface AppState {
  // ... estados existentes

  // Nuevos estados UX
  isCreatingConversation: boolean
  optimisticConversations: Map<string, ChatSessionOptimistic>
  isRevalidating: boolean
}

interface AppActions {
  // ... acciones existentes

  // Nuevas acciones UX
  createConversationOptimistic: (tempId: string) => void
  reconcileConversation: (tempId: string, realSession: ChatSession) => void
  setCreatingConversation: (creating: boolean) => void
  setRevalidating: (revalidating: boolean) => void
}

// Implementación
createConversationOptimistic: (tempId) => {
  const optimisticSession: ChatSessionOptimistic = {
    id: tempId,
    title: "Nueva conversación",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    message_count: 0,
    model: get().selectedModel,
    pinned: false,
    isOptimistic: true,
    isNew: true,
    tempId,
  }

  set((state) => ({
    chatSessions: [optimisticSession, ...state.chatSessions],
    currentChatId: tempId,
  }))
},

reconcileConversation: (tempId, realSession) => {
  set((state) => ({
    chatSessions: state.chatSessions.map((session) =>
      session.id === tempId ? { ...realSession, isNew: true } : session
    ),
    currentChatId: realSession.id,
  }))

  // Quitar badge "Nueva" después de 3.5s
  setTimeout(() => {
    set((state) => ({
      chatSessions: state.chatSessions.map((s) =>
        s.id === realSession.id ? { ...s, isNew: false } : s
      ),
    }))
  }, 3500)
},
```

#### Cambios en ConversationList.tsx
```tsx
interface ConversationListProps {
  // ... props existentes
  isCreatingConversation?: boolean
}

// Botón "Nueva conversación"
<button
  onClick={handleCreate}
  disabled={isCreatingConversation}
  className={cn(
    "flex h-8 items-center gap-2 px-3 rounded-lg",
    "border text-sm disabled:opacity-60 transition",
    isCreatingConversation && "cursor-not-allowed"
  )}
  aria-busy={isCreatingConversation}
>
  {isCreatingConversation ? (
    <>
      <Spinner className="h-4 w-4 animate-spin" />
      <span>Creando…</span>
    </>
  ) : (
    <>
      <PlusIcon className="h-4 w-4" />
      <span>Nueva conversación</span>
    </>
  )}
</button>

// Item de conversación con badge y resaltado
function ConversationItem({ session }: { session: ChatSessionOptimistic }) {
  const [highlight, setHighlight] = useState(!!session.isNew)

  useEffect(() => {
    if (highlight) {
      const timer = setTimeout(() => setHighlight(false), 3500)
      return () => clearTimeout(timer)
    }
  }, [highlight])

  return (
    <div
      className={cn(
        "relative rounded-md px-2 py-2 flex items-center gap-2",
        session.id === activeChatId && "bg-zinc-100 ring-2 ring-blue-500",
        highlight && "after:absolute after:inset-0 after:ring-2 after:ring-green-400/60 after:animate-pulse"
      )}
    >
      <MessageSquare className="h-4 w-4 shrink-0" />
      <span className="truncate text-sm">{session.title}</span>
      {session.isNew && (
        <span className="ml-auto text-[10px] font-medium bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
          Nueva
        </span>
      )}
    </div>
  )
}
```

#### Cambios en ChatView.tsx
```tsx
const handleCreateConversation = async () => {
  const tempId = `tmp_${crypto.randomUUID()}`

  try {
    setCreatingConversation(true)
    createConversationOptimistic(tempId)

    // Navegar inmediatamente (UI responsiva)
    router.push(`/chat/${tempId}`)

    // Crear en backend
    const response = await apiClient.createChatSession()

    // Reconciliar IDs
    reconcileConversation(tempId, response)
    router.replace(`/chat/${response.id}`)

    // Revalidar lista
    await loadChatSessions()

    toast.success("Conversación creada")
  } catch (error) {
    // Rollback optimista
    set((state) => ({
      chatSessions: state.chatSessions.filter((s) => s.id !== tempId),
      currentChatId: null,
    }))

    toast.error("No se pudo crear. Reintenta.")
  } finally {
    setCreatingConversation(false)
  }
}
```

#### Criterios de Aceptación
- ✅ Al hacer clic: botón muestra spinner y se deshabilita
- ✅ Nueva conversación aparece arriba con badge "Nueva"
- ✅ Resaltado temporal (ring verde animado) por 3.5s
- ✅ Se navega a /chat/[id] y el item queda seleccionado
- ✅ Scroll automático al nuevo item

---

### P0-UX-HIST-002: Señal de revalidación visible

**Prioridad:** P0 (Crítica)
**Tiempo estimado:** 2-3 horas
**Archivos:** Nuevo `RefreshBanner.tsx`, `store.ts`, `ChatView.tsx`

#### Nuevo componente: RefreshBanner.tsx
```tsx
'use client'

interface RefreshBannerProps {
  loading: boolean
}

export function RefreshBanner({ loading }: RefreshBannerProps) {
  return (
    <div
      className={cn(
        "pointer-events-none fixed top-0 left-0 right-0 h-0.5 z-50",
        "transition-opacity duration-200",
        loading ? "opacity-100" : "opacity-0"
      )}
      aria-hidden={!loading}
      aria-live="polite"
      aria-label={loading ? "Actualizando conversaciones" : ""}
    >
      <div
        className="h-full w-full animate-progress bg-blue-500"
        style={{
          animation: loading ? "progress 0.8s ease-in-out infinite" : "none"
        }}
      />
    </div>
  )
}
```

#### Agregar a tailwind.config.js
```js
module.exports = {
  theme: {
    extend: {
      keyframes: {
        progress: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' }
        }
      },
      animation: {
        progress: 'progress 0.8s ease-in-out infinite'
      }
    }
  }
}
```

#### Cambios en store.ts
```typescript
// Wrapper para setear isRevalidating
const withRevalidation = async (fn: () => Promise<void>) => {
  set({ isRevalidating: true })
  try {
    await fn()
  } finally {
    // Delay mínimo para evitar flicker en redes rápidas
    setTimeout(() => set({ isRevalidating: false }), 150)
  }
}

// Modificar acciones existentes
loadChatSessions: async () => {
  await withRevalidation(async () => {
    // ... implementación existente
  })
},

renameChatSession: async (chatId, newTitle) => {
  // ... optimistic update
  await withRevalidation(async () => {
    await apiClient.renameChatSession(chatId, newTitle)
  })
},
```

#### Cambios en ChatView.tsx
```tsx
import { RefreshBanner } from '../../../components/chat/RefreshBanner'

export function ChatView() {
  const { isRevalidating } = useChat()

  return (
    <>
      <RefreshBanner loading={isRevalidating} />
      {/* ... resto del componente */}
    </>
  )
}
```

#### Criterios de Aceptación
- ✅ Cada mutación muestra indicador ≤800ms
- ✅ No tapa interacción ni produce layout shift
- ✅ Banner oculto si request <150ms (red rápida)
- ✅ Aria-live anuncia "Actualizando"

---

## 💎 FASE 2: P1 - Mejoras Importantes (Día 2-3)

### P1-UX-HIST-003: Ajustar densidad del panel

**Prioridad:** P1 (Importante)
**Tiempo estimado:** 2-3 horas
**Archivos:** `ConversationList.tsx`

#### Cambios en ConversationList.tsx
```tsx
// Contenedor del panel (antes w-80 = 320px)
<div className="w-64 min-w-56 max-w-72 border-r bg-background p-2 space-y-2">
  {/* Panel: 256px (~20% más angosto) */}
</div>

// Título de sección
<p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">
  Sesiones
</p>
<h2 className="text-sm font-semibold text-white">
  Conversaciones
</h2>

// Botón "Nueva conversación"
<button className="h-8 px-2 rounded-lg border text-sm">
  {/* h-10 → h-8, px-3 → px-2 */}
</button>

// Íconos
<PlusIcon className="h-4 w-4" />
{/* h-5 w-5 → h-4 w-4 (20px → 16px) */}

// Items de conversación
<div className="rounded-md px-2 py-2 text-sm h-10">
  {/* text-base → text-sm, h-12 → h-10 */}
</div>

// Botones de acción en hover
<button className="h-7 w-7">
  {/* h-8 w-8 → h-7 w-7 */}
  <svg className="h-3.5 w-3.5" />
  {/* h-4 w-4 → h-3.5 w-3.5 */}
</button>
```

#### Criterios de Aceptación
- ✅ Panel ~15-20% más angosto (320px → 256px)
- ✅ Texto en items a .text-sm
- ✅ Botones h-8, px-2
- ✅ Íconos 16px
- ✅ Screenshots comparativos antes/después

---

### P1-UX-HIST-004: Feedback en acciones de item

**Prioridad:** P1 (Importante)
**Tiempo estimado:** 4-5 horas
**Archivos:** `ConversationList.tsx`, `store.ts`, nuevo `useDebouncedCallback.ts`, nuevo `ConfirmDeleteModal.tsx`

#### Nuevo hook: useDebouncedCallback.ts
```typescript
import { useCallback, useRef } from 'react'

export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout>()

  return useCallback(
    ((...args) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args)
      }, delay)
    }) as T,
    [callback, delay]
  )
}
```

#### Nuevo componente: ConfirmDeleteModal.tsx
```tsx
interface ConfirmDeleteModalProps {
  isOpen: boolean
  conversationTitle: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDeleteModal({
  isOpen,
  conversationTitle,
  onConfirm,
  onCancel,
}: ConfirmDeleteModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md">
        <h3 className="text-lg font-semibold mb-2">Eliminar conversación</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          ¿Estás seguro de eliminar "{conversationTitle}"? Esta acción no se puede deshacer.
        </p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded bg-gray-200 hover:bg-gray-300"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm rounded bg-red-500 text-white hover:bg-red-600"
          >
            Eliminar
          </button>
        </div>
      </div>
    </div>
  )
}
```

#### Cambios en ConversationList.tsx
```tsx
import { useDebouncedCallback } from '../../hooks/useDebouncedCallback'
import { ConfirmDeleteModal } from './ConfirmDeleteModal'

function ConversationList() {
  const [renamingSaving, setRenamingSaving] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; title: string } | null>(null)

  // Rename con debounce
  const debouncedRename = useDebouncedCallback(async (chatId: string, newTitle: string) => {
    try {
      setRenamingSaving(chatId)
      await onRenameChat(chatId, newTitle)
      toast.success("Conversación renombrada")
    } catch (error) {
      toast.error("Error al renombrar")
    } finally {
      setRenamingSaving(null)
    }
  }, 350)

  const handleRenameChange = (chatId: string, value: string) => {
    setRenameValue(value)
    debouncedRename(chatId, value)
  }

  // Pin con microtoast
  const handlePin = async (chatId: string, isPinned: boolean) => {
    try {
      await onPinChat(chatId)
      toast.success(isPinned ? "Conversación desfijada" : "Conversación fijada", {
        duration: 2000,
        position: "bottom-right",
      })
    } catch (error) {
      toast.error("Error al fijar")
    }
  }

  // Delete con confirmación
  const handleDeleteClick = (chatId: string, title: string) => {
    setDeleteConfirm({ id: chatId, title })
  }

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm) return

    try {
      // Encontrar vecino superior para seleccionar
      const currentIndex = sortedSessions.findIndex((s) => s.id === deleteConfirm.id)
      const nextSession = sortedSessions[currentIndex - 1] || sortedSessions[currentIndex + 1]

      await onDeleteChat(deleteConfirm.id)

      // Seleccionar vecino o mostrar empty state
      if (nextSession) {
        onSelectChat(nextSession.id)
      } else {
        router.push('/chat')
      }

      toast.success("Conversación eliminada")
    } catch (error) {
      toast.error("Error al eliminar")
    } finally {
      setDeleteConfirm(null)
    }
  }

  return (
    <>
      {/* Rename input con spinner */}
      {isRenaming ? (
        <div className="flex items-center gap-1">
          <input
            value={renameValue}
            onChange={(e) => handleRenameChange(session.id, e.target.value)}
            className="flex-1 text-sm"
          />
          {renamingSaving === session.id && (
            <Spinner className="h-3 w-3 animate-spin" />
          )}
        </div>
      ) : (
        <span>{session.title}</span>
      )}

      {/* Delete button */}
      <button
        onClick={() => handleDeleteClick(session.id, session.title)}
        className="h-7 w-7"
      >
        <TrashIcon className="h-3.5 w-3.5" />
      </button>

      {/* Modal de confirmación */}
      <ConfirmDeleteModal
        isOpen={!!deleteConfirm}
        conversationTitle={deleteConfirm?.title || ""}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteConfirm(null)}
      />
    </>
  )
}
```

#### Criterios de Aceptación
- ✅ Rename muestra "Guardando…" spinner y confirma
- ✅ Error → rollback y toast
- ✅ Pin/unpin no reordena con flicker
- ✅ Microtoast discreto en pin/unpin
- ✅ Delete pide confirmación
- ✅ Delete selecciona vecino superior o empty state

---

## 🎨 FASE 3: P2 - Polish Final (Día 3-4)

### P2-UX-HIST-005: Accesibilidad y anuncios

**Prioridad:** P2 (Polish)
**Tiempo estimado:** 3-4 horas
**Archivos:** `ConversationList.tsx`, nuevo `useAriaLive.ts`

#### Nuevo hook: useAriaLive.ts
```typescript
import { useEffect, useRef } from 'react'

export function useAriaLive() {
  const regionRef = useRef<HTMLDivElement>(null)

  const announce = (message: string) => {
    if (!regionRef.current) return

    regionRef.current.textContent = message

    // Limpiar después de anuncio
    setTimeout(() => {
      if (regionRef.current) {
        regionRef.current.textContent = ''
      }
    }, 1000)
  }

  return { announce, regionRef }
}
```

#### Cambios en ConversationList.tsx
```tsx
import { useAriaLive } from '../../hooks/useAriaLive'

function ConversationList() {
  const { announce, regionRef } = useAriaLive()

  // Anunciar eventos
  useEffect(() => {
    if (isCreatingConversation) {
      announce("Creando nueva conversación")
    }
  }, [isCreatingConversation])

  const handleRenameComplete = () => {
    announce("Conversación renombrada")
  }

  const handleDeleteComplete = () => {
    announce("Conversación eliminada")
  }

  return (
    <>
      {/* Región aria-live para anuncios */}
      <div
        ref={regionRef}
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      />

      {/* Lista con roles ARIA */}
      <div
        role="listbox"
        aria-label="Lista de conversaciones"
        aria-activedescendant={activeChatId || undefined}
      >
        {sortedSessions.map((session) => (
          <div
            key={session.id}
            id={session.id}
            role="option"
            aria-selected={session.id === activeChatId}
            tabIndex={session.id === activeChatId ? 0 : -1}
            className={cn(
              "rounded-md px-2 py-2 cursor-pointer",
              session.id === activeChatId &&
                "bg-zinc-100 ring-2 ring-blue-500 focus:ring-blue-600"
            )}
            onClick={() => handleSelect(session.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSelect(session.id)
              }
            }}
          >
            {/* ... contenido del item */}
          </div>
        ))}
      </div>
    </>
  )
}
```

#### Criterios de Aceptación
- ✅ Lectores anuncian eventos ("Conversación creada", etc.)
- ✅ Focus ring claro (ring-2 ring-blue-500)
- ✅ role="listbox" en contenedor
- ✅ role="option" en items
- ✅ aria-selected en item activo
- ✅ Axe DevTools sin violations críticas

---

## 📊 Métricas de Éxito

| Métrica | Antes | Después | Target |
|---------|-------|---------|--------|
| Tiempo percibido crear conversación | ~800ms | <100ms | ✅ Instantáneo |
| Ancho panel | 320px (w-80) | 256px (w-64) | ✅ 15-20% menos |
| Feedback visual en acciones | 60% | 100% | ✅ Todas |
| Axe violations críticas | 2-3 | 0 | ✅ 0 |
| Keyboard navigation | Parcial | Completo | ✅ 100% |

---

## 🧪 Plan de Testing

### Testing Manual por Fase

**FASE 1 (P0):**
- [ ] Crear conversación → feedback inmediato visible
- [ ] Badge "Nueva" aparece y desaparece después de 3.5s
- [ ] Reconciliación ID temporal → ID real sin flicker
- [ ] Banner de revalidación aparece <800ms en mutaciones
- [ ] Banner oculto en operaciones rápidas (<150ms)

**FASE 2 (P1):**
- [ ] Panel medido en DevTools: 256px ± 5px
- [ ] Rename con debounce: no guarda hasta 350ms después
- [ ] Pin muestra microtoast, sin reordenar con flicker
- [ ] Delete pide confirmación modal
- [ ] Delete selecciona vecino superior o empty state

**FASE 3 (P2):**
- [ ] Axe DevTools ejecutado: 0 errores críticos
- [ ] Screen reader (NVDA/JAWS): anuncia eventos
- [ ] Navegación teclado ↑/↓: funcional
- [ ] Enter selecciona conversación
- [ ] Focus ring visible en todos los estados

### Testing Automatizado (Futuro)

```typescript
// apps/web/src/components/chat/__tests__/ConversationList.test.tsx
describe('ConversationList - UX Improvements', () => {
  it('muestra spinner al crear conversación', async () => {
    const { getByRole } = render(<ConversationList {...props} />)
    const button = getByRole('button', { name: /nueva conversación/i })

    fireEvent.click(button)

    expect(getByText(/creando/i)).toBeInTheDocument()
    expect(button).toBeDisabled()
  })

  it('muestra badge "Nueva" en conversación recién creada', async () => {
    const { getByText } = render(<ConversationList {...propsWithNew} />)

    expect(getByText('Nueva')).toBeInTheDocument()

    await waitFor(() => {
      expect(queryByText('Nueva')).not.toBeInTheDocument()
    }, { timeout: 4000 })
  })

  it('debounce de rename funciona correctamente', async () => {
    const onRename = jest.fn()
    const { getByRole } = render(<ConversationList onRenameChat={onRename} />)

    const input = getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Nuevo título' } })

    expect(onRename).not.toHaveBeenCalled()

    await waitFor(() => {
      expect(onRename).toHaveBeenCalledWith(sessionId, 'Nuevo título')
    }, { timeout: 400 })
  })
})
```

---

## 📝 Commits Sugeridos

```bash
# FASE 1
git commit -m "feat: P0-UX-HIST-001 optimistic conversation creation

- Add optimistic UI for instant feedback
- Show 'Nueva' badge for 3.5s on new conversations
- Implement tempId → realId reconciliation
- Add spinner state to 'Nueva conversación' button

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

git commit -m "feat: P0-UX-HIST-002 revalidation progress indicator

- Add RefreshBanner component (Gmail-style)
- Show progress bar on mutations (<800ms)
- Hide on fast operations (<150ms)
- Add aria-live announcements

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# FASE 2
git commit -m "feat: P1-UX-HIST-003 optimize panel density

- Reduce panel width 320px → 256px (20%)
- Compact typography (text-base → text-sm)
- Reduce button heights (h-10 → h-8)
- Resize icons (20px → 16px)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

git commit -m "feat: P1-UX-HIST-004 action feedback improvements

- Add debounced rename (350ms) with spinner
- Show microtoasts on pin/unpin
- Add confirmation modal for delete
- Select neighbor after delete

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# FASE 3
git commit -m "feat: P2-UX-HIST-005 accessibility enhancements

- Add ARIA roles (listbox, option)
- Implement aria-live announcements
- Improve focus rings (ring-2 ring-blue-500)
- Pass Axe DevTools audit (0 critical)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 🚀 Deployment Checklist

- [ ] Todas las fases implementadas y testeadas
- [ ] Tests unitarios escritos y pasando
- [ ] Axe DevTools audit pasando (0 critical)
- [ ] Screenshots antes/después capturados
- [ ] Documentación actualizada
- [ ] PR creado con descripción detallada
- [ ] Code review aprobado
- [ ] Merge a develop
- [ ] Deploy a staging
- [ ] QA manual en staging
- [ ] Deploy a production

---

## ⚠️ Notas Importantes

1. **Backward Compatibility:** Todos los cambios son aditivos, no rompen funcionalidad existente
2. **Performance:** Optimistic UI reduce latencia percibida sin afectar servidor
3. **Rollback:** Cada fase es independiente, puede revertirse sin afectar otras
4. **Browser Support:** BroadcastChannel tiene 95%+ support (fallback a polling ya implementado)
5. **Accessibility:** WCAG 2.1 AA compliance target

---

**Autor:** Claude Code
**Aprobado por:** Dev Team
**Última actualización:** 2025-09-30
**Próxima revisión:** Tras implementación de FASE 1
