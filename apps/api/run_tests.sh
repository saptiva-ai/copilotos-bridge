#!/bin/bash

# Script para ejecutar suite completo de tests
# Incluye tests unitarios, integración y e2e

set -e  # Exit on error

# Configurar variable de entorno para tests
export PROMPT_REGISTRY_PATH=prompts/registry.yaml

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         COPILOTOS BRIDGE - TEST SUITE                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Debe ejecutar este script desde apps/api/${NC}"
    exit 1
fi

# Verificar que pytest esté instalado
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest no está instalado${NC}"
    echo -e "${YELLOW}Ejecute: pip install pytest pytest-asyncio${NC}"
    exit 1
fi

# Función para mostrar separador
separator() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Función para ejecutar tests con reporte
run_tests() {
    local name=$1
    local path=$2
    local marker=$3

    separator
    echo -e "${YELLOW}📋 Ejecutando: ${name}${NC}"
    echo ""

    if [ -n "$marker" ]; then
        pytest "$path" -v -m "$marker" --tb=short
    else
        pytest "$path" -v --tb=short
    fi

    local exit_code=$?
    echo ""

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ ${name}: PASSED${NC}"
    else
        echo -e "${RED}❌ ${name}: FAILED${NC}"
        return $exit_code
    fi
}

# 1. Tests Unitarios - Prompt Registry
run_tests "Tests Unitarios - Prompt Registry" "tests/test_prompt_registry.py"

# 2. Tests Unitarios - Health Check
run_tests "Tests Unitarios - Health Check" "tests/test_health.py"

# 3. Tests de Integración - Database
if [ -d "tests/integration" ]; then
    run_tests "Tests de Integración - Database" "tests/integration/test_database.py"
fi

# 4. Tests E2E - Registry Configuration
run_tests "Tests E2E - Registry Configuration" "tests/e2e/test_registry_configuration.py"

# 5. Tests E2E - Chat Models
echo -e "${YELLOW}⚠️  Nota: Tests E2E de chat requieren API corriendo${NC}"
echo -e "${YELLOW}   Si la API no está corriendo, estos tests fallarán${NC}"
echo ""
run_tests "Tests E2E - Chat Models" "tests/e2e/test_chat_models.py" || true

# Resumen final
separator
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  RESUMEN DE TESTS                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Tests unitarios completados${NC}"
echo -e "${GREEN}✅ Tests de integración completados${NC}"
echo -e "${GREEN}✅ Tests E2E de configuración completados${NC}"
echo -e "${YELLOW}⚠️  Tests E2E de chat requieren API en ejecución${NC}"
echo ""
echo -e "${BLUE}Para ejecutar solo un tipo de test:${NC}"
echo -e "  ${YELLOW}pytest tests/test_prompt_registry.py -v${NC}           # Unitarios"
echo -e "  ${YELLOW}pytest tests/e2e/ -v${NC}                              # E2E completos"
echo -e "  ${YELLOW}pytest tests/e2e/test_registry_configuration.py -v${NC} # E2E config"
echo ""
echo -e "${BLUE}Para ver cobertura:${NC}"
echo -e "  ${YELLOW}pytest --cov=src --cov-report=html${NC}"
echo ""
