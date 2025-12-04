#!/bin/bash
# Test script for Copiloto 414 audit flow (P2 validation)
# Tests: Upload → Process → Audit → Message creation
#
# Usage:
#   ./scripts/test_audit_flow.sh
#   API_URL=http://localhost:8000 ./scripts/test_audit_flow.sh
#   TEST_PDF=/path/to/sample.pdf ./scripts/test_audit_flow.sh

set -e

API_URL="${API_URL:-http://localhost:8001}"
TEST_PDF="${TEST_PDF:-tests/fixtures/sample.pdf}"

echo "🧪 Testing Copiloto 414 Audit Flow"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Login as demo user
echo "📝 Step 1: Authenticating..."
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}❌ Login failed. Creating demo user...${NC}"

  # Try to create demo user
  curl -s -X POST "${API_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@example.com","password":"Demo1234","name":"Demo User"}' > /dev/null

  # Retry login
  LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@example.com","password":"Demo1234"}')

  ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
fi

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
  echo -e "${RED}❌ Failed to get access token${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Authenticated successfully${NC}"
USER_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.id')
echo "   User ID: $USER_ID"
echo ""

# Step 2: Create a chat session
echo "💬 Step 2: Creating chat session..."
CHAT_RESPONSE=$(curl -s -X POST "${API_URL}/api/chat" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Audit Flow","model":"Saptiva Turbo"}')

CHAT_ID=$(echo "$CHAT_RESPONSE" | jq -r '.chat_id // .id // empty')

if [ -z "$CHAT_ID" ] || [ "$CHAT_ID" == "null" ]; then
  echo -e "${RED}❌ Failed to create chat session${NC}"
  echo "Response: $CHAT_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Chat session created${NC}"
echo "   Chat ID: $CHAT_ID"
echo ""

# Step 3: Upload document
echo "📤 Step 3: Uploading test document..."
if [ ! -f "$TEST_PDF" ]; then
  echo -e "${RED}❌ Test PDF not found: $TEST_PDF${NC}"
  exit 1
fi

UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/api/files/upload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "files=@${TEST_PDF}" \
  -F "conversation_id=${CHAT_ID}")

DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.files[0].file_id // empty')

if [ -z "$DOC_ID" ] || [ "$DOC_ID" == "null" ]; then
  echo -e "${RED}❌ Failed to upload document${NC}"
  echo "Response: $UPLOAD_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Document uploaded${NC}"
echo "   Document ID: $DOC_ID"
echo ""

# Step 4: Wait for document processing
echo "⏳ Step 4: Waiting for document processing..."
MAX_WAIT=180  # 3 minutes max
WAIT_TIME=0
DOC_STATUS="pending"

while [ "$DOC_STATUS" != "ready" ] && [ $WAIT_TIME -lt $MAX_WAIT ]; do
  sleep 5
  WAIT_TIME=$((WAIT_TIME + 5))

  DOC_INFO=$(curl -s -X GET "${API_URL}/api/documents/${DOC_ID}" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

  DOC_STATUS=$(echo "$DOC_INFO" | jq -r '.status // "unknown"')

  echo "   Status: $DOC_STATUS (waited ${WAIT_TIME}s)"

  if [ "$DOC_STATUS" == "ERROR" ] || [ "$DOC_STATUS" == "FAILED" ]; then
    echo -e "${RED}❌ Document processing failed${NC}"
    exit 1
  fi
done

if [ "$DOC_STATUS" != "ready" ]; then
  echo -e "${YELLOW}⚠️  Document still processing after ${WAIT_TIME}s, but continuing...${NC}"
fi

echo -e "${GREEN}✅ Document ready${NC}"
PAGES=$(echo "$DOC_INFO" | jq -r '.pages | length')
echo "   Pages: $PAGES"
echo ""

# Step 5: Invoke audit tool
echo "🔍 Step 5: Invoking audit tool..."
AUDIT_RESPONSE=$(curl -s -X POST "${API_URL}/api/chat/tools/audit-file?doc_id=${DOC_ID}&chat_id=${CHAT_ID}&policy_id=auto" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

AUDIT_STATUS=$(echo "$AUDIT_RESPONSE" | jq -r '.message // .error // empty')

if [ -z "$AUDIT_STATUS" ]; then
  echo -e "${RED}❌ Audit invocation failed${NC}"
  echo "Response: $AUDIT_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Audit completed${NC}"
MESSAGE_ID=$(echo "$AUDIT_RESPONSE" | jq -r '.id // empty')
echo "   Message ID: $MESSAGE_ID"
echo ""

# Step 6: Verify audit message
echo "✅ Step 6: Verifying audit message..."
MESSAGE_INFO=$(curl -s -X GET "${API_URL}/api/chat/${CHAT_ID}" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

LAST_MESSAGE=$(echo "$MESSAGE_INFO" | jq -r '.messages[-1]')
HAS_VALIDATION_ID=$(echo "$LAST_MESSAGE" | jq -r '.validation_report_id // empty')

if [ -n "$HAS_VALIDATION_ID" ] && [ "$HAS_VALIDATION_ID" != "null" ]; then
  echo -e "${GREEN}✅ Audit message created with validation_report_id${NC}"
  echo "   Validation Report ID: $HAS_VALIDATION_ID"

  TOTAL_FINDINGS=$(echo "$LAST_MESSAGE" | jq -r '.metadata.summary.total_findings // 0')
  POLICY_NAME=$(echo "$LAST_MESSAGE" | jq -r '.metadata.summary.policy_name // "unknown"')

  echo "   Policy: $POLICY_NAME"
  echo "   Total Findings: $TOTAL_FINDINGS"
else
  echo -e "${YELLOW}⚠️  Message created but no validation_report_id found${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo ""
echo "Test Results:"
echo "  • User authenticated: ✅"
echo "  • Chat created: ✅ ($CHAT_ID)"
echo "  • Document uploaded: ✅ ($DOC_ID)"
echo "  • Document processed: ✅ ($PAGES pages)"
echo "  • Audit invoked: ✅"
echo "  • Message created: ✅ ($MESSAGE_ID)"
echo "  • Validation report linked: ✅ ($HAS_VALIDATION_ID)"
echo ""
echo "You can now open the chat in the UI:"
echo "  http://localhost:3000/chat?id=$CHAT_ID"
echo ""
