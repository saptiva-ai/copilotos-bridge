#!/bin/bash
# ============================================================================
# SERVICE-SPECIFIC TAG AND PUSH SCRIPT
# ============================================================================
# Tags and pushes specific services to Docker Hub
# Usage: ./scripts/deploy/tag-push-service.sh <services> <version>
#
# Examples:
#   ./scripts/deploy/tag-push-service.sh "backend" 0.2.2
#   ./scripts/deploy/tag-push-service.sh "backend web" 0.2.2
#   ./scripts/deploy/tag-push-service.sh "all" 0.2.2
# ============================================================================

set -e

SERVICES="${1:-}"
VERSION="${2:-}"
DATETIME=$(date +%Y%m%d-%H%M)
DOCKERHUB_USER="jazielflores1998"
PROJECT="octavios-invex"

# Valid services
VALID_SERVICES=("backend" "web" "file-manager" "bank-advisor" "all")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# === VALIDACIÓN ===
if [ -z "$SERVICES" ] || [ -z "$VERSION" ]; then
    echo -e "${RED}❌ Services and version required${NC}"
    echo ""
    echo "Usage: $0 <services> <VERSION>"
    echo ""
    echo "Examples:"
    echo "  $0 'backend' 0.2.2"
    echo "  $0 'backend web' 0.2.2"
    echo "  $0 'all' 0.2.2"
    echo ""
    echo "Available services: ${VALID_SERVICES[*]}"
    exit 1
fi

# Parse services
if [ "$SERVICES" = "all" ]; then
    TAG_SERVICES=("backend" "web" "file-manager" "bank-advisor")
else
    read -ra TAG_SERVICES <<< "$SERVICES"
fi

# Validate services
for service in "${TAG_SERVICES[@]}"; do
    if [[ ! " ${VALID_SERVICES[@]} " =~ " ${service} " ]]; then
        echo -e "${RED}❌ Invalid service: $service${NC}"
        echo "Valid services: ${VALID_SERVICES[*]}"
        exit 1
    fi
done

echo "🏷️  Tagging and pushing services to Docker Hub ($DOCKERHUB_USER)"
echo ""
echo "Services: ${TAG_SERVICES[*]}"
echo "Version: $VERSION"
echo "Datetime: $DATETIME"
echo ""

for service in "${TAG_SERVICES[@]}"; do
    LOCAL_IMAGE="octavios-chat-bajaware_invex-${service}:latest"

    echo "📦 Processing $service..."

    # Tag with version
    docker tag "$LOCAL_IMAGE" "${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}"
    echo "   ✅ ${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}"

    # Tag with version + datetime
    docker tag "$LOCAL_IMAGE" "${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}-${DATETIME}"
    echo "   ✅ ${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}-${DATETIME}"

    # Tag with latest
    docker tag "$LOCAL_IMAGE" "${DOCKERHUB_USER}/${PROJECT}-${service}:latest"
    echo "   ✅ ${DOCKERHUB_USER}/${PROJECT}-${service}:latest"

    echo ""
done

echo "✅ All services tagged"
echo ""

# === PUSH ===
read -p "Push to Docker Hub? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  Push cancelled"
    exit 0
fi

echo ""
echo "📤 Pushing images to Docker Hub..."
echo ""

for service in "${TAG_SERVICES[@]}"; do
    echo "📤 Pushing $service..."

    docker push "${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}"
    docker push "${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}-${DATETIME}"
    docker push "${DOCKERHUB_USER}/${PROJECT}-${service}:latest"

    echo "   ✅ $service pushed"
    echo ""
done

echo "✅ All services pushed to Docker Hub"
echo ""
echo "🔗 Tagged and pushed images:"
docker images | grep "${DOCKERHUB_USER}/${PROJECT}" | grep -E "$(IFS='|'; echo "${TAG_SERVICES[*]}")" | head -20
