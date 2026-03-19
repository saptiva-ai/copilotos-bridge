# Bug Report — “Flash” de **Conversación no encontrada** al crear conversación

## Resumen
Al crear una nueva conversación desde el menú/historial, la UI navega a una ruta tipo `/chat/temp-<uuid>` y por ~100ms aparece la pantalla **“Conversación no encontrada”** antes de que cargue la conversación real. Es un “glitch” visual (flicker) causado por un estado intermedio mal modelado: el frontend interpreta “aún no tengo datos” como “no existe”.

> Evidencia visual: pantalla de error con el copy “Conversación no encontrada… Volver al chat”.

---

## Entorno
- Frontend: React + Next.js (probablemente App Router)
- Backend: FastAPI
- Infra: Docker
- UI: vista de chat con historial (drawer/sidebar)

---

## Pasos para reproducir
1. Estar en cualquier conversación existente.
2. Abrir el menú/historial.
3. Click en “Nueva conversación”.
4. Observar por un instante (casi imperceptible) la pantalla “Conversación no encontrada”.
5. Luego se muestra la conversación recién creada (o se redirige a la correcta).

---

## Comportamiento actual
- La app entra por un instante a un estado “error 404 / not found” (o “no acceso”) para la conversación temporal o aún no persistida.
- Inmediatamente después, la conversación existe / llega el estado / llega el redirect y se corrige.

---

## Comportamiento esperado
- Nunca deberíamos mostrar **“Conversación no encontrada”** durante un flujo normal de creación.
- Mientras se crea/carga la conversación, la UI debería:
  - Mantener la conversación anterior visible (sin “parpadeo”), o
  - Mostrar un estado neutral: *“Creando conversación…”* con skeleton/loader, o
  - Navegar a una pantalla “Nuevo chat” que no dependa de que el `conversationId` exista todavía.

---

## Impacto
- UX: sensación de inestabilidad / “app glitchy”.
- Confianza: el usuario percibe errores aunque todo funcione.
- Riesgo: si hay latencia real o race conditions más grandes, se puede quedar en 404.

---

## Hipótesis principales (causas probables)

### 1) **Ruta temporal** + render de “not found” por datos `null`
Patrón típico:
- Navegas a `/chat/temp-uuid`
- El componente de la página hace `fetchConversation(tempId)`
- Recibe 404 (porque todavía no existe) **o** estado inicial es `undefined`
- La UI decide: `if (!conversation) return <NotFound/>`
- Milisegundos después: llega la conversación real o se hace `router.replace(/chat/realId)`.

✅ Esto explica el “flash”.

---

### 2) Backend crea conversación pero **no está comprometida** cuando el frontend hace GET
Race condition:
- Frontend: `POST /conversations` (create)
- En paralelo o inmediatamente: `GET /conversations/:id`
- Si el POST responde antes de commit/transaction finish, el GET puede dar 404 por una ventana pequeña.

✅ También cuadra perfecto con ~100ms.

---

### 3) Next.js App Router: uso de `notFound()` demasiado agresivo
Si en `page.tsx` haces algo como:
- `const conv = await fetch(...); if (!conv) notFound();`
Eso puede gatillar “not found” en SSR/streaming, y luego en cliente se corrige (o viceversa), causando flicker.

---

### 4) Cache/estado (React Query / SWR / Zustand) con “stale → empty → refetch”
Si el query key cambia a un id nuevo, puede entrar a `data=undefined` por 1 frame, y tu UI lo interpreta como “no existe”.

---

## Dónde revisar (checklist rápido)

### Frontend (Next/React)
- **Router/navigation**:
  - ¿Al crear conversación navegas primero a `/chat/temp-*`?
  - ¿Haces `router.push` antes de tener el `id` real?
- **Render condicional**:
  - Busca `if (!conversation) return <NotFound />` o `notFound()`
  - Diferenciar explícitamente: `loading` vs `notFound` vs `unauthorized`
- **Data fetching** (React Query/SWR):
  - ¿`enabled` está correcto?
  - ¿`keepPreviousData` / `placeholderData` para evitar “data undefined”?
- **App Router**:
  - ¿Tienes `loading.tsx` en `/chat/[id]`?
  - ¿Tienes `error.tsx` o `not-found.tsx` y se está disparando por states intermedios?
- **UI State**:
  - Cuando se crea conversación, ¿se limpia el store global y eso provoca UI vacía 1 frame?

### Backend (FastAPI)
- Endpoint `POST /conversations`:
  - ¿Retorna antes de commit a DB?
  - ¿Genera ID real en backend y lo devuelve? (ideal)
- Consistencia:
  - Si hay colas/eventos, ¿la conversación “aparece” async?
- Respuestas:
  - Asegurar que el POST solo responde cuando ya es “fetchable”.

---

## Corrección propuesta (recomendada): Modelar estados y evitar 404 durante provisioning

### Objetivo
Separar claramente:
1) “Estoy creando / cargando”  
2) “Existe pero no tengo datos aún”  
3) “De verdad no existe / no acceso”

### Opción A (la más limpia): **Crear primero, navegar después**
Flujo:
1. Click “Nueva conversación”
2. UI entra a `creating=true` (muestra skeleton/overlay)
3. `POST /conversations` → devuelve `conversation_id`
4. `router.replace(/chat/:conversation_id)`
5. La página `/chat/:id` carga normal con `loading.tsx`

**Ventaja:** eliminas el `temp-*` y el flicker casi garantizado.

---

### Opción B: Mantener ruta “/chat/new” para estado de draft
Flujo:
1. `router.push(/chat/new)` (pantalla estable que NO depende de un ID)
2. Muestras input listo (“Escribe tu mensaje…”)
3. Cuando el usuario manda el primer mensaje:
   - creas conversación
   - `router.replace(/chat/:id)`

**Ventaja:** UX más natural: “nuevo chat” existe aunque no haya conversación persistida.

---

### Opción C: Si necesitas `temp-*`, entonces NO muestres NotFound al primer 404
Regla:
- Si el id empieza con `temp-` o tienes flag `isProvisioning`, entonces:
  - En vez de “Conversación no encontrada”, mostrar “Creando conversación…” + retry/backoff por 300–800ms.
  - Solo mostrar 404 después de X reintentos (p.ej. 1–2s) o si backend responde un error definitivo.

---

## Detalle de implementación (patrones concretos)

### 1) “No data” ≠ “Not found”
En el componente de página:
- `loading`: cuando request está en vuelo
- `notFound`: cuando backend confirma 404 definitivo
- `empty`: cuando todavía no hay mensajes pero la conversación existe

Ejemplo conceptual:
- `if (isLoading) return <ChatSkeleton />`
- `if (error?.status === 404 && !isProvisioning) return <NotFound />`
- `return <ChatUI conversation={data} />`

---

### 2) Next.js App Router: agrega `loading.tsx` en `/chat/[id]/loading.tsx`
Eso evita que el usuario vea UI incorrecta durante el cambio de segmento.
- `loading.tsx` debería ser un skeleton del chat (header + burbujas grises + composer deshabilitado).

---

### 3) React Query: usa `keepPreviousData` / `placeholderData`
Cuando cambias de conversación:
- Mantén la conversación previa visible hasta que la nueva esté lista, y encima un “Cargando…” sutil.
Esto mata el flicker de raíz.

---

## Mejora UX: transición suave + swipe (sidebar/historial)

### Problema típico
El flicker se nota más cuando:
- el drawer cierra,
- la lista se reordena (la nueva conversación aparece arriba),
- y la ruta cambia al mismo tiempo.

### Propuesta de “estado de transición”
- Congela la UI durante la transición:
  - cierra el drawer con animación
  - muestra overlay pequeño “Creando conversación…”
  - cuando tengas `id`, cambias ruta con `router.replace`
  - solo entonces actualizas la lista del historial (o animas el insert)

### Animaciones recomendadas
- Usa `useTransition()` (React) o un “route transition state”:
  - Mientras `isPending`, deshabilitar clicks y mostrar loader.
- Para swipe/drawer:
  - animar con CSS transform (translateX) o Framer Motion
  - mantener el contenido de chat montado (no desmontar) para evitar flashes.
- Opcional pro: View Transitions API (si te late ponerte fancy), pero con Framer Motion basta.

---

## Criterios de aceptación (para cerrar el bug)
- [ ] Al crear conversación, **nunca** aparece “Conversación no encontrada” en flujos normales.
- [ ] Si el backend tarda, se ve un estado neutral (skeleton/loader), no error.
- [ ] La transición de conversación vieja → nueva es suave:
  - o mantiene la anterior hasta que la nueva cargue,
  - o muestra “Nuevo chat” estable.
- [ ] Insertar la conversación nueva en historial no provoca saltos bruscos; se anima o se actualiza después del route change.

---

## Nota crítica (para que no nos autoengañemos)
El “flash” no es solo cosmético: es una señal de que tu máquina de estados de UI está incompleta.
En un chat, los estados mínimos reales son: `idle`, `creating`, `loading`, `ready`, `notFound`, `unauthorized`, `error`.
Si tu UI solo tiene `ready` vs `notFound`, vas a seguir viendo glitches cuando haya latencia o concurrencia.


