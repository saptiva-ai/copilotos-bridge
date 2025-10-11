#!/bin/bash
# ▸ Push Images to Docker Registry
# Usage: ./scripts/push-to-registry.sh [--no-build] [--version VERSION]
#
# Environment variables:
#   REGISTRY_URL     - Docker registry URL (e.g., ghcr.io/username/repo)
#   REGISTRY_USER    - Docker registry username (for authentication)
#   GITHUB_TOKEN     - GitHub token for authentication

set -e

# Load environment for server info
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$PROJECT_ROOT/envs/.env.prod" ]; then
    source "$PROJECT_ROOT/envs/.env.prod"
fi

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
REGISTRY_URL="${REGISTRY_URL:-}"
REGISTRY_USER="${REGISTRY_USER:-}"
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# Validate configuration
if [ -z "$REGISTRY_URL" ]; then
    echo "✖ Error: REGISTRY_URL not set"
    echo ""
    echo "Please configure in envs/.env.prod:"
    echo "  REGISTRY_URL=ghcr.io/username/repo"
    echo "  REGISTRY_USER=username"
    echo ""
    exit 1
fi

if [ -z "$REGISTRY_USER" ]; then
    echo "✖ Error: REGISTRY_USER not set"
    echo ""
    echo "Please configure in envs/.env.prod:"
    echo "  REGISTRY_USER=your-github-username"
    echo ""
    exit 1
fi

# Determine version
if [ -z "$VERSION" ]; then
    VERSION="$GIT_COMMIT"
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ▸ Copilotos Bridge - Push to Docker Registry               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "▸ Registry:  $REGISTRY_URL"
echo "▸  Version:  $VERSION"
echo "▸ Commit:   $GIT_COMMIT"
echo "◆ Branch:   $GIT_BRANCH"
echo ""

# Check if in correct directory
if [ ! -d "infra" ]; then
    echo "✖ Error: 'infra' directory not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Step 1: Build images (optional)
if [ "$NO_BUILD" = false ]; then
    echo "▸ [1/4] Building images..."
    cd infra
    docker compose -f docker-compose.yml build --no-cache
    cd ..
    echo "✔ Build complete"
    echo ""
else
    echo "▸  [1/4] Skipping build (--no-build flag)"
    echo ""
fi

# Step 2: Tag images
echo "▸  [2/4] Tagging images..."

# Tag with version
docker tag copilotos-api:latest "$REGISTRY_URL/api:$VERSION"
docker tag copilotos-web:latest "$REGISTRY_URL/web:$VERSION"
echo "   ✔ Tagged with version: $VERSION"

# Tag with latest (if on main branch)
if [ "$GIT_BRANCH" = "main" ]; then
    docker tag copilotos-api:latest "$REGISTRY_URL/api:latest"
    docker tag copilotos-web:latest "$REGISTRY_URL/web:latest"
    echo "   ✔ Tagged with: latest"
fi

echo ""

# Step 3: Login to registry
echo "⛨ [3/4] Logging in to registry..."
REGISTRY_HOST=$(echo "$REGISTRY_URL" | cut -d'/' -f1)
if [ -n "$GITHUB_TOKEN" ]; then
    echo "$GITHUB_TOKEN" | docker login "$REGISTRY_HOST" -u "$REGISTRY_USER" --password-stdin
    echo "✔ Login successful"
else
    echo "▲  GITHUB_TOKEN not set, attempting login without it..."
    # Will use docker credentials helper or fail
fi
echo ""

# Step 4: Push images
echo "▸ [4/4] Pushing images to registry..."

# Push version-tagged images
echo "   Pushing API:$VERSION..."
docker push "$REGISTRY_URL/api:$VERSION"
echo "   ✔ API pushed"

echo "   Pushing Web:$VERSION..."
docker push "$REGISTRY_URL/web:$VERSION"
echo "   ✔ Web pushed"

# Push latest tags (if on main)
if [ "$GIT_BRANCH" = "main" ]; then
    echo "   Pushing API:latest..."
    docker push "$REGISTRY_URL/api:latest"

    echo "   Pushing Web:latest..."
    docker push "$REGISTRY_URL/web:latest"
    echo "   ✔ Latest tags pushed"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✔ Push Complete!                                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "▸ Published Images:"
echo "   $REGISTRY_URL/api:$VERSION"
echo "   $REGISTRY_URL/web:$VERSION"
if [ "$GIT_BRANCH" = "main" ]; then
    echo "   $REGISTRY_URL/api:latest"
    echo "   $REGISTRY_URL/web:latest"
fi
echo ""
echo "▸ Deploy to production:"
if [ -n "$PROD_SERVER_HOST" ]; then
    echo "   make deploy-registry"
    echo ""
    echo "▸  Or manually:"
    echo "   ssh ${PROD_SERVER_HOST}"
    echo "   cd ${PROD_DEPLOY_PATH:-/opt/copilotos-bridge}"
    echo "   ./scripts/deploy.sh registry --skip-build"
else
    echo "   Configure PROD_SERVER_HOST in envs/.env.prod first"
    echo "   Then run: make deploy-registry"
fi
echo ""
echo "▸ View in registry:"
if [[ "$REGISTRY_URL" == ghcr.io/* ]]; then
    # Extract username/repo from ghcr.io/username/repo format
    REPO_PATH=$(echo "$REGISTRY_URL" | cut -d'/' -f2-)
    echo "   https://github.com/${REPO_PATH}/pkgs/container/${REPO_PATH//\//%2F}%2Fapi"
    echo "   https://github.com/${REPO_PATH}/pkgs/container/${REPO_PATH//\//%2F}%2Fweb"
else
    echo "   Check your registry dashboard: $REGISTRY_URL"
fi
echo ""
