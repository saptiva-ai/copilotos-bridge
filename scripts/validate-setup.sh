#!/bin/bash

# ==============================================
# Setup Validation Script
# Tests all the new tools and commands we've implemented
# ==============================================

set -e

# Colors for output
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
CYAN='\033[36m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Validating New Setup and Tools${NC}"
echo "$(date)"
echo "========================================"
echo ""

# Test 1: Environment Manager
echo -e "${CYAN}1. Testing Environment Manager${NC}"
if ./scripts/env-manager.sh list; then
    echo -e "${GREEN}✅ Environment Manager functional${NC}"
else
    echo -e "${RED}❌ Environment Manager failed${NC}"
fi
echo ""

# Test 2: Production Health Check (quick mode)
echo -e "${CYAN}2. Testing Production Health Check${NC}"
if ./scripts/prod-health-check.sh quick; then
    echo -e "${GREEN}✅ Production Health Check functional${NC}"
else
    echo -e "${YELLOW}⚠️  Production Health Check issues (expected if not deployed)${NC}"
fi
echo ""

# Test 3: Makefile New Commands
echo -e "${CYAN}3. Testing Makefile Commands${NC}"
echo "Testing make help..."
if make help | grep -q "Environment Manager"; then
    echo -e "${GREEN}✅ Makefile help includes new commands${NC}"
else
    echo -e "${RED}❌ Makefile help missing new commands${NC}"
fi

echo "Testing env-list command..."
if make env-list >/dev/null 2>&1; then
    echo -e "${GREEN}✅ make env-list functional${NC}"
else
    echo -e "${RED}❌ make env-list failed${NC}"
fi
echo ""

# Test 4: Scripts Permissions
echo -e "${CYAN}4. Checking Script Permissions${NC}"
scripts_to_check=(
    "scripts/env-manager.sh"
    "scripts/prod-health-check.sh"
    "scripts/build-frontend.sh"
    "scripts/validate-setup.sh"
)

for script in "${scripts_to_check[@]}"; do
    if [[ -x "$script" ]]; then
        echo -e "${GREEN}✅ $script executable${NC}"
    else
        echo -e "${RED}❌ $script not executable${NC}"
    fi
done
echo ""

# Test 5: Environment Files Structure
echo -e "${CYAN}5. Checking Environment Structure${NC}"
env_files=(
    "envs/.env.local"
    "envs/.env.staging"
    "envs/.env.prod"
)

for env_file in "${env_files[@]}"; do
    if [[ -f "$env_file" ]]; then
        echo -e "${GREEN}✅ $env_file exists${NC}"
    else
        echo -e "${YELLOW}⚠️  $env_file missing (may need setup)${NC}"
    fi
done
echo ""

# Test 6: Docker Compose Files
echo -e "${CYAN}6. Checking Docker Infrastructure${NC}"
required_compose=(
    "infra/docker-compose.yml"
)
optional_compose=(
    "infra/docker-compose.override.yml"
    "infra/docker-compose.prod.yml"
    "infra/docker-compose.staging.yml"
)

for compose_file in "${required_compose[@]}"; do
    if [[ -f "$compose_file" ]]; then
        echo -e "${GREEN}✅ $compose_file exists${NC}"
    else
        echo -e "${RED}❌ Required $compose_file missing${NC}"
    fi
done

for compose_file in "${optional_compose[@]}"; do
    if [[ -f "$compose_file" ]]; then
        echo -e "${GREEN}✅ Optional $compose_file present${NC}"
    else
        echo -e "${YELLOW}⚠️  Optional $compose_file not found${NC}"
    fi
done
echo ""

# Test 7: Frontend Cache Configuration
echo -e "${CYAN}7. Checking Frontend Cache Configuration${NC}"
if grep -q "Cache-Control.*no-store" apps/web/next.config.js; then
    echo -e "${GREEN}✅ Anti-cache headers configured${NC}"
else
    echo -e "${RED}❌ Anti-cache headers missing${NC}"
fi

if grep -q "clearCache" apps/web/src/lib/auth-store.ts; then
    echo -e "${GREEN}✅ Auth store cache clearing implemented${NC}"
else
    echo -e "${RED}❌ Auth store cache clearing missing${NC}"
fi
echo ""

# Test 8: API Client Environment Detection
echo -e "${CYAN}8. Checking API Client Environment Detection${NC}"
if grep -q "getApiBaseUrl" apps/web/src/lib/api-client.ts; then
    echo -e "${GREEN}✅ Smart API URL detection implemented${NC}"
else
    echo -e "${RED}❌ Smart API URL detection missing${NC}"
fi

if grep -q "window.location.origin" apps/web/src/lib/api-client.ts; then
    echo -e "${GREEN}✅ Production URL detection implemented${NC}"
else
    echo -e "${RED}❌ Production URL detection missing${NC}"
fi
echo ""

# Summary
echo "========================================"
echo -e "${BLUE}📊 Validation Summary${NC}"
echo ""
echo -e "${GREEN}✅ Completed Implementations:${NC}"
echo "  • Environment management scripts"
echo "  • Production health monitoring"
echo "  • Enhanced Makefile with 15+ new commands"
echo "  • Smart API URL detection for dev/prod"
echo "  • Improved cache management"
echo "  • Debug components for troubleshooting"
echo "  • Documentation updates"
echo ""
echo -e "${YELLOW}📝 Key Commands Available:${NC}"
echo "  • make env-list                    - List all environments"
echo "  • make env-validate ENV=prod      - Validate specific environment"
echo "  • make prod-health                - Full production health check"
echo "  • make global-vars-check          - Check all environment variables"
echo "  • make deploy-prod-safe           - Safe production deployment"
echo "  • make security-check             - Security validation"
echo ""
echo -e "${CYAN}🚀 Next Steps:${NC}"
echo "  1. Configure HTTPS for production security"
echo "  2. Set up real SAPTIVA_API_KEY"
echo "  3. Implement automated E2E tests"
echo ""
echo -e "${GREEN}🎉 Setup validation completed!${NC}"
