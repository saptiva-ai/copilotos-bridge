#!/bin/bash
# ========================================
# SAFE DEPLOYMENT SCRIPT
# ========================================
# Quick deployment with safety checks
# Usage: ./DEPLOY-NOW.sh [deploy|deploy-fast|deploy-clean]

set -e

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

DEPLOY_METHOD="${1:-deploy}"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}SAFE DEPLOYMENT WORKFLOW${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Method:${NC} make $DEPLOY_METHOD"
echo -e "${YELLOW}Time:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Function to check last command status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}$1${NC}"
    else
        echo -e "${RED}$1 FAILED!${NC}"
        echo -e "${RED}Aborting deployment${NC}"
        exit 1
    fi
}

# Phase 1: Pre-flight checks
echo -e "${BLUE}━━━ Phase 1/5: Pre-flight Checks ━━━${NC}"
echo ""

echo "Checking git status..."
git status --short
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}Warning: Uncommitted changes detected${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
fi
check_status "Git status checked"

echo "Verifying backup scripts..."
ls -la scripts/backup-mongodb.sh scripts/restore-mongodb.sh > /dev/null 2>&1
check_status "Backup scripts present"

echo "Checking Makefile commands..."
make help | grep -q "backup-mongodb-prod"
check_status "Makefile updated"

# Phase 2: Create backup
echo ""
echo -e "${BLUE}━━━ Phase 2/5: Pre-deployment Backup (CRITICAL) ━━━${NC}"
echo ""
echo -e "${YELLOW}This will create a backup before deploying${NC}"
echo "If deployment fails, you can restore from this backup"
echo ""
read -p "Create pre-deployment backup? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "SSH into production and creating backup..."
    echo -e "${YELLOW}(You will need to run this manually on the server)${NC}"
    echo ""
    echo "Run these commands on production server:"
    echo "  cd ~/copilotos-bridge"
    echo "  source envs/.env.prod"
    echo "  make backup-mongodb-prod"
    echo ""
    read -p "Press Enter when backup is complete..."
fi

# Phase 3: Deploy
echo ""
echo -e "${BLUE}━━━ Phase 3/5: Deployment ━━━${NC}"
echo ""
echo -e "${YELLOW}Starting deployment with: make $DEPLOY_METHOD${NC}"
echo "Estimated time: 8-12 minutes"
echo ""
read -p "Ready to deploy? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    START_TIME=$(date +%s)
    make $DEPLOY_METHOD
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    check_status "Deployment completed in ${DURATION}s"
else
    echo "Deployment cancelled"
    exit 0
fi

# Phase 4: Verification
echo ""
echo -e "${BLUE}━━━ Phase 4/5: Post-deployment Verification ━━━${NC}"
echo ""

echo "Waiting for services to stabilize (30 seconds)..."
sleep 30

echo "Checking deployment status..."
make deploy-status || echo -e "${YELLOW}Could not check server status (run manually on server)${NC}"

# Phase 5: Post-deploy tasks
echo ""
echo -e "${BLUE}━━━ Phase 5/5: Post-deployment Tasks ━━━${NC}"
echo ""

echo "Remember to:"
echo "  1. Clear cache: make clear-cache (on server)"
echo "  2. Verify backup system: make monitor-backups (on server)"
echo "  3. Test application functionality"
echo "  4. Monitor logs for errors"
echo ""

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}DEPLOYMENT WORKFLOW COMPLETED${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Deployment Summary:"
echo "  Method: $DEPLOY_METHOD"
echo "  Duration: ${DURATION}s"
echo "  Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Next Steps:"
echo "  ▸ Review: docs/PRE-DEPLOYMENT-CHECKLIST.md"
echo "  ▸ Verify: SSH to server and run post-deploy checks"
echo "  ◆ Document: Update deployment log"
echo ""
