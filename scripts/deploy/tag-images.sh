#!/bin/bash
set -e

# ============================================================================
# IMAGE TAGGING SCRIPT
# ============================================================================
# Tags Docker images with version, date, and latest
# Usage: ./scripts/tag-images.sh
# ============================================================================

VERSION="0.1.2"
DATETIME=$(date +%Y%m%d-%H%M)
REGISTRY="ghcr.io/saptiva-ai"
PROJECT="octavios-chat-bajaware_invex"

SERVICES=("backend" "web" "file-manager" "bank-advisor")

echo "🏷️  Tagging images with version $VERSION and datetime $DATETIME"
echo ""

for service in "${SERVICES[@]}"; do
    LOCAL_IMAGE="${PROJECT}-${service}:latest"

    echo "📦 Tagging $service..."

    # Tag with version
    docker tag "$LOCAL_IMAGE" "${REGISTRY}/${PROJECT}-${service}:${VERSION}"
    echo "   ✅ ${REGISTRY}/${PROJECT}-${service}:${VERSION}"

    # Tag with version + datetime
    docker tag "$LOCAL_IMAGE" "${REGISTRY}/${PROJECT}-${service}:${VERSION}-${DATETIME}"
    echo "   ✅ ${REGISTRY}/${PROJECT}-${service}:${VERSION}-${DATETIME}"

    # Tag with latest
    docker tag "$LOCAL_IMAGE" "${REGISTRY}/${PROJECT}-${service}:latest"
    echo "   ✅ ${REGISTRY}/${PROJECT}-${service}:latest"

    echo ""
done

echo "✅ All images tagged successfully"
echo ""
echo "🔗 Tagged images:"
docker images | grep "${REGISTRY}/${PROJECT}" | head -20
