#!/bin/bash
# ========================================
# DEMO SERVER SETUP SCRIPT
# ========================================
# Prepares Capital 414 demo server (34.172.67.93) for deployment
#
# This script:
# ✅ Installs Docker and Docker Compose
# ✅ Configures user permissions
# ✅ Installs system dependencies (git, curl, jq)
# ✅ Clones the project repository
# ✅ Configures environment variables
#
# Usage:
#   ./scripts/setup-demo-server.sh
#
# Server: 34.172.67.93 (cuatro-catorce)
# User: jf
# OS: Ubuntu 24.04 LTS
#
set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEMO_SERVER="jf@34.172.67.93"
DEMO_PATH="/home/jf/capital414-chat"
REPO_URL="https://github.com/saptiva-ai/capital414-chat.git"  # Adjust this URL

# ========================================
# LOGGING FUNCTIONS
# ========================================
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✔${NC} $1"; }
log_warning() { echo -e "${YELLOW}▲${NC} $1"; }
log_error() { echo -e "${RED}✖${NC} $1"; }

step() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ========================================
# MAIN SETUP SCRIPT
# ========================================
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  CAPITAL 414 DEMO SERVER SETUP                                ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Verify SSH connection
    log_info "Testing SSH connection to $DEMO_SERVER..."
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$DEMO_SERVER" "echo 2>&1" > /dev/null 2>&1; then
        log_error "Cannot connect to $DEMO_SERVER"
        echo "Check SSH keys and network connectivity"
        exit 1
    fi
    log_success "SSH connection OK"

    # Step 1: Install Docker
    step "Step 1/6: Install Docker"
    log_info "Checking if Docker is already installed..."

    ssh "$DEMO_SERVER" 'bash -s' << 'ENDSSH'
        set -e

        if command -v docker &> /dev/null; then
            echo "Docker is already installed: $(docker --version)"
            exit 0
        fi

        echo "Installing Docker..."

        # Update package index
        sudo apt-get update -qq

        # Install prerequisites
        sudo apt-get install -y -qq \
            ca-certificates \
            curl \
            gnupg \
            lsb-release

        # Add Docker's official GPG key
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
            sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg

        # Set up the repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker Engine
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        # Add current user to docker group
        sudo usermod -aG docker $USER

        echo "Docker installed successfully!"
        docker --version
ENDSSH

    log_success "Docker installation complete"

    # Step 2: Install system dependencies
    step "Step 2/6: Install System Dependencies"

    ssh "$DEMO_SERVER" 'bash -s' << 'ENDSSH'
        set -e
        echo "Installing git, curl, jq..."
        sudo apt-get install -y -qq git curl jq make
        echo "Dependencies installed:"
        git --version
        jq --version
ENDSSH

    log_success "System dependencies installed"

    # Step 3: Verify Docker Compose
    step "Step 3/6: Verify Docker Compose"

    ssh "$DEMO_SERVER" 'bash -s' << 'ENDSSH'
        set -e
        if docker compose version &> /dev/null; then
            echo "Docker Compose is available:"
            docker compose version
        else
            echo "ERROR: Docker Compose plugin not found"
            exit 1
        fi
ENDSSH

    log_success "Docker Compose verified"

    # Step 4: Clone repository
    step "Step 4/6: Clone Project Repository"

    log_info "Checking if project directory exists..."
    if ssh "$DEMO_SERVER" "[ -d $DEMO_PATH ]"; then
        log_warning "Project directory already exists at $DEMO_PATH"
        read -p "Do you want to delete and re-clone? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing directory..."
            ssh "$DEMO_SERVER" "rm -rf $DEMO_PATH"
        else
            log_info "Keeping existing directory"
        fi
    fi

    if ! ssh "$DEMO_SERVER" "[ -d $DEMO_PATH ]"; then
        log_info "Cloning repository..."

        # Check if we need to use SSH or HTTPS for cloning
        if [ -f ".git/config" ]; then
            # We're in a git repo, let's transfer the code via tar
            log_info "Transferring code via tar (no git clone)..."

            # Create tarball excluding unnecessary files
            tar czf /tmp/capital414-chat.tar.gz \
                --exclude='.git' \
                --exclude='node_modules' \
                --exclude='.next' \
                --exclude='apps/api/.venv' \
                --exclude='apps/api/__pycache__' \
                --exclude='*.pyc' \
                --exclude='.pytest_cache' \
                -C "$(pwd)" .

            # Transfer and extract
            scp /tmp/capital414-chat.tar.gz "$DEMO_SERVER:/tmp/"
            ssh "$DEMO_SERVER" "mkdir -p $DEMO_PATH && tar xzf /tmp/capital414-chat.tar.gz -C $DEMO_PATH && rm /tmp/capital414-chat.tar.gz"
            rm /tmp/capital414-chat.tar.gz

            log_success "Code transferred successfully"
        else
            log_error "Not in a git repository. Please run this from the project root."
            exit 1
        fi
    fi

    # Step 5: Copy environment file
    step "Step 5/6: Configure Environment Variables"

    log_info "Copying .env.prod to server..."
    if [ ! -f "envs/.env.prod" ]; then
        log_error "envs/.env.prod not found in local repository"
        exit 1
    fi

    scp envs/.env.prod "$DEMO_SERVER:$DEMO_PATH/envs/.env.prod"

    # Also create a symlink for .env
    ssh "$DEMO_SERVER" "cd $DEMO_PATH/envs && ln -sf .env.prod .env"

    log_success "Environment configured"

    # Step 6: Fix permissions and validate
    step "Step 6/6: Final Validation"

    ssh "$DEMO_SERVER" "bash -s" << ENDSSH
        set -e
        cd $DEMO_PATH

        # Make scripts executable
        chmod +x scripts/*.sh

        # Verify structure
        echo "Verifying project structure..."
        ls -la apps/api/
        ls -la apps/web/
        ls -la infra/
        ls -la scripts/

        echo ""
        echo "Docker info:"
        docker --version
        docker compose version

        echo ""
        echo "Project files:"
        ls -lh envs/.env.prod
ENDSSH

    log_success "Validation complete"

    # Summary
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  SETUP COMPLETE                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Server:${NC}       $DEMO_SERVER"
    echo -e "${BLUE}Path:${NC}         $DEMO_PATH"
    echo -e "${BLUE}Status:${NC}       Ready for deployment"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Deploy to server:  ${GREEN}make deploy-demo${NC}"
    echo "  2. Check status:      ${GREEN}make status-demo${NC}"
    echo "  3. View logs:         ${GREEN}make logs-demo${NC}"
    echo ""
    echo -e "${YELLOW}Note:${NC} You may need to log out and back in for Docker group changes to take effect"
    echo "      Or run: ${GREEN}ssh $DEMO_SERVER 'newgrp docker'${NC}"
    echo ""
}

# Run main function
main "$@"
