# MCP Debugging & Tidewave/Playwright Usage

Lecciones aprendidas y comandos prácticos para habilitar y usar los MCP (Tidewave y Playwright) en dev sin romper el stack.

---

## Errores comunes y soluciones

### Error: "1 MCP server failed" en Claude Code

**Síntoma:** Claude Code muestra "1 MCP server failed" al iniciar.

**Causa raíz:** Configuración incorrecta del transporte MCP para Tidewave.

**Diagnóstico:**
```bash
# Ver qué servidor está fallando
claude mcp list

# Verificar logs del backend
docker logs <backend-container> 2>&1 | grep -i tidewave
```

**Solución:**
```bash
# 1. NO configurar Tidewave manualmente en .mcp.json con tipo "sse"
# 2. Usar el comando oficial de Claude Code con transporte HTTP:
claude mcp add --transport http tidewave http://localhost:8000/tidewave/mcp
```

> **Importante:** Tidewave usa JSON-RPC 2.0 sobre HTTP, NO SSE (Server-Sent Events).

---

### Error: "405 Method Not Allowed" en /tidewave/mcp

**Síntoma:** `GET /tidewave/mcp HTTP/1.1" 405 Method Not Allowed`

**Causa raíz:** El cliente está intentando GET pero Tidewave solo acepta POST.

**Diagnóstico:**
```bash
# Test correcto (POST)
curl -X POST http://localhost:8000/tidewave/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
# Respuesta esperada: {"jsonrpc": "2.0", "id": 1, "result": {}}
```

**Solución:** Verificar que `.mcp.json` NO tenga configuración SSE para Tidewave. Usar `claude mcp add --transport http`.

---

### Error: "The empty string is not valid username" (MongoDB)

**Síntoma:** Backend crashea con error de PyMongo sobre username vacío.

**Causa raíz:** Las variables `$MONGODB_USER` y `$MONGODB_PASSWORD` no se interpolan en docker-compose.

**Diagnóstico:**
```bash
# Ver variables dentro del contenedor
docker exec <backend-container> env | grep MONGODB
# Si MONGODB_URL muestra usuario/password vacíos, el problema es interpolación
```

**Solución:**
```bash
# SIEMPRE usar --env-file al levantar con docker-compose
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml \
  --env-file envs/.env up -d backend
```

> **Nota:** El `env_file:` en el servicio solo pasa variables AL contenedor, no las usa para interpolación en el archivo compose.

---

### Error: "Error loading ASGI app. Could not import module src.main"

**Síntoma:** Backend en loop de reinicio constante.

**Causa raíz:**
1. Imagen production desactualizada (código no copiado)
2. Variables de entorno faltantes causando errores de importación

**Diagnóstico:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep backend
# Si muestra "Restarting" continuamente, hay un problema de startup
```

**Soluciones:**
1. Usar modo development (monta código como volumen):
   ```bash
   docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml \
     --env-file envs/.env up -d backend
   ```
2. O reconstruir imagen production:
   ```bash
   make rebuild-backend
   ```

---

## Lecciones clave

- Usa el mismo `COMPOSE_PROJECT_NAME` y red del stack principal para que los servicios se vean entre sí.
- Tidewave requiere `tidewave[fastapi]` instalado en la imagen y `TIDEWAVE_ENABLED=true` en el backend.
- El endpoint correcto para Tidewave MCP es `POST /tidewave/mcp` (GET/HEAD responde 405; `/tidewave/messages` no existe).
- Playwright MCP puede correrse como contenedor (puerto 8931) o por stdio con `npx @executeautomation/playwright-mcp-server --stdio`.
- Evita conflictos de puertos/nombres: si ya hay un backend en 8000 o un contenedor `agent_playwright`, detén/remueve antes de levantar los de Tidewave.
- No mezcles redes: conecta backend y Playwright a la red `octavios-chat-bajaware_invex_octavios-network` para que alcancen minio/redis/mongo del stack.

---

## Variables de entorno requeridas

Asegúrate de tener estas variables en `envs/.env`:

```bash
# Tidewave MCP
TIDEWAVE_ENABLED=true
TIDEWAVE_ALLOW_REMOTE_ACCESS=true

# MongoDB (para interpolación en compose)
MONGODB_USER=octavios_user
MONGODB_PASSWORD=<tu_password>
MONGODB_DATABASE=octavios

# Redis
REDIS_PASSWORD=<tu_password>
```

---

## Comandos recomendados

### Levantar stack completo (desarrollo)
```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml \
  --env-file envs/.env up -d
```

### Levantar solo backend con hot reload
```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml \
  --env-file envs/.env up -d backend
```

### Configurar Tidewave MCP en Claude Code
```bash
claude mcp add --transport http tidewave http://localhost:8000/tidewave/mcp
```

### Verificar servidores MCP
```bash
claude mcp list
```

### Verificar Tidewave funcionando
```bash
curl -X POST http://localhost:8000/tidewave/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

### Verificar Playwright contenedor
```bash
docker ps | grep agent_playwright  # puerto 8931
```

---

## Qué evitar

- **NO** configurar Tidewave en `.mcp.json` con tipo `"sse"` - usar `claude mcp add --transport http`
- **NO** lanzar compose SIN `--env-file envs/.env` - las variables no se interpolan
- **NO** lanzar compose con `COMPOSE_PROJECT_NAME` diferente - rompe acceso a servicios
- **NO** usar `/tidewave/messages` - responde 404; usar `/tidewave/mcp` con POST
- **NO** dejar contenedores viejos en el mismo puerto - detenerlos antes de recrear
- **NO** olvidar la red correcta: `octavios-chat-bajaware_invex_octavios-network`

---

## Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| "1 MCP server failed" | Config SSE incorrecta | `claude mcp add --transport http tidewave ...` |
| "405 Method Not Allowed" | GET en vez de POST | Verificar config MCP usa HTTP |
| "empty string is not valid username" | Variables no interpoladas | Agregar `--env-file envs/.env` |
| Backend "Restarting" loop | Variables faltantes o imagen vieja | Usar modo dev o rebuild |
| Tidewave no habilitado | Variable faltante | Agregar `TIDEWAVE_ENABLED=true` |
