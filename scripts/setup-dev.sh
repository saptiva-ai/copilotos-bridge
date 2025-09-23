#!/bin/bash

# ========================================
# Setup de Desarrollo Local - Copilot OS
# ========================================

set -e

echo "🚀 Configurando entorno de desarrollo local..."

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
}

# Verificar prerrequisitos
log "Verificando prerrequisitos..."

# Node.js
if ! command -v node &> /dev/null; then
    error "Node.js no encontrado. Instala Node.js >= 18"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    error "Node.js versión $NODE_VERSION detectada. Se requiere >= 18"
    exit 1
fi
success "Node.js $(node -v) ✓"

# Python
if ! command -v python3 &> /dev/null; then
    error "Python3 no encontrado. Instala Python >= 3.10"
    exit 1
fi
success "Python $(python3 --version) ✓"

# pnpm
if ! command -v pnpm &> /dev/null; then
    warning "pnpm no encontrado. Instalando..."
    npm install -g pnpm
fi
success "pnpm $(pnpm --version) ✓"

# Ir al directorio raíz del proyecto
cd "$(dirname "$0")/.."

# Instalar dependencias
log "Instalando dependencias..."
pnpm install
success "Dependencias instaladas"

# Configurar variables de entorno para desarrollo
log "Configurando variables de entorno..."

# Backend - usar configuración de desarrollo
cp apps/api/.env.development apps/api/.env.local
success "Backend .env.local configurado"

# Frontend - verificar y crear si no existe
if [ ! -f apps/web/.env.local ]; then
    cp apps/web/.env.local.example apps/web/.env.local
    success "Frontend .env.local creado"
else
    success "Frontend .env.local ya existe"
fi

# Construir shared package
log "Construyendo shared package..."
pnpm --filter shared build
success "Shared package construido"

# Configurar entorno Python para API
log "Configurando entorno Python..."
cd apps/api

# Crear virtual environment si no existe
if [ ! -d "venv" ]; then
    python3 -m venv venv
    success "Virtual environment creado"
fi

# Activar virtual environment e instalar dependencias
source venv/bin/activate
pip install -r requirements.txt
success "Dependencias Python instaladas"

cd ../..

# Verificar configuración
log "Verificando configuración..."

# Verificar que las APIs keys están configuradas
if grep -q "SAPTIVA_API_KEY=va-ai-" apps/api/.env.local; then
    success "SAPTIVA API key configurada"
else
    warning "SAPTIVA API key no configurada en apps/api/.env.local"
fi

# Crear archivo de estado para desarrollo
cat > .dev-status << EOF
# Estado del entorno de desarrollo
SETUP_DATE=$(date)
SETUP_COMPLETE=true
FRONTEND_PORT=3000
BACKEND_PORT=8001
NODE_VERSION=$(node -v)
PYTHON_VERSION=$(python3 --version)
PNPM_VERSION=$(pnpm --version)
EOF

echo
success "🎉 Entorno de desarrollo configurado exitosamente!"
echo
echo -e "${BLUE}Próximos pasos:${NC}"
echo "1. Levantar la API:     ${GREEN}pnpm run dev:api${NC}"
echo "2. Levantar el frontend: ${GREEN}pnpm run dev:web${NC}"
echo "3. Acceder a:           ${GREEN}http://localhost:3000${NC}"
echo
echo -e "${YELLOW}Notas:${NC}"
echo "• API corre en puerto 8001"
echo "• Frontend en puerto 3000"
echo "• Sin Docker - usa servicios locales/simulados"
echo "• SAPTIVA API real configurada"
echo "• MongoDB y Redis opcionales (usa fallbacks)"
echo