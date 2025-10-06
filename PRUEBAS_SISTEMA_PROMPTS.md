# Guía de Pruebas: Sistema de Prompts por Modelo

## ✅ Sistema Actualizado y Funcionando

Los contenedores han sido actualizados con la implementación del **sistema de prompts por modelo**. El sistema está activo con `ENABLE_MODEL_SYSTEM_PROMPT=true`.

---

## 🧪 Pruebas en la Aplicación Web

### Prueba 1: Comparar Respuestas de Diferentes Modelos

Esta prueba demuestra cómo cada modelo tiene un comportamiento diferenciado según su configuración.

**Pasos:**
1. Abre la aplicación: `http://localhost:3000`
2. Inicia sesión (o crea una cuenta si es necesario)
3. Crea una nueva conversación

**Mensaje de prueba:**
```
Dame 3 puntos clave sobre inteligencia artificial
```

**Prueba con cada modelo:**

#### a) **Saptiva Turbo** (Optimizado para velocidad)
- Selecciona: `Saptiva Turbo` en el selector de modelo
- Envía el mensaje
- **Comportamiento esperado:**
  - Respuesta en ≤6 bullets (configurado con addendum)
  - Temperatura: 0.25 (más determinística)
  - Respuesta concisa y rápida
  - Max tokens: 1200 (canal "chat")

#### b) **Saptiva Cortex** (Optimizado para rigor)
- Cambia a: `Saptiva Cortex`
- Envía el MISMO mensaje
- **Comportamiento esperado:**
  - Supuestos explícitos
  - Nivel de confianza declarado
  - Temperatura: 0.35 (más variación)
  - Razonamiento más profundo

#### c) **Saptiva Ops** (Optimizado para código)
- Cambia a: `Saptiva Ops`
- Prueba con: `"Escribe una función Python que valide emails"`
- **Comportamiento esperado:**
  - Código con pruebas incluidas
  - Temperatura: 0.2 (muy determinística)
  - Prácticas DevOps y seguridad
  - Snippets testeables

---

### Prueba 2: Validar Context Injection

Esta prueba verifica que el contexto se inyecta correctamente en el prompt del usuario.

**Pasos:**
1. Abre Chrome DevTools (F12)
2. Ve a la pestaña "Network"
3. Filtra por "chat"
4. Envía un mensaje en la app
5. Inspecciona el payload del request a `/api/chat`

**Qué verificar:**
```json
{
  "message": "Tu mensaje aquí",
  "model": "Saptiva Turbo",
  "channel": "chat",  // ← Debería aparecer
  "context": {        // ← Debería contener datos de sesión
    "chat_id": "...",
    "user_id": "..."
  }
}
```

**Comportamiento esperado:**
- El backend agrega automáticamente `chat_id` y `user_id` al contexto
- El context se formatea en el mensaje del usuario

---

### Prueba 3: Verificar Telemetría (Logs del Backend)

Esta prueba confirma que la telemetría con hash SHA256 funciona correctamente.

**Pasos:**
1. Envía un mensaje en la app
2. En la terminal, ejecuta:
```bash
docker logs copilotos-api 2>&1 | grep "system_hash\|request_id\|Built Saptiva payload"
```

**Qué esperar en los logs:**
```json
{
  "event": "Built Saptiva payload with model-specific prompt",
  "model": "Saptiva Turbo",
  "channel": "chat",
  "request_id": "abc-123-def-456",
  "system_hash": "f962b2adf7b10997",  // Hash SHA256 (16 chars)
  "prompt_version": "v1",
  "max_tokens": 1200,
  "temperature": 0.25,
  "has_tools": false
}
```

**Validaciones:**
✅ `system_hash` presente (NO el contenido del prompt)
✅ `request_id` único por request
✅ `max_tokens` = 1200 para canal "chat"
✅ `temperature` específica del modelo

---

## 🔬 Pruebas con cURL (Sin UI)

Si prefieres probar directamente contra la API:

### Paso 1: Obtener Token de Autenticación

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "tu-email@example.com",
    "password": "tu-password"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### Paso 2: Probar Diferentes Modelos

#### a) **Saptiva Turbo** (Brevedad)
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Dame 3 bullets sobre IA",
    "model": "Saptiva Turbo",
    "channel": "chat",
    "context": {"test_id": "turbo-001"}
  }' | jq .
```

**Verificar en respuesta:**
- Respuesta concisa (≤6 bullets)
- `model`: "Saptiva Turbo"

#### b) **Saptiva Cortex** (Rigor)
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Explica machine learning",
    "model": "Saptiva Cortex",
    "channel": "chat",
    "context": {"test_id": "cortex-001"}
  }' | jq .
```

**Verificar en respuesta:**
- Supuestos explícitos
- Nivel de confianza mencionado

#### c) **Cambiar Canal** (max_tokens diferente)
```bash
# Canal "report" → max_tokens: 3500
curl -X POST http://localhost:8001/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Genera un reporte sobre tendencias de IA",
    "model": "Saptiva Cortex",
    "channel": "report",
    "context": {"test_id": "report-001"}
  }' | jq .
```

**Verificar en logs:**
```bash
docker logs copilotos-api 2>&1 | grep "max_tokens" | tail -1
```
Debería mostrar: `"max_tokens": 3500`

---

## 🎯 Pruebas Avanzadas

### Prueba 4: Feature Flag (Rollback)

Desactivar el sistema de prompts y volver a comportamiento legacy:

```bash
# 1. Editar envs/.env
nano envs/.env
# Cambiar: ENABLE_MODEL_SYSTEM_PROMPT=false

# 2. Reiniciar API
docker compose -f infra/docker-compose.yml --env-file envs/.env restart api

# 3. Verificar logs
docker logs copilotos-api 2>&1 | grep "legacy"
```

**Comportamiento esperado:**
- Logs muestran: `"legacy_mode": true`
- Prompts NO usan sistema nuevo
- Temperatura default: 0.7

**Revertir:**
```bash
# Cambiar de vuelta: ENABLE_MODEL_SYSTEM_PROMPT=true
docker compose -f infra/docker-compose.yml --env-file envs/.env restart api
```

---

### Prueba 5: Herramientas (Tools Injection)

Si tienes herramientas habilitadas:

```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Busca información actual sobre GPT-4",
    "model": "Saptiva Turbo",
    "channel": "chat",
    "tools_enabled": {
      "web_search": true
    }
  }' | jq .
```

**Verificar en logs:**
```bash
docker logs copilotos-api 2>&1 | grep "has_tools" | tail -1
```
Debería mostrar: `"has_tools": true`

---

## 📊 Checklist de Validación

Use esta checklist para confirmar que todo funciona:

### Funcionalidad Básica
- [ ] ✅ API levanta sin errores (health check OK)
- [ ] ✅ Modelos diferentes dan respuestas diferenciadas
- [ ] ✅ Context injection funciona (chat_id, user_id)

### Telemetría
- [ ] ✅ `system_hash` aparece en logs (16 chars)
- [ ] ✅ NO aparece contenido del prompt en logs
- [ ] ✅ `request_id` es único por request
- [ ] ✅ `max_tokens` varía según canal (chat:1200, report:3500)
- [ ] ✅ `temperature` varía según modelo

### Configuración por Modelo
- [ ] ✅ **Saptiva Turbo**: Respuestas concisas (≤6 bullets)
- [ ] ✅ **Saptiva Cortex**: Supuestos explícitos
- [ ] ✅ **Saptiva Ops**: Código con tests

### Feature Flag
- [ ] ✅ `ENABLE_MODEL_SYSTEM_PROMPT=false` → legacy mode
- [ ] ✅ `ENABLE_MODEL_SYSTEM_PROMPT=true` → nuevo sistema

---

## 🐛 Troubleshooting

### Problema: "Token de autenticación requerido"
**Solución:** Obtén un token con `/api/auth/login` primero

### Problema: Logs no muestran `system_hash`
**Solución:**
1. Verifica `ENABLE_MODEL_SYSTEM_PROMPT=true` en `envs/.env`
2. Reinicia la API: `docker compose restart api`

### Problema: Modelos responden igual
**Solución:**
1. Verifica que `prompts/registry.yaml` tenga addendums diferentes
2. Compara valores de `temperature` en logs

### Problema: "Prompt registry not found"
**Solución:**
1. Verifica que existe: `ls apps/api/prompts/registry.yaml`
2. Verifica `PROMPT_REGISTRY_PATH` en `envs/.env`

---

## 📈 Métricas a Monitorear

En producción, monitorea:

1. **Latencia por modelo:**
   - Turbo debería ser más rápido (temp: 0.25)
   - Cortex puede ser más lento (razonamiento profundo)

2. **Distribución de system_hash:**
   - Deberías ver ~5 hashes diferentes (uno por modelo)
   - Hash debe ser consistente para el mismo modelo

3. **Tool-call rate:**
   - Compara con/sin `tools_enabled`

4. **Error rate:**
   - Debería ser similar a comportamiento legacy

---

## ✅ Validación Final

Si completaste todas las pruebas y el checklist está OK:

**🎉 Sistema de Prompts por Modelo Funcionando Correctamente**

**Próximos pasos:**
1. Crear PR para merge a `develop`
2. Desplegar en staging
3. Canary rollout: 10% → 50% → 100%

---

**Creado:** 2025-10-06
**Branch:** `feat/model-system-prompts`
**Commit:** `491d993`
