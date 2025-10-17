#!/bin/sh
################################################################################
# Dependency Verification Script
#
# Verifies that critical dependencies and symlinks are correctly installed
# before starting the development server.
#
# This prevents the "Module not found" webpack errors caused by:
# - Missing symlinks in pnpm workspace
# - Corrupted webpack cache
# - Anonymous volume timing issues
#
# Usage:
#   ./scripts/verify-deps.sh [--fix]
#
# Options:
#   --fix    Attempt to fix issues by reinstalling dependencies
################################################################################

set -e

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

FIX_MODE=false
if [ "$1" = "--fix" ]; then
    FIX_MODE=true
fi

echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${BLUE}Dependency Verification${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

ISSUES_FOUND=0
WORKSPACE_ROOT="/app"
WEB_ROOT="$WORKSPACE_ROOT/apps/web"

# Critical dependencies that must be present as symlinks
CRITICAL_DEPS="
react
react-dom
react-hot-toast
next
zustand
"

# ============================================================================
# 1. Check if we're in Docker
# ============================================================================
if [ ! -f "/.dockerenv" ] && [ "$IN_DOCKER" != "1" ]; then
    echo "${YELLOW}Not running in Docker, skipping checks${NC}"
    exit 0
fi

# ============================================================================
# 2. Check workspace structure
# ============================================================================
echo "${YELLOW}[1/5] Checking workspace structure...${NC}"

if [ ! -f "$WORKSPACE_ROOT/package.json" ]; then
    echo "${RED}Workspace root package.json not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "${GREEN}Workspace root exists${NC}"
fi

if [ ! -f "$WEB_ROOT/package.json" ]; then
    echo "${RED}Web app package.json not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "${GREEN}Web app exists${NC}"
fi

echo ""

# ============================================================================
# 3. Check pnpm installation
# ============================================================================
echo "${YELLOW}[2/5] Checking pnpm...${NC}"

if ! command -v pnpm >/dev/null 2>&1; then
    echo "${RED}pnpm not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    PNPM_VERSION=$(pnpm --version)
    echo "${GREEN}pnpm installed: $PNPM_VERSION${NC}"
fi

echo ""

# ============================================================================
# 4. Check root node_modules
# ============================================================================
echo "${YELLOW}[3/5] Checking root node_modules...${NC}"

if [ ! -d "$WORKSPACE_ROOT/node_modules" ]; then
    echo "${RED}Root node_modules not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "${GREEN}Root node_modules exists${NC}"

    # Check pnpm store
    if [ ! -d "$WORKSPACE_ROOT/node_modules/.pnpm" ]; then
        echo "${RED}pnpm store (.pnpm) not found${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        STORE_SIZE=$(du -sh "$WORKSPACE_ROOT/node_modules/.pnpm" 2>/dev/null | cut -f1)
        echo "${GREEN}pnpm store exists: $STORE_SIZE${NC}"
    fi
fi

echo ""

# ============================================================================
# 5. Check web app node_modules and critical symlinks
# ============================================================================
echo "${YELLOW}[4/5] Checking web app dependencies...${NC}"

if [ ! -d "$WEB_ROOT/node_modules" ]; then
    echo "${RED}Web app node_modules not found${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "${GREEN}Web app node_modules exists${NC}"

    # Check critical symlinks
    MISSING_DEPS=""
    for dep in $CRITICAL_DEPS; do
        DEP_PATH="$WEB_ROOT/node_modules/$dep"

        if [ ! -e "$DEP_PATH" ]; then
            echo "${RED}Missing: $dep${NC}"
            MISSING_DEPS="$MISSING_DEPS $dep"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        elif [ ! -L "$DEP_PATH" ]; then
            echo "${YELLOW}Not a symlink: $dep${NC}"
        else
            # Check if symlink target exists
            if [ ! -e "$DEP_PATH" ]; then
                echo "${RED}Broken symlink: $dep${NC}"
                MISSING_DEPS="$MISSING_DEPS $dep"
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
            else
                TARGET=$(readlink "$DEP_PATH")
                echo "${GREEN}$dep → $(basename "$TARGET")${NC}"
            fi
        fi
    done
fi

echo ""

# ============================================================================
# 6. Check webpack cache
# ============================================================================
echo "${YELLOW}[5/5] Checking webpack cache...${NC}"

NEXT_DIR="$WEB_ROOT/.next"
CACHE_DIR="$NEXT_DIR/cache"

if [ ! -d "$NEXT_DIR" ]; then
    echo "${YELLOW}.next directory not found (will be created on first run)${NC}"
elif [ ! -d "$CACHE_DIR" ]; then
    echo "${YELLOW}webpack cache not found (will be created on first run)${NC}"
else
    CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
    CACHE_AGE=$(find "$CACHE_DIR" -type f -printf '%T@\n' 2>/dev/null | sort -n | tail -1)
    if [ -n "$CACHE_AGE" ]; then
        CURRENT_TIME=$(date +%s)
        AGE_SECONDS=$((CURRENT_TIME - ${CACHE_AGE%.*}))
        AGE_MINUTES=$((AGE_SECONDS / 60))
        echo "${GREEN}webpack cache exists: $CACHE_SIZE (${AGE_MINUTES}m old)${NC}"
    else
        echo "${GREEN}webpack cache exists: $CACHE_SIZE${NC}"
    fi
fi

echo ""

# ============================================================================
# Summary and Fix
# ============================================================================
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${BLUE}Summary${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$ISSUES_FOUND" -eq 0 ]; then
    echo "${GREEN}All checks passed! Dependencies are correctly installed.${NC}"
    echo ""
    exit 0
else
    echo "${RED}Found $ISSUES_FOUND issue(s)${NC}"
    echo ""

    if [ "$FIX_MODE" = true ]; then
        echo "${YELLOW}Attempting to fix issues...${NC}"
        echo ""

        # Change to workspace root
        cd "$WORKSPACE_ROOT" || exit 1

        # Clear webpack cache if it exists
        if [ -d "$CACHE_DIR" ]; then
            echo "${YELLOW}→ Clearing webpack cache...${NC}"
            rm -rf "$CACHE_DIR"
            echo "${GREEN}Cache cleared${NC}"
        fi

        # Reinstall dependencies
        echo "${YELLOW}→ Reinstalling dependencies...${NC}"
        pnpm install --frozen-lockfile

        echo ""
        echo "${GREEN}Fix attempt completed${NC}"
        echo "${YELLOW}Please restart the development server${NC}"
        echo ""
        exit 0
    else
        echo "${YELLOW}Recommendations:${NC}"
        echo ""
        echo "  1. Run with --fix flag to attempt automatic repair:"
        echo "     ${GREEN}./scripts/verify-deps.sh --fix${NC}"
        echo ""
        echo "  2. Or manually fix:"
        echo "     ${GREEN}docker compose down -v${NC}"
        echo "     ${GREEN}docker compose up --build${NC}"
        echo ""
        echo "  3. Clear webpack cache:"
        echo "     ${GREEN}make webpack-cache-clear${NC}"
        echo ""
        exit 1
    fi
fi
