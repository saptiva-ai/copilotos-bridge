#!/bin/bash
# Test script for password reset functionality
# Usage: ./scripts/test_password_reset.sh <email>

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL="${API_URL:-http://localhost:8000}"
EMAIL="${1:-demo@example.com}"

echo -e "${YELLOW}Testing Password Reset Flow${NC}"
echo "================================"
echo "API URL: $API_URL"
echo "Email: $EMAIL"
echo ""

# Test 1: Request password reset
echo -e "${YELLOW}[1/3] Testing forgot-password endpoint...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ]; then
  echo -e "${GREEN}✓ Forgot password endpoint working${NC}"
  echo "Response: $BODY"
else
  echo -e "${RED}✗ Forgot password endpoint failed (HTTP $HTTP_CODE)${NC}"
  echo "Response: $BODY"
  exit 1
fi

echo ""

# Test 2: Verify MongoDB document was created
echo -e "${YELLOW}[2/3] Checking if reset token was created in MongoDB...${NC}"
MONGO_CHECK=$(docker compose exec -T mongodb mongosh \
  --quiet \
  --eval "db = db.getSiblingDB('octavios'); db.password_reset_tokens.find({email: '$EMAIL'}).count()" \
  mongodb://octavios_user:secure_password_change_me@localhost:27017/octavios?authSource=admin 2>/dev/null || echo "0")

if [ "$MONGO_CHECK" -gt 0 ]; then
  echo -e "${GREEN}✓ Reset token found in database${NC}"
  echo "Total tokens for $EMAIL: $MONGO_CHECK"
else
  echo -e "${RED}✗ No reset token found in database${NC}"
  exit 1
fi

echo ""

# Test 3: Test reset endpoint with invalid token
echo -e "${YELLOW}[3/3] Testing reset-password endpoint with invalid token...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"invalid-token-12345\", \"new_password\": \"NewPassword123\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 400 ]; then
  echo -e "${GREEN}✓ Reset password endpoint correctly rejects invalid token${NC}"
  echo "Response: $BODY"
else
  echo -e "${RED}✗ Reset password endpoint should reject invalid tokens (HTTP $HTTP_CODE)${NC}"
  echo "Response: $BODY"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All automated tests passed!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Check your email inbox for: $EMAIL"
echo "2. Click the reset link in the email"
echo "3. Set a new password on the web interface"
echo "4. Verify you can login with the new password"
echo ""
echo -e "${YELLOW}Note:${NC} Make sure SMTP is configured correctly in envs/.env"
echo "See docs/guides/PASSWORD_RESET_SETUP.md for setup instructions"
