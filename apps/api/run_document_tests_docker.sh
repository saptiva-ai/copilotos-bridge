#!/bin/bash
# ============================================================================
# Script para ejecutar tests E2E de documentos DENTRO del contenedor
# ============================================================================
# Este script ejecuta los tests dentro del contenedor copilotos-api donde
# las configuraciones de MongoDB y Redis ya están correctas.
# ============================================================================

set -e  # Exit on error

echo "🧪 Ejecutando tests E2E de documentos en contenedor..."
echo ""

# Verificar que el contenedor esté corriendo
if ! docker ps | grep -q "copilotos-api"; then
    echo "❌ Error: Contenedor copilotos-api no está corriendo"
    echo "   Por favor ejecuta: make dev"
    exit 1
fi

echo "✅ Contenedor copilotos-api está corriendo"
echo ""

# Instalar pytest en el contenedor si no está instalado
echo "📦 Verificando pytest en contenedor..."
docker exec copilotos-api bash -c "pip list | grep -q pytest || pip install pytest pytest-asyncio" > /dev/null 2>&1
echo "✅ pytest instalado"
echo ""

# Ejecutar tests dentro del contenedor
echo "🚀 Ejecutando tests E2E de documentos..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Usar exec sin -it para evitar error de TTY
# Usar python -m pytest porque pytest no está en PATH
docker exec copilotos-api bash -c "cd /app && python -m pytest tests/e2e/test_documents.py -v --tb=short --color=yes"

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
