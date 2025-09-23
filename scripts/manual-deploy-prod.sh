#!/bin/bash
# ========================================
# SCRIPT DE DEPLOY MANUAL A PRODUCCIÓN
# ========================================
# Para usar en servidor: 34.42.214.246
# Usuario: jf
# Path: /home/jf/copilotos-bridge

set -e

echo "🚀 Iniciando deploy manual a producción..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para log
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Verificar que estamos en el directorio correcto
if [ ! -f "package.json" ] || [ ! -d "apps" ]; then
    error "No estás en el directorio del proyecto copilotos-bridge"
fi

log "Verificando prerrequisitos..."

# Verificar Git
if ! command -v git &> /dev/null; then
    error "Git no encontrado"
fi

# Verificar Docker
if ! command -v docker &> /dev/null; then
    error "Docker no encontrado"
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose no encontrado"
fi

success "Prerrequisitos verificados"

# Actualizar código
log "Actualizando código desde GitHub..."
git fetch origin
git checkout main
git pull origin main

# Verificar versión
log "Verificando versión actual..."
CURRENT_COMMIT=$(git rev-parse HEAD)
CURRENT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "No tag")
echo "Commit actual: $CURRENT_COMMIT"
echo "Tag actual: $CURRENT_TAG"

success "Código actualizado"

# Verificar archivo de variables de entorno
log "Verificando configuración de producción..."
if [ ! -f "envs/.env.prod" ]; then
    warning "Archivo envs/.env.prod no encontrado. Creando desde ejemplo..."
    cp envs/.env.prod envs/.env.prod.backup 2>/dev/null || true

    echo "# ========================================"
    echo "# CONFIGURACIÓN CRÍTICA REQUERIDA"
    echo "# ========================================"
    echo "Debes configurar las siguientes variables en envs/.env.prod:"
    echo "- DOMAIN=tu-dominio.com"
    echo "- MONGODB_PASSWORD=password-seguro"
    echo "- REDIS_PASSWORD=password-seguro"
    echo "- JWT_SECRET_KEY=clave-jwt-muy-segura"
    echo "- SECRET_KEY=clave-sesion-muy-segura"
    echo "- SAPTIVA_API_KEY=tu-api-key-saptiva"
    echo ""
    echo "¿Has configurado estas variables? (y/N)"
    read -r CONFIGURED
    if [[ ! "$CONFIGURED" =~ ^[Yy]$ ]]; then
        error "Configura las variables de entorno antes de continuar"
    fi
fi

success "Configuración verificada"

# Parar servicios existentes
log "Parando servicios existentes..."
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod down 2>/dev/null || true

# Limpiar contenedores huérfanos
docker container prune -f 2>/dev/null || true

success "Servicios existentes detenidos"

# Crear directorios de datos
log "Preparando directorios de datos..."
sudo mkdir -p /opt/copilotos-bridge/data/mongodb
sudo mkdir -p /opt/copilotos-bridge/data/redis
sudo mkdir -p /opt/copilotos-bridge/logs
sudo mkdir -p /opt/copilotos-bridge/backups

# Establecer permisos
sudo chown -R 999:999 /opt/copilotos-bridge/data/mongodb
sudo chown -R 999:999 /opt/copilotos-bridge/data/redis
sudo chmod -R 755 /opt/copilotos-bridge/data

success "Directorios preparados"

# Construir y levantar servicios
log "Construyendo y levantando servicios..."
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod up -d --build

success "Servicios iniciados"

# Esperar a que los servicios estén listos
log "Esperando a que los servicios estén listos..."
sleep 30

# Verificar servicios
log "Verificando servicios..."
if curl -f http://localhost:8001/api/health &>/dev/null; then
    success "API funcionando correctamente"
else
    warning "API no responde - verificando logs..."
    docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod logs api --tail=20
fi

if curl -f http://localhost:3000 &>/dev/null; then
    success "Frontend funcionando correctamente"
else
    warning "Frontend no responde - verificando logs..."
    docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod logs web --tail=20
fi

# Mostrar estado final
log "Estado final de los servicios:"
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod ps

echo
success "🎉 Deploy de producción completado!"
echo
echo -e "${BLUE}URLs de acceso:${NC}"
echo "• Frontend: ${GREEN}http://34.42.214.246:3000${NC}"
echo "• API:      ${GREEN}http://34.42.214.246:8001${NC}"
echo "• Health:   ${GREEN}http://34.42.214.246:8001/api/health${NC}"
echo
echo -e "${BLUE}Comandos útiles:${NC}"
echo "• Ver logs:     ${GREEN}docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod logs -f${NC}"
echo "• Estado:       ${GREEN}docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod ps${NC}"
echo "• Reiniciar:    ${GREEN}docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod restart${NC}"
echo "• Health check: ${GREEN}make health${NC}"
echo
echo -e "${YELLOW}Información del deploy:${NC}"
echo "• Fecha: $(date)"
echo "• Commit: $CURRENT_COMMIT"
echo "• Tag: $CURRENT_TAG"
echo "• Usuario: $(whoami)"
echo "• Servidor: $(hostname)"