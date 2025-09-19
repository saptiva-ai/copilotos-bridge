# 🚀 Guía para Replicar CI/CD de Aletheia

## 📋 Resumen del Setup Actual

### 🏗️ Configuración Exitosa en `copilotos-bridge`
- **Servidor**: `34.42.214.246`
- **Usuario**: `jf`
- **SSH Key**: Ya configurada en GitHub Secrets
- **Deploy automático**: ✅ Staging (develop) y Production (main)
- **Health checks**: ✅ Con rollback automático

## 🔄 Pasos para Replicar en Repo Aletheia

### 1. 📁 Estructura de Directorios en Servidor

```bash
# En el servidor 34.42.214.246 como usuario jf
/home/jf/
├── copilotos-bridge/          # ✅ Ya existe
├── aletheia-api/              # 🆕 Crear para Aletheia
├── staging-backup-*/          # Backups automáticos copilotos
├── aletheia-staging-backup-*/ # 🆕 Backups automáticos Aletheia
├── backup-*/                  # Backups producción copilotos
└── aletheia-backup-*/         # 🆕 Backups producción Aletheia
```

### 2. 🔐 GitHub Secrets (Ya Configurados)

Los siguientes secrets **YA ESTÁN** configurados y se pueden reutilizar:

- ✅ `PRODUCTION_SSH_KEY`: SSH private key para acceso al servidor
- ✅ Usuario `jf` ya configurado en el servidor
- ✅ Permisos sudo y Docker ya configurados

### 3. 📝 Archivo CI/CD para Aletheia

Crear en el repo de Aletheia: `.github/workflows/ci-cd-aletheia.yml`

**Diferencias clave vs copilotos-bridge:**

#### 🔧 Configuración Específica Aletheia:
- **Python**: 3.11+ (en lugar de Node.js + Python)
- **Puerto**: 8000 (en lugar de 3000/8001)
- **Servicios**: Redis + Weaviate (en lugar de MongoDB + Redis)
- **Deploy Dir**: `/home/jf/aletheia-api`
- **Health Check**: `http://localhost:8000/health`

#### 🧪 Tests y Quality:
- **Linting**: black, flake8, mypy
- **Tests**: pytest con coverage
- **Dependencies**: requirements.txt + requirements-dev.txt

#### 🐳 Docker:
- **Compose Files**:
  - `docker-compose.yml` (desarrollo/staging)
  - `docker-compose.prod.yml` (producción)

### 4. 🛠️ Configuración en el Servidor

#### 4.1 Crear directorio para Aletheia
```bash
# SSH al servidor
ssh jf@34.42.214.246

# Crear directorio para Aletheia
mkdir -p /home/jf/aletheia-api
cd /home/jf/aletheia-api

# El primer deploy clonará automáticamente el repo
```

#### 4.2 Variables de Entorno Aletheia
```bash
# En el servidor, crear .env para Aletheia
cat > /home/jf/aletheia-api/.env << 'EOF'
# SAPTIVA Configuration
SAPTIVA_API_KEY=va-ai-Jm4BHuDYPiNAlv7OoBuO8G58S23sSgIAmbZ6nqUKFOqSY8vmB2Liba-ZRzcgjJLpqOFmza8bK9vvUT39EhaKjeGZHFJE8EVQtKABOG1hc_A
SAPTIVA_BASE_URL=https://api.saptiva.com

# Vector Database
WEAVIATE_HOST=http://localhost:8080
VECTOR_BACKEND=weaviate

# Search API
TAVILY_API_KEY=tu-tavily-api-key

# Storage
ARTIFACTS_DIR=./runs

# Redis
REDIS_URL=redis://localhost:6379/1

# Observability
OTEL_SERVICE_NAME=aletheia-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Security
API_KEY_HEADER=X-API-Key
ALLOWED_ORIGINS=http://34.42.214.246:3000,http://localhost:3000
EOF
```

### 5. 🔄 Workflow de Deploy

#### 5.1 Branches y Environments:
- **`develop`** → Auto-deploy a **Staging** (puerto 8000)
- **`main`** → Auto-deploy a **Production** (puerto 8000)

#### 5.2 Health Checks:
- **Endpoint**: `GET /health`
- **Expected**: 200 status
- **Timeout**: 20 segundos (más tiempo que copilotos)
- **Rollback**: Automático si falla

#### 5.3 Puertos y URLs:
- **Aletheia API**: `http://34.42.214.246:8000`
- **Aletheia Docs**: `http://34.42.214.246:8000/docs`
- **Copilotos Web**: `http://34.42.214.246:3000` (sin conflicto)
- **Copilotos API**: `http://34.42.214.246:8001` (sin conflicto)

### 6. 🎯 Checklist de Implementación

#### En el Repo de Aletheia:
- [ ] Copiar el archivo `ALETHEIA_CICD_TEMPLATE.yml` a `.github/workflows/ci-cd-aletheia.yml`
- [ ] Ajustar URLs del repositorio en el workflow
- [ ] Configurar `requirements.txt` y `requirements-dev.txt`
- [ ] Añadir tests básicos en directorio `tests/`
- [ ] Crear `docker-compose.yml` para desarrollo
- [ ] Crear `docker-compose.prod.yml` para producción
- [ ] Añadir endpoint `/health` en la API

#### En GitHub:
- [ ] Los secrets `PRODUCTION_SSH_KEY` ya están configurados ✅
- [ ] Configurar environments "staging" y "production"
- [ ] Activar Actions en el repo

#### En el Servidor:
- [ ] Crear directorio `/home/jf/aletheia-api`
- [ ] Configurar variables de entorno `.env`
- [ ] Verificar que Docker tiene permisos
- [ ] Probar acceso SSH desde GitHub Actions

### 7. 🧪 Test del Pipeline

#### 7.1 Test Staging:
```bash
# Push a develop branch
git checkout develop
git push origin develop

# Verificar en:
# - GitHub Actions ejecutándose
# - http://34.42.214.246:8000/health
```

#### 7.2 Test Production:
```bash
# Merge a main branch
git checkout main
git merge develop
git push origin main

# Verificar deployment production
```

### 8. ⚡ Ventajas del Setup

#### ✅ Reutilización de Infraestructura:
- Mismo servidor para ambos proyectos
- Mismas credenciales SSH
- Docker ya configurado
- Usuario `jf` con permisos correctos

#### ✅ Isolation:
- Directorios separados
- Puertos diferentes (3000/8001 vs 8000)
- Workflows independientes
- Backups separados

#### ✅ Consistencia:
- Mismo patrón de deploy
- Mismos health checks
- Mismo sistema de rollback
- Misma estructura de logs

### 9. 🔧 Troubleshooting

#### SSH Issues:
```bash
# Test SSH connectivity
ssh -i ~/.ssh/your-key jf@34.42.214.246

# Check GitHub Actions logs for SSH errors
```

#### Docker Issues:
```bash
# On server, check Docker status
docker ps
docker-compose ps

# Check Aletheia logs
cd /home/jf/aletheia-api
docker-compose logs -f
```

#### Port Conflicts:
```bash
# Check what's running on port 8000
sudo netstat -tlnp | grep :8000

# Kill if needed
sudo fuser -k 8000/tcp
```

### 10. 🎉 Resultado Final

Después de la implementación tendrás:

- **Copilotos**: `http://34.42.214.246:3000` + `http://34.42.214.246:8001`
- **Aletheia**: `http://34.42.214.246:8000`
- **Deploy automático**: Para ambos proyectos
- **Health checks**: Con rollback en ambos
- **Backups**: Separados y automáticos
- **Same server**: Máximo aprovechamiento de recursos