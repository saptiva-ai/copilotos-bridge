# Optimización de Recursos del Sistema

## 📊 Análisis Actual de Recursos

### Estado de Memoria (RAM)

```
Total Sistema: 7.5 GB
Usado: 1.6 GB (21%)
Disponible: 5.6 GB (75%)
Swap: 2 GB (sin usar)
```

**Uso por Contenedor:**
| Contenedor | Memoria Usada | % del Límite | Límite |
|------------|---------------|--------------|--------|
| **API (FastAPI)** | 72 MB | 0.94% | 7.5 GB |
| **Web (Next.js)** | 372 MB | 4.87% | 7.5 GB |
| **MongoDB** | 180 MB | 2.37% | 7.5 GB |
| **Redis** | 4.3 MB | 0.06% | 7.5 GB |
| **TOTAL** | ~628 MB | ~8.4% | - |

### Estado de CPU

```
API:     0.23% - Mínimo (idle)
Web:     0.00% - Idle
MongoDB: 0.70% - Indexación/Background tasks
Redis:   0.80% - Cache operations
```

### Estado de Disco

**Uso de Docker:**
```
Imágenes:      59 GB total (55 GB reclaimable = 93%)
Contenedores:  18 MB
Volúmenes:     2.68 GB (2 GB reclaimable = 73%)
Build Cache:   21 GB (100% reclaimable)
```

**Problemas Identificados:**
- ✅ Contenedores activos: Solo 628 MB (óptimo)
- ⚠️ Imágenes sin usar: 55 GB desperdiciados
- ⚠️ Volúmenes huérfanos: 45 volúmenes no utilizados
- ⚠️ Build cache: 21 GB acumulado
- ⚠️ Imágenes dangling: 7+ imágenes de 380MB-1.33GB cada una

## 🎯 Recomendaciones de Optimización

### 1. Limpieza Inmediata de Docker (Libera ~76 GB)

#### Limpieza Segura (Recomendada)
```bash
# 1. Eliminar imágenes dangling (sin tag)
docker image prune -f
# Libera: ~5-8 GB

# 2. Eliminar build cache
docker builder prune -af
# Libera: ~21 GB

# 3. Eliminar volúmenes huérfanos
docker volume prune -f
# Libera: ~2 GB

# 4. Eliminar contenedores detenidos
docker container prune -f
# Libera: ~100 MB

# TOTAL ESTIMADO: ~28-31 GB liberados
```

#### Limpieza Agresiva (Solo si necesitas más espacio)
```bash
# Limpieza completa del sistema Docker
docker system prune -af --volumes

# ⚠️ ADVERTENCIA: Esto elimina:
# - Todos los contenedores detenidos
# - Todas las imágenes no usadas por al menos un contenedor
# - Todos los volúmenes no usados
# - Todo el build cache
# TOTAL ESTIMADO: ~55+ GB liberados
```

#### Script de Limpieza Automatizada
```bash
#!/bin/bash
# scripts/docker-cleanup.sh

echo "🧹 Iniciando limpieza de Docker..."

# Imágenes dangling
echo "1. Eliminando imágenes sin tag..."
docker image prune -f

# Contenedores detenidos
echo "2. Eliminando contenedores detenidos..."
docker container prune -f

# Build cache (mantener últimos 7 días)
echo "3. Limpiando build cache antiguo..."
docker builder prune -af --filter "until=168h"

# Volúmenes huérfanos (cuidado con datos)
echo "4. Eliminando volúmenes huérfanos..."
docker volume prune -f

echo "✅ Limpieza completada!"
docker system df
```

**Programar limpieza semanal:**
```bash
# Agregar a crontab
crontab -e

# Ejecutar cada domingo a las 3 AM
0 3 * * 0 /home/jazielflo/Proyects/copilotos-bridge/scripts/docker-cleanup.sh >> /tmp/docker-cleanup.log 2>&1
```

### 2. Optimización de Imágenes Docker

#### A. Reducir Tamaño de Imagen Web (De 1.33GB → ~400MB)

**Problema Actual:**
- Imagen de desarrollo: 1.33 GB
- Incluye dependencias de dev innecesarias
- node_modules sin optimizar

**Solución:**

```dockerfile
# apps/web/Dockerfile - Optimizaciones adicionales

# =========================================
# OPTIMIZACIÓN 1: Usar alpine más pequeño
# =========================================
FROM node:20-alpine AS base
# Alpine es ~50 MB vs ~150 MB de slim

# =========================================
# OPTIMIZACIÓN 2: Prune node_modules en prod
# =========================================
FROM base AS pruner

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages
COPY apps/web ./apps/web

# Eliminar devDependencies
RUN pnpm prune --prod

# =========================================
# OPTIMIZACIÓN 3: Usar en runner stage
# =========================================
FROM node:20-alpine AS runner
# ...
COPY --from=pruner --chown=app:appgroup /app/node_modules ./node_modules
# Resultado: Reduce ~200-300 MB
```

**Mejoras adicionales para next.config.js:**

```javascript
// apps/web/next.config.js
module.exports = {
  // Optimización de build
  swcMinify: true,

  // Reducir tamaño de bundle
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },

  // Standalone output (ya implementado)
  output: 'standalone',

  // Optimizar imágenes
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60,
  },
}
```

#### B. Optimizar Imagen API (De 380MB → ~250MB)

```dockerfile
# apps/api/Dockerfile - Optimizaciones

# =========================================
# OPTIMIZACIÓN 1: Multi-stage más agresivo
# =========================================
FROM python:3.11-alpine AS base  # Alpine en vez de slim
# Alpine: ~50 MB vs Slim: ~130 MB

# Instalar dependencias de compilación solo en stage temporal
FROM base AS builder
RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# =========================================
# OPTIMIZACIÓN 2: Stage final minimalista
# =========================================
FROM base AS production

# Solo copiar wheels compilados
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# El resto igual...
# Resultado: Reduce ~100-130 MB
```

**Optimizar requirements.txt:**
```bash
# Usar pip-tools para generar requirements.txt optimizado
pip install pip-tools

# Crear requirements.in con solo dependencias directas
cat > apps/api/requirements.in << EOF
fastapi
uvicorn[standard]
motor
beanie
redis
pydantic
python-jose[cryptography]
passlib[argon2]
structlog
EOF

# Generar requirements.txt con versiones bloqueadas
pip-compile requirements.in

# Resultado: Solo dependencias necesarias, sin duplicados
```

### 3. Configurar Límites de Recursos en Docker Compose

**Problema:** Sin límites, contenedores pueden consumir toda la RAM disponible.

**Solución:** Agregar límites en `docker-compose.yml`

```yaml
# infra/docker-compose.yml

services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1.0'      # Máximo 1 CPU core
          memory: 512M     # Máximo 512 MB RAM
        reservations:
          cpus: '0.25'     # Mínimo 25% de 1 core
          memory: 128M     # Mínimo 128 MB RAM

  web:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G       # Next.js necesita más para builds
        reservations:
          cpus: '0.25'
          memory: 256M

  mongodb:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M     # MongoDB puede usar mucho si no se limita
        reservations:
          cpus: '0.25'
          memory: 256M
    # Configurar WiredTiger cache
    command: >
      --wiredTigerCacheSizeGB 0.25  # Limitar cache a 256 MB

  redis:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M     # Redis es muy eficiente
        reservations:
          cpus: '0.1'
          memory: 32M
    # Limitar memoria de Redis
    command: >
      redis-server
      --maxmemory 100mb
      --maxmemory-policy allkeys-lru
```

**Beneficios:**
- Previene memory leaks que consuman todo el sistema
- Mejora estabilidad en producción
- Permite correr más servicios en el mismo hardware
- Facilita debugging de problemas de memoria

### 4. Optimizar MongoDB

#### A. Configuración de WiredTiger

```yaml
# docker-compose.yml
mongodb:
  command: >
    mongod
    --wiredTigerCacheSizeGB 0.25
    --wiredTigerCheckpointDelaySecs 60
```

#### B. Índices Eficientes

```python
# apps/api/src/models/user.py
from beanie import Indexed

class User(Document):
    username: Indexed(str, unique=True)  # Índice para búsquedas rápidas
    email: Indexed(str, unique=True)
    created_at: Indexed(datetime)  # Para queries con ORDER BY

    class Settings:
        # Optimización de cache
        use_cache = True
        cache_expiration_time = 300  # 5 minutos
```

#### C. Proyecciones en Queries

```python
# Antes (trae todos los campos)
users = await User.find().to_list()

# Después (solo campos necesarios)
users = await User.find(
    projection_model=UserListItem  # Solo id, username, email
).to_list()

# Reduce transferencia de datos y memoria
```

### 5. Optimizar Redis

#### A. Configuración de Memoria

```bash
# redis.conf o command en docker-compose
maxmemory 100mb
maxmemory-policy allkeys-lru  # Eliminar keys menos usadas

# Desactivar persistencia si no es crítico (gana velocidad)
save ""
appendonly no
```

#### B. Expiración de Keys

```python
# apps/api/src/services/cache_service.py

async def cache_with_ttl(key: str, data: dict, ttl: int = 300):
    """Cache con expiración automática"""
    await redis.setex(
        key,
        ttl,  # 5 minutos por defecto
        json.dumps(data)
    )

# Evita que el cache crezca indefinidamente
```

### 6. Optimización de Next.js

#### A. Configurar SWC Minifier

```javascript
// next.config.js
module.exports = {
  swcMinify: true,  // ~7x más rápido que Terser

  // Reducir bundle size
  modularizeImports: {
    'lodash': {
      transform: 'lodash/{{member}}',
    },
  },
}
```

#### B. Lazy Loading de Componentes

```typescript
// Antes
import HeavyComponent from './HeavyComponent'

// Después
import dynamic from 'next/dynamic'
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Spinner />,
  ssr: false,  // Solo en client-side si es pesado
})

// Reduce initial bundle en ~100-200 KB por componente pesado
```

#### C. Optimizar Fuentes

```typescript
// app/layout.tsx
import { Inter } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',  // Mejora performance
  preload: true,
})
```

### 7. Optimización de FastAPI

#### A. Workers de Uvicorn Dinámicos

```python
# apps/api/src/main.py
import multiprocessing

def get_workers():
    """Calcula workers óptimos basado en CPU"""
    cpus = multiprocessing.cpu_count()
    # Fórmula recomendada: (2 x CPU) + 1
    return min((2 * cpus) + 1, 4)  # Max 4 en desarrollo

# En Dockerfile CMD
CMD ["python", "-m", "uvicorn", "src.main:app",
     "--host", "0.0.0.0", "--port", "8001",
     "--workers", "2"]  # Configurar según servidor
```

#### B. Pooling de Conexiones

```python
# apps/api/src/core/database.py
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(
    MONGODB_URL,
    maxPoolSize=50,      # Máximo conexiones
    minPoolSize=10,      # Mínimo conexiones (mantiene pool caliente)
    maxIdleTimeMS=30000, # Cierra idle después de 30s
)
```

#### C. Redis Connection Pooling

```python
# apps/api/src/core/cache.py
import aioredis

redis_pool = aioredis.ConnectionPool(
    max_connections=20,
    decode_responses=True,
)
redis = aioredis.Redis(connection_pool=redis_pool)
```

### 8. Monitoreo de Recursos

#### A. Script de Monitoreo

```bash
#!/bin/bash
# scripts/monitor-resources.sh

echo "=== Docker Resources Monitor ==="
echo ""
echo "Container Stats:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""
echo "Disk Usage:"
docker system df
echo ""
echo "System Memory:"
free -h
echo ""
echo "Top Memory Consumers:"
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | sort -k2 -h -r | head -5
```

#### B. Prometheus + Grafana (Opcional)

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
```

## 📈 Resultados Esperados

### Antes de Optimizaciones
```
Disco Docker:      59 GB (55 GB reclaimable)
RAM Contenedores:  628 MB (sin límites)
Imagen Web:        1.33 GB
Imagen API:        380 MB
Build Time Web:    ~2-3 minutos
```

### Después de Optimizaciones
```
Disco Docker:      ~8-10 GB (limpieza regular)
RAM Contenedores:  ~600 MB (con límites configurados)
Imagen Web:        ~400-500 MB (-60%)
Imagen API:        ~250 MB (-35%)
Build Time Web:    ~1-1.5 minutos (-40%)
```

**Ahorro Total de Disco:** ~49 GB (83%)
**Reducción de Imágenes:** ~60% más pequeñas
**Mejora de Estabilidad:** Límites previenen OOM kills

## 🎯 Plan de Implementación Recomendado

### Fase 1: Limpieza Inmediata (5 minutos)
```bash
make clean-docker  # O ejecutar script de limpieza
```
**Impacto:** Libera ~28 GB inmediatamente

### Fase 2: Configurar Límites (10 minutos)
1. Agregar límites de recursos a `docker-compose.yml`
2. Reiniciar servicios: `make restart`

**Impacto:** Previene problemas futuros de memoria

### Fase 3: Optimizar Dockerfiles (30 minutos)
1. Implementar multi-stage más agresivos
2. Usar Alpine en vez de Slim donde sea posible
3. Rebuild imágenes: `make build`

**Impacto:** Reduce ~60% tamaño de imágenes

### Fase 4: Optimizaciones de Aplicación (1-2 horas)
1. Configurar MongoDB WiredTiger
2. Implementar lazy loading en Next.js
3. Configurar workers de Uvicorn
4. Optimizar queries con proyecciones

**Impacto:** Mejora performance general ~30-40%

### Fase 5: Monitoreo Continuo (Setup único)
1. Configurar script de limpieza automática
2. Agregar cron job semanal
3. Opcional: Setup Prometheus + Grafana

**Impacto:** Mantiene sistema optimizado a largo plazo

## 💡 Tips Adicionales

### Para Desarrollo
- Usar `docker-compose.dev.yml` con volúmenes para hot reload
- No configurar límites muy estrictos (dificulta debugging)
- Mantener build cache para builds rápidos

### Para Producción
- Usar `docker-compose.yml` con límites configurados
- Implementar limpieza automática cada semana
- Monitorear métricas con Prometheus
- Considerar Docker Swarm o Kubernetes para escalado

### Comandos Útiles
```bash
# Ver uso detallado de volúmenes
docker system df -v | grep volume

# Encontrar imágenes más grandes
docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | sort -k2 -h -r | head -10

# Monitoreo en tiempo real
watch -n 2 'docker stats --no-stream'

# Espacio usado por cada contenedor
docker ps -q | xargs docker inspect --format='{{.Name}}: {{.SizeRw}}' | sort -k2 -h -r
```
