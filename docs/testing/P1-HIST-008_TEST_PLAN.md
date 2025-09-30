# 🧪 P1-HIST-008: Real-time Sync - Plan de Testing

**Fecha:** 2025-09-30
**Branch:** `feature/P1-HIST-008-realtime-sync`

---

## 🎯 Objetivo

Verificar que los cambios en el historial de conversaciones se sincronicen automáticamente entre múltiples pestañas/ventanas del navegador.

---

## 🔧 Setup Previo

1. **Levantar la aplicación:**
   ```bash
   cd /home/jazielflo/Proyects/copilotos-bridge
   docker-compose up -d
   ```

2. **Verificar servicios:**
   ```bash
   docker ps
   # Debe mostrar: copilotos-api, copilotos-web, mongo, redis
   ```

3. **Abrir navegador:**
   - Chrome/Edge (mejor soporte para BroadcastChannel)
   - Abrir DevTools en ambas pestañas (F12)
   - Ir a Console para ver logs de sync

---

## 📋 Test Cases

### **Test 1: Crear Conversación**

**Escenario:** Una pestaña crea una conversación, otra pestaña debe verla automáticamente.

**Pasos:**
1. Abrir 2 pestañas: Tab A y Tab B en `http://localhost:3000`
2. Login en ambas pestañas con el mismo usuario
3. **En Tab A:**
   - Click en "Nueva conversación"
   - Enviar mensaje: "Test cross-tab sync 1"
   - Verificar que aparece en el historial de Tab A
4. **En Tab B:**
   - Esperar 1-2 segundos
   - ✅ Verificar que la nueva conversación aparece en el historial

**Resultado Esperado:**
- ✅ Nueva conversación aparece en Tab B sin recargar
- ✅ Console log en Tab B: `Sync event: session_created`
- ✅ Sin errores en console

**Fallback (si falla BroadcastChannel):**
- ⏱️ En polling mode, puede tardar 5-10s en sincronizar
- ✅ Debe aparecer eventualmente sin recargar

---

### **Test 2: Renombrar Conversación**

**Escenario:** Una pestaña renombra una conversación, otra pestaña debe ver el nuevo nombre.

**Pasos:**
1. Tener al menos 1 conversación en ambas pestañas (Tab A y Tab B)
2. **En Tab A:**
   - Hover sobre una conversación
   - Click en icono de editar (lápiz)
   - Cambiar nombre a "Renamed via Tab A"
   - Presionar Enter
3. **En Tab B:**
   - Esperar 1-2 segundos
   - ✅ Verificar que el título cambia a "Renamed via Tab A"

**Resultado Esperado:**
- ✅ Título actualiza en Tab B sin recargar
- ✅ Toast "Conversación renombrada" aparece en Tab A
- ✅ Console log en Tab B: `Sync event: session_renamed`
- ✅ Sin flickering ni estados inconsistentes

---

### **Test 3: Fijar Conversación**

**Escenario:** Una pestaña fija una conversación, otra pestaña debe verla moverse al tope.

**Pasos:**
1. Tener al menos 2 conversaciones en ambas pestañas (Tab A y Tab B)
2. **En Tab A:**
   - Hover sobre una conversación NO fijada
   - Click en icono de pin (📌)
3. **En Tab B:**
   - Esperar 1-2 segundos
   - ✅ Verificar que la conversación se mueve al bloque superior (pinned)

**Resultado Esperado:**
- ✅ Conversación aparece en sección "Fijadas" en Tab B
- ✅ Toast "Conversación fijada" aparece en Tab A
- ✅ Console log en Tab B: `Sync event: session_pinned`
- ✅ Orden de lista se actualiza correctamente

---

### **Test 4: Eliminar Conversación**

**Escenario:** Una pestaña elimina una conversación, otra pestaña debe verla desaparecer.

**Pasos:**
1. Tener al menos 2 conversaciones en ambas pestañas (Tab A y Tab B)
2. **En Tab A:**
   - Hover sobre una conversación
   - Click en icono de basura (🗑️)
   - Confirmar eliminación (si hay modal)
3. **En Tab B:**
   - Esperar 1-2 segundos
   - ✅ Verificar que la conversación desaparece de la lista

**Resultado Esperado:**
- ✅ Conversación desaparece en Tab B sin recargar
- ✅ Toast "Conversación eliminada" aparece en Tab A
- ✅ Console log en Tab B: `Sync event: session_deleted`
- ✅ Si Tab B tenía esa conversación abierta, debe limpiar el detalle

---

### **Test 5: Múltiples Pestañas (3+)**

**Escenario:** Verificar que sync funciona con más de 2 pestañas.

**Pasos:**
1. Abrir 3 pestañas: Tab A, Tab B, Tab C
2. Login en todas con el mismo usuario
3. **En Tab A:**
   - Crear conversación "Test Multi-Tab"
4. **En Tab B:**
   - Renombrar a "Updated from Tab B"
5. **En Tab C:**
   - Fijar la conversación
6. Verificar en Tab A → debe ver rename + pin

**Resultado Esperado:**
- ✅ Todas las pestañas se mantienen sincronizadas
- ✅ No hay race conditions ni estados inconsistentes
- ✅ Eventos se propagan a TODAS las pestañas (excepto la que originó el evento)

---

### **Test 6: Fallback a Polling (Safari/Navegadores antiguos)**

**Escenario:** Simular navegador sin soporte de BroadcastChannel.

**Pasos:**
1. Abrir DevTools → Console
2. Ejecutar: `delete window.BroadcastChannel`
3. Recargar ambas pestañas (Tab A y Tab B)
4. Verificar en console: `BroadcastChannel not supported, using polling fallback`
5. Realizar Test 1-4 nuevamente

**Resultado Esperado:**
- ✅ Sync funciona via polling (con delay de 5-10s)
- ✅ Console log: `Polling started`
- ✅ No errores fatales
- ⏱️ Sincronización más lenta pero funcional

---

### **Test 7: Optimistic Updates + Sync**

**Escenario:** Verificar que optimistic updates y sync no causan conflictos.

**Pasos:**
1. Abrir Tab A y Tab B
2. **Detener API:** `docker stop copilotos-api`
3. **En Tab A:**
   - Intentar renombrar conversación
   - Esperar retry (3 intentos)
   - Ver rollback a nombre original
4. **Reiniciar API:** `docker start copilotos-api`
5. **En Tab A:**
   - Renombrar nuevamente (ahora debe funcionar)
6. **En Tab B:**
   - Debe ver el nombre actualizado

**Resultado Esperado:**
- ✅ Rollback funciona correctamente en Tab A
- ✅ Tab B NO recibe evento de cambio hasta que API responde exitosamente
- ✅ Sin estados inconsistentes entre pestañas
- ✅ Broadcast solo ocurre en success, no en optimistic update

---

### **Test 8: Performance con Muchas Operaciones**

**Escenario:** Verificar que sync no causa lag con operaciones rápidas.

**Pasos:**
1. Abrir Tab A y Tab B
2. **En Tab A:**
   - Crear 10 conversaciones rápidamente (click, click, click...)
   - Renombrar 5 de ellas
   - Fijar 3
   - Eliminar 2
3. **En Tab B:**
   - Observar actualizaciones

**Resultado Esperado:**
- ✅ Tab B se actualiza sin lag notable
- ✅ Sin flickering excesivo
- ✅ Orden final consistente entre ambas pestañas
- ✅ Sin memory leaks (verificar en DevTools → Performance → Memory)

---

### **Test 9: Cross-Tab después de Inactividad**

**Escenario:** Verificar que sync funciona después de dejar pestañas inactivas.

**Pasos:**
1. Abrir Tab A y Tab B
2. **En Tab A:**
   - Crear conversación "Before Idle"
3. Esperar 5 minutos sin tocar ninguna pestaña
4. **En Tab A:**
   - Crear conversación "After Idle"
5. **En Tab B:**
   - Debe ver ambas conversaciones

**Resultado Esperado:**
- ✅ Sync funciona después de inactividad
- ✅ Polling no se detiene durante idle
- ✅ BroadcastChannel sigue activo

---

### **Test 10: Diferentes Usuarios (Aislamiento)**

**Escenario:** Verificar que sync NO ocurre entre diferentes usuarios.

**Pasos:**
1. Abrir Tab A → Login como User 1
2. Abrir Tab B (modo incógnito) → Login como User 2
3. **En Tab A (User 1):**
   - Crear conversación "User 1 Chat"
4. **En Tab B (User 2):**
   - NO debe ver "User 1 Chat"
   - Crear conversación "User 2 Chat"
5. **En Tab A (User 1):**
   - NO debe ver "User 2 Chat"

**Resultado Esperado:**
- ✅ Cada usuario solo ve sus propias conversaciones
- ✅ BroadcastChannel NO propaga entre diferentes usuarios
- ✅ Backend filtra por user_id (permisos correctos)

---

## 🔍 Debugging Tips

### **Console Logs Esperados (BroadcastChannel mode):**

**Tab A (origen del evento):**
```
[DEBUG] Broadcasted sync event { type: 'session_renamed', chatId: 'chat-123' }
[INFO] Chat session renamed { chatId: 'chat-123', newTitle: 'New Name' }
```

**Tab B (receptor):**
```
[DEBUG] Received sync event { type: 'session_renamed', source: 'tab-xyz', chatId: 'chat-123' }
[DEBUG] Sync event: session_renamed { chatId: 'chat-123' }
[INFO] Loading chat sessions...
```

---

### **Console Logs Esperados (Polling mode):**

**Tab A:**
```
[WARN] BroadcastChannel not supported, using polling fallback
[DEBUG] Polling started { initialDelay: 5000 }
[DEBUG] Stored event for polling { type: 'session_renamed', totalEvents: 1 }
```

**Tab B:**
```
[WARN] BroadcastChannel not supported, using polling fallback
[DEBUG] Polling started { initialDelay: 5000 }
[DEBUG] Found new events via polling { count: 1 }
[DEBUG] Sync event: session_renamed { chatId: 'chat-123' }
```

---

### **Errores Comunes y Soluciones:**

#### ❌ Error: "BroadcastChannel is not defined"
**Causa:** Navegador muy antiguo o SSR render
**Solución:** Verificar que `SyncProvider` use `'use client'` directive

#### ❌ Error: "Maximum call stack size exceeded"
**Causa:** Loop infinito entre broadcast y listener
**Solución:** Verificar que `loadChatSessions` NO broadcaste evento (solo mutaciones individuales)

#### ❌ Error: Sync no funciona en Tab B
**Causa:** Listeners no configurados o SyncProvider no montado
**Solución:**
1. Verificar que `<SyncProvider />` está en layout
2. Verificar console logs de setup
3. Ejecutar `getSyncInstance().getStatus()` en console

#### ❌ Error: Lag extremo en Tab B
**Causa:** Polling muy agresivo o demasiadas recargas
**Solución:**
1. Verificar polling delay (debe ser 5s inicialmente)
2. Reducir eventos broadcast solo a mutaciones exitosas
3. Implementar debounce en listeners

---

## 📊 Métricas de Éxito

| Métrica | Target | Método de Medición |
|---------|--------|-------------------|
| **Latencia sync (BroadcastChannel)** | < 100ms | DevTools → Performance → Time between events |
| **Latencia sync (Polling)** | < 10s | Tiempo entre acción en Tab A y update en Tab B |
| **Tests pasados** | 10/10 | Checklist manual |
| **Cero errores en console** | ✅ | Verificación visual |
| **Sin memory leaks** | ✅ | DevTools → Memory → Heap snapshot antes/después |

---

## ✅ Checklist de Completación

- [ ] Test 1: Crear conversación ✅
- [ ] Test 2: Renombrar conversación ✅
- [ ] Test 3: Fijar conversación ✅
- [ ] Test 4: Eliminar conversación ✅
- [ ] Test 5: Múltiples pestañas (3+) ✅
- [ ] Test 6: Fallback a polling ✅
- [ ] Test 7: Optimistic updates + sync ✅
- [ ] Test 8: Performance con muchas operaciones ✅
- [ ] Test 9: Cross-tab después de inactividad ✅
- [ ] Test 10: Aislamiento entre usuarios ✅
- [ ] Sin errores en console ✅
- [ ] Sin memory leaks ✅
- [ ] Latencia < 100ms (BroadcastChannel) ✅
- [ ] Latencia < 10s (Polling) ✅

---

## 🚀 Próximos Pasos

Una vez que todos los tests pasen:

1. ✅ Crear commit: `feat: P1-HIST-008 real-time cross-tab sync`
2. ✅ Actualizar documentación P1-HIST-008
3. ✅ Merge a `develop`
4. ✅ Actualizar `BACKLOG_RECONCILIADO.md` (P1 100% completa)
5. 🎉 Release v0.3.1 con P1 completa

---

**Responsable:** Dev Team
**Fecha límite:** 2025-09-30
**Estado:** ⏳ **TESTING**