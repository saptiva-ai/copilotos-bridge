# Versioned Deployment with Automatic Rollback

Sistema consolidado de deployment con versionado automático, health checks y rollback en caso de fallo.

## Características

✅ **Versionado Automático**: Cada deploy genera una versión única (git SHA + timestamp)
✅ **Backup Pre-Deploy**: Se guarda la versión actual antes de desplegar
✅ **Health Checks**: Validación automática post-deploy (API + Web + Database)
✅ **Rollback Automático**: Si falla el health check, restaura la versión anterior
✅ **Rollback Manual**: Puedes volver a cualquier versión previa
✅ **Historial**: Tracking completo de deployments (exitosos, fallidos, rollbacks)
✅ **Múltiples Métodos**: Tar transfer, Docker registry, o local

---

## Uso Rápido

### Deploy Estándar (Recomendado)

```bash
make deploy
```

- Construye imágenes con versión única
- Transfiere vía tar (no requiere registry)
- Hace backup de versión actual
- Deploy en servidor
- Ejecuta health checks
- Si falla: rollback automático

**Tiempo**: 8-12 minutos

### Deploy Rápido (Sin Build)

```bash
make deploy-fast
```

Usa imágenes existentes, útil para redeploys rápidos.
**Tiempo**: 3-5 minutos

### Deploy desde Registry

```bash
make deploy-registry
```

Más rápido si tienes Docker registry configurado (GHCR).
**Tiempo**: 3-5 minutos

---

## Rollback

### Rollback Automático

Si un deploy falla el health check, el sistema automáticamente:

1. Detecta el fallo
2. Restaura imágenes de backup
3. Reinicia servicios con versión anterior
4. Verifica que el rollback funcione

**No requiere intervención manual**.

### Rollback Manual

#### Volver a versión anterior

```bash
make rollback
```

#### Volver a versión específica

```bash
./scripts/rollback.sh e4534e6-20251011-143052
```

#### Ver versiones disponibles

```bash
make deploy-history
```

Muestra:
- Historial de deployments
- Versiones exitosas y fallidas
- Imágenes de backup disponibles

---

## Verificación y Monitoreo

### Ver Estado del Servidor

```bash
make deploy-status
```

Muestra:
- Versión actual desplegada
- Git commit en servidor
- Contenedores corriendo
- Health checks (API, Web)

### Ver Historial

```bash
make deploy-history
```

Output de ejemplo:

```
Recent deployments:
  ✔ e4534e6-20251011-143052 - 2025-10-11T14:30:52-05:00 (via tar)
  ✖ abc1234-20251011-120000 - 2025-10-11T12:00:00-05:00 (via tar)
  ↩ d5f9876-20251010-180000 - 2025-10-10T18:00:00-05:00 (via rollback)
```

---

## Métodos de Deploy

### 1. TAR Transfer (Default)

**Cuándo usar**: Siempre, no requiere registry configurado.

```bash
./scripts/deploy.sh tar
# o simplemente
make deploy
```

**Cómo funciona**:
1. Build local
2. Export a tar.gz
3. SCP a servidor
4. Load en servidor
5. Deploy

**Pros**: No requiere registry, funciona siempre
**Contras**: Más lento por transferencia de archivos

### 2. Docker Registry

**Cuándo usar**: Cuando tienes GHCR o Docker Hub configurado.

```bash
./scripts/deploy.sh registry
# o
make deploy-registry
```

**Cómo funciona**:
1. Build local
2. Push a registry (ghcr.io)
3. Pull en servidor
4. Deploy

**Pros**: Más rápido, versionado en registry
**Contras**: Requiere autenticación y registry configurado

### 3. Local

**Cuándo usar**: Solo desarrollo, NO producción.

```bash
./scripts/deploy.sh local
```

**Pros**: Instantáneo para testing
**Contras**: No versiona, no hace backup

---

## Opciones Avanzadas

### Deploy sin Health Check (Peligroso)

```bash
./scripts/deploy.sh tar --skip-healthcheck
```

⚠️ **No recomendado**: Puede dejar sistema en estado inválido.

### Deploy sin Rollback Automático

```bash
./scripts/deploy.sh tar --no-rollback
```

Útil para debugging cuando quieres inspeccionar el estado fallido.

### Deploy Forzado (Sin Confirmación)

```bash
./scripts/deploy.sh tar --force
```

Para scripts automatizados (CI/CD).

---

## Arquitectura de Versiones

### Generación de Versiones

Formato: `<git-sha>-<timestamp>`

Ejemplo: `e4534e6-20251011-143052`

- **git-sha**: 7 caracteres del commit actual
- **timestamp**: YYYYMMDD-HHMMSS en zona local

### Almacenamiento

#### En Local (`~/.copilotos-deploy/`)

```
~/.copilotos-deploy/
├── versions/
│   └── history.log          # Historial de deployments
└── backups/
    └── metadata.json        # Info de backups
```

#### En Servidor (`/opt/copilotos-bridge/.deploy/`)

```
/opt/copilotos-bridge/.deploy/
├── current_version          # Versión actualmente desplegada
├── current_method           # Método usado (tar/registry/local)
└── versions.log             # Historial completo
```

#### En Docker

```bash
# Imágenes versionadas
copilotos-api:e4534e6-20251011-143052
copilotos-web:e4534e6-20251011-143052

# Backups
copilotos-api:backup-e4534e6-20251011-143052
copilotos-web:backup-e4534e6-20251011-143052

# Latest (siempre apunta a versión actual)
copilotos-api:latest
copilotos-web:latest
```

### Limpieza Automática

El sistema mantiene:
- **Últimas 5 versiones** en Docker
- **Últimos 10 registros** en historial
- **Backups** de todas las versiones exitosas

---

## Troubleshooting

### Deploy falla en health check

```bash
# Ver logs del servidor
ssh user@server 'docker logs copilotos-api'

# Verificar estado
make deploy-status

# El sistema debería haber hecho rollback automático
# Si no, hacer rollback manual:
make rollback
```

### "Backup images not found"

Si el rollback falla porque no encuentra backup:

```bash
# Ver imágenes disponibles en servidor
ssh user@server 'docker images | grep copilotos'

# Rollback a versión específica que sí tenga backup
./scripts/rollback.sh VERSION
```

### Transfer lento por tar

Usa registry en su lugar:

```bash
# Primera vez: configura registry
echo "REGISTRY_URL=ghcr.io/yourorg/copilotos-bridge" >> envs/.env.prod

# Autentica en GHCR
docker login ghcr.io

# Deploy via registry
make deploy-registry
```

### Permisos SSH

```bash
# Verifica conectividad
ssh user@server 'echo OK'

# Si falla, agrega tu key
ssh-copy-id user@server
```

---

## Integración con CI/CD

### GitHub Actions

```yaml
- name: Deploy to Production
  env:
    PROD_SERVER_HOST: ${{ secrets.PROD_SERVER }}
    PROD_DEPLOY_PATH: /opt/copilotos-bridge
  run: |
    # Setup SSH
    mkdir -p ~/.ssh
    echo "${{ secrets.SSH_KEY }}" > ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa

    # Deploy (auto-versioned)
    ./scripts/deploy.sh tar --force
```

### Manual desde CI

```bash
# Build localmente, deploy via registry
make push-registry
ssh server 'cd /opt/copilotos-bridge && make deploy-registry'
```

---

## Migración desde Scripts Antiguos

Si venías usando `deploy-with-tar.sh` o `deploy-from-registry.sh`:

### Antes

```bash
./scripts/deploy-with-tar.sh
./scripts/deploy-from-registry.sh
```

### Ahora

```bash
# Mismo comportamiento, pero con versionado y rollback
./scripts/deploy.sh tar
./scripts/deploy.sh registry

# O simplemente
make deploy
make deploy-registry
```

**Ventajas adicionales**:
- Versionado automático
- Rollback si falla
- Historial tracking
- Health checks más robustos

---

## Comandos Rápidos (Cheat Sheet)

```bash
# Deploy
make deploy                 # Deploy completo con versionado
make deploy-fast            # Deploy sin rebuild
make deploy-registry        # Deploy desde registry

# Rollback
make rollback               # Volver a versión anterior
make deploy-history         # Ver versiones disponibles

# Monitoreo
make deploy-status          # Estado del servidor
make logs                   # Ver logs en vivo

# Avanzado
./scripts/deploy.sh tar --skip-build        # Sin rebuild
./scripts/deploy.sh --version abc123        # Deploy versión específica
./scripts/rollback.sh abc123-20251011       # Rollback a versión exacta
```

---

## Mejores Prácticas

### ✅ DO

- **Siempre usa `make deploy`** para producción
- **Verifica con `make deploy-status`** después del deploy
- **Mantén historial local** para debugging
- **Prueba en staging** antes de producción
- **Documenta cambios críticos** en git commit messages

### ❌ DON'T

- **No uses `--skip-healthcheck`** en producción
- **No hagas deploy sin commit previo** (versión será incorrecta)
- **No borres backups manualmente** del servidor
- **No uses `local` method** en producción
- **No ignores warnings** del health check

---

## Soporte y Ayuda

```bash
# Ver ayuda de deploy
./scripts/deploy.sh --help

# Ver ayuda de rollback
./scripts/rollback.sh --help

# Ver todos los comandos disponibles
make help
```

Para issues o mejoras, ver: `docs/DEPLOYMENT.md`

---

**Última actualización**: 2025-10-11
**Versión del sistema**: 1.0.0
