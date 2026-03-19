# Deploy Scripts

Scripts para build, push y deploy de servicios OctaviOS.

> **Full Documentation**: See [docs/manuals/deploy/README.md](../../docs/manuals/deploy/README.md) for complete deployment guides and best practices.

## Scripts disponibles

| Script | Descripción | Common Usage |
|--------|-------------|--------------|
| `detect-changes.sh` | Detecta qué servicios cambiaron | `./detect-changes.sh --since-tag v1.4.6` |
| `build.sh` | Construye imágenes Docker | `./build.sh -v 1.4.7 -s backend` |
| `push.sh` | Push de imágenes a Docker Hub | `./push.sh -v 1.4.7 -s backend` |
| `update-images.sh` | Actualiza versiones en docker-compose.images.yml | `./update-images.sh -v 1.4.7` |
| `validate-deploy.sh` | Valida el estado del deploy | `./validate-deploy.sh 1.4.7` |
| `load-env.sh` | Carga variables de entorno | `source ./load-env.sh` |

## Quick Reference

```bash
# Full deploy flow (single service)
./scripts/deploy/build.sh -v 1.4.7 -s backend
./scripts/deploy/push.sh -v 1.4.7 -s backend
./scripts/deploy/update-images.sh -v 1.4.7 -s backend
git add -A && git commit -m "chore(deploy): bump backend to v1.4.7"
git push origin main
```

## ⚠️ Critical Best Practices

### When deploying bug fixes:

1. **Use `--no-cache`** to ensure your fix is included in the image:
   ```bash
   docker build --no-cache -t saptivaai/octavios-invex-backend:1.4.7 \
       -f apps/backend/Dockerfile apps/backend/
   ```

2. **Verify fix is in image BEFORE pushing**:
   ```bash
   docker run --rm saptivaai/octavios-invex-backend:1.4.7 \
       grep "YOUR_FIX_COMMENT" /app/src/services/file.py
   ```

3. **On production: ALWAYS remove the shared volume**:
   ```bash
   docker volume rm octavios-chat-bajaware_invex_backend_shared
   ```
   Without this step, old code in the volume will override your image changes!

4. **Flush Redis after deploy**:
   ```bash
   docker exec backend python3 -c \
       "import os,redis;r=redis.from_url(os.environ.get('REDIS_URL'));r.flushall()"
   ```

## Uso

### Detectar cambios

```bash
# Comparar con commit anterior
./detect-changes.sh

# Comparar con tag específico
./detect-changes.sh --since-tag v1.4.1

# Output JSON para scripts
./detect-changes.sh --json
# {"services": ["backend", "web"], "all": false, "changes": 5}

# Ver ayuda
./detect-changes.sh --help
```

### Build de imágenes

```bash
# Build de todos los servicios
./build.sh -v 1.4.2

# Build de un servicio específico
./build.sh -v 1.4.2 -s backend

# Dry run (solo muestra comandos)
./build.sh -v 1.4.2 --dry-run

# Auto-incrementar versión desde último tag
./build.sh --next
```

### Push a Docker Hub

```bash
# Push de todos los servicios
./push.sh -v 1.4.2

# Push de un servicio específico
./push.sh -v 1.4.2 -s backend

# Dry run
./push.sh -v 1.4.2 --dry-run
```

### Actualizar docker-compose.images.yml

```bash
# Actualizar todos los servicios
./update-images.sh -v 1.4.2

# Actualizar solo un servicio
./update-images.sh -v 1.4.2 -s backend

# Dry run
./update-images.sh -v 1.4.2 --dry-run
```

## CI/CD Integration

El workflow unificado `.github/workflows/ci-cd.yml` maneja todo el pipeline:

### Flujo automático

| Trigger | Tests | Build | Deploy |
|---------|-------|-------|--------|
| Push a `develop` | ✓ Servicios afectados | ✗ | ✗ |
| PR a `main`/`develop` | ✓ Servicios afectados | ✗ | ✗ |
| Push a `main` | ✓ Servicios afectados | ✓ Solo cambiados | ✗ |
| Tag `v*` | ✓ Servicios afectados | ✓ Solo cambiados | ✓ Producción |
| Manual | Configurable | ✓ Seleccionados | ✓ Opcional |

### Características

- **Detección granular**: Solo ejecuta jobs para servicios con cambios
- **Matrix dinámico**: Build paralelo de múltiples servicios
- **Auto-versioning**: Incrementa patch version desde último tag
- **Security scan**: Trivy en PRs y main branch

### Secrets requeridos en GitHub

| Secret | Descripción |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Usuario Docker Hub |
| `DOCKERHUB_TOKEN` | Token de acceso |
| `PROD_HOST` | IP del servidor de producción |
| `PROD_USER` | Usuario SSH |
| `PROD_SSH_KEY` | Clave privada SSH |
| `PROD_PATH` | Path del proyecto en producción |

## Mapeo de servicios a paths

| Servicio | Paths que lo afectan |
|----------|---------------------|
| `backend` | `apps/backend/` |
| `web` | `apps/web/`, `packages/` |
| `file-manager` | `plugins/public/file-manager/` |

Cambios en `infra/` afectan a **todos** los servicios.

## Flujo de deploy manual

```bash
# 1. Detectar qué cambió
./scripts/deploy/detect-changes.sh --since-tag v1.4.1

# 2. Build solo lo que cambió (ejemplo: solo backend)
./scripts/deploy/build.sh -v 1.4.2 -s backend

# 3. Push a Docker Hub
./scripts/deploy/push.sh -v 1.4.2 -s backend

# 4. Actualizar compose
./scripts/deploy/update-images.sh -v 1.4.2 -s backend

# 5. En producción
ssh user@prod
cd /path/to/project
git pull
docker pull saptiva/octavios-backend:1.4.2
docker compose -f infra/docker-compose.yml -f infra/docker-compose.images.yml up -d backend
```
