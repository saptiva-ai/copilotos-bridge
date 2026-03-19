#!/bin/bash
# Reset/Create demo user for E2E tests
API_URL="http://localhost:8000"
USERNAME="demo"
PASSWORD="${E2E_USER_PASSWORD:-Demo1234}"
EMAIL="demo@saptiva.ai"

echo "Creating user $USERNAME at $API_URL..."

# Register user
curl -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}"

# Test login
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

if [ "$STATUS" == "200" ]; then
  echo "SUCCESS: User $USERNAME is ready."
else
  echo "FAILURE: Could not login with $USERNAME (HTTP $STATUS)."
fi
