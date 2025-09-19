#!/bin/bash

# ========================================
# Script de Despliegue de Producción - CopilotOS Bridge
# ========================================

set -e

echo "🚀 Iniciando despliegue de producción..."

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

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.production"

# Verificar que estamos en el directorio correcto
cd "$PROJECT_ROOT"

# Verificar prerrequisitos
log "Verificando prerrequisitos..."

# Docker
if ! command -v docker &> /dev/null; then
    error "Docker no encontrado. Instala Docker para continuar."
fi

# Docker Compose
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose no encontrado. Instala Docker Compose para continuar."
fi

success "Prerrequisitos verificados"

# Verificar archivo de variables de entorno
if [ ! -f "$ENV_FILE" ]; then
    error "Archivo .env.production no encontrado. Ejecuta la configuración primero."
fi

# Verificar que las variables críticas estén configuradas
log "Verificando configuración de producción..."

# Cargar variables de entorno de los archivos disponibles
ENV_FILES=("$ENV_FILE" "$PROJECT_ROOT/.env")
for file in "${ENV_FILES[@]}"; do
    if [ -f "$file" ]; then
        log "Cargando variables desde ${file#$PROJECT_ROOT/}"
        set -a
        # shellcheck disable=SC1090
        source "$file"
        set +a
    else
        warning "Archivo ${file#$PROJECT_ROOT/} no encontrado"
    fi
done

# Función para verificar variables críticas en el entorno actual
check_env_var() {
    local var_name="$1"
    local var_value="${!var_name}"

    if [ -z "$var_value" ] || [[ "$var_value" == *"CHANGE_ME"* ]] || [[ "$var_value" == '__SET_VIA_SECRETS__' ]] || [[ "$var_value" == '__GENERATE_IN_PRODUCTION__' ]]; then
        error "Variable ${var_name} no configurada correctamente en entorno de producción"
    fi
}

# Variables críticas que deben estar configuradas
CRITICAL_VARS=(
    "DOMAIN"
    "MONGODB_PASSWORD"
    "REDIS_PASSWORD"
    "JWT_SECRET_KEY"
    "SECRET_KEY"
    "SAPTIVA_API_KEY"
)

for var in "${CRITICAL_VARS[@]}"; do
    check_env_var "$var"
done

success "Configuración de producción verificada"

# Crear directorios de datos si no existen
log "Preparando directorios de datos..."
sudo mkdir -p /opt/copilotos-bridge/data/mongodb
sudo mkdir -p /opt/copilotos-bridge/data/redis
sudo mkdir -p /opt/copilotos-bridge/logs
sudo mkdir -p /opt/copilotos-bridge/backups

# Establecer permisos correctos
sudo chown -R 999:999 /opt/copilotos-bridge/data/mongodb  # MongoDB user
sudo chown -R 999:999 /opt/copilotos-bridge/data/redis    # Redis user
sudo chmod -R 755 /opt/copilotos-bridge/data

success "Directorios preparados"

# Construir imágenes si están configuradas para build local
log "Preparando imágenes Docker..."

# Verificar si necesitamos construir localmente
if grep -q "build:" docker-compose.prod.yml; then
    log "Construyendo imágenes localmente..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    success "Imágenes construidas"
else
    log "Descargando imágenes desde registry..."
    docker-compose -f docker-compose.prod.yml pull
    success "Imágenes descargadas"
fi

# Detener servicios existentes si están corriendo
log "Deteniendo servicios existentes..."
docker-compose -f docker-compose.prod.yml down --remove-orphans || true

# Limpiar volúmenes si se especifica
if [ "$1" = "--clean" ]; then
    warning "Limpiando volúmenes existentes..."
    docker-compose -f docker-compose.prod.yml down -v
    docker system prune -f
fi

# Crear red si no existe
docker network create copilotos-prod-network 2>/dev/null || true

# Iniciar servicios de base (MongoDB, Redis)
log "Iniciando servicios de base de datos..."
docker-compose -f docker-compose.prod.yml up -d mongodb redis

# Esperar a que los servicios estén saludables
log "Esperando a que los servicios estén listos..."
timeout 60 bash -c 'until docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; do sleep 2; done' || {
    error "Los servicios de base de datos no iniciaron correctamente"
}

success "Servicios de base de datos iniciados"

# Iniciar servicios de aplicación
log "Iniciando servicios de aplicación..."
docker-compose -f docker-compose.prod.yml up -d api web

# Esperar a que la API esté lista
log "Verificando que la API esté disponible..."
timeout 120 bash -c 'until curl -f http://localhost:8001/api/health &>/dev/null; do sleep 5; done' || {
    error "La API no se inició correctamente"
}

success "API iniciada correctamente"

# Verificar que el frontend esté disponible
log "Verificando que el frontend esté disponible..."
timeout 60 bash -c 'until curl -f http://localhost:3000 &>/dev/null; do sleep 5; done' || {
    error "El frontend no se inició correctamente"
}

success "Frontend iniciado correctamente"

# Mostrar estado de los servicios
log "Estado de los servicios:"
docker-compose -f docker-compose.prod.yml ps

# Mostrar logs recientes
log "Logs recientes de la API:"
docker-compose -f docker-compose.prod.yml logs --tail=20 api

# Configurar backup automático (opcional)
if command -v crontab &> /dev/null; then
    log "Configurando backup automático..."

    # Crear script de backup
    cat > /opt/copilotos-bridge/scripts/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/copilotos-bridge/backups"

# Backup MongoDB
docker exec copilotos-mongodb-prod mongodump --out "/data/backup/mongodb_$DATE"
tar -czf "$BACKUP_DIR/mongodb_$DATE.tar.gz" -C /opt/copilotos-bridge/data/mongodb backup

# Limpiar backups antiguos (mantener últimos 7 días)
find "$BACKUP_DIR" -name "mongodb_*.tar.gz" -mtime +7 -delete

echo "Backup completado: mongodb_$DATE.tar.gz"
EOF

    chmod +x /opt/copilotos-bridge/scripts/backup.sh

    # Agregar a crontab si no existe
    if ! crontab -l 2>/dev/null | grep -q "backup.sh"; then
        (crontab -l 2>/dev/null; echo "0 2 * * * /opt/copilotos-bridge/scripts/backup.sh >> /opt/copilotos-bridge/logs/backup.log 2>&1") | crontab -
        success "Backup automático configurado (diario a las 2 AM)"
    fi
fi

# Configurar logrotate
log "Configurando rotación de logs..."
sudo tee /etc/logrotate.d/copilotos-bridge > /dev/null << 'EOF'
/opt/copilotos-bridge/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        docker-compose -f /opt/copilotos-bridge/docker-compose.prod.yml restart
    endscript
}
EOF

success "Logrotate configurado"

# Crear archivo de estado del despliegue
cat > /opt/copilotos-bridge/.deployment-status << EOF
DEPLOYMENT_DATE=$(date)
DEPLOYMENT_SUCCESS=true
API_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000
GIT_COMMIT=$(git rev-parse HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
DOCKER_IMAGES=$(docker-compose -f docker-compose.prod.yml images --format "table {{.Service}}\t{{.Image}}\t{{.Tag}}")
EOF

echo
success "🎉 Despliegue de producción completado exitosamente!"
echo
echo -e "${BLUE}URLs de acceso:${NC}"
echo "• Frontend: ${GREEN}http://localhost:3000${NC}"
echo "• API:      ${GREEN}http://localhost:8001${NC}"
echo "• Docs:     ${GREEN}http://localhost:8001/docs${NC}"
echo "• Health:   ${GREEN}http://localhost:8001/health${NC}"
echo
echo -e "${BLUE}Comandos útiles:${NC}"
echo "• Ver logs:     ${GREEN}docker-compose -f docker-compose.prod.yml logs -f${NC}"
echo "• Estado:       ${GREEN}docker-compose -f docker-compose.prod.yml ps${NC}"
echo "• Reiniciar:    ${GREEN}docker-compose -f docker-compose.prod.yml restart${NC}"
echo "• Detener:      ${GREEN}docker-compose -f docker-compose.prod.yml down${NC}"
echo
echo -e "${YELLOW}Notas importantes:${NC}"
echo "• Los datos se guardan en /opt/copilotos-bridge/data/"
echo "• Los logs están en /opt/copilotos-bridge/logs/"
echo "• Los backups automáticos se ejecutan diariamente"
echo "• Configura un proxy reverso (nginx/traefik) para HTTPS"
echo
