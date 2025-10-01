# Diagnóstico: Errores de Conexión en Producción

**Fecha**: 2025-09-30
**Servidor**: `jf@34.42.214.246`
**Severidad**: 🟡 MEDIA
**Estado**: 1 problema crítico identificado, resto preventivo

---

## 📊 Resumen Ejecutivo

**Estado de servicios**: ✅ Todos los contenedores `healthy`
- `copilotos-api`: UP 4 horas, healthy
- `copilotos-web`: UP 4 horas, healthy
- `copilotos-mongodb`: UP 4 horas, healthy
- `copilotos-redis`: UP 4 horas, healthy

**Problema crítico detectado**:
- ❌ **Redis cache connection failed** (Error 111: Connection refused)
- Timestamp: `2025-09-30T20:19:00.585060Z`

---

## 🔍 Problemas Identificados

### 1. 🔴 Redis Connection Failed (Crítico - CONFIRMADO)

**Problema**: El API intenta conectarse a Redis en `localhost:6379` pero el servicio está en el contenedor `redis:6379`.

**Evidencia en logs**:
```json
{
  "error": "Error 111 connecting to localhost:6379. Connection refused.",
  "event": "Redis cache connection failed",
  "logger": "src.core.redis_cache",
  "level": "warning",
  "timestamp": "2025-09-30T20:19:00.585060Z"
}
```

**Variables de entorno actuales**:
```bash
REDIS_URL=redis://:redis_password_change_me@redis:6379/0  # ❌ Contraseña incorrecta
REDIS_PORT=6379
REDIS_PASSWORD=SecureRedisProd2024!Change  # ✅ Contraseña real
```

**Análisis**:
- `REDIS_URL` tiene contraseña `redis_password_change_me` (placeholder)
- `REDIS_PASSWORD` tiene `SecureRedisProd2024!Change` (real)
- Mismatch causa falla de autenticación

**Impacto**:
- Cache de historial no funciona → cada request va a MongoDB
- Rate limiting puede no funcionar correctamente
- Mayor latencia en requests de historial
- Mayor carga en MongoDB

**Solución**:

```bash
# En el servidor de producción
ssh jf@34.42.214.246

# Opción 1: Editar docker-compose.yml y usar REDIS_PASSWORD
# Buscar donde se define REDIS_URL y cambiar a:
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Opción 2: Actualizar .env para que coincida
REDIS_URL=redis://:SecureRedisProd2024!Change@redis:6379/0

# Reiniciar API
docker compose restart api

# Verificar logs
docker logs copilotos-api --tail=50 | grep -i redis
```

**Prioridad**: 🔴 CRÍTICA - Corregir en las próximas 24h

---

### 2. ⚠️ Configuración CORS (Preventivo)

**Problema**: El backend FastAPI tiene CORS configurado solo para `localhost:3000` por defecto, pero en producción el dominio es `copiloto.saptiva.com`.

**Ubicación**: `apps/api/src/core/config.py:179-182`

```python
# CORS
cors_origins: List[str] = Field(
    default=["http://localhost:3000"],  # ❌ Solo localhost
    description="Allowed CORS origins"
)
```

**En `.env.production` línea 69**:
```bash
CORS_ORIGINS=["https://copiloto.saptiva.com"]  # ✅ Correcto pero puede no parsearse bien
```

**Síntomas**:
- Requests desde el navegador bloqueadas con error: `Access to fetch at 'https://copiloto.saptiva.com/api/chat' from origin 'https://copiloto.saptiva.com' has been blocked by CORS policy`
- Console del navegador muestra: `No 'Access-Control-Allow-Origin' header is present`

**Solución**:

```python
# apps/api/src/core/config.py
cors_origins: List[str] = Field(
    default=["http://localhost:3000", "https://copiloto.saptiva.com"],
    description="Allowed CORS origins"
)

# O mejor, parsear desde env:
@property
def cors_origins_list(self) -> List[str]:
    """Parse CORS origins from environment variable."""
    import json
    cors_str = os.getenv("CORS_ORIGINS", '["http://localhost:3000"]')
    try:
        return json.loads(cors_str)
    except:
        # Fallback: split by comma
        return [origin.strip() for origin in cors_str.split(",")]
```

**Prioridad**: 🔴 CRÍTICA - Implementar YA

---

### 2. ⚠️ Timeouts de SAPTIVA Demasiado Cortos

**Problema**: Los timeouts actuales pueden ser insuficientes para queries complejas.

**Configuración actual** (`.env.production:43-46`):
```bash
SAPTIVA_TIMEOUT=120           # Total timeout (OK)
SAPTIVA_CONNECT_TIMEOUT=30    # ⚠️ Podría ser corto
SAPTIVA_READ_TIMEOUT=60       # ⚠️ Podría ser corto para LLM generativo
```

**En el código** (`apps/api/src/services/saptiva_client.py:66`):
```python
self.client = httpx.AsyncClient(
    timeout=httpx.Timeout(self.timeout, connect=5.0),  # ❌ Solo 5s de connect
    ...
)
```

**Síntomas**:
- Errores `ReadTimeout` o `ConnectTimeout` en logs
- Requests que fallan antes de recibir respuesta completa del LLM

**Solución**:

```python
# apps/api/src/services/saptiva_client.py
self.client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        timeout=self.settings.saptiva_read_timeout or 120,  # Total
        connect=self.settings.saptiva_connect_timeout or 10,  # Connect
        read=self.settings.saptiva_read_timeout or 90,        # Read (para streaming)
        write=10.0                                             # Write
    ),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    http2=True,
)
```

**Prioridad**: 🟡 MEDIA - Implementar en próximo deploy

---

### 3. ⚠️ Sin Manejo de Reconexión en ApiClient (Frontend)

**Problema**: El frontend no tiene retry logic para errores de red transitorios.

**Ubicación**: `apps/web/src/lib/api-client.ts:141-183`

```typescript
this.client = axios.create({
    baseURL: this.baseURL,
    timeout: 30000,  // 30s - puede ser corto para queries complejas
    headers: { ... }
})
```

**Síntomas**:
- Error en UI: "Network Error" o "Request failed with status code 500"
- No reintenta automáticamente en caso de error temporal

**Solución**: Añadir interceptor con retry logic

```typescript
// apps/web/src/lib/api-client.ts
import axiosRetry from 'axios-retry'

// En initializeClient():
axiosRetry(this.client, {
    retries: 3,
    retryDelay: axiosRetry.exponentialDelay,
    retryCondition: (error) => {
        // Retry solo en errores de red o 5xx
        return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
               (error.response?.status || 0) >= 500
    },
    onRetry: (retryCount, error, requestConfig) => {
        logWarn(`Retrying request (${retryCount}/3): ${requestConfig.url}`)
    }
})
```

**Prioridad**: 🟢 BAJA - Nice to have

---

### 4. 🔴 MongoDB Connection Pooling Agresivo

**Problema**: Pool muy grande puede causar exhaustion de conexiones en MongoDB.

**Configuración actual** (`apps/api/src/core/config.py:58-63`):
```python
db_min_pool_size: int = Field(default=10)
db_max_pool_size: int = Field(default=100)  # ⚠️ Muy alto para producción
db_connection_timeout_ms: int = Field(default=5000)
db_server_selection_timeout_ms: int = Field(default=5000)  # ⚠️ Muy corto
```

**Síntomas**:
- Errores: `ServerSelectionTimeoutError: No servers available`
- Logs: `Connection pool exhausted`

**Solución**:

```bash
# .env.production
DB_MIN_POOL_SIZE=5
DB_MAX_POOL_SIZE=50  # Reducir a 50 para evitar exhaustion
DB_CONNECTION_TIMEOUT_MS=10000  # Aumentar a 10s
DB_SERVER_SELECTION_TIMEOUT_MS=10000  # Aumentar a 10s
DB_MAX_IDLE_TIME_MS=300000  # 5 minutos
```

**Prioridad**: 🟡 MEDIA - Ajustar en próximo deploy

---

### 5. ⚠️ Rate Limiting Muy Estricto

**Problema**: 200 requests/min puede ser bajo para usuarios activos (3.3 req/s).

**Configuración actual** (`.env.production:51`):
```bash
RATE_LIMIT_REQUESTS_PER_MINUTE=200
```

**Síntomas**:
- Errores 429 (Too Many Requests)
- Chat bloqueado temporalmente

**Solución**: Aumentar límite o implementar rate limiting por usuario

```bash
# .env.production
RATE_LIMIT_REQUESTS_PER_MINUTE=500  # O más dependiendo del uso
RATE_LIMIT_PERIOD=60
```

**Prioridad**: 🟢 BAJA - Monitorear primero

---

## 🔧 Plan de Acción Inmediato

### Paso 1: Verificar y Corregir CORS (Crítico)

```bash
# SSH al servidor de producción
ssh copiloto.saptiva.com

# Verificar variable de entorno
echo $CORS_ORIGINS

# Si está vacío o incorrecto, actualizar .env
cd /path/to/copilotos-bridge
nano .env.production

# Asegurar que tenga:
CORS_ORIGINS=https://copiloto.saptiva.com,https://www.copiloto.saptiva.com

# Reiniciar servicio API
docker compose restart api

# O si es systemd:
sudo systemctl restart copilotos-api
```

### Paso 2: Aumentar Timeouts de SAPTIVA

```bash
# Editar .env.production
SAPTIVA_CONNECT_TIMEOUT=15  # De 30 a 15 (más razonable)
SAPTIVA_READ_TIMEOUT=120    # De 60 a 120 (el doble para LLM)

# Reiniciar
docker compose restart api
```

### Paso 3: Ajustar Pool de MongoDB

```bash
# Editar .env.production
DB_MAX_POOL_SIZE=50
DB_SERVER_SELECTION_TIMEOUT_MS=10000

# Reiniciar
docker compose restart api
```

### Paso 4: Verificar Logs

```bash
# Revisar logs del API
docker compose logs -f --tail=100 api | grep -i "error\|timeout\|cors"

# Revisar logs de MongoDB
docker compose logs -f --tail=50 mongodb

# Revisar logs de Redis
docker compose logs -f --tail=50 redis
```

---

## 📊 Comandos de Diagnóstico

### Verificar Conectividad desde el Servidor

```bash
# Test de conexión a SAPTIVA API
curl -I https://api.saptiva.com/v1/models \
  -H "Authorization: Bearer $SAPTIVA_API_KEY"

# Test de MongoDB
docker exec -it copilotos-mongodb mongosh \
  -u $MONGODB_USER -p $MONGODB_PASSWORD \
  --eval "db.adminCommand({ ping: 1 })"

# Test de Redis
docker exec -it copilotos-redis redis-cli \
  -a $REDIS_PASSWORD PING
```

### Verificar Headers CORS desde Cliente

```bash
# Desde tu máquina local (simular request del navegador)
curl -I https://copiloto.saptiva.com/api/health \
  -H "Origin: https://copiloto.saptiva.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization"

# Debe retornar:
# Access-Control-Allow-Origin: https://copiloto.saptiva.com
# Access-Control-Allow-Credentials: true
```

### Monitorear Errores en Tiempo Real

```bash
# Terminal 1: Logs del API
docker compose logs -f api | grep -E "error|Error|ERROR"

# Terminal 2: Logs del Frontend (si está en Docker)
docker compose logs -f web | grep -E "error|Error|ERROR"

# Terminal 3: Monitorear conexiones a MongoDB
watch -n 5 'docker exec copilotos-mongodb mongosh -u $MONGODB_USER -p $MONGODB_PASSWORD --quiet --eval "db.serverStatus().connections"'
```

---

## 🧪 Tests de Verificación Post-Fix

### Test 1: CORS Fixed

```bash
# Desde navegador (DevTools Console)
fetch('https://copiloto.saptiva.com/api/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)

# Debe retornar: {status: "healthy", ...}
# Sin errores CORS
```

### Test 2: Timeouts Fixed

```bash
# Enviar query compleja que toma >60s
curl -X POST https://copiloto.saptiva.com/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explica en detalle la teoría de la relatividad con ejemplos y ecuaciones",
    "model": "Saptiva Cortex",
    "max_tokens": 4000
  }'

# Debe completar sin timeout
```

### Test 3: Connection Pool Fixed

```bash
# Enviar 50 requests simultáneas
for i in {1..50}; do
  curl -X GET https://copiloto.saptiva.com/api/health \
    -H "Authorization: Bearer $TOKEN" &
done
wait

# Todas deben retornar 200 OK
# Sin errores "No servers available"
```

---

## 📝 Checklist de Producción

- [ ] Verificar `CORS_ORIGINS` en `.env.production`
- [ ] Reiniciar servicio API después de cambios
- [ ] Monitorear logs durante 1 hora post-deploy
- [ ] Ejecutar tests de verificación
- [ ] Documentar cambios en CHANGELOG
- [ ] Notificar a usuarios sobre mantenimiento (si downtime)
- [ ] Configurar alertas de error en Sentry/NewRelic (si aplica)
- [ ] Backup de configuración actual antes de cambios

---

## 🔗 Referencias

- **CORS en FastAPI**: https://fastapi.tiangolo.com/tutorial/cors/
- **httpx Timeouts**: https://www.python-httpx.org/advanced/#timeout-configuration
- **MongoDB Connection Pooling**: https://www.mongodb.com/docs/drivers/python/pymongo/current/api/pymongo/pool.html
- **Axios Retry**: https://github.com/softonic/axios-retry

---

**Próxima revisión**: Después de implementar fixes, monitorear por 48h y actualizar este documento.
