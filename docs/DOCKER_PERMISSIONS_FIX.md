# 🔧 Docker Permissions Fix - Solución Completa

## 🎯 Problema Resuelto

Anteriormente, cuando Next.js se construía dentro de Docker, los archivos en `apps/web/.next` se creaban como `root`, causando problemas de permisos en el sistema host. Esto requería `sudo` para eliminar o modificar estos archivos.

## ✅ Solución Implementada

### 1. **Usuario No-Root en Dockerfile**
- ✅ Argumentos de build `UID` y `GID` configurables
- ✅ Usuario `app` con IDs que coinciden con el usuario host
- ✅ Todos los `COPY` usan `--chown=app:appgroup`
- ✅ Comandos `RUN` ejecutados como usuario `app`

### 2. **Docker Compose Mejorado**
- ✅ Variables de entorno `UID` y `GID` automáticas
- ✅ Configuración `user: "${UID:-1001}:${GID:-1001}"`
- ✅ Volúmenes nombrados para cache de Next.js

### 3. **Configuración de Next.js Optimizada**
- ✅ `distDir` dinámico: `/tmp/next-cache` en Docker, `.next` en local
- ✅ Variable de entorno `IN_DOCKER=1` para detección automática

### 4. **Volúmenes Nombrados para Cache**
```yaml
volumes:
  - next_cache:/app/apps/web/.next
  - next_standalone_cache:/tmp/next-cache
```

## 🚀 Uso

### Opción 1: Script Automático (Recomendado)
```bash
./scripts/fix-docker-permissions.sh
```

Este script:
- 🧹 Limpia archivos root existentes
- 🔧 Configura UID/GID automáticamente
- 🐳 Reconstruye imágenes con permisos correctos
- ✅ Verifica que todo funcione

### Opción 2: Manual
```bash
# 1. Limpiar archivos root (si existen)
sudo rm -rf apps/web/.next

# 2. Configurar variables de entorno
export UID=$(id -u)
export GID=$(id -g)

# 3. Construir con permisos correctos
cd infra
docker-compose build --no-cache web

# 4. Ejecutar
docker-compose up web
```

### Opción 3: Script de Conveniencia
```bash
# Para builds futuros, usar:
./scripts/docker-build.sh web
```

## 📋 Validación

### Verificar Permisos Correctos
```bash
# 1. Ejecutar un build
cd infra
UID=$(id -u) GID=$(id -g) docker-compose up --build web

# 2. Verificar que .next NO se crea como root
ls -ld apps/web/.next
# Debería mostrar tu usuario, NO root

# 3. Verificar que puedes eliminar sin sudo
rm -rf apps/web/.next  # No debería requerir sudo
```

### Verificar Usuario en Contenedor
```bash
# Verificar UID/GID dentro del contenedor
docker-compose exec web id
# Debería mostrar uid=1001(app) gid=1001(appgroup) o tus IDs reales
```

## 🔧 Características Técnicas

### Dockerfile Actualizado
```dockerfile
# Argumentos configurables
ARG UID=1001
ARG GID=1001

# Usuario con IDs del host
RUN addgroup --system --gid ${GID} appgroup
RUN adduser --system --uid ${UID} --ingroup appgroup app

# Todos los archivos owned por app
COPY --chown=app:appgroup source/ destination/

# Ejecutar como non-root
USER app
```

### Docker Compose Configurado
```yaml
web:
  build:
    args:
      UID: ${UID:-1001}
      GID: ${GID:-1001}
  user: "${UID:-1001}:${GID:-1001}"
  volumes:
    - next_cache:/app/apps/web/.next
```

### Next.js Config Inteligente
```javascript
const nextConfig = {
  // Cache en ubicación que no causa problemas de permisos
  distDir: process.env.IN_DOCKER === '1' ? '/tmp/next-cache' : '.next',
}
```

## 🎯 Beneficios

1. **✅ Sin archivos root**: Todos los archivos creados pertenecen a tu usuario
2. **✅ Sin sudo requerido**: Puedes eliminar/modificar archivos normalmente
3. **✅ Portable**: Funciona en cualquier máquina con cualquier UID/GID
4. **✅ Automático**: Se configura automáticamente con el script
5. **✅ Cache eficiente**: Volúmenes nombrados mejoran performance
6. **✅ Seguro**: Contenedores ejecutan como non-root

## 🛡️ Seguridad

- **Principio de menor privilegio**: Contenedores no ejecutan como root
- **Aislamiento**: Volúmenes nombrados evitan contaminar el host
- **Consistencia**: Mismos permisos en desarrollo y producción

## 🔄 Workflow Típico

```bash
# Primera vez o después de problemas de permisos
./scripts/fix-docker-permissions.sh

# Desarrollo normal
cd infra
docker-compose up

# Builds futuros
./scripts/docker-build.sh web
```

## ❓ Troubleshooting

### Si sigues viendo archivos root:
```bash
# Verificar que las variables estén configuradas
echo "UID=$UID, GID=$GID"

# Re-ejecutar el script de fix
./scripts/fix-docker-permissions.sh

# Forzar rebuild completo
docker system prune -f
./scripts/fix-docker-permissions.sh
```

### Si el contenedor no arranca:
```bash
# Verificar logs
docker-compose logs web

# Verificar que el usuario app existe
docker-compose exec web id
```

---

**✨ Resultado Final**: ¡No más `sudo rm -rf apps/web/.next`! Todos los archivos creados por Docker respetan tus permisos de usuario local.