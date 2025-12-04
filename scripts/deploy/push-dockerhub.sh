#!/bin/bash
set -e

# ============================================================================
# DOCKER HUB PUSH SCRIPT
# ============================================================================
# Pushes all tagged images to Docker Hub
# Usage: ./scripts/push-dockerhub.sh
# ============================================================================

VERSION="0.1.2"
DATETIME="20251202-1519"
DOCKERHUB_USER="jazielflores1998"
PROJECT="octavios-invex"

SERVICES=("backend" "web" "file-manager" "bank-advisor")

echo "📤 Pushing images to Docker Hub ($DOCKERHUB_USER)"
echo ""
echo "⚠️  Nota: backend es 15GB, esto puede tardar varios minutos"
echo ""

for service in "${SERVICES[@]}"; do
    echo "🚀 Pushing $service..."

    # Push version tag
    echo "   → Pushing ${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}..."
    docker push "${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}"

    # Push version+datetime tag
    echo "   → Pushing ${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}-${DATETIME}..."
    docker push "${DOCKERHUB_USER}/${PROJECT}-${service}:${VERSION}-${DATETIME}"

    # Push latest tag
    echo "   → Pushing ${DOCKERHUB_USER}/${PROJECT}-${service}:latest..."
    docker push "${DOCKERHUB_USER}/${PROJECT}-${service}:latest"

    echo "   ✅ $service pushed successfully"
    echo ""
done

echo "✅ All images pushed to Docker Hub"
echo ""
echo "🔗 Images disponibles en:"
for service in "${SERVICES[@]}"; do
    echo "   - https://hub.docker.com/r/${DOCKERHUB_USER}/${PROJECT}-${service}"
done
