#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8001}"
TEST_USER_EMAIL="test-mvp-$(date +%s)@example.com"
TEST_USER_PASSWORD="TestPass123!"
TEST_USER_USERNAME="mvp-tester-$(date +%s)"

# Results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Test functions
test_health() {
    log_test "Health check"
    if curl -sf "${API_URL}/api/health" > /dev/null; then
        log_success "API is healthy"
    else
        log_error "API health check failed"
        return 1
    fi
}

test_register_user() {
    log_test "User registration"

    REGISTER_RESPONSE=$(curl -sf -X POST "${API_URL}/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"${TEST_USER_EMAIL}\",
            \"username\": \"${TEST_USER_USERNAME}\",
            \"password\": \"${TEST_USER_PASSWORD}\"
        }" || echo "FAILED")

    if [[ "$REGISTER_RESPONSE" == "FAILED" ]]; then
        log_error "Failed to register user"
        return 1
    fi

    ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')

    if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
        log_error "No access token received"
        return 1
    fi

    export ACCESS_TOKEN
    log_success "User registered successfully"
}

test_upload_pdf() {
    log_test "PDF upload"

    # Create a simple test PDF
    TEST_PDF="/tmp/test-mvp-$(date +%s).pdf"
    cat > "$TEST_PDF" << 'EOFPDF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 65 >>
stream
BT
/F1 24 Tf
100 700 Td
(Test Document for MVP Validation) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000229 00000 n
0000000329 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
444
%%EOF
EOFPDF

    UPLOAD_RESPONSE=$(curl -sf -X POST "${API_URL}/api/files/upload" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -F "files=@${TEST_PDF}" || echo "FAILED")

    if [[ "$UPLOAD_RESPONSE" == "FAILED" ]]; then
        log_error "Failed to upload PDF"
        rm -f "$TEST_PDF"
        return 1
    fi

    FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.files[0].file_id')
    FILE_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.files[0].status')

    if [[ -z "$FILE_ID" || "$FILE_ID" == "null" ]]; then
        log_error "No file_id received"
        rm -f "$TEST_PDF"
        return 1
    fi

    if [[ "$FILE_STATUS" != "READY" ]]; then
        log_error "File status is not READY: $FILE_STATUS"
        rm -f "$TEST_PDF"
        return 1
    fi

    export FILE_ID
    export TEST_PDF
    log_success "PDF uploaded successfully (file_id: ${FILE_ID:0:8}...)"
}

test_chat_with_document() {
    log_test "Chat with document (MVP flow)"

    CHAT_RESPONSE=$(curl -sf -X POST "${API_URL}/api/chat" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"message\": \"Revísalo y dame 3 puntos clave del documento\",
            \"file_ids\": [\"${FILE_ID}\"],
            \"model\": \"Saptiva Turbo\"
        }" || echo "FAILED")

    if [[ "$CHAT_RESPONSE" == "FAILED" ]]; then
        log_error "Failed to send chat message"
        return 1
    fi

    RESPONSE_CONTENT=$(echo "$CHAT_RESPONSE" | jq -r '.response')
    RESPONSE_MODEL=$(echo "$CHAT_RESPONSE" | jq -r '.model')

    if [[ -z "$RESPONSE_CONTENT" || "$RESPONSE_CONTENT" == "null" ]]; then
        log_error "No content in response"
        return 1
    fi

    # Check if model defaults to Saptiva Turbo
    if [[ "$RESPONSE_MODEL" == *"Turbo"* ]]; then
        log_success "Chat completed with Saptiva Turbo"
    else
        log_error "Model is not Saptiva Turbo: $RESPONSE_MODEL"
        return 1
    fi

    # Check response length
    RESPONSE_LENGTH=${#RESPONSE_CONTENT}
    if [[ $RESPONSE_LENGTH -gt 50 ]]; then
        log_success "Response is coherent (length: $RESPONSE_LENGTH chars)"
    else
        log_error "Response too short: $RESPONSE_LENGTH chars"
        return 1
    fi
}

test_chat_without_model() {
    log_test "Chat defaults to Saptiva Turbo when model not specified"

    CHAT_RESPONSE=$(curl -sf -X POST "${API_URL}/api/chat" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"message\": \"¿Qué es un MVP?\"
        }" || echo "FAILED")

    if [[ "$CHAT_RESPONSE" == "FAILED" ]]; then
        log_error "Failed to send chat message"
        return 1
    fi

    RESPONSE_MODEL=$(echo "$CHAT_RESPONSE" | jq -r '.model')

    if [[ "$RESPONSE_MODEL" == *"Turbo"* ]]; then
        log_success "Model defaulted to Saptiva Turbo correctly"
    else
        log_error "Model did not default to Saptiva Turbo: $RESPONSE_MODEL"
        return 1
    fi
}

test_expired_document() {
    log_test "Graceful handling of expired documents"

    # Get Redis container name
    REDIS_CONTAINER=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -1)

    if [[ -z "$REDIS_CONTAINER" ]]; then
        log_error "Redis container not found"
        return 1
    fi

    # Delete the document from Redis cache
    docker exec "$REDIS_CONTAINER" redis-cli DEL "doc:text:${FILE_ID}" > /dev/null

    log_info "Deleted doc:text:${FILE_ID} from Redis cache"

    # Try to use the expired document
    CHAT_RESPONSE=$(curl -sf -X POST "${API_URL}/api/chat" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"message\": \"Resume este documento\",
            \"file_ids\": [\"${FILE_ID}\"]
        }" || echo "FAILED")

    if [[ "$CHAT_RESPONSE" == "FAILED" ]]; then
        log_error "Request failed (should degrade gracefully)"
        return 1
    fi

    # Check that we got a response (not a 500)
    RESPONSE_CONTENT=$(echo "$CHAT_RESPONSE" | jq -r '.response')

    if [[ -n "$RESPONSE_CONTENT" && "$RESPONSE_CONTENT" != "null" ]]; then
        log_success "Flow continued gracefully despite expired document"
    else
        log_error "No response content received"
        return 1
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test files..."
    rm -f "$TEST_PDF" 2>/dev/null || true
}

# Main execution
main() {
    log_section "MVP Validation Script"
    log_info "API URL: $API_URL"

    # Phase 1: SMOKE tests
    log_section "PHASE 1: SMOKE TESTS"
    test_health || true
    test_register_user || exit 1  # Must succeed
    test_upload_pdf || exit 1     # Must succeed
    test_chat_with_document || true
    test_chat_without_model || true

    # Phase 2: EDGE cases
    log_section "PHASE 2: EDGE CASES"
    test_expired_document || true

    # Results
    log_section "VALIDATION RESULTS"
    echo -e "Total tests: ${TESTS_TOTAL}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Trap to ensure cleanup
trap cleanup EXIT

# Run main
main "$@"
