#!/bin/bash
# 📤 Push Images to Docker Registry
# Usage: ./scripts/push-to-registry.sh [--no-build] [--version VERSION]
#
# Environment variables:
#   REGISTRY_URL     - Docker registry URL (default: ghcr.io/jazielflo/copilotos-bridge)
#   GITHUB_TOKEN     - GitHub token for authentication

set -e

# Parse arguments
NO_BUILD=false
VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--no-build] [--version VERSION]"
            exit 1
            ;;
    esac
done

# Configuration
REGISTRY_URL="${REGISTRY_URL:-ghcr.io/jazielflo/copilotos-bridge}"
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# Determine version
if [ -z "$VERSION" ]; then
    VERSION="$GIT_COMMIT"
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  📤 Copilotos Bridge - Push to Docker Registry               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 Registry:  $REGISTRY_URL"
echo "🏷️  Version:  $VERSION"
echo "🔖 Commit:   $GIT_COMMIT"
echo "🌿 Branch:   $GIT_BRANCH"
echo ""

# Check if in correct directory
if [ ! -d "infra" ]; then
    echo "❌ Error: 'infra' directory not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Step 1: Build images (optional)
if [ "$NO_BUILD" = false ]; then
    echo "🔨 [1/4] Building images..."
    cd infra
    docker compose -f docker-compose.yml build --no-cache
    cd ..
    echo "✅ Build complete"
    echo ""
else
    echo "⏭️  [1/4] Skipping build (--no-build flag)"
    echo ""
fi

# Step 2: Tag images
echo "🏷️  [2/4] Tagging images..."

# Tag with version
docker tag copilotos-api:latest "$REGISTRY_URL/api:$VERSION"
docker tag copilotos-web:latest "$REGISTRY_URL/web:$VERSION"
echo "   ✅ Tagged with version: $VERSION"

# Tag with latest (if on main branch)
if [ "$GIT_BRANCH" = "main" ]; then
    docker tag copilotos-api:latest "$REGISTRY_URL/api:latest"
    docker tag copilotos-web:latest "$REGISTRY_URL/web:latest"
    echo "   ✅ Tagged with: latest"
fi

echo ""

# Step 3: Login to registry
echo "🔐 [3/4] Logging in to registry..."
if [ -n "$GITHUB_TOKEN" ]; then
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u jazielflo --password-stdin
    echo "✅ Login successful"
else
    echo "⚠️  GITHUB_TOKEN not set, attempting login without it..."
    # Will use docker credentials helper or fail
fi
echo ""

# Step 4: Push images
echo "📤 [4/4] Pushing images to registry..."

# Push version-tagged images
echo "   Pushing API:$VERSION..."
docker push "$REGISTRY_URL/api:$VERSION"
echo "   ✅ API pushed"

echo "   Pushing Web:$VERSION..."
docker push "$REGISTRY_URL/web:$VERSION"
echo "   ✅ Web pushed"

# Push latest tags (if on main)
if [ "$GIT_BRANCH" = "main" ]; then
    echo "   Pushing API:latest..."
    docker push "$REGISTRY_URL/api:latest"

    echo "   Pushing Web:latest..."
    docker push "$REGISTRY_URL/web:latest"
    echo "   ✅ Latest tags pushed"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Push Complete!                                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 Published Images:"
echo "   $REGISTRY_URL/api:$VERSION"
echo "   $REGISTRY_URL/web:$VERSION"
if [ "$GIT_BRANCH" = "main" ]; then
    echo "   $REGISTRY_URL/api:latest"
    echo "   $REGISTRY_URL/web:latest"
fi
echo ""
echo "🚀 Deploy to production:"
echo "   ssh jf@34.42.214.246"
echo "   cd /home/jf/copilotos-bridge"
echo "   ./scripts/deploy-from-registry.sh $VERSION"
echo ""
echo "📋 View in registry:"
echo "   https://github.com/jazielflo/copilotos-bridge/pkgs/container/copilotos-bridge%2Fapi"
echo "   https://github.com/jazielflo/copilotos-bridge/pkgs/container/copilotos-bridge%2Fweb"
echo ""
