# Deploy Manual

> Referencia operativa para deployar OctaviOS Chat a produccion.
>
> **Regla #1**: Siempre usar los scripts de `scripts/deploy/`. Los comandos manuales
> de Docker solo se documentan como referencia de emergencia.

---

## 1. Consultar versiones

La fuente de verdad es el manifiesto `infra/docker-compose.images.yml`.

```bash
# Ver todas las versiones vigentes
grep 'image:' infra/docker-compose.images.yml

# Ver version de un servicio especifico
grep 'octavios-invex-backend:' infra/docker-compose.images.yml
grep 'octavios-invex-dashboard:' infra/docker-compose.images.yml
```

### Tracks de versionado

| Track | Servicios | Descripcion |
|-------|-----------|-------------|
| **principal** | backend, web, bank-advisor | Comparten cadencia de release. `--next` auto-incrementa desde la version del backend. |
| **independiente** | dashboard | Versionado propio (ej: 1.0.x). Siempre requiere `-s dashboard -v $DASH_VERSION`. |
| **congelado** | file-manager | No cambia entre releases salvo parche critico. |

> **Nunca** usar `--next` para dashboard: leeria la version del backend y asignaria un tag incorrecto.

---

## 2. Flujo de deploy (scripts)

Todos los scripts estan en `scripts/deploy/` y aceptan `--dry-run` para previsualizar sin ejecutar.

### Paso a paso

```
 build.sh  →  push.sh  →  update-images.sh  →  git commit/push  →  PROD deploy
```

### 2.1 Build

```bash
# Servicios principales — auto-incremento de version
./scripts/deploy/build.sh --next                # patch (mas comun)
./scripts/deploy/build.sh --next minor          # minor
./scripts/deploy/build.sh --next major          # major

# Servicios principales — version explicita
./scripts/deploy/build.sh -v $VERSION

# Dashboard — siempre version explicita
./scripts/deploy/build.sh -s dashboard -v $DASH_VERSION

# Un solo servicio principal
./scripts/deploy/build.sh -s backend -v $VERSION
```

Que hace `build.sh`:
- Habilita BuildKit automaticamente.
- Genera 4 tags por servicio: local, `$VERSION`, `$VERSION-$DATETIME`, `latest`.
- Conoce el target y contexto correcto de cada servicio (ver tabla abajo).
- `--next` lee la version actual del manifiesto y la incrementa.

### 2.2 Push a Docker Hub

```bash
# Servicios principales
./scripts/deploy/push.sh -v $VERSION

# Dashboard
./scripts/deploy/push.sh -s dashboard -v $DASH_VERSION

# Un solo servicio
./scripts/deploy/push.sh -s backend -v $VERSION

# Sin tag :latest (raro, pero util para pre-releases)
./scripts/deploy/push.sh -v $VERSION --skip-latest
```

Que hace `push.sh`:
- Verifica login en Docker Hub (soporta credential helpers modernos).
- Retry automatico: 3 intentos con 5s de espera entre cada uno.
- Pusha tag `$VERSION` + `latest` por servicio.

### 2.3 Actualizar manifiesto

```bash
# Servicios principales
./scripts/deploy/update-images.sh -v $VERSION

# Dashboard (solo cambia su linea, no toca el header)
./scripts/deploy/update-images.sh -s dashboard -v $DASH_VERSION

# Un solo servicio
./scripts/deploy/update-images.sh -s backend -v $VERSION
```

Que hace `update-images.sh`:
- Crea backup automatico (`docker-compose.images.yml.bak`).
- Detecta la version actual *per-service* (dashboard lee su propia version, no la del backend).
- Actualiza el header del manifiesto solo cuando cambian servicios principales.

### 2.4 Commit, push, deploy en PROD

```bash
# Commit local
git add infra/docker-compose.images.yml
git commit -m "chore: bump $SERVICE $VERSION"
git push origin main

# En PROD
ssh $PROD_USER@$PROD_HOST
cd $PROD_DIR
git pull origin main

docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.images.yml \
  -f infra/docker-compose.production.yml \
  --env-file envs/.env \
  rm -sf $SERVICE                           # detener solo lo que cambia

docker volume rm octavios-chat-bajaware_invex_backend_shared 2>/dev/null || true  # solo si backend cambia

docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.images.yml \
  -f infra/docker-compose.production.yml \
  --env-file envs/.env \
  pull $SERVICE

docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.images.yml \
  -f infra/docker-compose.production.yml \
  --env-file envs/.env \
  up -d $SERVICE
```

### 2.5 Post-deploy

```bash
# Flush Redis (requiere auth)
docker exec octavios-chat-bajaware_invex-redis \
  redis-cli -a $(docker exec octavios-chat-bajaware_invex-redis printenv REDIS_PASSWORD) FLUSHDB

# Health checks
curl -sf http://localhost:8000/api/health | python3 -m json.tool   # backend
curl -sf http://localhost:8050/dashboard/ -o /dev/null -w '%{http_code}\n'  # dashboard
curl -sf http://localhost:8002/health | python3 -m json.tool       # bank-advisor
curl -sf http://localhost:3000 -o /dev/null -w '%{http_code}\n'    # web

# Limpiar imagenes viejas
docker image prune -af --filter 'until=24h'

# Eliminar imagenes duplicadas de versiones anteriores
# Listar todas las imagenes del proyecto con sus versiones:
docker images 'saptivaai/octavios-invex-*' --format '{{.Repository}}\t{{.Tag}}\t{{.Size}}' | sort
# Eliminar versiones que ya no se usan (ejemplo: v1.4.35 reemplazada por v1.4.36):
docker rmi saptivaai/octavios-invex-backend:1.4.35 \
  saptivaai/octavios-invex-bank-advisor:1.4.35 \
  saptivaai/octavios-invex-web:1.4.35
# Verificar que solo quedan las versiones actuales:
docker images 'saptivaai/octavios-invex-*' --format '{{.Repository}}\t{{.Tag}}\t{{.Size}}' | sort
```

> **Regla**: Despues de cada deploy exitoso, eliminar las imagenes de la version anterior.
> Cada version de los 3 servicios principales ocupa ~2.7GB. Acumular versiones viejas
> llena el disco rapidamente.

### 2.6 Dry-run

Cualquier script acepta `--dry-run` para ver que haria sin ejecutar nada:

```bash
./scripts/deploy/build.sh --next --dry-run
./scripts/deploy/push.sh -v $VERSION --dry-run
./scripts/deploy/update-images.sh -s dashboard -v $DASH_VERSION --dry-run
```

---

## 3. Referencia de scripts

| Script | Que hace | Flags clave |
|--------|----------|-------------|
| `build.sh` | Construye imagenes Docker | `-v`, `-s`, `--next [patch\|minor\|major]`, `--dry-run` |
| `push.sh` | Push a Docker Hub con retry | `-v`, `-s`, `--skip-latest`, `--dry-run` |
| `update-images.sh` | Actualiza el manifiesto | `-v`, `-s`, `-c` (changelog), `--dry-run` |
| `detect-changes.sh` | Detecta servicios con cambios desde ultimo tag | — |
| `validate-deploy.sh` | Valida que el deploy este correcto | — |
| `load-env.sh` | Carga variables de entorno | — |

### Configuracion de build por servicio

| Servicio | Dockerfile | Contexto | Target | Build args |
|----------|-----------|----------|--------|------------|
| backend | `apps/backend/Dockerfile` | `apps/backend/` | `production` | — |
| web | `apps/web/Dockerfile` | `.` (raiz) | `runner` | `NEXT_PUBLIC_API_URL=""` |
| bank-advisor | `plugins/bank-advisor-private/Dockerfile` | `.` (raiz) | — | — |
| dashboard | `apps/dashboard/Dockerfile` | `apps/dashboard/` | — | — |

---

## 4. Detectar versiones de imagenes

### Version en el manifiesto (fuente de verdad)

```bash
grep 'image:' infra/docker-compose.images.yml
```

### Version corriendo en PROD

```bash
# En el servidor PROD
docker inspect --format '{{.Config.Image}}' $(docker ps -q --filter name=$SERVICE)
```

### Version en Docker Hub

```bash
# Listar tags remotos (requiere login)
docker manifest inspect saptivaai/octavios-invex-$SERVICE:$VERSION > /dev/null 2>&1 \
  && echo "EXISTS" || echo "NOT FOUND"
```

### Comparar local vs PROD vs manifiesto

```bash
# Local: que imagen esta tageada
docker images saptivaai/octavios-invex-$SERVICE --format '{{.Tag}}' | sort -V

# Manifiesto: que dice el archivo
grep "octavios-invex-$SERVICE:" infra/docker-compose.images.yml

# PROD: que corre en el servidor
ssh $PROD_USER@$PROD_HOST "docker images saptivaai/octavios-invex-$SERVICE --format '{{.Tag}}' | sort -V"
```

---

## 5. Best practices

### Versionado

- **Nunca** reusar un tag de version existente. Si `1.4.35` ya fue pusheado, usar `1.4.36`.
- **Siempre** incrementar: patch para bug fixes, minor para features, major para breaking changes.
- Dashboard y servicios principales tienen tracks separados. No mezclar versiones.
- Usar `--dry-run` antes de ejecutar cualquier script para verificar el output esperado.

### Build

- Usar los scripts (`build.sh`) en lugar de `docker build` directo. Los scripts configuran BuildKit, tags consistentes y el contexto correcto por servicio.
- **Nunca** buildear imagenes en PROD. Siempre build local → push → pull en PROD.
- Para bug fixes criticos usar `--no-cache` en build manual. Los scripts usan `BUILDKIT_INLINE_CACHE` que cubre la mayoria de casos.

### Push

- Verificar login antes de push: `push.sh` lo hace automaticamente (soporta credential helpers).
- **Siempre** pushear tanto el tag de version como `:latest`.
- Si el push falla, el script reintenta 3 veces. Si sigue fallando, verificar `docker login -u saptivaai`.

### Manifiesto

- `infra/docker-compose.images.yml` es la **unica fuente de verdad** para versiones en PROD.
- Agregar siempre un bloque de changelog en los comentarios del manifiesto al actualizar.
- Commit del manifiesto separado del commit de codigo: `chore: bump $SERVICE $VERSION`.
- **Nunca** editar el manifiesto a mano si `update-images.sh` puede hacerlo.

### Deploy en PROD

- **Siempre** usar los 3 archivos compose + env-file (ver seccion Compose flags).
- **Siempre** eliminar el volumen `backend_shared` cuando backend cambia — evita que codigo viejo persista.
- **Siempre** hacer `pull` antes de `up -d` para asegurar que la imagen nueva se descargue.
- **Siempre** flush Redis despues de deploy de backend (evita cache stale).
- **Siempre** correr health checks despues del deploy.
- Limpiar imagenes viejas con `docker image prune -af --filter 'until=24h'`.
- **Siempre** eliminar imagenes de la version anterior despues de un deploy exitoso (~2.7GB por release).

### Orden de operaciones (checklist)

1. `build.sh` — construir imagen(es)
2. `push.sh` — subir a Docker Hub
3. `update-images.sh` — actualizar manifiesto
4. `git commit && git push` — pushear manifiesto a main
5. SSH a PROD → `git pull` → `rm -sf` → `volume rm` → `pull` → `up -d`
6. Redis flush + health checks + image prune
7. Eliminar imagenes de version anterior (`docker rmi saptivaai/octavios-invex-*:$OLD_VERSION`)

---

## 6. Compose flags

Siempre usar los 3 archivos + env-file en PROD:

```bash
COMPOSE="docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.images.yml \
  -f infra/docker-compose.production.yml \
  --env-file envs/.env"

$COMPOSE up -d
$COMPOSE logs -f $SERVICE
$COMPOSE ps
```

---

## 7. Servicios y puertos

| Servicio | Puerto | Health endpoint |
|----------|--------|-----------------|
| backend | 8000 | `/api/health` |
| bank-advisor | 8002 | `/health` |
| web | 3000 | `/` (200 OK) |
| dashboard | 8050 | `/dashboard/` (200 OK) |
| mongodb | 27017 | — |
| redis | 6379 | — |

---

## 8. MongoDB en PROD

```bash
docker exec <mongodb-container> \
  mongosh -u $MONGODB_USER -p $MONGODB_PASSWORD \
  --authenticationDatabase admin $MONGODB_DATABASE \
  --eval 'QUERY'
```

Ejemplos utiles:
```js
// Contar por status
db.message_feedback.aggregate([{$group: {_id: "$status", count: {$sum: 1}}}])

// Migrar status
db.message_feedback.updateMany({status: "OLD"}, {$set: {status: "NEW"}})

// Ver tickets con feedback
db.message_feedback.aggregate([
  {$match: {ticket_id: {$ne: null}}},
  {$group: {_id: {ticket: "$ticket_id", status: "$status"}, n: {$sum: 1}}},
  {$sort: {"_id.ticket": 1}}
])
```

---

## 9. Errores comunes

### Codigo no se actualiza despues del deploy

**Causa**: Volumen `backend_shared` monta codigo viejo sobre la imagen.

**Fix**: `docker volume rm octavios-chat-bajaware_invex_backend_shared` antes de levantar.

### Redis devuelve datos viejos

**Fix**: `docker exec ...-redis redis-cli -a $REDIS_PASSWORD FLUSHDB`

### Web muestra CORS errors con localhost:8000

**Causa**: `NEXT_PUBLIC_API_URL` se hardcodea en build time.

**Fix**: Rebuildir con `--build-arg NEXT_PUBLIC_API_URL=""` y verificar:
```bash
docker run --rm $IMAGE sh -c "grep -r 'localhost:8000' /app/apps/web/.next/static/chunks/" \
  && echo "FAIL" || echo "OK"
```

### `docker compose up -d` dice "up-to-date" pero corre codigo viejo

**Fix**: `docker compose ... up -d --force-recreate $SERVICE`

### Build no incluye cambios recientes

**Fix**: Usar `--no-cache` en build manual. Los scripts usan `BUILDKIT_INLINE_CACHE`.

### Push dice "not logged in" a pesar de estarlo

**Causa**: `docker info` no muestra Username con credential helpers modernos.

**Fix**: Verificar auth en `~/.docker/config.json`:
```bash
cat ~/.docker/config.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.get('auths',{}).keys()))"
```
Si no hay auths: `docker login -u saptivaai`

---

## 10. Git y Pull Requests

### Flujo de branches

```
main (produccion)
 └── develop (integracion)
      └── feat/fix-xxx (trabajo diario)
```

- `main` es la rama de produccion. Solo recibe merges via PR.
- `develop` es la rama de integracion donde se acumulan cambios.
- Branches de trabajo se crean desde `develop`.

### Workflow para deploy

```bash
# 1. Crear branch de trabajo desde develop
git checkout develop && git pull origin develop
git checkout -b fix/my-feature-branch

# 2. Hacer commits con prefijo convencional
git commit -m "fix(scope): descripcion del cambio"

# 3. Push y crear PR a develop
git push -u origin fix/my-feature-branch
gh pr create --base develop --title "fix(scope): descripcion" --body "..."

# 4. Despues de review y merge a develop, crear PR de release a main
gh pr create --base main --head develop \
  --title "release: backend v$VERSION / dashboard v$DASH_VERSION" \
  --body "## Changes ..."

# 5. Merge a main y deploy con scripts
```

### Reglas de commits

| Prefijo | Uso |
|---------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Correccion de bug |
| `chore` | Mantenimiento, bumps de version |
| `docs` | Solo documentacion |
| `refactor` | Cambio sin efecto externo |
| `test` | Solo tests |

Formato: `tipo(scope): descripcion corta en imperativo`

### Antes de hacer PR a main

```bash
make test T=api                    # tests backend
cd apps/web && pnpm test           # tests web
git diff develop...HEAD | grep -iE "(API_KEY|password|secret|token)" || echo "OK"
```

### Hotfix directo a main (emergencia)

Solo cuando el fix no puede esperar el ciclo develop → main:

```bash
git checkout main && git pull origin main
git checkout -b hotfix/critical-fix
# ... hacer fix ...
git push -u origin hotfix/critical-fix
gh pr create --base main --title "hotfix: descripcion"
# Merge inmediato → deploy → backport a develop:
git checkout develop && git merge main
```

---

## 11. Rollback rapido

```bash
# En PROD: editar manifiesto a version anterior
vim infra/docker-compose.images.yml

docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.images.yml \
  -f infra/docker-compose.production.yml \
  --env-file envs/.env \
  up -d --force-recreate $SERVICE
```

---

## 12. Deploy manual de emergencia

> Solo usar si los scripts no estan disponibles (ej: maquina sin el repo clonado).
> En condiciones normales, siempre usar los scripts de la seccion 2.

```bash
# Build (sustituir segun tabla de "Configuracion de build por servicio")
docker build --no-cache --target $TARGET \
  -t saptivaai/octavios-invex-$SERVICE:$VERSION \
  -t saptivaai/octavios-invex-$SERVICE:latest \
  -f $DOCKERFILE $CONTEXT

# Push
docker login -u saptivaai
docker push saptivaai/octavios-invex-$SERVICE:$VERSION
docker push saptivaai/octavios-invex-$SERVICE:latest

# Actualizar manifiesto manualmente
vim infra/docker-compose.images.yml
git add infra/docker-compose.images.yml
git commit -m "chore: bump $SERVICE $VERSION"
git push origin main
```

---

## Referencia adicional

| Recurso | Path |
|---------|------|
| Scripts de deploy | [scripts/deploy/](../../../scripts/deploy/) |
| Checklists | [checklists/](checklists/) |
| Runbooks | [runbooks/](runbooks/) |
| Lecciones pasadas | [lessons/](lessons/) |
| Procedures legacy | [procedures/](procedures/) |
