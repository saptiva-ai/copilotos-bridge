# Scripts Directory

Colección organizada de scripts para desarrollo, testing, deployment y mantenimiento del proyecto Octavios Chat.

**Última actualización:** 3 de Diciembre 2025

---

## 📊 Organización de Carpetas

**Todos los scripts están organizados en subcarpetas por categoría.**
Usa `make <comando>` o `make scripts.<category>.<name>` para ejecutarlos.

```
scripts/
├── 📁 ci/              # CI/CD integration scripts
├── 📁 database/        # Database operations, backups & migrations (17 scripts)
├── 📁 deploy/          # Deployment scripts (5 scripts)
├── 📁 fixtures/        # Test fixtures & sample data
├── 📁 git-hooks/       # Git hook templates (2 scripts)
├── 📁 legacy/          # Archived & obsolete scripts (NO USAR)
│   ├── deploy_archive/     # 18 deploys obsoletos
│   └── old_deployment/     # 6 scripts de deployment antiguos
├── 📁 maintenance/     # System maintenance & diagnostics (14 scripts)
├── 📁 migrations/      # Data migrations
├── 📁 security/        # Security audits & checks (5 scripts)
├── 📁 setup/           # Project setup & configuration (13 scripts)
├── 📁 testing/         # Test runners & validation (42 scripts)
├── 📁 tests/           # Test suites organized (e2e, smoke, utils)
└── 📁 validation/      # Validation scripts
```

**✨ Nuevo:** Todos los scripts se ejecutan vía Makefile con dot notation:
```bash
make scripts.<category>.<name>    # Cualquier script
make db.backup                     # Database backup
make test.api                      # API tests
make deploy-registry VERSION=x.x.x # Deploy desde registry
```

---

## 📁 Guía de Subcarpetas

### [`ci/`](ci/README.md) - CI/CD Scripts
Scripts para integración continua y automatización.

**Scripts principales:**
- `audit-tests.sh` - Tests de auditoría en CI

---

### [`database/`](database/README.md) - Database Management
Operaciones de base de datos, backups, restauraciones y migraciones.

**Scripts principales:**
- `backup-mongodb.sh` - Backup automático de MongoDB
- `restore-mongodb.sh` - Restore desde backup
- `migrate-conversation-timestamps.py` - Migración de timestamps
- `migrate-ready-to-active.py` - Migración de estados
- `fix-orphaned-drafts.py` - Fix drafts huérfanos
- `cleanup-duplicate-drafts.py` - Limpiar drafts duplicados
- `rotate-mongo-credentials.sh` - Rotación de credentials
- `rotate-redis-credentials.sh` - Rotación de credentials Redis

**Uso:**
```bash
# Backup
./scripts/database/backup-mongodb.sh

# Restore
./scripts/database/restore-mongodb.sh

# Migraciones
python scripts/database/migrate-conversation-timestamps.py
```

---

### [`deploy/`](deploy/README.md) - Deployment Scripts
Scripts de deployment y gestión de imágenes Docker.

**Scripts principales:**
- `deploy-to-production.sh` - ⭐ Deploy completo a producción vía Docker Hub
- `tag-dockerhub.sh` - Tag de imágenes para Docker Hub
- `tag-images.sh` - Tag de imágenes locales
- `push-dockerhub.sh` - Push de imágenes a Docker Hub
- `start-production.sh` - Iniciar servicios en producción

**Uso:**
```bash
# Deploy completo
make deploy-registry VERSION=0.1.3

# En servidor
./scripts/deploy/deploy-to-production.sh 0.1.3

# Tag y push
./scripts/deploy/tag-dockerhub.sh 0.1.3
./scripts/deploy/push-dockerhub.sh
```

---

### [`maintenance/`](maintenance/README.md) - System Maintenance
Mantenimiento del sistema, diagnósticos y troubleshooting.

**Scripts principales:**
- `health-check.sh` - Health check de servicios
- `prod-health-check.sh` - Health check de producción
- `quick-diagnostic.sh` - Diagnóstico rápido completo
- `dev-troubleshoot.sh` - Solución automatizada de problemas
- `docker-cleanup.sh` - Limpieza de Docker
- `diagnose-nginx-413.sh` - Diagnóstico de error 413
- `fix-nginx-413.sh` - Fix para error 413
- `monitor-backups.sh` - Monitoreo de backups
- `cleanup-server.sh` - Limpieza de servidor

**Uso:**
```bash
# Health check
./scripts/maintenance/health-check.sh

# Diagnóstico completo
./scripts/maintenance/quick-diagnostic.sh

# Troubleshooting
./scripts/maintenance/dev-troubleshoot.sh cache
./scripts/maintenance/dev-troubleshoot.sh ports

# Docker cleanup
./scripts/maintenance/docker-cleanup.sh
```

---

### [`security/`](security/README.md) - Security Audits
Auditorías de seguridad y verificaciones.

**Scripts principales:**
- `security-audit.sh` - Auditoría de seguridad completa
- `security-audit-focused.sh` - Auditoría enfocada
- `security-audit-precise.sh` - Auditoría precisa
- `security-check.sh` - Verificación de seguridad
- `remove-audit-system.sh` - Remover sistema de auditoría

**Uso:**
```bash
# Auditoría completa
./scripts/security/security-audit.sh

# Auditoría rápida
./scripts/security/security-check.sh
```

---

### [`setup/`](setup/README.md) - Project Setup
Scripts de configuración inicial y ambiente.

**Scripts principales:**
- `env-checker.sh` - Validación de variables de entorno ([Documentación detallada](setup/README_ENV_CHECKER.md))
- `env-manager.sh` - Gestión de variables de entorno
- `interactive-env-setup.sh` - Setup interactivo
- `generate-secrets.py` - Generación de secrets
- `create-demo-user.py` - Crear usuario demo
- `fix_demo_user.py` - Fix usuario demo
- `setup-dev.sh` - Setup de desarrollo
- `setup-docker-secrets.sh` - Setup de Docker secrets
- `setup-demo-server.sh` - Setup de servidor demo
- `setup-ssl-414.sh` - Setup de SSL

**Uso:**
```bash
# Verificar environment
./scripts/setup/env-checker.sh warn

# Setup interactivo
./scripts/setup/interactive-env-setup.sh development

# Generar secrets
python scripts/setup/generate-secrets.py

# Crear usuario demo
python scripts/setup/create-demo-user.py
```

---

### [`testing/`](testing/README.md) - Testing & Validation
Tests, validaciones y verificaciones del sistema.

**Scripts principales:**
- `test-auth-and-chat.py` - Tests de auth + chat
- `test-mongodb.py` - Tests de MongoDB
- `test-all-models.py` - Tests de todos los modelos
- `test-rag-ingestion.py` - Tests de RAG ingestion
- `test-semantic-search.py` - Tests de búsqueda semántica
- `test_mcp_tools.sh` - Testing interactivo MCP ([Documentación](testing/README_MCP_TESTING.md))
- `validate-config.sh` - Validación de configuración
- `validate-mvp.sh` - Validación de MVP
- `validate-production-readiness.sh` - Validación pre-producción
- `verify-deployment.sh` - Verificación de deployment
- `verify-deps.sh` - Verificación de dependencias

**Uso:**
```bash
# Tests de integración
python scripts/testing/test-auth-and-chat.py

# Tests MCP interactivos
./scripts/testing/test_mcp_tools.sh

# Validaciones
./scripts/testing/validate-mvp.sh
./scripts/testing/validate-production-readiness.sh

# Verificaciones
./scripts/testing/verify-deployment.sh
```

---

### [`tests/`](tests/README.md) - Shell Test Suite
Suite de tests automatizados en shell (e2e, smoke tests).

**Estructura:**
- `e2e/` - Tests end-to-end (*.test.sh)
- `smoke/` - Tests de smoke/sanidad
- `utils/` - Helpers y wrappers
- `deprecated/` - Tests en proceso de deprecación

**Uso:**
```bash
# Ejecutar todos los shell tests
make test:sh

# Lint shell scripts
make lint:sh

# Format shell scripts
make fix:sh

# Ver README_tests.md para convenciones completas
```

---

### [`migrations/`](migrations/README.md) - Data Migrations
Migraciones de datos y schema.

**Scripts principales:**
- `add_bank_chart_ttl_indexes.py` - Agregar índices TTL

---

### [`legacy/`](legacy/) - ⚠️ Scripts Obsoletos
**NO USAR - Solo referencia histórica**

Contiene scripts archivados que ya no se deben usar:
- `deploy_archive/` - 18 scripts de deploy obsoletos
- `old_deployment/` - 6 scripts de deployment antiguos
- Otros scripts deprecated

---

## 🔧 Workflows Comunes

### Deploy a Producción
```bash
# 1. LOCAL: Build y push a Docker Hub
make deploy-registry VERSION=0.1.3

# 2. SERVIDOR: Deploy automatizado
./scripts/deploy-to-production.sh 0.1.3

# 3. Verificar deployment
ssh servidor "cd proyecto && docker compose ps"
```

### Testing Completo
```bash
# Tests principales
./scripts/test-runner.sh

# Tests específicos de Bank Advisor
python scripts/test_bank_query_hybrid.py

# Tests de integración
python scripts/testing/test-auth-and-chat.py

# Validar antes de producción
./scripts/testing/validate-production-readiness.sh
```

### Troubleshooting
```bash
# 1. Diagnóstico rápido
./scripts/maintenance/quick-diagnostic.sh

# 2. Verificar logs
make logs

# 3. Limpiar cache
./scripts/maintenance/dev-troubleshoot.sh cache

# 4. Health check
./scripts/maintenance/health-check.sh
```

### Database Operations
```bash
# Backup
./scripts/database/backup-mongodb.sh

# Restore
./scripts/database/restore-mongodb.sh

# Inicializar Bank Advisor
./scripts/init-bankadvisor-db.sh

# Migraciones
python scripts/database/migrate-conversation-timestamps.py
```

---

## 📖 Referencias

- **Deploy Guide:** `docs/DEPLOY_ANALISIS_Y_GUIA.md`
- **Arquitectura:** `docs/ARQUITECTURA_SCRIPTS_Y_DOCKER.md`
- **Makefile:** `Makefile` (comandos make)

---

## 🗂️ Cambios Recientes (Dic 2025)

### Reorganización Completa
- ✅ **Eliminados 88 scripts** (duplicados y obsoletos)
- ✅ Scripts organizados en subcarpetas por categoría
- ✅ Makefile actualizado para usar scripts de subcarpetas
- ✅ Documentación completa creada

### Resumen de Limpieza
| Acción | Cantidad | Ubicación |
|--------|----------|-----------|
| Carpeta deployment/ eliminada | 16 scripts | Duplicados exactos |
| Deploy obsoletos archivados | 18 scripts | `legacy/deploy_archive/` |
| Duplicados database eliminados | 13 scripts | Movidos a `database/` |
| Duplicados setup eliminados | 9 scripts | Movidos a `setup/` |
| Duplicados testing eliminados | 19 scripts | Movidos a `testing/` |
| Duplicados maintenance eliminados | 10 scripts | Movidos a `maintenance/` |
| Duplicados security eliminados | 5 scripts | Movidos a `security/` |
| Scripts únicos categorizados | 15 scripts | Varias subcarpetas |
| Scripts deployment obsoletos | 6 scripts | `legacy/old_deployment/` |

**Total organizado:** 111 scripts
**Total eliminado/archivado:** 88 scripts

### Estructura Final
- **Root:** 18 scripts core de uso muy frecuente
- **Subcarpetas:** ~100+ scripts organizados por categoría
- **Legacy:** 25+ scripts archivados (solo referencia)

---

## ⚠️ Advertencias Importantes

1. **Scripts en `legacy/`:** ⛔ NO usar - están obsoletos
2. **Deploy:** ⭐ Usar SOLO `deploy-to-production.sh` (registry strategy)
3. **Git hooks:** Se ejecutan automáticamente, no llamar manualmente
4. **Database:** Siempre hacer backup antes de operaciones destructivas
5. **Paths actualizados:** El Makefile ahora usa rutas de subcarpetas (ej: `scripts/setup/env-checker.sh`)

---

## 🆘 Ayuda

- `make help` - Ver todos los comandos disponibles
- `./scripts/maintenance/quick-diagnostic.sh` - Diagnóstico rápido
- Individual scripts soportan `--help` o `-h` (mayoría)
- Ver README.md en cada subcarpeta para detalles específicos

---

**Mantenido por:** Equipo Saptiva AI
