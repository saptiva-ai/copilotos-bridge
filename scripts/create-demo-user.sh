#!/bin/bash
#
# Simple demo user creation script using API endpoints
# Works with the running Docker environment
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Demo user credentials
USERNAME="demo_admin"
EMAIL="demo@saptiva.ai"
PASSWORD="ChangeMe123!"

# API configuration
API_URL="${API_URL:-http://localhost:8001}"
MAX_RETRIES=5
RETRY_DELAY=2

echo -e "${BLUE}🚀 Creating demo user for Copilotos Bridge...${NC}"
echo "=================================================="

# Function to wait for API to be ready
wait_for_api() {
    echo -e "${YELLOW}⏳ Waiting for API to be ready...${NC}"

    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s -f "${API_URL}/api/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API is ready!${NC}"
            return 0
        fi

        echo -e "${YELLOW}   Attempt ${i}/${MAX_RETRIES} - API not ready yet, waiting ${RETRY_DELAY}s...${NC}"
        sleep $RETRY_DELAY
    done

    echo -e "${RED}❌ API failed to become ready after ${MAX_RETRIES} attempts${NC}"
    echo -e "${YELLOW}💡 Try running: make dev${NC}"
    return 1
}

# Function to delete existing demo user (requires admin access or database direct access)
delete_demo_user() {
    echo -e "${YELLOW}🗑️  Checking if demo user needs to be recreated...${NC}"

    # Test if current password works
    LOGIN_TEST=$(curl -s -w "\n%{http_code}" \
        -X POST "${API_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"identifier\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" 2>/dev/null)

    LOGIN_CODE=$(echo "$LOGIN_TEST" | tail -n1)

    if [ "$LOGIN_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Demo user already has correct credentials${NC}"
        return 0
    fi

    if [ "$LOGIN_CODE" = "401" ] || [ "$LOGIN_CODE" = "404" ]; then
        echo -e "${BLUE}ℹ️  Demo user not found yet. Proceeding with creation...${NC}"
        return 0
    fi

    # Any other status likely means conflicting credentials
    echo -e "${YELLOW}⚠️  Demo user exists but has incorrect password${NC}"
    echo -e "${YELLOW}💡 Please manually clean up the database or use a different username${NC}"
    echo ""
    echo -e "${BLUE}Database cleanup options:${NC}"
    echo -e "   1. Delete specific user: ${BLUE}docker exec infra-mongodb mongosh -u copilotos_user -p secure_password_change_me --authenticationDatabase admin copilotos --eval \"db.users.deleteOne({username: 'demo_admin'})\"${NC}"
    echo -e "   2. Drop users collection: ${BLUE}docker exec infra-mongodb mongosh -u copilotos_user -p secure_password_change_me --authenticationDatabase admin copilotos --eval \"db.users.drop()\"${NC}"
    echo ""
    return 1
}

# Function to create user via API
create_user() {
    echo -e "${YELLOW}👤 Creating demo user...${NC}"

    # Create JSON payload
    JSON_PAYLOAD=$(cat <<EOF
{
  "username": "$USERNAME",
  "email": "$EMAIL",
  "password": "$PASSWORD"
}
EOF
)

    # Make API request
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "${API_URL}/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "$JSON_PAYLOAD" 2>/dev/null)

    # Extract HTTP code and response body
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$RESPONSE" | head -n-1)

    case $HTTP_CODE in
        200|201)
            echo -e "${GREEN}✅ Demo user created successfully!${NC}"
            echo -e "   ${BLUE}Username:${NC} $USERNAME"
            echo -e "   ${BLUE}Email:${NC}    $EMAIL"
            echo -e "   ${BLUE}Password:${NC} $PASSWORD"
            echo ""
            echo -e "${GREEN}🎉 You can now login at: ${API_URL%:*}:3000/login${NC}"
            return 0
            ;;
        409|422)
            # User might already exist, try to get more details
            if echo "$RESPONSE_BODY" | grep -q "already exists\|duplicate\|unique\|already registered"; then
                echo -e "${YELLOW}ℹ️  Demo user already exists!${NC}"
                echo -e "   ${BLUE}Username:${NC} $USERNAME"
                echo -e "   ${BLUE}Email:${NC}    $EMAIL"
                echo -e "   ${BLUE}Password:${NC} $PASSWORD"
                echo ""
                echo -e "${GREEN}🎉 You can login at: ${API_URL%:*}:3000/login${NC}"
                return 0
            else
                echo -e "${RED}❌ Validation error:${NC}"
                echo "$RESPONSE_BODY" | head -5
                return 1
            fi
            ;;
        *)
            echo -e "${RED}❌ Unexpected response (HTTP $HTTP_CODE):${NC}"
            echo "$RESPONSE_BODY" | head -5
            return 1
            ;;
    esac
}

# Function to test login
test_login() {
    echo -e "${YELLOW}🔍 Testing login...${NC}"

    LOGIN_PAYLOAD=$(cat <<EOF
{
  "identifier": "$USERNAME",
  "password": "$PASSWORD"
}
EOF
)

    LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "${API_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "$LOGIN_PAYLOAD" 2>/dev/null)

    LOGIN_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)

    if [ "$LOGIN_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Login test successful!${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Login test failed (HTTP $LOGIN_CODE)${NC}"
        echo "   This might be normal if the user was just created"
        return 0
    fi
}

# Function to show troubleshooting tips
show_troubleshooting() {
    echo -e "${YELLOW}📖 Troubleshooting:${NC}"
    echo "   1. Make sure the development environment is running:"
    echo -e "      ${BLUE}make dev${NC}"
    echo ""
    echo "   2. Check container status:"
    echo -e "      ${BLUE}docker ps${NC}"
    echo ""
    echo "   3. Check API health:"
    echo -e "      ${BLUE}curl ${API_URL}/api/health${NC}"
    echo ""
    echo "   4. View API logs:"
    echo -e "      ${BLUE}docker logs infra-api${NC}"
}

# Main execution
main() {
    # Wait for API
    if ! wait_for_api; then
        show_troubleshooting
        exit 1
    fi

    # Check/delete existing user if needed
    if ! delete_demo_user; then
        echo ""
        show_troubleshooting
        exit 1
    fi

    # Create user
    if ! create_user; then
        echo ""
        show_troubleshooting
        exit 1
    fi

    # Test login
    test_login

    echo ""
    echo -e "${GREEN}✅ Demo user setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}🌐 Access the application:${NC}"
    echo -e "   Frontend: ${BLUE}http://localhost:3000${NC}"
    echo -e "   API:      ${BLUE}http://localhost:8001${NC}"
    echo -e "   Login:    ${BLUE}http://localhost:3000/login${NC}"
}

# Handle script interruption
trap 'echo -e "\n${YELLOW}⚠️  Script interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@"
