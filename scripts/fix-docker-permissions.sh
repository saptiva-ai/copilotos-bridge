#!/bin/bash
# ============================================================================
# Docker Permissions Fix Script
# ============================================================================
# Fixes permission issues with Next.js builds in Docker by:
# 1. Cleaning up any root-owned files
# 2. Setting proper UID/GID for Docker builds
# 3. Rebuilding with correct permissions

set -e

echo "🔧 Docker Permissions Fix - Copilotos Bridge"
echo "============================================="

# Emojis for logs
RED='🔴'
GREEN='🟢'
YELLOW='🟡'
BLUE='🔵'
NC='' # No Color

# Get current user UID and GID
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

echo -e "${BLUE}Current User ID:${NC} $CURRENT_UID"
echo -e "${BLUE}Current Group ID:${NC} $CURRENT_GID"
echo

# Step 1: Clean up any existing root-owned files
echo -e "${YELLOW}1. Cleaning up root-owned build artifacts...${NC}"

# Check if .next directory exists and if it has root permissions
if [ -d "apps/web/.next" ]; then
    NEXT_OWNER=$(stat -c '%U' apps/web/.next 2>/dev/null || echo "unknown")
    if [ "$NEXT_OWNER" = "root" ]; then
        echo -e "   ${RED}Found root-owned .next directory${NC}"
        echo -e "   Removing with sudo..."
        sudo rm -rf apps/web/.next
        echo -e "   ${GREEN}✅ Cleaned up apps/web/.next${NC}"
    else
        echo -e "   ${GREEN}✅ .next directory has correct permissions${NC}"
        rm -rf apps/web/.next
    fi
else
    echo -e "   ${GREEN}✅ No .next directory found${NC}"
fi

# Clean up any other potential root-owned build artifacts
echo "   Cleaning other build artifacts..."
rm -rf apps/web/dist apps/web/out apps/web/.turbo 2>/dev/null || true
rm -rf node_modules/.cache 2>/dev/null || true

echo -e "${GREEN}✅ Build artifacts cleaned${NC}"
echo

# Step 2: Set environment variables for Docker build
echo -e "${YELLOW}2. Setting up environment variables...${NC}"

export UID=$CURRENT_UID
export GID=$CURRENT_GID

echo "   UID=$UID"
echo "   GID=$GID"
echo -e "${GREEN}✅ Environment variables set${NC}"
echo

# Step 3: Build with proper permissions
echo -e "${YELLOW}3. Building Docker images with correct permissions...${NC}"

echo "   Building web service..."
cd infra

# Stop any running containers first
echo "   Stopping existing containers..."
docker-compose down web 2>/dev/null || true

# Remove old images to force rebuild
echo "   Removing old images..."
docker rmi copilotos-web 2>/dev/null || true
docker rmi infra-web 2>/dev/null || true

# Build with no cache to ensure clean build
echo "   Building new image..."
UID=$CURRENT_UID GID=$CURRENT_GID docker-compose build --no-cache web

echo -e "${GREEN}✅ Docker build completed${NC}"
echo

# Step 4: Verification
echo -e "${YELLOW}4. Verifying permissions...${NC}"

# Start the service temporarily to test
echo "   Starting web service for verification..."
UID=$CURRENT_UID GID=$CURRENT_GID docker-compose up -d web

# Wait a moment for container to start
sleep 3

# Check if container is running
if docker-compose ps web | grep -q "Up"; then
    echo -e "   ${GREEN}✅ Web container started successfully${NC}"

    # Check permissions inside container
    echo "   Checking file permissions inside container..."
    CONTAINER_USER=$(docker-compose exec -T web id -u)
    CONTAINER_GROUP=$(docker-compose exec -T web id -g)

    echo "   Container UID: $CONTAINER_USER"
    echo "   Container GID: $CONTAINER_GROUP"

    if [ "$CONTAINER_USER" = "$CURRENT_UID" ] && [ "$CONTAINER_GROUP" = "$CURRENT_GID" ]; then
        echo -e "   ${GREEN}✅ Container running with correct user permissions${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Container user/group doesn't match host${NC}"
    fi
else
    echo -e "   ${RED}❌ Web container failed to start${NC}"
fi

# Stop the test container
docker-compose down web 2>/dev/null || true

cd ..

echo
echo "============================================="
echo -e "${GREEN}🎉 Permission fix process completed!${NC}"
echo
echo -e "${BLUE}📋 Summary:${NC}"
echo "   ✅ Root-owned files cleaned"
echo "   ✅ Environment variables configured"
echo "   ✅ Docker images rebuilt with correct permissions"
echo "   ✅ Verification completed"
echo
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "   1. To start the development environment:"
echo "      cd infra && UID=$CURRENT_UID GID=$CURRENT_GID docker-compose up"
echo
echo "   2. To start only the web service:"
echo "      cd infra && UID=$CURRENT_UID GID=$CURRENT_GID docker-compose up web"
echo
echo "   3. To add UID/GID to your shell profile (optional):"
echo "      echo 'export UID=\$(id -u)' >> ~/.bashrc"
echo "      echo 'export GID=\$(id -g)' >> ~/.bashrc"
echo
echo -e "${YELLOW}💡 Note:${NC} Any new builds will respect your user permissions"
echo "   and create files owned by your user instead of root."
echo

# Create a convenience script for future builds
cat > scripts/docker-build.sh << 'EOF'
#!/bin/bash
# Convenience script for building with correct permissions
export UID=$(id -u)
export GID=$(id -g)
cd infra
docker-compose build "$@"
EOF

chmod +x scripts/docker-build.sh

echo -e "${GREEN}📝 Created convenience script: scripts/docker-build.sh${NC}"
echo "   Use this script for future Docker builds with correct permissions"
echo