#!/bin/bash
# ============================================================================
# Script para ejecutar tests E2E de documentos
# ============================================================================
# Este script configura el entorno correcto y ejecuta los tests de documentos
# con las credenciales apropiadas del backup.
# ============================================================================

set -e  # Exit on error

echo "🧪 Configurando entorno para tests E2E de documentos..."
echo ""

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Verificar que el venv existe
if [ ! -d ".venv" ]; then
    echo "❌ Error: No se encontró .venv"
    echo "   Por favor ejecuta: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activar venv
echo "📦 Activando entorno virtual..."
source .venv/bin/activate

# Cargar variables de entorno del backup
BACKUP_ENV="/home/jazielflo/Proyects/backup/copilotos-bridge/envs/.env"
if [ ! -f "$BACKUP_ENV" ]; then
    echo "❌ Error: No se encontró el archivo .env del backup en $BACKUP_ENV"
    exit 1
fi

echo "🔐 Cargando credenciales desde $BACKUP_ENV..."

# Leer variables específicas del backup (evitar CORS_ORIGINS que causa problemas)
export MONGODB_USER=$(grep '^MONGODB_USER=' "$BACKUP_ENV" | cut -d '=' -f2)
export MONGODB_PASSWORD=$(grep '^MONGODB_PASSWORD=' "$BACKUP_ENV" | cut -d '=' -f2)
export MONGODB_DATABASE=$(grep '^MONGODB_DATABASE=' "$BACKUP_ENV" | cut -d '=' -f2)
export REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "$BACKUP_ENV" | cut -d '=' -f2)
export JWT_SECRET_KEY=$(grep '^JWT_SECRET_KEY=' "$BACKUP_ENV" | cut -d '=' -f2)
export SECRET_KEY=$(grep '^SECRET_KEY=' "$BACKUP_ENV" | cut -d '=' -f2)
export SAPTIVA_API_KEY=$(grep '^SAPTIVA_API_KEY=' "$BACKUP_ENV" | cut -d '=' -f2)

# Configurar URLs para tests locales (usar localhost en vez de hostnames de Docker)
export MONGODB_URL="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27018/${MONGODB_DATABASE}?authSource=admin&directConnection=true"
export REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:6380/0"
export REDIS_HOST="localhost"
export REDIS_PORT="6380"

# Variables adicionales necesarias
export DEBUG="true"
export LOG_LEVEL="info"
export JWT_ALGORITHM="HS256"
export SAPTIVA_BASE_URL="https://api.saptiva.com"

echo "✅ Variables cargadas:"
echo "   MongoDB: localhost:27018/$MONGODB_DATABASE"
echo "   Redis: localhost:6380"
echo "   User: $MONGODB_USER"

# Verificar contenedores
echo ""
echo "🐳 Verificando contenedores..."
if ! docker ps | grep -q "copilotos-mongodb"; then
    echo "❌ Error: Contenedor MongoDB no está corriendo"
    echo "   Por favor ejecuta: make dev"
    exit 1
fi

if ! docker ps | grep -q "copilotos-redis"; then
    echo "❌ Error: Contenedor Redis no está corriendo"
    echo "   Por favor ejecuta: make dev"
    exit 1
fi

echo "✅ MongoDB: OK (puerto 27018)"
echo "✅ Redis: OK (puerto 6380)"

# Verificar pytest instalado
echo ""
echo "🔍 Verificando pytest..."
if ! python -c "import pytest" 2>/dev/null; then
    echo "❌ Error: pytest no está instalado"
    echo "   Instalando pytest..."
    pip install pytest pytest-asyncio
fi

echo "✅ pytest instalado"

# Ejecutar tests
echo ""
echo "🚀 Ejecutando tests E2E de documentos..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

pytest tests/e2e/test_documents.py -v --tb=short --color=yes

EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tests completados exitosamente"
else
    echo "❌ Tests fallaron (exit code: $EXIT_CODE)"
fi
echo ""

exit $EXIT_CODE
