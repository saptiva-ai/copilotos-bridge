# Makefile - Comandos de Optimización de Recursos

## Comandos Disponibles

### 1. `make resources`

**Descripción:** Muestra un resumen completo del uso de recursos de Docker y del sistema.

**Output:**
```
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵  📊 Docker Resources Summary
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟡 Docker Disk Usage:
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          4         4         2.924GB   18.86MB (0%)
Containers      4         4         18.76MB   0B (0%)
Local Volumes   24        4         1.532GB   1.164GB (75%)
Build Cache     0         0         0B        0B

🟡 Container Resources:
CONTAINER      CPU %     MEM USAGE / LIMIT     MEM %
copilotos-web  0.02%     378MiB / 7.465GiB     4.95%
copilotos-api  0.23%     75.79MiB / 7.465GiB   0.99%
...

🟡 System Memory:
              total        used        free      available
Mem:          7.5Gi       1.8Gi       4.8Gi     5.5Gi
Swap:         2.0Gi          0B       2.0Gi
```

**Cuándo usar:**
- Verificar cuánto espacio están usando tus contenedores
- Identificar si hay espacio reclaimable
- Monitorear uso de RAM y CPU de contenedores

---

### 2. `make resources-monitor`

**Descripción:** Monitoreo en tiempo real de recursos de Docker (actualiza cada 2 segundos).

**Output:**
```
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵  📊 Real-time Resource Monitor (Ctrl+C to stop)
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTAINER      CPU %     MEM USAGE / LIMIT     MEM %     NET I/O
copilotos-web  0.15%     380MiB / 7.465GiB     4.98%     1.2kB / 0B
copilotos-api  0.30%     76MiB / 7.465GiB      1.00%     0B / 0B
...
```

**Cuándo usar:**
- Debugging de problemas de performance
- Identificar contenedores que consumen muchos recursos
- Verificar que los límites de recursos están funcionando

**Tip:** Presiona `Ctrl+C` para salir del monitor

---

### 3. `make docker-cleanup`

**Descripción:** Limpieza segura de Docker (build cache, imágenes dangling, contenedores detenidos).

**Características:**
- ✅ Elimina build cache antiguo (>7 días)
- ✅ Elimina imágenes sin tag (dangling)
- ✅ Elimina contenedores detenidos
- ⚠️ Pregunta confirmación para volúmenes huérfanos
- ✅ NO afecta contenedores activos
- ✅ NO afecta imágenes en uso

**Output:**
```
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵  🧹 Docker Safe Cleanup
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Uso actual de Docker:
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          34        4         46.83GB   44.3GB (94%)
...

1. Eliminando imágenes sin tag (dangling)...
✓ Eliminadas 7 imágenes dangling

2. Eliminando contenedores detenidos...
✓ Eliminados 8 contenedores detenidos

3. Limpiando build cache antiguo (>7 días)...
✓ Build cache antiguo eliminado

4. Volúmenes huérfanos detectados:
   Encontrados 45 volúmenes huérfanos
   ¿Eliminar volúmenes huérfanos? (y/N):
```

**Cuándo usar:**
- Mantenimiento semanal regular
- Antes de deployments importantes
- Cuando el disco se está llenando
- Después de múltiples rebuilds

**Espacio típico liberado:** 5-30 GB

---

### 4. `make docker-cleanup-aggressive`

**Descripción:** Limpieza agresiva que elimina TODO lo que no esté en uso actualmente.

**⚠️ ADVERTENCIA:** Este comando elimina:
- ❌ TODAS las imágenes no usadas por contenedores activos
- ❌ TODOS los volúmenes huérfanos
- ❌ TODO el build cache
- ✅ NO afecta contenedores activos ni sus imágenes

**Confirmación requerida:**
```
⚠️  WARNING: This will remove ALL unused Docker images and volumes!
Active containers will NOT be affected.

Are you sure? (yes/NO):
```

**Output:**
```
Removing all unused images...
Deleted Images:
untagged: old-image:latest
...
Total reclaimed space: 44.3GB

Removing all unused volumes...
Total reclaimed space: 2.3GB

Removing all build cache...
Total reclaimed space: 25.5GB

✓ Aggressive cleanup completed!

TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          4         4         2.9GB     0B (0%)
Containers      4         4         18.7MB    0B (0%)
Local Volumes   4         4         370MB     0B (0%)
Build Cache     0         0         0B        0B
```

**Cuándo usar:**
- Cuando necesitas liberar MUCHO espacio rápido
- Antes de re-clonar el proyecto
- Limpieza profunda mensual
- Preparación para deployment mayor

**Espacio típico liberado:** 50-70 GB

**⚠️ Consecuencias:**
- Next.js necesitará rebuildearse desde cero
- Primeros builds serán más lentos (sin cache)
- Imágenes de test/desarrollo serán eliminadas

---

### 5. `make build-optimized`

**Descripción:** Build de imágenes con optimizaciones activadas.

**Optimizaciones incluidas:**
- ✅ Multi-stage builds (separación build/runtime)
- ✅ Build cache inline (reutilización entre builds)
- ✅ Layer caching optimizado
- ✅ Eliminación de dependencias de desarrollo en producción

**Output:**
```
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵  🏗️  Building Optimized Docker Images
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Optimizations enabled:
  • Multi-stage builds
  • Alpine base images where possible
  • Build cache utilization
  • Layer optimization

Building API (FastAPI)...
[+] Building 45.2s (18/18) FINISHED
...

Building Web (Next.js)...
[+] Building 120.5s (25/25) FINISHED
...

✓ Optimized images built successfully!

Image sizes:
copilotos-api    latest    290MB
copilotos-web    latest    1.06GB
```

**Cuándo usar:**
- Builds para producción
- Cuando quieres imágenes más pequeñas
- Antes de push a registry
- Deployment optimizado

**Beneficios:**
- Imágenes 30-50% más pequeñas
- Builds subsecuentes más rápidos (cache)
- Menos transferencia de red en deploys
- Menor uso de disco en producción

---

### 6. `make deploy-optimized`

**Descripción:** Workflow completo de deployment optimizado.

**Pasos automáticos:**
1. **Cleanup** → Elimina build cache antiguo (>7 días)
2. **Build** → Construye imágenes optimizadas con cache
3. **Deploy** → Ejecuta `make deploy-clean`
4. **Post-cleanup** → Elimina dangling images generadas
5. **Report** → Muestra uso de recursos final

**Output:**
```
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵  🚀 Optimized Deployment Workflow
🔵━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Cleanup old artifacts...
Deleted build cache 154MB

Step 2: Building optimized images...
[Runs make build-optimized]

Step 3: Deploying with resource limits...
[Runs make deploy-clean]

✓ Optimized deployment completed!

Post-deployment cleanup...
Deleted dangling images: 3.4GB

[Shows final resource usage]
```

**Cuándo usar:**
- Deployment a producción
- Deployment crítico que debe ser confiable
- Cuando quieres asegurar imágenes limpias
- Releases importantes

**Tiempo estimado:** 15-20 minutos (build completo)

**Ventajas vs `make deploy-clean`:**
- Limpieza automática pre/post deployment
- Optimizaciones de build activadas
- Reporte de recursos incluido
- Menos intervención manual

---

## Workflows Recomendados

### Desarrollo Diario
```bash
# Ver recursos
make resources

# Si hay >10 GB reclaimable
make docker-cleanup
```

### Mantenimiento Semanal
```bash
# Limpieza segura
make docker-cleanup

# Verificar resultado
make resources
```

### Limpieza Profunda Mensual
```bash
# Backup importante primero (opcional)
make db-backup

# Limpieza agresiva
make docker-cleanup-aggressive

# Rebuild si es necesario
make dev-build
```

### Deployment a Producción
```bash
# Opción 1: Rápido (si builds recientes son buenos)
make deploy-quick

# Opción 2: Optimizado (recomendado)
make deploy-optimized

# Opción 3: Clean build (garantizado fresco)
make deploy-clean
```

---

## Usar Límites de Recursos

### Activar Límites de Recursos

```bash
# Development con límites
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.dev.yml \
               -f infra/docker-compose.resources.yml \
               up

# Production con límites (recomendado)
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.resources.yml \
               up
```

### Límites Configurados

| Servicio | CPU Max | RAM Max | RAM Min |
|----------|---------|---------|---------|
| API      | 1 core  | 512 MB  | 128 MB  |
| Web      | 1 core  | 1 GB    | 256 MB  |
| MongoDB  | 1 core  | 512 MB  | 256 MB  |
| Redis    | 0.5 core| 128 MB  | 32 MB   |

### Beneficios de Límites

- ✅ Previene memory leaks que consuman toda la RAM
- ✅ Distribución justa de recursos
- ✅ Facilita debugging (límites claros)
- ✅ Permite correr más servicios en mismo hardware
- ✅ Evita OOM kills del sistema operativo

---

## Tips y Mejores Prácticas

### 1. Monitoreo Regular
```bash
# Ver uso actual
make resources

# Monitoreo continuo durante desarrollo
make resources-monitor
```

### 2. Limpieza Preventiva
```bash
# Cada semana
make docker-cleanup

# Antes de deployment importante
make docker-cleanup
```

### 3. Identificar Problemas

**Si un contenedor usa mucha RAM:**
```bash
# Ver logs para memory errors
make logs-api | grep -i "memory\|oom"

# Ver stats en tiempo real
make resources-monitor
```

**Si build cache crece mucho:**
```bash
# Ver tamaño
docker system df

# Si >20 GB, limpiar
docker builder prune -af
```

### 4. Automatización

**Cron job para limpieza semanal:**
```bash
# Editar crontab
crontab -e

# Agregar (domingos 3 AM)
0 3 * * 0 cd /path/to/copilotos-bridge && make docker-cleanup >> /tmp/cleanup.log 2>&1
```

---

## Advertencias Importantes

### NO hacer en Producción Activa
```bash
# NUNCA en prod activo
make docker-cleanup-aggressive  # Puede eliminar imágenes en uso
make clean-volumes              # PÉRDIDA DE DATOS
```

### HACER Regularmente
```bash
# Seguro en cualquier momento
make resources                  # Solo lectura
make docker-cleanup             # Limpieza segura
make resources-monitor          # Solo observación
```

### Antes de Limpieza Agresiva
```bash
# 1. Backup de datos importantes
make db-backup

# 2. Verificar qué se eliminará
docker images --filter "dangling=false"

# 3. Confirmar que no hay deployments en curso
make status
```

---

## Métricas de Éxito

### Uso Óptimo de Recursos

| Métrica | Óptimo | Aceptable | Acción Requerida |
|---------|--------|-----------|------------------|
| Docker Images | <5 GB | 5-10 GB | >10 GB → Cleanup |
| Build Cache | <5 GB | 5-15 GB | >15 GB → Prune |
| Volúmenes | <2 GB | 2-5 GB | >5 GB → Review |
| RAM Contenedores | <1 GB | 1-2 GB | >2 GB → Investigate |

### Después de Limpieza Exitosa

```
✅ Antes:  75 GB Docker total
✅ Después: 4.5 GB Docker total
✅ Liberado: 70.5 GB (94% reducción)
```

---

## 🆘 Troubleshooting

### Problema: "No se liberó espacio después de cleanup"

**Causa:** Imágenes aún en uso por contenedores detenidos.

**Solución:**
```bash
# Ver contenedores detenidos
docker ps -a

# Eliminar contenedores detenidos
docker container prune -f

# Retry cleanup
make docker-cleanup
```

### Problema: "Build falló después de cleanup agresivo"

**Causa:** Build cache eliminado, build desde cero.

**Solución:** Es esperado, solo toma más tiempo.
```bash
# Primera vez será lenta
make dev-build  # ~5-10 minutos

# Subsecuentes builds rápidas (cache rebuildeado)
make dev-build  # ~1-2 minutos
```

### Problema: "Container killed (OOMKilled)"

**Causa:** Contenedor excedió límite de memoria.

**Solución:**
```bash
# Ver logs
docker logs <container_id>

# Opción 1: Aumentar límite en docker-compose.resources.yml
# memory: 512M → memory: 1G

# Opción 2: Deshabilitar límites temporalmente
# No usar docker-compose.resources.yml
```

---

## Referencias

- [Docker System Prune](https://docs.docker.com/engine/reference/commandline/system_prune/)
- [Docker Resource Constraints](https://docs.docker.com/config/containers/resource_constraints/)
- [RESOURCE_OPTIMIZATION.md](./RESOURCE_OPTIMIZATION.md) - Guía completa
- [Makefile](../Makefile) - Código fuente de comandos
