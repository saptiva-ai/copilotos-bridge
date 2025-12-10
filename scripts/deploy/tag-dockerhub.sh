#!/bin/bash
set -e

# ============================================================================
# DOCKER HUB TAGGING SCRIPT
# ============================================================================
# Tags Docker images for Docker Hub
# Usage: ./scripts/tag-dockerhub.sh
# ============================================================================

VERSION="0.2.2"
DATETIME=$(date +%Y%m%d-%H%M)
DOCKERHUB_USER="${DOCKER_REGISTRY_USER:-your_registry_user}"
PROJECT="octavios-invex"

SERVICES=("backend" "web" "file-manager" "bank-advisor")

echo "🏷️  Re-tagging images for Docker Hub ($DOCKERHUB_USER)"
echo ""

for service in "${SERVICES[@]}"; do
    LOCAL_IMAGE="octavios-chat-bajaware_invex-${service}:latest"

    echo "📦 Tagging $service..."

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

echo "✅ All images tagged for Docker Hub"
echo ""
echo "🔗 Tagged images:"
docker images | grep "${DOCKERHUB_USER}/${PROJECT}" | head -20
