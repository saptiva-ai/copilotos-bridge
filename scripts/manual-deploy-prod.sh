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
COMPOSE_BASE="infra/docker-compose.yml"
COMPOSE_PROD="infra/docker-compose.prod.yml"
ENV_FILE="envs/.env.prod"

if [ ! -f "$ENV_FILE" ]; then
    error "Archivo envs/.env.prod no encontrado. Asegúrate de que el repositorio esté actualizado."
fi

if [ ! -f "$COMPOSE_BASE" ]; then
    error "No se encontró $COMPOSE_BASE"
fi

COMPOSE_ARGS=(-f "$COMPOSE_BASE")
if [ -f "$COMPOSE_PROD" ]; then
    log "Usando override de producción: $COMPOSE_PROD"
    COMPOSE_ARGS+=(-f "$COMPOSE_PROD")
fi

# Verificar variables críticas
log "Verificando variables críticas..."
source "$ENV_FILE"

if [[ -z "$SAPTIVA_API_KEY" || "$SAPTIVA_API_KEY" == *"CHANGE_ME"* ]]; then
    error "SAPTIVA_API_KEY no configurada correctamente en envs/.env.prod"
fi

if [[ -z "$MONGODB_PASSWORD" || "$MONGODB_PASSWORD" == *"CHANGE_ME"* ]]; then
    error "MONGODB_PASSWORD no configurada correctamente en envs/.env.prod"
fi

success "Configuración verificada - Variables críticas configuradas correctamente"

# Parar servicios existentes
log "Parando servicios existentes..."
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" down 2>/dev/null || true

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
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" up -d --build

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
    docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" logs api --tail=20
fi

if curl -f http://localhost:3000 &>/dev/null; then
    success "Frontend funcionando correctamente"
else
    warning "Frontend no responde - verificando logs..."
    docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" logs web --tail=20
fi

# Mostrar estado final
log "Estado final de los servicios:"
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" ps

echo
success "🎉 Deploy de producción completado!"
echo
echo -e "${BLUE}URLs de acceso:${NC}"
echo "• Frontend: ${GREEN}http://34.42.214.246:3000${NC}"
echo "• API:      ${GREEN}http://34.42.214.246:8001${NC}"
echo "• Health:   ${GREEN}http://34.42.214.246:8001/api/health${NC}"
echo
echo -e "${BLUE}Comandos útiles:${NC}"
echo "• Ver logs:     ${GREEN}docker compose ${COMPOSE_ARGS[*]} --env-file $ENV_FILE logs -f${NC}"
echo "• Estado:       ${GREEN}docker compose ${COMPOSE_ARGS[*]} --env-file $ENV_FILE ps${NC}"
echo "• Reiniciar:    ${GREEN}docker compose ${COMPOSE_ARGS[*]} --env-file $ENV_FILE restart${NC}"
echo "• Health check: ${GREEN}make health${NC}"
echo
echo -e "${YELLOW}Información del deploy:${NC}"
echo "• Fecha: $(date)"
echo "• Commit: $CURRENT_COMMIT"
echo "• Tag: $CURRENT_TAG"
echo "• Usuario: $(whoami)"
echo "• Servidor: $(hostname)"
