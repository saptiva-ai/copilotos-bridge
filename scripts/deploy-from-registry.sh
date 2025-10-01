#!/bin/bash
# 🚀 Production Deploy from Docker Registry
# Usage: ./scripts/deploy-from-registry.sh [VERSION]
#
# Environment variables:
#   REGISTRY_URL     - Docker registry URL (default: ghcr.io/jazielflo/copilotos-bridge)
#   SKIP_HEALTH      - Skip health check (default: false)

set -e

# Configuration
REGISTRY_URL="${REGISTRY_URL:-ghcr.io/jazielflo/copilotos-bridge}"
VERSION="${1:-latest}"
SKIP_HEALTH="${SKIP_HEALTH:-false}"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  🚀 Copilotos Bridge - Production Deploy from Registry       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 Registry: $REGISTRY_URL"
echo "🏷️  Version: $VERSION"
echo ""

# Step 1: Pull images
echo "📥 [1/5] Pulling images from registry..."
docker pull "$REGISTRY_URL/api:$VERSION"
docker pull "$REGISTRY_URL/web:$VERSION"
echo "✅ Images pulled successfully"
echo ""

# Step 2: Tag for local use
echo "🏷️  [2/5] Tagging images for local deployment..."
docker tag "$REGISTRY_URL/api:$VERSION" copilotos-api:latest
docker tag "$REGISTRY_URL/web:$VERSION" copilotos-web:latest
echo "✅ Images tagged"
echo ""

# Step 3: Check current directory
if [ ! -d "infra" ]; then
    echo "❌ Error: 'infra' directory not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Step 4: Stop current services
echo "🛑 [3/5] Stopping current services..."
cd infra
docker compose -f docker-compose.yml down
echo "✅ Services stopped"
echo ""

# Step 5: Start new services
echo "🚀 [4/5] Starting services with new images..."
docker compose -f docker-compose.yml up -d
echo "✅ Services started"
echo ""

# Step 6: Health check
echo "🏥 [5/5] Running health checks..."
sleep 10

if [ "$SKIP_HEALTH" != "true" ]; then
    echo "   Checking API health..."
    HEALTH_RESPONSE=$(curl -sS http://localhost:8001/api/health || echo "FAILED")

    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo "   ✅ API is healthy"
        echo ""
        echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        echo "   ⚠️  API health check failed - container may still be starting"
        echo "   Run manually: curl http://localhost:8001/api/health | jq '.'"
    fi
else
    echo "   ⏭️  Health check skipped"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Deployment Complete!                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep copilotos || docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "🔍 Quick Commands:"
echo "   View logs:    docker logs -f copilotos-api"
echo "   Health check: curl http://localhost:8001/api/health | jq '.'"
echo "   Stop:         cd infra && docker compose down"
echo "   Rollback:     ./scripts/deploy-from-registry.sh <previous-version>"
echo ""
