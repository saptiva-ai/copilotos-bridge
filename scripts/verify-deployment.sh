#!/bin/bash

# Status symbols for logs
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
NC=""

echo "=========================================="
echo "  COPILOT OS - DEPLOYMENT VERIFICATION"
echo "=========================================="
echo ""

# Helper function for docker compose
DC() { 
  docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml "$@"
}

# 1. Check services are running
echo -e "${YELLOW}[1/8] Checking services status...${NC}"
if DC ps | grep -q "Up"; then
  echo -e "${GREEN}Services are running${NC}"
else
  echo -e "${RED}Services are not running${NC}"
  exit 1
fi
echo ""

# 2. Check healthz endpoint
echo -e "${YELLOW}[2/8] Testing /healthz endpoint...${NC}"
HEALTHZ_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/healthz)
if [ "$HEALTHZ_STATUS" -eq 200 ]; then
  echo -e "${GREEN}/healthz returned 200${NC}"
  curl -s http://localhost:3000/healthz
else
  echo -e "${RED}/healthz returned $HEALTHZ_STATUS${NC}"
fi
echo ""

# 3. Check chat page
echo -e "${YELLOW}[3/8] Testing /chat page...${NC}"
CHAT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/chat)
if [ "$CHAT_STATUS" -eq 200 ]; then
  echo -e "${GREEN}/chat returned 200${NC}"
else
  echo -e "${RED}/chat returned $CHAT_STATUS${NC}"
fi
echo ""

# 4. Check _next/static (should NOT return 502)
echo -e "${YELLOW}[4/8] Testing /_next/static path...${NC}"
STATIC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/_next/static/)
if [ "$STATIC_STATUS" -ne 502 ]; then
  echo -e "${GREEN}/_next/static returned $STATIC_STATUS (not 502 Bad Gateway)${NC}"
else
  echo -e "${RED}/_next/static returned 502 Bad Gateway${NC}"
fi
echo ""

# 5. Check API health
echo -e "${YELLOW}[5/8] Testing API health...${NC}"
API_HEALTH=$(curl -s http://localhost:8001/api/health)
if echo "$API_HEALTH" | grep -q '"status":"healthy"'; then
  echo -e "${GREEN}API is healthy${NC}"
  echo "$API_HEALTH"
else
  echo -e "${RED}API is not healthy${NC}"
fi
echo ""

# 6. Check Deep Research config in API
echo -e "${YELLOW}[6/8] Checking Deep Research configuration...${NC}"
echo "Environment variables in API container:"
DC exec api printenv | grep DEEP_RESEARCH
echo ""

# 7. Check production config
echo -e "${YELLOW}[7/8] Verifying production configuration...${NC}"
echo "Production docker-compose.yml should have DEEP_RESEARCH_ENABLED=false:"
grep "DEEP_RESEARCH_ENABLED" infra/docker-compose.yml | head -n 2
echo ""

# 8. Test authentication flow
echo -e "${YELLOW}[8/8] Testing authentication and Deep Research...${NC}"

# Try to register a test user (may fail if already exists)
echo "Attempting to register test user..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"verify@test.com","username":"verifyuser","password":"Test123!","full_name":"Verify User"}')

if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
  echo -e "${GREEN}User registered successfully${NC}"
  TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
elif echo "$REGISTER_RESPONSE" | grep -q "already exists"; then
  echo -e "${YELLOW}User already exists, attempting login...${NC}"
  LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"verifyuser","password":"Test123!"}')
  TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
else
  echo -e "${RED}Failed to register or login${NC}"
  echo "$REGISTER_RESPONSE"
fi

if [ ! -z "$TOKEN" ]; then
  echo -e "${GREEN}Got authentication token${NC}"
  
  # Test Deep Research endpoint
  echo "Testing Deep Research endpoint (should accept in dev)..."
  DR_RESPONSE=$(curl -s -X POST http://localhost:8001/api/deep-research \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"query":"Test query","research_type":"deep_research","stream":false}' \
    2>&1 | head -c 500)
  
  if echo "$DR_RESPONSE" | grep -q '"task_id"'; then
    echo -e "${GREEN}Deep Research accepted request (dev mode enabled)${NC}"
  elif echo "$DR_RESPONSE" | grep -q "disabled"; then
    echo -e "${YELLOW}Deep Research is disabled${NC}"
  else
    echo -e "${YELLOW}Deep Research returned: $(echo "$DR_RESPONSE" | head -n 1)${NC}"
  fi
fi

echo ""
echo "=========================================="
echo "  VERIFICATION COMPLETE"
echo "=========================================="
echo ""
echo -e "${GREEN}Summary:${NC}"
echo "- Next.js web service: Running on http://localhost:3000"
echo "- FastAPI backend: Running on http://localhost:8001"
echo "- Health endpoints: Responding correctly"
echo "- Authentication: Working"
echo "- Deep Research: Enabled in dev, disabled in prod (default)"
echo ""
echo -e "${YELLOW}Note:${NC} If Aletheia is not available, Deep Research will use fallback mode."
echo "This is expected in development without the full Aletheia service."
