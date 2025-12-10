#!/usr/bin/env bash
set -euo pipefail

# Smoke test to ensure chat keeps context between turns.
# Usage:
#   BASE_URL=http://localhost:8000 USER_ID=<uuid> ./tests/test_conversation_context.sh

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL=${BASE_URL:-http://localhost:8000}
USER_ID=${USER_ID:-bf481dbe-2c23-4e68-ba85-c5a8a2f84ef3}
MODEL=${MODEL:-SAPTIVA_TURBO}
TIMEOUT=${TIMEOUT:-15}

trap 'echo -e "${RED}✗ Error on line ${LINENO}${NC}"' ERR

require_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    echo -e "${RED}✗ Missing dependency: $1${NC}"
    exit 1
  }
}

require_bin curl
require_bin jq

echo -e "${BLUE}=== Testing Conversation Context (BASE_URL=${BASE_URL}) ===${NC}\n"

post_json() {
  local url="$1"
  local payload="$2"
  curl -sS --fail-with-body --max-time "${TIMEOUT}" \
    -H "Content-Type: application/json" \
    -X POST "${url}" \
    -d "${payload}"
}

create_conversation() {
  echo -e "${GREEN}1) Creating new conversation...${NC}"
  local response
  response=$(post_json "${BASE_URL}/api/conversations" "{\"user_id\": \"${USER_ID}\"}")
  local conv_id
  conv_id=$(echo "${response}" | jq -r '.id // empty')
  if [ -z "${conv_id}" ] || [ "${conv_id}" = "null" ]; then
    echo -e "${RED}✗ Conversation ID missing in response${NC}"
    echo "${response}"
    exit 1
  fi
  echo -e "Conversation ID: ${conv_id}\n"
  echo "${conv_id}"
}

send_message() {
  local message="$1"
  local conversation_id="$2"
  echo -e "${GREEN}${3}${NC}"
  post_json "${BASE_URL}/api/chat/message" "{
    \"message\": \"${message}\",
    \"conversation_id\": \"${conversation_id}\",
    \"user_id\": \"${USER_ID}\",
    \"model\": \"${MODEL}\",
    \"stream\": false
  }"
}

CONV_ID=$(create_conversation)

MSG1_RESPONSE=$(send_message "¿cuál es el PDM de INVEX?" "${CONV_ID}" "2) Sending first message about PDM...")
MSG1_CONTENT=$(echo "${MSG1_RESPONSE}" | jq -r '.content // empty')
echo "First response preview:"
echo "${MSG1_CONTENT}" | head -c 200
echo -e "\n"

sleep 2

MSG2_RESPONSE=$(send_message "¿cuánto es?" "${CONV_ID}" "3) Sending follow-up question (same conversation)...")
MSG2_CONTENT=$(echo "${MSG2_RESPONSE}" | jq -r '.content // empty')

echo "Second response:"
echo "${MSG2_CONTENT}"
echo ""

echo -e "${BLUE}=== Checking if context was maintained ===${NC}"
if echo "${MSG2_CONTENT}" | grep -Eqi "PDM|INVEX"; then
  echo -e "${GREEN}✓ SUCCESS: Context maintained (response mentions PDM or INVEX)${NC}"
else
  echo -e "${RED}✗ FAILURE: Context lost (no PDM/INVEX reference)${NC}"
  exit 1
fi
