#!/bin/bash

# ==============================================
# Production Health Check Script
# Comprehensive validation for production deployments
# ==============================================

set -e

# Colors for output
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
CYAN='\033[36m'
NC='\033[0m' # No Color

# Configuration
PROD_HOST="34.42.214.246"
PROD_USER="jf"
LOCAL_API="http://localhost:8001"
PROD_API="http://$PROD_HOST"
FRONTEND_URL="http://$PROD_HOST"

# Test credentials (for integration testing)
TEST_USER="demo_admin"
TEST_PASS="ChangeMe123!"

show_help() {
    echo -e "${GREEN}🏥 Production Health Check${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [command]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  full            - Complete health check (default)"
    echo "  quick           - Quick connectivity check"
    echo "  auth            - Authentication flow test"
    echo "  api             - API endpoints test"
    echo "  frontend        - Frontend availability test"
    echo "  infrastructure  - Infrastructure components test"
    echo "  remote          - Run checks on remote server"
    echo "  compare         - Compare local vs production"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 full"
    echo "  $0 quick"
    echo "  $0 auth"
}

check_connectivity() {
    echo -e "${CYAN}🌐 Connectivity Check${NC}"
    echo ""

    # Test SSH connectivity
    echo -e "${YELLOW}🔑 SSH Connectivity:${NC}"
    if timeout 10 ssh -o ConnectTimeout=5 "$PROD_USER@$PROD_HOST" "echo 'SSH OK'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH connection successful${NC}"
    else
        echo -e "${RED}❌ SSH connection failed${NC}"
        return 1
    fi

    # Test HTTP connectivity
    echo -e "${YELLOW}🌐 HTTP Connectivity:${NC}"
    if timeout 10 curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✅ HTTP connection successful${NC}"
    else
        echo -e "${RED}❌ HTTP connection failed${NC}"
        return 1
    fi

    echo ""
    return 0
}

check_api_health() {
    echo -e "${CYAN}🔌 API Health Check${NC}"
    echo ""

    # Health endpoint
    echo -e "${YELLOW}❤️ Health Endpoint:${NC}"
    local health_response=$(timeout 15 curl -s "$PROD_API/api/health" 2>/dev/null || echo "ERROR")

    if echo "$health_response" | grep -q '"status".*"healthy"'; then
        echo -e "${GREEN}✅ API health endpoint responding${NC}"
        local uptime=$(echo "$health_response" | grep -o '"uptime_seconds":[0-9]*' | cut -d':' -f2)
        if [[ -n "$uptime" && "$uptime" -gt 0 ]]; then
            echo -e "${BLUE}   Uptime: $((uptime / 3600))h $((uptime % 3600 / 60))m${NC}"
        fi
    else
        echo -e "${RED}❌ API health endpoint failed${NC}"
        echo "Response: ${health_response:0:200}..."
        return 1
    fi

    # Test core endpoints
    echo -e "${YELLOW}🔍 Core Endpoints:${NC}"
    local endpoints=(
        "/api/health"
        "/api/auth/login"
    )

    for endpoint in "${endpoints[@]}"; do
        local status_code=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" "$PROD_API$endpoint" 2>/dev/null || echo "000")
        if [[ "$status_code" == "200" || "$status_code" == "405" || "$status_code" == "422" ]]; then
            echo -e "${GREEN}✅ $endpoint (HTTP $status_code)${NC}"
        else
            echo -e "${RED}❌ $endpoint (HTTP $status_code)${NC}"
        fi
    done

    echo ""
    return 0
}

check_authentication() {
    echo -e "${CYAN}🔐 Authentication Flow Test${NC}"
    echo ""

    # Test login
    echo -e "${YELLOW}🔑 Testing login...${NC}"
    local login_response=$(timeout 20 curl -s -X POST "$PROD_API/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"identifier\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}" 2>/dev/null || echo "ERROR")

    if echo "$login_response" | grep -q '"access_token"'; then
        echo -e "${GREEN}✅ Login successful${NC}"

        # Extract token for further testing
        local token=$(echo "$login_response" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

        if [[ -n "$token" ]]; then
            echo -e "${BLUE}   Token: ${token:0:20}...${NC}"

            # Test authenticated endpoint
            echo -e "${YELLOW}👤 Testing authenticated endpoint...${NC}"
            local me_response=$(timeout 15 curl -s "$PROD_API/api/auth/me" \
                -H "Authorization: Bearer $token" 2>/dev/null || echo "ERROR")

            if echo "$me_response" | grep -q '"username"'; then
                echo -e "${GREEN}✅ Authenticated endpoint working${NC}"
                local username=$(echo "$me_response" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
                echo -e "${BLUE}   User: $username${NC}"
            else
                echo -e "${RED}❌ Authenticated endpoint failed${NC}"
                return 1
            fi
        fi
    else
        echo -e "${RED}❌ Login failed${NC}"
        echo "Response: ${login_response:0:200}..."
        return 1
    fi

    echo ""
    return 0
}

check_frontend() {
    echo -e "${CYAN}🌐 Frontend Check${NC}"
    echo ""

    # Basic availability
    echo -e "${YELLOW}📱 Frontend Availability:${NC}"
    local status_code=$(timeout 15 curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null || echo "000")

    if [[ "$status_code" == "200" ]]; then
        echo -e "${GREEN}✅ Frontend responding (HTTP $status_code)${NC}"
    else
        echo -e "${RED}❌ Frontend not available (HTTP $status_code)${NC}"
        return 1
    fi

    # Check for essential resources
    echo -e "${YELLOW}📦 Essential Resources:${NC}"
    local resources=(
        "/_next/static/"
        "/favicon.ico"
    )

    for resource in "${resources[@]}"; do
        local res_status=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL$resource" 2>/dev/null || echo "000")
        if [[ "$res_status" == "200" || "$res_status" == "404" ]]; then
            echo -e "${GREEN}✅ $resource (HTTP $res_status)${NC}"
        else
            echo -e "${YELLOW}⚠️  $resource (HTTP $res_status)${NC}"
        fi
    done

    echo ""
    return 0
}

check_infrastructure() {
    echo -e "${CYAN}🏗️ Infrastructure Check${NC}"
    echo ""

    echo -e "${YELLOW}🐳 Checking Docker containers on remote...${NC}"
    local container_status=$(timeout 20 ssh "$PROD_USER@$PROD_HOST" "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep copilotos" 2>/dev/null || echo "ERROR")

    if [[ "$container_status" != "ERROR" ]]; then
        echo -e "${GREEN}✅ Containers running:${NC}"
        echo "$container_status"
    else
        echo -e "${RED}❌ Could not retrieve container status${NC}"
        return 1
    fi

    echo ""

    echo -e "${YELLOW}💾 Checking disk space...${NC}"
    local disk_usage=$(timeout 15 ssh "$PROD_USER@$PROD_HOST" "df -h | grep -E '(/$|/var)'" 2>/dev/null || echo "ERROR")

    if [[ "$disk_usage" != "ERROR" ]]; then
        echo -e "${GREEN}✅ Disk usage:${NC}"
        echo "$disk_usage"
    else
        echo -e "${YELLOW}⚠️  Could not retrieve disk usage${NC}"
    fi

    echo ""
    return 0
}

run_remote_checks() {
    echo -e "${CYAN}🖥️  Remote Server Checks${NC}"
    echo ""

    # Create temporary script for remote execution
    local remote_script="/tmp/health_check_$(date +%s).sh"

    cat > "$remote_script" << 'EOF'
#!/bin/bash
echo "🔍 Running remote health checks..."
echo ""

echo "📊 System Resources:"
echo "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

echo "🐳 Docker Status:"
docker ps --filter "name=copilotos" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not available"
echo ""

echo "🌐 Network Ports:"
netstat -tlnp 2>/dev/null | grep -E ':(3000|8001|80|443)' || ss -tlnp | grep -E ':(3000|8001|80|443)' || echo "Port info not available"
echo ""

echo "📁 Project Files:"
if [ -d "/home/jf/copilotos-bridge" ]; then
    echo "✅ Project directory exists"
    echo "Latest commit: $(cd /home/jf/copilotos-bridge && git log --oneline -1 2>/dev/null || echo 'Git info not available')"
else
    echo "❌ Project directory not found"
fi
EOF

    # Execute remote script
    if timeout 30 ssh "$PROD_USER@$PROD_HOST" "bash -s" < "$remote_script" 2>/dev/null; then
        echo -e "${GREEN}✅ Remote checks completed${NC}"
    else
        echo -e "${RED}❌ Remote checks failed${NC}"
        return 1
    fi

    # Cleanup
    rm -f "$remote_script"
    echo ""
    return 0
}

compare_environments() {
    echo -e "${CYAN}⚖️  Environment Comparison${NC}"
    echo ""

    echo -e "${YELLOW}🔍 Comparing API responses...${NC}"

    # Compare health endpoints
    echo "Local API Health:"
    timeout 10 curl -s "$LOCAL_API/api/health" 2>/dev/null | head -c 200 || echo "Local API not available"
    echo ""

    echo "Production API Health:"
    timeout 10 curl -s "$PROD_API/api/health" 2>/dev/null | head -c 200 || echo "Production API not available"
    echo ""

    echo -e "${YELLOW}📊 Response Time Comparison:${NC}"
    echo "Local API:"
    timeout 15 curl -s -o /dev/null -w "  Time: %{time_total}s, Size: %{size_download} bytes\n" "$LOCAL_API/api/health" 2>/dev/null || echo "  Not available"

    echo "Production API:"
    timeout 15 curl -s -o /dev/null -w "  Time: %{time_total}s, Size: %{size_download} bytes\n" "$PROD_API/api/health" 2>/dev/null || echo "  Not available"

    echo ""
    return 0
}

full_health_check() {
    echo -e "${GREEN}🏥 Full Production Health Check${NC}"
    echo "$(date)"
    echo "========================================"
    echo ""

    local checks=("check_connectivity" "check_api_health" "check_authentication" "check_frontend" "check_infrastructure")
    local failed_checks=()

    for check in "${checks[@]}"; do
        if ! $check; then
            failed_checks+=("$check")
        fi
    done

    echo "========================================"

    if [[ ${#failed_checks[@]} -eq 0 ]]; then
        echo -e "${GREEN}🎉 All health checks passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed checks: ${failed_checks[*]}${NC}"
        return 1
    fi
}

# Main command dispatcher
case "${1:-full}" in
    "full")
        full_health_check
        ;;
    "quick")
        check_connectivity
        ;;
    "auth")
        check_authentication
        ;;
    "api")
        check_api_health
        ;;
    "frontend")
        check_frontend
        ;;
    "infrastructure")
        check_infrastructure
        ;;
    "remote")
        run_remote_checks
        ;;
    "compare")
        compare_environments
        ;;
    "help"|*)
        show_help
        ;;
esac