# Copilotos Bridge Makefile
# Development-optimized workflow with auto .venv management
.PHONY: help dev test test-all clean build lint security security-audit install-hooks shell-api shell-web \
        push-registry push-registry-fast deploy-registry deploy-prod deploy deploy-tar deploy-fast deploy-clean \
        db-migrate db-backup db-restore db-stats db-collections db-fix-drafts \
        backup-mongodb-prod restore-mongodb-prod backup-volumes monitor-backups \
        redis-stats redis-monitor generate-credentials rotate-mongo-password rotate-redis-password reset \
        debug-containers debug-api debug-models \
        debug-file-sync debug-endpoints debug-logs-errors debug-network debug-full \
        troubleshoot resources resources-monitor docker-cleanup docker-cleanup-aggressive

# ============================================================================
# CONFIGURATION
# ============================================================================

# Project
PROJECT_NAME := copilotos
COMPOSE_FILE_BASE := infra/docker-compose.yml
COMPOSE_FILE_DEV := infra/docker-compose.dev.yml

# Environment
DEV_ENV_FILE := envs/.env
DEV_ENV_FALLBACK := envs/.env.local
DEV_ENV_EXAMPLE := envs/.env.local.example
PROD_ENV_FILE := envs/.env.prod

# Load production environment variables for deployment commands
ifneq (,$(wildcard $(PROD_ENV_FILE)))
	include $(PROD_ENV_FILE)
	export
endif

# Production deployment configuration (with fallback defaults)
# These should be set in envs/.env.prod for production deployments
PROD_SERVER_IP ?= your-server-ip-here
PROD_SERVER_USER ?= your-ssh-user
PROD_SERVER_HOST ?= $(PROD_SERVER_USER)@$(PROD_SERVER_IP)
PROD_DEPLOY_PATH ?= /opt/copilotos-bridge
PROD_BACKUP_DIR ?= /opt/backups/copilotos-production

# Legacy variable support (backward compatibility)
DEPLOY_SERVER ?= $(PROD_SERVER_HOST)
DEPLOY_PATH ?= $(PROD_DEPLOY_PATH)
BACKUP_DIR ?= $(PROD_BACKUP_DIR)

# Docker
LOCAL_UID := $(shell id -u)
LOCAL_GID := $(shell id -g)
DOCKER_COMPOSE_BASE := env UID=$(LOCAL_UID) GID=$(LOCAL_GID) docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE_BASE)
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE_BASE) -f $(COMPOSE_FILE_DEV)

# Python virtual environment
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
PYTHON_SYS := python3

# Status symbols for logs
RED := ✖ 
GREEN := ✔ 
YELLOW := ▲ 
BLUE := ▸ 
NC := "" # No Color

# ============================================================================
# DEFAULT & HELP
# ============================================================================

.DEFAULT_GOAL := help

## Show available commands with descriptions
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "CopilotOS - Development Command Center"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▸ Quick Start"
	@echo "  make setup                First-time setup (interactive)"
	@echo "  make setup-quick          Quick setup (non-interactive)"
	@echo "  make setup-interactive-prod  Production setup (interactive)"
	@echo "  make dev                  Start development environment (hot reload)"
	@echo "  make create-demo-user     Create demo user (demo / Demo1234)"
	@echo "  make logs                 View live logs from all services"
	@echo ""
	@echo "▲ Common Issue: Code changes not reflected"
	@echo "  make rebuild-api          Rebuild API with --no-cache"
	@echo "  make rebuild-web          Rebuild web with --no-cache"
	@echo "  make rebuild-all          Rebuild every service when env vars change"
	@echo "  (Use rebuild + docker compose down/up to bypass Docker cache)"
	@echo ""
	@echo "▸ Development"
	@echo "  make dev                  Start development stack"
	@echo "  make dev-build            Build and start dev services"
	@echo "  make stop                 Stop dev services"
	@echo "  make stop-all             Stop every project container"
	@echo "  make restart              Restart all services"
	@echo "  make logs                 Follow combined logs"
	@echo "  make logs-api             Follow API logs"
	@echo "  make logs-web             Follow web logs"
	@echo "  make status               Show docker-compose status"
	@echo ""
	@echo "▸ Authentication & Users"
	@echo "  make create-demo-user     Create demo user (demo / Demo1234)"
	@echo "  make delete-demo-user     Delete demo user"
	@echo "  make list-users           List registered users"
	@echo "  make test-login           Validate demo credentials"
	@echo "  make get-token            Retrieve JWT for demo user"
	@echo "  make clear-cache          Clear Redis cache"
	@echo ""
	@echo "▸ Container Access"
	@echo "  make shell-api            Bash shell in API container"
	@echo "  make shell-web            Shell in web container"
	@echo "  make shell-db             MongoDB shell"
	@echo "  make shell-redis          Redis CLI"
	@echo ""
	@echo "▸ Testing"
	@echo "  make test                 Run tests within containers"
	@echo "  make test-all             Full backend + frontend test suite"
	@echo "  make test-api             API unit tests"
	@echo "  make test-web             Web unit tests"
	@echo "  make test-e2e             Playwright end-to-end tests"
	@echo "  make health               Service health check"
	@echo ""
	@echo "▸ Code Quality"
	@echo "  make lint                 Run linters (Python & TypeScript)"
	@echo "  make lint-fix             Auto-fix lint issues"
	@echo "  make security             Security checks (fast)"
	@echo "  make security-audit       Full security audit (IPs, secrets, paths)"
	@echo "  make install-hooks        Install security-focused git hooks"
	@echo "  make verify               Full verification workflow"
	@echo ""
	@echo "▸ Database Operations"
	@echo "  make db-migrate           Apply migrations"
	@echo "  make db-backup            Simple MongoDB backup"
	@echo "  make db-restore           Restore backup"
	@echo "  make db-stats             Database statistics"
	@echo "  make db-collections       Collection counts"
	@echo "  make db-fix-drafts        Repair orphaned drafts"
	@echo "  make redis-stats          Redis metrics"
	@echo "  make redis-monitor        Monitor Redis commands"
	@echo ""
	@echo "▸ Credential Management"
	@echo "  make generate-credentials Generate strong random secrets"
	@echo "  make rotate-mongo-password  Safe MongoDB rotation"
	@echo "  make rotate-redis-password  Safe Redis rotation"
	@echo "  make reset                Complete reset with new credentials (▲ deletes data)"
	@echo "  See docs/CREDENTIAL_MANAGEMENT.md for full procedures"
	@echo ""
	@echo "▸ Backup & Disaster Recovery"
	@echo "  make backup-mongodb-prod  Advanced MongoDB backup with retention"
	@echo "  make restore-mongodb-prod Restore from production backup"
	@echo "  make backup-volumes       Backup MongoDB & Redis volumes"
	@echo "  make monitor-backups      Check backup freshness"
	@echo "  See docs/DISASTER-RECOVERY.md for details"
	@echo ""
	@echo "▸ Debugging & Diagnostics"
	@echo "  make troubleshoot         Troubleshooting menu"
	@echo "  make debug-full           Comprehensive diagnostic report"
	@echo "  make debug-containers     Container status & resources"
	@echo "  make debug-api            API configuration summary"
	@echo "  $(YELLOW)make debug-models$(NC)    Inspect model fields"
	@echo "  $(YELLOW)make debug-file-sync$(NC) Check file sync (volume mounts)"
	@echo "  $(YELLOW)make debug-network$(NC)   Test container connectivity"
	@echo "  $(YELLOW)make debug-endpoints$(NC) Test API endpoints"
	@echo "  $(YELLOW)make debug-logs-errors$(NC) Show recent errors in logs"
	@echo ""
	@echo "$(GREEN) ▸ Cleanup:$(NC)"
	@echo "  $(YELLOW)make clean$(NC)           Stop and remove containers"
	@echo "  $(YELLOW)make clean-volumes$(NC)   Clean including volumes (▲  DATA LOSS)"
	@echo "  $(YELLOW)make clean-all$(NC)       Deep clean (Docker system prune)"
	@echo ""
	@echo "$(GREEN) ▸ Resource Optimization:$(NC)"
	@echo "  $(YELLOW)make resources$(NC)                Show Docker resource usage summary"
	@echo "  $(YELLOW)make resources-monitor$(NC)        Real-time resource monitoring"
	@echo "  $(YELLOW)make docker-cleanup$(NC)           Safe cleanup (build cache, dangling images)"
	@echo "  $(YELLOW)make docker-cleanup-aggressive$(NC) Aggressive cleanup (▲  removes unused images)"
	@echo ""
	@echo "$(GREEN) ▸ Build:$(NC)"
	@echo "  $(YELLOW)make build$(NC)                Build all images"
	@echo ""
	@echo "$(GREEN) ▸ Production Deployment (Versioned with Rollback):$(NC)"
	@echo "  $(YELLOW)make deploy$(NC)               ▸ Deploy with auto-versioning + rollback (~8-12 min)"
	@echo "  $(YELLOW)make deploy-fast$(NC)          Fast deploy (skip build, use existing images)"
	@echo "  $(YELLOW)make deploy-registry$(NC)      Deploy from Docker registry (~3-5 min)"
	@echo "  $(YELLOW)make deploy-status$(NC)        Check production server status"
	@echo ""
	@echo "$(GREEN) ▸ Rollback & Recovery:$(NC)"
	@echo "  $(YELLOW)make rollback$(NC)             ▸ Rollback to previous version (automatic)"
	@echo "  $(YELLOW)make deploy-history$(NC)       Show deployment history and versions"
	@echo ""
	@echo "$(BLUE)Deployment Features:$(NC)"
	@echo "  ✔ Automatic versioning (git SHA + timestamp)"
	@echo "  ✔ Pre-deployment backup"
	@echo "  ✔ Health check validation"
	@echo "  ✔ Auto-rollback on failure"
	@echo ""
	@echo "$(GREEN) ▸ Registry Workflow (Advanced):$(NC)"
	@echo "  $(YELLOW)make push-registry$(NC)        Push images to Docker registry"
	@echo "  $(YELLOW)make deploy-prod$(NC)          Complete workflow (build+push+guide)"
	@echo ""
	@echo "$(GREEN) ▸ Maintenance:$(NC)"
	@echo "  $(YELLOW)make clear-cache$(NC)          Clear server cache (Redis + restart)"
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Demo Credentials: $(NC)$(YELLOW)demo / Demo1234$(NC)"
	@echo "$(BLUE)Frontend:        $(NC)$(YELLOW)http://localhost:3000$(NC)"
	@echo "$(BLUE)API:             $(NC)$(YELLOW)http://localhost:8001$(NC)"
	@echo "$(BLUE)API Docs:        $(NC)$(YELLOW)http://localhost:8001/docs$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# ============================================================================
# SETUP & INITIALIZATION
# ============================================================================

## Create Python virtual environment
$(VENV_DIR):
	@echo "$(YELLOW)Creating Python virtual environment...$(NC)"
	@$(PYTHON_SYS) -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip setuptools wheel
	@echo "$(GREEN) Virtual environment created$(NC)"

## Install Python dependencies
venv-install: $(VENV_DIR)
	@echo "$(YELLOW)Installing Python dependencies...$(NC)"
	@if [ -f apps/api/requirements.txt ]; then \
		$(PIP) install -r apps/api/requirements.txt; \
	fi
	@echo "$(GREEN) Python dependencies installed$(NC)"

## Interactive environment setup (recommended)
setup-interactive:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Interactive Environment Setup$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x scripts/interactive-env-setup.sh
	@./scripts/interactive-env-setup.sh development
	@$(MAKE) --no-print-directory venv-install

## Interactive production setup
setup-interactive-prod:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Interactive Production Setup$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x scripts/interactive-env-setup.sh
	@./scripts/interactive-env-setup.sh production
	@$(MAKE) --no-print-directory venv-install

## Ensure environment file exists (non-interactive fallback)
ensure-env:
	@if [ ! -f $(DEV_ENV_FILE) ]; then \
		if [ -f $(DEV_ENV_FALLBACK) ]; then \
			echo "$(YELLOW)Creating $(DEV_ENV_FILE) from $(DEV_ENV_FALLBACK)...$(NC)"; \
			cp $(DEV_ENV_FALLBACK) $(DEV_ENV_FILE); \
		elif [ -f $(DEV_ENV_EXAMPLE) ]; then \
			echo "$(YELLOW)Creating $(DEV_ENV_FILE) from $(DEV_ENV_EXAMPLE)...$(NC)"; \
			cp $(DEV_ENV_EXAMPLE) $(DEV_ENV_FILE); \
		else \
			echo "$(RED)Error: No environment file found!$(NC)"; \
			echo "Please create $(DEV_ENV_FILE) or $(DEV_ENV_FALLBACK)"; \
			exit 1; \
		fi; \
	fi

## First-time setup: interactive configuration (RECOMMENDED)
setup: setup-interactive
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)◆ Setup completed!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Run: $(GREEN)make dev$(NC)"
	@echo "  2. Run: $(GREEN)make create-demo-user$(NC)"
	@echo "  3. Visit: $(BLUE)http://localhost:3000$(NC)"
	@echo ""

## Quick setup (non-interactive, uses example files)
setup-quick: ensure-env venv-install
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)◆ Quick setup completed!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)  Warning: You're using example configuration!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit $(DEV_ENV_FILE) and add your API keys"
	@echo "  2. Run: $(GREEN)make dev$(NC)"
	@echo "  3. Run: $(GREEN)make create-demo-user$(NC)"
	@echo "  4. Visit: $(BLUE)http://localhost:3000$(NC)"
	@echo ""

# ============================================================================
# DEVELOPMENT
# ============================================================================
#
# WHEN TO USE THESE COMMANDS:
#
# Daily development:
#   make dev         - First time or after `make clean`
#   make logs        - Monitor what's happening
#   make restart     - Quick restart without rebuilding
#
# Code changes not reflecting?
#   make rebuild-api - API code changed but container shows old code
#   make rebuild-all - Multiple files changed or env vars updated
#
# Build issues / permission errors:
#   make clean-next  - Next.js build artifacts causing issues
#   make fresh       - Nuclear option: clean everything and rebuild
# ============================================================================

## Start development environment with hot reload
## Note: .next uses anonymous Docker volume to prevent permission issues
dev: ensure-env
	@echo "$(YELLOW) Starting development environment...$(NC)"
	@$(DOCKER_COMPOSE_DEV) up -d
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "  $(BLUE) Frontend:$(NC) $(YELLOW)http://localhost:3000$(NC)"
	@echo "  $(BLUE) API:$(NC)      $(YELLOW)http://localhost:8001$(NC)"
	@echo "  $(BLUE) Docs:$(NC)     $(YELLOW)http://localhost:8001/docs$(NC)"
	@echo ""
	@echo "$(YELLOW) Waiting for services to be healthy...$(NC)"
	@sleep 10
	@$(MAKE) --no-print-directory health

## Build and start development environment
dev-build: ensure-env
	@echo "$(YELLOW) Building and starting development environment...$(NC)"
	@$(DOCKER_COMPOSE_DEV) up -d --build
	@echo "$(GREEN) ✓ Services built and started$(NC)"
	@sleep 10
	@$(MAKE) --no-print-directory health

## Rebuild API container without cache
rebuild-api: ensure-env
	@echo "$(YELLOW) Rebuilding API container without cache...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --no-cache api
	@$(DOCKER_COMPOSE_DEV) down api
	@$(DOCKER_COMPOSE_DEV) up -d api
	@echo "$(GREEN) ✓ API container rebuilt and restarted$(NC)"
	@echo "$(BLUE) ℹ  Container recreated with fresh code and env vars$(NC)"

## Rebuild web container without cache
rebuild-web: ensure-env
	@echo "$(YELLOW) Rebuilding Web container without cache...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --no-cache web
	@$(DOCKER_COMPOSE_DEV) down web
	@$(DOCKER_COMPOSE_DEV) up -d web
	@echo "$(GREEN) ✓ Web container rebuilt and restarted$(NC)"
	@echo "$(BLUE) ℹ  Container recreated with fresh code and env vars$(NC)"

## Rebuild all containers without cache
rebuild-all: ensure-env
	@echo "$(YELLOW)Rebuilding all containers without cache...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --no-cache
	@$(DOCKER_COMPOSE_DEV) down
	@$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN) ✓ All containers rebuilt and restarted$(NC)"
	@echo "$(BLUE) ℹ  All containers recreated with fresh code and env vars$(NC)"

## Clean Next.js cache and volumes
## Removes both host .next directory and Docker anonymous volumes
clean-next: stop
	@echo "$(YELLOW)Cleaning Next.js cache and volumes...$(NC)"
	@rm -rf apps/web/.next 2>/dev/null || true
	@docker volume ls -qf "dangling=true" | xargs -r docker volume rm 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_next_cache $(PROJECT_NAME)_next_standalone_cache $(PROJECT_NAME)_web-next-cache 2>/dev/null || true
	@echo "$(GREEN) Next.js cache cleaned$(NC)"

## Clean all caches and volumes
clean-cache: stop
	@echo "$(YELLOW) Cleaning all caches and volumes...$(NC)"
	@rm -rf apps/web/.next 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_next_cache $(PROJECT_NAME)_next_standalone_cache $(PROJECT_NAME)_web-next-cache 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_mongodb_data $(PROJECT_NAME)_mongodb_config $(PROJECT_NAME)_redis_data 2>/dev/null || echo "$(YELLOW) Database volumes not removed (use 'make clean-all' to remove them)$(NC)"
	@echo "$(GREEN) ✓ Cache cleaned$(NC)"

## Nuclear option: clean everything including database
clean-all: stop
	@echo "$(RED) ▲ WARNING: This will delete ALL data including database!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW) Cleaning everything...$(NC)"; \
		rm -rf apps/web/.next 2>/dev/null || true; \
		$(DOCKER_COMPOSE_DEV) down -v --remove-orphans; \
		docker volume prune -f; \
		echo "$(GREEN) ✓ Everything cleaned$(NC)"; \
	else \
		echo "$(YELLOW) Cancelled$(NC)"; \
	fi

## Fresh start: clean and rebuild
fresh: clean-next dev
	@echo "$(GREEN) ✓ Fresh start completed!$(NC)"

## Clean development environment (removes volumes and cache)
# REMOVED: dev-clean - Use 'make fresh' instead for full clean rebuild

## Clear Next.js webpack cache only (inside container)
# REMOVED: webpack-cache-clear - Use 'make clean-cache' instead

## Verify dependencies and symlinks
verify-deps:
	@echo "$(YELLOW) Running dependency verification...$(NC)"
	@chmod +x scripts/verify-deps.sh
	@docker exec $(PROJECT_NAME)-web /app/scripts/verify-deps.sh || true

## Verify and fix dependencies
verify-deps-fix:
	@echo "$(YELLOW) Running dependency verification with auto-fix...$(NC)"
	@chmod +x scripts/verify-deps.sh
	@docker exec $(PROJECT_NAME)-web /app/scripts/verify-deps.sh --fix || true

## Stop all services (dev compose)
stop:
	@echo "$(YELLOW)Stopping services...$(NC)"
	@$(DOCKER_COMPOSE_DEV) down
	@echo "$(GREEN) ✓ Services stopped$(NC)"

## Stop ALL project containers (including base compose)
stop-all:
	@echo "$(YELLOW)Stopping ALL project containers...$(NC)"
	@cd infra && docker compose down --remove-orphans 2>/dev/null || true
	@$(DOCKER_COMPOSE_DEV) down --remove-orphans
	@echo "$(GREEN) ✓ All project containers stopped$(NC)"

## Restart all services (recreates containers to reload env vars)
# ▲  IMPORTANT: This uses 'down' + 'up' instead of 'restart' because
#    'docker compose restart' does NOT reload environment variables from .env
#    Use this command after:
#    • Updating credentials in .env
#    • Changing environment variables
#    • Modifying docker-compose.yml
restart:
	@echo "$(YELLOW)Restarting services (recreating containers to reload env vars)...$(NC)"
	@$(DOCKER_COMPOSE_DEV) down
	@$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN) ✓ Services restarted$(NC)"
	@echo "$(YELLOW)▸ Waiting for services to be ready...$(NC)"
	@sleep 3
	@if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then \
		echo "$(GREEN) API is healthy!$(NC)"; \
	else \
		echo "$(YELLOW)  API may need more time. Check: make health$(NC)"; \
	fi

## Follow logs from all services
logs:
	@$(DOCKER_COMPOSE_DEV) logs -f --tail=100

## Follow API logs only
logs-api:
	@$(DOCKER_COMPOSE_DEV) logs -f --tail=100 api

## Follow web logs only
logs-web:
	@$(DOCKER_COMPOSE_DEV) logs -f --tail=100 web

## Show service status
status:
	@echo "$(BLUE)Service Status:$(NC)"
	@$(DOCKER_COMPOSE_DEV) ps
	@echo ""
	@echo "$(BLUE)Docker Resources:$(NC)"
	@docker system df

# ============================================================================
# HEALTH & VERIFICATION
# ============================================================================

## Check service health
health:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Health Check$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@printf "  $(YELLOW) API Health:$(NC)        "
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 && \
		echo "$(GREEN) ✓ Healthy$(NC)" || \
		echo "$(RED) ✖ Not responding$(NC)"
	@printf "  $(YELLOW)Frontend:$(NC)          "
	@curl -sf http://localhost:3000/healthz > /dev/null 2>&1 && \
		echo "$(GREEN) ✓ Healthy$(NC)" || \
		echo "$(RED) ✖ Not responding$(NC)"
	@printf "  $(YELLOW) MongoDB:$(NC)           "
	@$(DOCKER_COMPOSE_DEV) exec -T mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1 && \
		echo "$(GREEN) ✓ Connected$(NC)" || \
		echo "$(RED) ✖ Not connected$(NC)"
	@printf "  $(YELLOW) Redis:$(NC)             "
	@$(DOCKER_COMPOSE_DEV) exec -T redis redis-cli ping > /dev/null 2>&1 && \
		echo "$(GREEN) ✓ Connected$(NC)" || \
		echo "$(RED) ✖ Not connected$(NC)"
	@echo ""

## Full verification (setup + health + auth)
verify: health
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Verification Tests$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@bash scripts/verify-deployment.sh 2>/dev/null || echo "$(YELLOW) Run 'bash scripts/verify-deployment.sh' for full verification$(NC)"

# ============================================================================
# AUTHENTICATION & USERS
# ============================================================================

## Create demo user (username: demo, password: Demo1234)
create-demo-user:
	@echo "$(YELLOW) Creating demo user...$(NC)"
	@echo ""
	@echo "  $(BLUE) Username:$(NC) $(GREEN)demo$(NC)"
	@echo "  $(BLUE) Password:$(NC) $(GREEN)Demo1234$(NC)"
	@echo "  $(BLUE) Email:$(NC)    $(GREEN)demo@example.com$(NC)"
	@echo ""
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 || \
		(echo "$(RED) API not ready. Run 'make dev' first$(NC)" && exit 1)
	@curl -X POST http://localhost:8001/api/auth/register \
		-H "Content-Type: application/json" \
		-d '{"username":"demo","email":"demo@example.com","password":"Demo1234"}' \
		2>/dev/null | grep -q "access_token" && \
		echo "$(GREEN) ✓ Demo user created successfully!$(NC)" || \
		(echo "$(YELLOW) ▲ User may already exist. Try 'make delete-demo-user' first$(NC)" && exit 1)
	@echo ""
	@echo "$(GREEN) You can now login at:$(NC) $(BLUE)http://localhost:3000/login$(NC)"

## Delete demo user
delete-demo-user:
	@echo "$(YELLOW)Deleting demo user...$(NC)"
	@docker exec infra-api python -c "\
import asyncio, os; \
from motor.motor_asyncio import AsyncIOMotorClient; \
async def main(): \
	url = os.getenv('MONGODB_URL'); \
	client = AsyncIOMotorClient(url); \
	db_name = url.split('/')[-1].split('?')[0]; \
	db = client[db_name]; \
	result = await db['users'].delete_many({'username': 'demo'}); \
	print(f'Deleted {result.deleted_count} user(s)'); \
asyncio.run(main())" 2>&1 | grep -E "Deleted" || echo "$(RED) Failed to delete user$(NC)"
	@echo "$(GREEN) Demo user deleted$(NC)"
	@echo "$(YELLOW)Run 'make clear-cache' to clear Redis cache$(NC)"

## List all users in database
list-users:
	@echo "$(BLUE)Database Users:$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec mongodb mongosh copilotos \
		--eval "db.users.find({}, {username: 1, email: 1, is_active: 1, created_at: 1}).forEach(printjson)" \
		--quiet 2>/dev/null || echo "$(RED) Cannot connect to database$(NC)"

## Test login with demo credentials
test-login:
	@echo "$(YELLOW)Testing login with demo credentials...$(NC)"
	@curl -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"demo","password":"Demo1234"}' \
		2>/dev/null | grep -q "access_token" && \
		echo "$(GREEN) Login successful!$(NC)" || \
		(echo "$(RED) Login failed$(NC)" && echo "$(YELLOW)Try: make clear-cache && make delete-demo-user && make create-demo-user$(NC)")

## Clear server cache (Redis + restart web container) - For production deployments
clear-cache:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Clearing Server Cache$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/clear-server-cache.sh

## Clear local Redis cache (for development)
clear-redis-local:
	@echo "$(YELLOW)Clearing local Redis cache...$(NC)"
	@docker exec $(PROJECT_NAME)-redis redis-cli -a redis_password_change_me FLUSHALL 2>&1 | grep -q "OK" && \
		echo "$(GREEN) Redis cache cleared$(NC)" || \
		echo "$(RED) Failed to clear cache$(NC)"

## Get JWT token for demo user
get-token:
	@echo "$(YELLOW)Getting JWT token for demo user...$(NC)"
	@TOKEN=$$(curl -s -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"demo","password":"Demo1234"}' | \
		grep -o '"access_token":"[^"]*"' | cut -d'"' -f4); \
	if [ -n "$$TOKEN" ]; then \
		echo "$(GREEN) Token obtained$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Export to use in requests:$(NC)"; \
		echo "  export TOKEN=\"$$TOKEN\""; \
		echo ""; \
		echo "$(YELLOW)Example usage:$(NC)"; \
		echo "  curl -H \"Authorization: Bearer \$$TOKEN\" http://localhost:8001/api/chat"; \
	else \
		echo "$(RED) Failed to get token$(NC)"; \
	fi

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

## Run database migrations
db-migrate:
	@echo "$(YELLOW)Running database migrations...$(NC)"
	@if [ -f scripts/migrate-conversation-timestamps.py ]; then \
		docker cp scripts/migrate-conversation-timestamps.py $(PROJECT_NAME)-api:/tmp/; \
		printf "y\n" | docker exec -i $(PROJECT_NAME)-api python3 /tmp/migrate-conversation-timestamps.py; \
		echo "$(GREEN) Migration completed$(NC)"; \
	else \
		echo "$(RED) Migration script not found$(NC)"; \
	fi

## Backup MongoDB database
db-backup:
	@echo "$(YELLOW)Backing up MongoDB database...$(NC)"
	@mkdir -p backups
	@BACKUP_FILE="backups/mongodb-$$(date +%Y%m%d-%H%M%S).archive"; \
	docker exec $(PROJECT_NAME)-mongodb mongodump \
		--uri="mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin" \
		--archive=/tmp/backup.archive; \
	docker cp $(PROJECT_NAME)-mongodb:/tmp/backup.archive $$BACKUP_FILE; \
	echo "$(GREEN) Backup created: $$BACKUP_FILE$(NC)"

## Restore MongoDB database from backup
db-restore:
	@echo "$(RED)▲  WARNING: This will restore database from backup!$(NC)"
	@read -p "Backup file path: " BACKUP_FILE; \
	if [ ! -f "$$BACKUP_FILE" ]; then \
		echo "$(RED) Backup file not found$(NC)"; \
		exit 1; \
	fi; \
	docker cp $$BACKUP_FILE $(PROJECT_NAME)-mongodb:/tmp/restore.archive; \
	docker exec $(PROJECT_NAME)-mongodb mongorestore \
		--uri="mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin" \
		--archive=/tmp/restore.archive \
		--drop; \
	echo "$(GREEN) Database restored$(NC)"

## Show database statistics
db-stats:
	@echo "$(BLUE)Database Statistics:$(NC)"
	@echo ""
	@$(DOCKER_COMPOSE_DEV) exec mongodb mongosh copilotos \
		--eval "db.stats()" \
		--quiet 2>/dev/null || echo "$(RED) Cannot connect to database$(NC)"

## List all collections and document counts
db-collections:
	@echo "$(BLUE)Collections:$(NC)"
	@echo ""
	@$(DOCKER_COMPOSE_DEV) exec mongodb mongosh copilotos \
		--eval "db.getCollectionNames().forEach(function(c) { print(c + ': ' + db[c].countDocuments({})); })" \
		--quiet 2>/dev/null || echo "$(RED) Cannot connect to database$(NC)"

## Fix orphaned draft conversations
db-fix-drafts:
	@echo "$(YELLOW)Fixing orphaned draft conversations...$(NC)"
	@if [ -f scripts/fix-orphaned-drafts.py ]; then \
		docker cp scripts/fix-orphaned-drafts.py $(PROJECT_NAME)-api:/tmp/; \
		docker exec $(PROJECT_NAME)-api python3 /tmp/fix-orphaned-drafts.py; \
		echo "$(GREEN) Drafts fixed$(NC)"; \
	else \
		echo "$(RED) Fix script not found$(NC)"; \
	fi

## Advanced MongoDB backup (uses new backup script with retention)
backup-mongodb-prod:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Production MongoDB Backup$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x scripts/backup-mongodb.sh
	@./scripts/backup-mongodb.sh

## Restore MongoDB from production backup
restore-mongodb-prod:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ MongoDB Restore$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x scripts/restore-mongodb.sh
	@./scripts/restore-mongodb.sh

## Backup Docker volumes (MongoDB + Redis data)
backup-volumes:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Docker Volumes Backup$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x scripts/backup-docker-volumes.sh
	@./scripts/backup-docker-volumes.sh

## Monitor backup health
monitor-backups:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Backup Health Monitor$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x scripts/monitor-backups.sh
	@./scripts/monitor-backups.sh

## Show Redis keys and memory usage
redis-stats:
	@echo "$(BLUE)Redis Statistics:$(NC)"
	@echo ""
	@printf "  $(YELLOW)Total Keys:$(NC)       "
	@docker exec $(PROJECT_NAME)-redis redis-cli -a redis_password_change_me DBSIZE 2>/dev/null | tail -1
	@printf "  $(YELLOW)Memory Used:$(NC)      "
	@docker exec $(PROJECT_NAME)-redis redis-cli -a redis_password_change_me INFO memory 2>/dev/null | grep used_memory_human | cut -d: -f2
	@printf "  $(YELLOW)Connected Clients:$(NC) "
	@docker exec $(PROJECT_NAME)-redis redis-cli -a redis_password_change_me INFO clients 2>/dev/null | grep connected_clients | cut -d: -f2
	@echo ""

## Monitor Redis commands in real-time
redis-monitor:
	@echo "$(YELLOW)Monitoring Redis commands (Ctrl+C to stop)...$(NC)"
	@docker exec -it $(PROJECT_NAME)-redis redis-cli -a redis_password_change_me MONITOR 2>/dev/null

# ============================================================================
# CREDENTIAL MANAGEMENT
# ============================================================================
#
# WHEN TO USE THESE COMMANDS:
#
# First-time setup:
#   make generate-credentials  - Generate secure random passwords for .env file
#                                Use when: Setting up new environment (dev/prod)
#
# Regular rotation (recommended every 3 months):
#   make rotate-mongo-password - Safely rotate MongoDB password WITHOUT data loss
#   make rotate-redis-password - Safely rotate Redis password WITHOUT data loss
#                                Always test in DEV before PROD!
#
# Production validation:
#   make validate-production   - Check system readiness for credential rotation
#                                Use when: Before any production rotation
#                                Validates: env_file config, credential sync, backups, scripts
#
# Emergency reset (DEVELOPMENT ONLY):
#   make reset                 - Complete reset: stop → delete volumes → regenerate credentials → restart
#                                ▲  WARNING: Deletes ALL data including database!
#                                Use when: Starting fresh, credential mismatch, corrupted volumes
#
# Security best practices:
#   - Rotate credentials every 3 months (MongoDB/Redis) or 6 months (JWT)
#   - NEVER reuse DEV credentials in PROD
#   - Always backup before rotating in PROD
#   - Test rotation in DEV first
#   - Run validate-production before any production rotation
#
# ============================================================================
# ▲  CRITICAL LESSONS LEARNED FROM PRODUCTION ISSUES
# ============================================================================
#
# 1. Docker Compose RESTART Does NOT Reload Environment Variables
#    ------------------------------------------------------------
#    PROBLEM: After updating .env with new credentials and running
#             'docker compose restart', containers still use OLD credentials
#             causing authentication failures.
#
#    ROOT CAUSE: 'docker compose restart' only restarts processes but does NOT
#                recreate containers or reload environment variables from .env
#
#    SOLUTION: Always use 'down' + 'up' to reload credentials:
#              ✔ CORRECT:   docker compose down api && docker compose up -d api
#              ✖ WRONG:     docker compose restart api
#
#    IMPACT: This caused Redis authentication errors (WRONGPASS), MongoDB auth
#            failures, and led developers to incorrectly delete volumes thinking
#            data was corrupted, when it was only a credential sync issue.
#
# 2. docker-compose.yml MUST Have env_file Directive
#    ------------------------------------------------
#    PROBLEM: Services not synchronizing credentials from .env file
#
#    SOLUTION: Every service must have:
#              services:
#                api:
#                  env_file:
#                    - ../envs/.env    # ← CRITICAL
#
#    Without this, containers use hardcoded/default values and ignore .env changes
#
# 3. External API Integration Requirements (Saptiva Specific)
#    ---------------------------------------------------------
#    SAPTIVA API REQUIRES:
#    • Trailing slash in endpoint: /v1/chat/completions/ (not /v1/chat/completions)
#    • Capitalized model names: "Saptiva Turbo" (not "saptiva-turbo")
#    • Redirect handling enabled: follow_redirects=True
#
#    Without these, you'll get 404 errors even with valid API keys
#
# 4. Health Checks Are Essential After Configuration Changes
#    --------------------------------------------------------
#    After credential rotation or environment reset, wait for services to
#    initialize properly before declaring success. Use health check loops
#    (see 'make reset' implementation)
#
# 5. Credential Desynchronization is the #1 Cause of Issues
#    -------------------------------------------------------
#    SYMPTOMS:
#    • "Cargando conversaciones..." stuck loading
#    • "Generando respuesta..." hangs indefinitely
#    • Redis WRONGPASS errors in logs
#    • MongoDB authentication failures
#
#    DIAGNOSIS:
#    • Check .env has correct password: grep REDIS_PASSWORD envs/.env
#    • Check container env: docker inspect <container> | grep PASSWORD
#    • If they don't match → credential desync → recreate container
#
#    FIX: Update .env, then docker compose down <service> && up -d <service>
#
# See: docs/CREDENTIAL_MANAGEMENT.md for complete procedures
# ============================================================================

## Generate secure credentials for .env file
generate-credentials:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)⛨ Secure Credential Generator$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Generating secure random credentials...$(NC)"
	@echo ""
	@echo "$(GREEN)MongoDB/Redis Password (32 characters):$(NC)"
	@openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
	@echo ""
	@echo "$(GREEN)JWT Secret Key (64 characters):$(NC)"
	@openssl rand -base64 64 | tr -d '\n' && echo ""
	@echo ""
	@echo "$(YELLOW)◆ Usage:$(NC)"
	@echo "  1. Copy the generated passwords above"
	@echo "  2. Update your envs/.env or envs/.env.prod file:"
	@echo "     MONGODB_PASSWORD=<32-char-password>"
	@echo "     REDIS_PASSWORD=<32-char-password>"
	@echo "     JWT_SECRET_KEY=<64-char-key>"
	@echo "  3. Run: $(GREEN)make restart$(NC)"
	@echo ""
	@echo "$(YELLOW)  Security Note:$(NC)"
	@echo "  • NEVER commit these passwords to git"
	@echo "  • Use different passwords for DEV vs PROD"
	@echo "  • Store PROD credentials in a secure vault"
	@echo ""

## Rotate MongoDB password safely (WITHOUT data loss)
rotate-mongo-password:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ MongoDB Password Rotation$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@if ! docker ps | grep -q "$(PROJECT_NAME)-mongodb"; then \
		echo "$(RED) MongoDB container not running$(NC)"; \
		echo "  Run: $(GREEN)make dev$(NC) first"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Current MongoDB password in envs/.env:$(NC)"
	@grep MONGODB_PASSWORD $(DEV_ENV_FILE) || echo "  $(RED)MONGODB_PASSWORD not found$(NC)"
	@echo ""
	@echo "$(YELLOW)  IMPORTANT: This will change the password in MongoDB WITHOUT deleting data$(NC)"
	@echo ""
	@read -p "Enter OLD password (current): " OLD_PASS && \
	echo "" && \
	read -p "Enter NEW password: " NEW_PASS && \
	echo "" && \
	chmod +x scripts/rotate-mongo-credentials.sh && \
	./scripts/rotate-mongo-credentials.sh "$$OLD_PASS" "$$NEW_PASS" && \
	echo "" && \
	echo "$(GREEN)✔ MongoDB password rotated!$(NC)" && \
	echo "" && \
	echo "$(YELLOW)◆ Next steps:$(NC)" && \
	echo "  1. Update $(DEV_ENV_FILE):" && \
	echo "     MONGODB_PASSWORD=$$NEW_PASS" && \
	echo "  2. Recreate containers (REQUIRED to reload credentials):" && \
	echo "     $(GREEN)make restart$(NC)  (uses down+up, NOT restart)" && \
	echo "" && \
	echo "$(YELLOW)  Note: 'make restart' recreates containers to reload .env$(NC)" && \
	echo "$(YELLOW)   Old 'docker compose restart' doesn't work for credential changes!$(NC)" && \
	echo ""

## Rotate Redis password safely (WITHOUT data loss)
rotate-redis-password:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Redis Password Rotation$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@if ! docker ps | grep -q "$(PROJECT_NAME)-redis"; then \
		echo "$(RED) Redis container not running$(NC)"; \
		echo "  Run: $(GREEN)make dev$(NC) first"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Current Redis password in envs/.env:$(NC)"
	@grep REDIS_PASSWORD $(DEV_ENV_FILE) || echo "  $(RED)REDIS_PASSWORD not found$(NC)"
	@echo ""
	@echo "$(YELLOW)  IMPORTANT: This will change the password in Redis WITHOUT deleting data$(NC)"
	@echo ""
	@read -p "Enter NEW password: " NEW_PASS && \
	echo "" && \
	chmod +x scripts/rotate-redis-credentials.sh && \
	./scripts/rotate-redis-credentials.sh "$$NEW_PASS" && \
	echo "" && \
	echo "$(GREEN)✔ Redis password rotated!$(NC)" && \
	echo "" && \
	echo "$(YELLOW)◆ Next steps:$(NC)" && \
	echo "  1. Update $(DEV_ENV_FILE):" && \
	echo "     REDIS_PASSWORD=$$NEW_PASS" && \
	echo "  2. Recreate containers (REQUIRED to reload credentials):" && \
	echo "     $(GREEN)make restart$(NC)  (uses down+up, NOT restart)" && \
	echo "" && \
	echo "$(YELLOW)  Note: 'make restart' recreates containers to reload .env$(NC)" && \
	echo "$(YELLOW)   Old 'docker compose restart' doesn't work for credential changes!$(NC)" && \
	echo ""

## Validate production readiness before credential rotation
validate-production:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Production Readiness Validation$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking system configuration for safe credential rotation...$(NC)"
	@echo ""
	@chmod +x scripts/validate-production-readiness.sh
	@./scripts/validate-production-readiness.sh

## Complete environment reset (▲ DELETES ALL DATA)
reset:
	@echo "$(RED)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(RED)  ▲  COMPLETE ENVIRONMENT RESET$(NC)"
	@echo "$(RED)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)This will:$(NC)"
	@echo "  1. Stop all containers"
	@echo "  2. Delete all volumes (MongoDB data, Redis data)"
	@echo "  3. Generate new secure credentials"
	@echo "  4. Update envs/.env with new credentials"
	@echo "  5. Restart development environment"
	@echo ""
	@echo "$(RED)▲  WARNING: ALL DATABASE DATA WILL BE LOST!$(NC)"
	@echo ""
	@read -p "Are you absolutely sure? Type 'reset' to confirm: " confirm; \
	if [ "$$confirm" != "reset" ]; then \
		echo "$(YELLOW)Reset cancelled$(NC)"; \
		exit 0; \
	fi; \
	echo ""; \
	echo "$(YELLOW) Step 1/5: Stopping all containers...$(NC)"; \
	$(DOCKER_COMPOSE_DEV) down --remove-orphans; \
	echo "$(GREEN) Containers stopped$(NC)"; \
	echo ""; \
	echo "$(YELLOW)▸  Step 2/5: Deleting volumes...$(NC)"; \
	docker volume rm $(PROJECT_NAME)_mongodb_data $(PROJECT_NAME)_mongodb_config $(PROJECT_NAME)_redis_data 2>/dev/null || true; \
	echo "$(GREEN) Volumes deleted$(NC)"; \
	echo ""; \
	echo "$(YELLOW)⛨ Step 3/5: Generating new credentials...$(NC)"; \
	MONGO_PASS=$$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32); \
	REDIS_PASS=$$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32); \
	JWT_SECRET=$$(openssl rand -base64 64 | tr -d '\n'); \
	echo "  • MongoDB: $$MONGO_PASS"; \
	echo "  • Redis: $$REDIS_PASS"; \
	echo "  • JWT: $${JWT_SECRET:0:20}..."; \
	echo "$(GREEN) Credentials generated$(NC)"; \
	echo ""; \
	echo "$(YELLOW)◆ Step 4/5: Updating $(DEV_ENV_FILE)...$(NC)"; \
	if [ -f $(DEV_ENV_FILE) ]; then \
		sed -i.bak "s|^MONGODB_PASSWORD=.*|MONGODB_PASSWORD=$$MONGO_PASS|" $(DEV_ENV_FILE); \
		sed -i.bak "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$$REDIS_PASS|" $(DEV_ENV_FILE); \
		sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$$JWT_SECRET|" $(DEV_ENV_FILE); \
		rm -f $(DEV_ENV_FILE).bak; \
		echo "$(GREEN) $(DEV_ENV_FILE) updated$(NC)"; \
	else \
		echo "$(RED) $(DEV_ENV_FILE) not found$(NC)"; \
		echo "  Run: $(GREEN)make setup$(NC) first"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "$(YELLOW)▸ Step 5/5: Starting development environment...$(NC)"; \
	$(MAKE) --no-print-directory dev; \
	echo ""; \
	echo "$(YELLOW)▸ Waiting for services to initialize with new credentials...$(NC)"; \
	sleep 5; \
	MAX_ATTEMPTS=30; \
	ATTEMPT=0; \
	while [ $$ATTEMPT -lt $$MAX_ATTEMPTS ]; do \
		if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then \
			echo "$(GREEN) Services are ready!$(NC)"; \
			break; \
		fi; \
		ATTEMPT=$$((ATTEMPT + 1)); \
		sleep 2; \
	done; \
	if [ $$ATTEMPT -eq $$MAX_ATTEMPTS ]; then \
		echo "$(YELLOW)  Services may need more time to start$(NC)"; \
		echo "$(YELLOW)Check status with: make health$(NC)"; \
	fi; \
	echo ""; \
	echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
	echo "$(GREEN)✔ Environment reset completed!$(NC)"; \
	echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
	echo ""; \
	echo "$(YELLOW)◆ Next steps:$(NC)"; \
	echo "  1. Run: $(GREEN)make create-demo-user$(NC)"; \
	echo "  2. Visit: $(BLUE)http://localhost:3000$(NC)"; \
	echo ""; \
	echo "$(YELLOW)◆ New credentials have been saved to $(DEV_ENV_FILE)$(NC)"; \
	echo ""

# ============================================================================
# CONTAINER ACCESS
# ============================================================================

## Shell into API container
shell-api:
	@docker exec -it $(PROJECT_NAME)-api bash

## Shell into web container
shell-web:
	@docker exec -it $(PROJECT_NAME)-web sh

## MongoDB shell
shell-db:
	@docker exec -it $(PROJECT_NAME)-mongodb mongosh copilotos

## Redis CLI
shell-redis:
	@docker exec -it $(PROJECT_NAME)-redis redis-cli

# ============================================================================
# DEBUGGING & DIAGNOSTICS
# ============================================================================

## Show detailed container information
debug-containers:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Container Debug Information$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Container Status:$(NC)"
	@$(DOCKER_COMPOSE_DEV) ps
	@echo ""
	@echo "$(YELLOW)Resource Usage:$(NC)"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
		$(PROJECT_NAME)-api $(PROJECT_NAME)-web $(PROJECT_NAME)-mongodb $(PROJECT_NAME)-redis 2>/dev/null || true
	@echo ""

## Inspect API container configuration
debug-api:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)API Container Debug$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Volume Mounts:$(NC)"
	@docker inspect $(PROJECT_NAME)-api --format='{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Type}}){{"\n"}}{{end}}'
	@echo ""
	@echo "$(YELLOW)Environment Variables (filtered):$(NC)"
	@docker exec $(PROJECT_NAME)-api env | grep -E "MONGODB|REDIS|SAPTIVA|JWT|DEBUG|LOG_LEVEL" | sort
	@echo ""
	@echo "$(YELLOW)Python Version:$(NC)"
	@docker exec $(PROJECT_NAME)-api python3 --version
	@echo ""
	@echo "$(YELLOW)Installed Packages:$(NC)"
	@docker exec $(PROJECT_NAME)-api pip list | grep -E "fastapi|motor|beanie|redis|pydantic"
	@echo ""

## Check if models have expected fields
debug-models:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Model Field Inspection$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)ChatSession Model Fields:$(NC)"
	@docker exec $(PROJECT_NAME)-api python3 -c "\
import sys; \
sys.path.insert(0, '/app/src'); \
from models.chat import ChatSession; \
fields = ChatSession.model_fields; \
for name, field in fields.items(): \
    print(f'  {name}: {field.annotation}'); \
" 2>/dev/null || echo "$(RED) Failed to inspect model$(NC)"
	@echo ""

## Verify file checksums inside container vs local
debug-file-sync:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)File Synchronization Check$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking models/chat.py:$(NC)"
	@LOCAL_MD5=$$(md5sum apps/api/src/models/chat.py | cut -d' ' -f1); \
	CONTAINER_MD5=$$(docker exec $(PROJECT_NAME)-api md5sum /app/src/models/chat.py | cut -d' ' -f1); \
	echo "  Local:     $$LOCAL_MD5"; \
	echo "  Container: $$CONTAINER_MD5"; \
	if [ "$$LOCAL_MD5" = "$$CONTAINER_MD5" ]; then \
		echo "  $(GREEN) Files match$(NC)"; \
	else \
		echo "  $(RED) Files differ!$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Checking routers/conversations.py:$(NC)"
	@LOCAL_MD5=$$(md5sum apps/api/src/routers/conversations.py | cut -d' ' -f1); \
	CONTAINER_MD5=$$(docker exec $(PROJECT_NAME)-api md5sum /app/src/routers/conversations.py | cut -d' ' -f1); \
	echo "  Local:     $$LOCAL_MD5"; \
	echo "  Container: $$CONTAINER_MD5"; \
	if [ "$$LOCAL_MD5" = "$$CONTAINER_MD5" ]; then \
		echo "  $(GREEN) Files match$(NC)"; \
	else \
		echo "  $(RED) Files differ!$(NC)"; \
	fi
	@echo ""

## Test API endpoints with authentication
debug-endpoints:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)API Endpoint Testing$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@printf "  $(YELLOW)/api/health:$(NC)       "
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 && \
		echo "$(GREEN) OK$(NC)" || echo "$(RED) FAIL$(NC)"
	@printf "  $(YELLOW)/api/models:$(NC)       "
	@curl -sf http://localhost:8001/api/models > /dev/null 2>&1 && \
		echo "$(GREEN) OK$(NC)" || echo "$(RED) FAIL$(NC)"
	@echo ""
	@echo "$(YELLOW)Testing authenticated endpoints...$(NC)"
	@TOKEN=$$(curl -s -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"demo","password":"Demo1234"}' 2>/dev/null | \
		grep -o '"access_token":"[^"]*"' | cut -d'"' -f4); \
	if [ -n "$$TOKEN" ]; then \
		echo "  $(GREEN) Authentication successful$(NC)"; \
		printf "  $(YELLOW)/api/sessions:$(NC)     "; \
		curl -sf -H "Authorization: Bearer $$TOKEN" \
			"http://localhost:8001/api/sessions?limit=1" > /dev/null 2>&1 && \
			echo "$(GREEN) OK$(NC)" || echo "$(RED) FAIL$(NC)"; \
		printf "  $(YELLOW)/api/conversations:$(NC) "; \
		curl -sf -H "Authorization: Bearer $$TOKEN" \
			"http://localhost:8001/api/conversations?limit=1" > /dev/null 2>&1 && \
			echo "$(GREEN) OK$(NC)" || echo "$(RED) FAIL$(NC)"; \
	else \
		echo "  $(RED) Authentication failed$(NC)"; \
		echo "  $(YELLOW)Run 'make create-demo-user' first$(NC)"; \
	fi
	@echo ""

## Show recent API logs with errors highlighted
debug-logs-errors:
	@echo "$(YELLOW)Recent API errors (last 50 lines):$(NC)"
	@$(DOCKER_COMPOSE_DEV) logs --tail=50 api 2>&1 | grep -iE "error|exception|traceback|failed" || \
		echo "$(GREEN) No recent errors found$(NC)"

## Network debugging - show container connectivity
debug-network:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Network Connectivity$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Testing container-to-container connectivity:$(NC)"
	@printf "  $(YELLOW)API -> MongoDB:$(NC)  "
	@docker exec $(PROJECT_NAME)-api nc -zv mongodb 27017 2>&1 | grep -q "open" && \
		echo "$(GREEN) Connected$(NC)" || echo "$(RED) Cannot connect$(NC)"
	@printf "  $(YELLOW)API -> Redis:$(NC)    "
	@docker exec $(PROJECT_NAME)-api nc -zv redis 6379 2>&1 | grep -q "open" && \
		echo "$(GREEN) Connected$(NC)" || echo "$(RED) Cannot connect$(NC)"
	@printf "  $(YELLOW)Web -> API:$(NC)      "
	@docker exec $(PROJECT_NAME)-web wget --spider -q http://api:8001/api/health 2>&1 && \
		echo "$(GREEN) Connected$(NC)" || echo "$(RED) Cannot connect$(NC)"
	@echo ""

## Full diagnostic report
debug-full: debug-containers debug-api debug-models debug-file-sync debug-network debug-endpoints
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✓ Full diagnostic completed$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

## Quick diagnostic check (runs script)
# REMOVED: diag - Use 'make debug-full' instead for comprehensive diagnostics

## Troubleshoot common development issues
troubleshoot:
	@echo "$(YELLOW)Available troubleshooting options:$(NC)"
	@echo ""
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh ports$(NC)        - Fix port conflicts"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh cache$(NC)        - Clear all caches"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh permissions$(NC)  - Fix file permissions"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh volumes$(NC)      - Fix volume mounts"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh rebuild$(NC)      - Full rebuild"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh database$(NC)     - Fix MongoDB issues"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh redis$(NC)        - Fix Redis issues"
	@echo "  $(BLUE)./scripts/dev-troubleshoot.sh all$(NC)          - Run all fixes"
	@echo ""

# ============================================================================
# TESTING
# ============================================================================
#
# WHEN TO USE THESE COMMANDS:
#
# During development (quick feedback):
#   make test          - Run both API and web tests inside Docker containers
#                        Fast, consistent, no local setup needed
#
# Before committing (comprehensive):
#   make test-all      - Complete suite with detailed output (backend + frontend)
#                        Runs in .venv (faster than Docker)
#                        Includes: Prompt registry, E2E, model mapping, chat API
#                        Exit code: 0 if all pass, 1 if any fail
#
# Specific component tests:
#   make test-api      - API tests only (pytest with coverage)
#   make test-web      - Frontend tests only (Jest/Vitest)
#   make test-e2e      - E2E tests with Playwright
#
# CI/CD pipelines:
#   make test-all      - Use this for comprehensive validation
#                        Generates reports, exit codes, and test counts
# ============================================================================

## Run all tests (inside Docker containers)
test: test-api test-web
	@echo "$(GREEN) All tests completed$(NC)"

## Run complete test suite (backend + frontend) with detailed output
test-all:
	@echo "$(YELLOW)Running complete test suite...$(NC)"
	@chmod +x scripts/run_all_tests.sh
	@./scripts/run_all_tests.sh

## Run API unit tests
test-api:
	@echo "$(YELLOW)Running API tests...$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec api pytest tests/ -v --cov=src || true

## Run web unit tests
test-web:
	@echo "$(YELLOW)Running web tests...$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec web pnpm test || true

## Run E2E tests
test-e2e: venv-install
	@echo "$(YELLOW)Running E2E tests...$(NC)"
	@pnpm exec playwright test || true

# ============================================================================
# CODE QUALITY
# ============================================================================

## Run linters
lint:
	@echo "$(YELLOW)Running linters...$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec api ruff check . || true
	@$(DOCKER_COMPOSE_DEV) exec web pnpm lint || true

## Fix lint issues
lint-fix:
	@echo "$(YELLOW)Fixing lint issues...$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec api ruff check . --fix || true
	@$(DOCKER_COMPOSE_DEV) exec api ruff format . || true
	@$(DOCKER_COMPOSE_DEV) exec web pnpm lint --fix || true

## Run security scans
security:
	@echo "$(YELLOW)Running security scans...$(NC)"
	@bash scripts/security-audit.sh 2>/dev/null || echo "$(RED)Security script not found$(NC)"

## Run comprehensive security audit (detects secrets, IPs, paths)
security-audit:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)⛨ Security Audit$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Scanning for sensitive information...$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Checking for hardcoded IPs...$(NC)"
	@grep -rn --color=always --include="*.sh" --include="*.yml" --include="*.yaml" --include="Makefile" \
		-E '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' . 2>/dev/null | grep -v "127.0.0.1\|0.0.0.0\|192.168\|your-server-ip" | head -5 || echo "  $(GREEN) No hardcoded production IPs$(NC)"
	@echo ""
	@echo "$(YELLOW)2. Checking for API keys...$(NC)"
	@grep -rn --color=always --include="*.md" --include="*.sh" --include="*.yml" \
		-E 'va-ai-[A-Za-z0-9_-]{40,}' . 2>/dev/null | head -3 || echo "  $(GREEN) No exposed API keys$(NC)"
	@echo ""
	@echo "$(YELLOW)3. Checking for absolute paths...$(NC)"
	@grep -rn --color=always --include="*.sh" --include="*.yml" --include="Makefile" \
		-E '/home/(jf|ubuntu|jazielflo|user)/' . 2>/dev/null | grep -v "your-path\|example\|EXAMPLE" | head -5 || echo "  $(GREEN) No hardcoded paths$(NC)"
	@echo ""
	@echo "$(GREEN) Security audit completed$(NC)"
	@echo ""
	@echo "$(YELLOW)For detailed findings, see: $(NC)$(BLUE)docs/SECURITY_AUDIT_REPORT.md$(NC)"
	@echo ""

## Install git hooks for security checks
install-hooks:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)⛨ Installing Git Hooks$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@if [ -f scripts/git-hooks/pre-commit ]; then \
		echo "$(YELLOW)Installing pre-commit hook...$(NC)"; \
		mkdir -p .git/hooks; \
		cp scripts/git-hooks/pre-commit .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "$(GREEN) Pre-commit hook installed$(NC)"; \
		echo ""; \
		echo "$(YELLOW)The hook will check for:$(NC)"; \
		echo "  • .env files"; \
		echo "  • Real API keys (va-ai-...)"; \
		echo "  • Production IPs"; \
		echo "  • Hardcoded passwords/secrets"; \
		echo "  • Absolute server paths"; \
		echo "  • Large files (>1MB)"; \
		echo ""; \
		echo "$(YELLOW)To bypass (NOT RECOMMENDED):$(NC)"; \
		echo "  git commit --no-verify"; \
		echo ""; \
	else \
		echo "$(RED) Pre-commit hook not found at scripts/git-hooks/pre-commit$(NC)"; \
		exit 1; \
	fi

# ============================================================================
# CLEANUP
# ============================================================================

## Stop and remove containers
clean:
	@echo "$(YELLOW)Cleaning up containers...$(NC)"
	@$(DOCKER_COMPOSE_DEV) down --remove-orphans
	@echo "$(GREEN) Cleanup completed$(NC)"

## Clean including volumes (▲ DATA LOSS)
clean-volumes:
	@echo "$(RED)▲  WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE_DEV) down -v --remove-orphans; \
		echo "$(GREEN) Volumes cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# Removed deprecated clean-docker command (use clean-all instead)

# ============================================================================
# BUILD & PRODUCTION
# ============================================================================

## Build all images
build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --parallel
	@echo "$(GREEN) Build completed$(NC)"

## Start production environment
# REMOVED: prod - Use 'make deploy' or 'make deploy-tar' for actual production deployment

# ============================================================================
# DEPLOYMENT TO PRODUCTION
# ============================================================================
#
# WHEN TO USE THESE COMMANDS:
#
# Regular deployments (recommended):
#   make deploy-quick  - Fastest (~3-5 min), incremental build with cache
#                        Use for: Bug fixes, small features, daily deploys
#
# Production releases (when quality matters):
#   make deploy-clean  - Slowest (~12-15 min), guaranteed fresh build
#                        Use for: Major releases, dependency updates, monthly deploys
#
# Docker Registry workflow (fastest, requires registry setup):
#   make deploy-prod   - Build locally, push to registry, deploy on server (~3 min)
#                        Use for: Teams with Docker Hub/GitHub Packages configured
#
# TAR workflow (no registry needed):
#   make deploy-tar    - Complete automated deployment (~12 min)
#                        Use for: Simple setups, no registry access
#
# After deployment:
#   make clear-cache   - Clear Redis cache and restart web (important!)
#                        Use after: Every deployment to ensure new code loads
# ============================================================================

## Push images to Docker registry (build + tag + push)
push-registry:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Pushing to Docker Registry$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/push-to-registry.sh

## Push without rebuilding (use existing images)
push-registry-fast:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Pushing to Docker Registry (Fast Mode)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/push-to-registry.sh --no-build

## Complete deployment workflow via registry (build+push+deploy)
deploy-prod: push-registry
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✔ Images pushed to registry!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@if [ "$(PROD_SERVER_HOST)" = "your-ssh-user@your-server-ip-here" ]; then \
		echo "$(RED)▲ WARNING: Production server not configured!$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Configure production server in envs/.env.prod:$(NC)"; \
		echo "  PROD_SERVER_IP=your-actual-server-ip"; \
		echo "  PROD_SERVER_USER=your-ssh-user"; \
		echo "  PROD_DEPLOY_PATH=/path/to/deployment"; \
		echo ""; \
		echo "$(YELLOW)Or run: $(NC)$(GREEN)make setup-interactive-prod$(NC)"; \
		echo ""; \
		exit 1; \
	fi
	@echo "$(YELLOW)▸ Deploying from registry (with versioning + rollback):$(NC)"
	@echo ""
	@./scripts/deploy.sh registry --skip-build
	@echo ""

## Versioned deployment with automatic rollback (default: tar method)
deploy:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Versioned Deployment with Rollback$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/deploy.sh tar

## Deploy via tar transfer (no registry needed, ~8-12 min)
deploy-tar:
	@./scripts/deploy.sh tar

## Deploy via Docker registry (fastest if registry configured, ~3-5 min)
deploy-registry:
	@./scripts/deploy.sh registry

## Fast deployment (skip build, use existing images)
deploy-fast:
	@./scripts/deploy.sh tar --skip-build

## Rollback to previous version (automatic)
rollback:
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(YELLOW)▸ Rollback to Previous Version$(NC)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/rollback.sh

## List deployment history and available versions
deploy-history:
	@./scripts/rollback.sh --list

## Check production server status
deploy-status:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Production Server Status$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@if [ -z "$(PROD_SERVER_HOST)" ]; then \
		echo "$(RED)▲ ERROR: Production server not configured!$(NC)"; \
		echo "Run: $(GREEN)make setup-interactive-prod$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(BLUE)Git Status:$(NC)"
	@ssh $(PROD_SERVER_HOST) "cd $(PROD_DEPLOY_PATH) && git log -1 --format='  %h - %s (%ar)'"
	@echo ""
	@echo "$(BLUE)Current Version:$(NC)"
	@ssh $(PROD_SERVER_HOST) "cat $(PROD_DEPLOY_PATH)/.deploy/current_version 2>/dev/null || echo '  Unknown'" | sed 's/^/  /'
	@echo ""
	@echo "$(BLUE)Running Containers:$(NC)"
	@ssh $(PROD_SERVER_HOST) "docker ps --format '  {{.Names}}\t{{.Status}}' --filter 'name=copilotos'" || echo "  No containers running"
	@echo ""
	@echo "$(BLUE)Health Check:$(NC)"
	@ssh $(PROD_SERVER_HOST) "curl -sf http://localhost:8001/api/health | jq -r '\"  API: \" + .status'" || echo "  API: Error"
	@ssh $(PROD_SERVER_HOST) "curl -sf -o /dev/null -w '  Web: HTTP %{http_code}\n' http://localhost:3000" || echo "  Web: Error"
	@echo ""

# ============================================================================
# RESOURCE OPTIMIZATION
# ============================================================================
#
# WHEN TO USE THESE COMMANDS:
#
# Before starting work:
#   make resources              - Check current disk usage (takes 2 seconds)
#                                 Look for "RECLAIMABLE" column
#
# Weekly maintenance:
#   make docker-cleanup         - Safe cleanup (frees 5-15 GB typically)
#                                 Removes: Build cache >7 days, dangling images, stopped containers
#                                 Safe to run: Yes, interactive confirmation for volumes
#
# Monthly deep clean (or when disk is full):
#   make docker-cleanup-aggressive - Deep cleanup (frees 50-70 GB typically)
#                                    Removes: ALL unused images, volumes, build cache
#                                    Warning: Requires explicit "yes" confirmation
#                                    Next build will be slower (rebuilds from scratch)
#
# Production deployments:
#   make deploy-optimized       - Clean + optimized build + deploy + cleanup
#                                 Includes resource limits, multi-stage optimization
#                                 Takes 15-20 min but guarantees minimal image size
#
# Monitoring (continuous):
#   make resources-monitor      - Live view (updates every 2s, Ctrl+C to exit)
#                                 Use when: Debugging memory leaks or CPU spikes
# ============================================================================

## Show Docker resource usage summary
resources:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)▸ Docker Resources Summary$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@echo "$(YELLOW)▸ Docker Disk Usage:$(NC)"
	@docker system df
	@echo ""
	@echo "$(YELLOW)▸ Container Resources:$(NC)"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
	@echo ""
	@echo "$(YELLOW)◆ System Memory:$(NC)"
	@free -h || echo "Command not available on this system"
	@echo ""
	@echo "$(YELLOW)▸ Reclaimable Space:$(NC)"
	@echo "  • Run '$(GREEN)make docker-cleanup$(NC)' to free up space safely"
	@echo "  • Run '$(GREEN)make docker-cleanup-aggressive$(NC)' for deep cleanup"
	@echo ""

## Monitor Docker resources in real-time
resources-monitor:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)▸ Real-time Resource Monitor (Ctrl+C to stop)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@watch -n 2 'docker stats --no-stream'

## Safe Docker cleanup (build cache, dangling images, stopped containers)
docker-cleanup:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)▸ Docker Safe Cleanup$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@chmod +x scripts/docker-cleanup.sh
	@./scripts/docker-cleanup.sh

## Aggressive Docker cleanup (removes all unused images and volumes)
docker-cleanup-aggressive:
	@echo "$(RED)▲  WARNING: This will remove ALL unused Docker images and volumes!$(NC)"
	@echo "$(YELLOW)Active containers will NOT be affected.$(NC)"
	@echo ""
	@read -p "Are you sure? (yes/NO): " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	@echo ""
	@echo "$(YELLOW)Removing all unused images...$(NC)"
	@docker image prune -af
	@echo ""
	@echo "$(YELLOW)Removing all unused volumes...$(NC)"
	@docker volume prune -f
	@echo ""
	@echo "$(YELLOW)Removing all build cache...$(NC)"
	@docker builder prune -af
	@echo ""
	@echo "$(GREEN) Aggressive cleanup completed!$(NC)"
	@echo ""
	@docker system df

## Build images with optimization flags
# REMOVED: build-optimized - Default build already uses optimizations (multi-stage, BUILDKIT, caching)

## Deploy with optimized images (clean build + resource limits)
# REMOVED: deploy-optimized - Use 'make deploy-clean' instead, already includes optimizations

# ============================================================================
# MODEL & CONFIGURATION VALIDATION
# ============================================================================
#
# WHEN TO USE THESE COMMANDS:
#
# After changing model configurations:
#   make check-registry        - Verify if registry.yaml needs rebuild
#   make validate-models       - Check if models are properly configured
#   make rebuild-with-registry - Rebuild API with updated registry.yaml
#
# When models show unexpected behavior:
#   make check-localstorage    - Show localStorage cleanup instructions
#   make troubleshoot-models   - Comprehensive model troubleshooting
#
# Quick fixes:
#   make fix-tools-cache       - Clear localStorage tools cache
#   make fix-stale-container   - Rebuild container with latest files
# ============================================================================

## Check if registry.yaml has changed and container needs rebuild
check-registry:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Registry Configuration Check$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking registry.yaml synchronization...$(NC)"
	@echo ""
	@if [ ! -f apps/api/prompts/registry.yaml ]; then \
		echo "$(RED) registry.yaml not found!$(NC)"; \
		exit 1; \
	fi
	@LOCAL_MD5=$$(md5sum apps/api/prompts/registry.yaml | cut -d' ' -f1); \
	CONTAINER_MD5=$$(docker exec $(PROJECT_NAME)-api md5sum /app/prompts/registry.yaml 2>/dev/null | cut -d' ' -f1); \
	if [ -z "$$CONTAINER_MD5" ]; then \
		echo "$(RED) Cannot check container (not running?)$(NC)"; \
		echo "  Run: $(GREEN)make dev$(NC) first"; \
		exit 1; \
	fi; \
	echo "  Local registry:     $$LOCAL_MD5"; \
	echo "  Container registry: $$CONTAINER_MD5"; \
	echo ""; \
	if [ "$$LOCAL_MD5" = "$$CONTAINER_MD5" ]; then \
		echo "$(GREEN) Registry files are synchronized$(NC)"; \
		echo ""; \
		docker exec $(PROJECT_NAME)-api grep "Saptiva Legacy" /app/prompts/registry.yaml > /dev/null 2>&1 && \
			echo "$(GREEN) Saptiva Legacy is configured$(NC)" || \
			echo "$(YELLOW) Saptiva Legacy not found in registry$(NC)"; \
	else \
		echo "$(RED) Registry files are OUT OF SYNC!$(NC)"; \
		echo ""; \
		echo "$(YELLOW)This means:$(NC)"; \
		echo "  • You changed registry.yaml locally"; \
		echo "  • Container still has OLD version"; \
		echo "  • Models may not work as expected"; \
		echo ""; \
		echo "$(YELLOW)To fix:$(NC)"; \
		echo "  $(GREEN)make rebuild-with-registry$(NC)"; \
		echo ""; \
		exit 1; \
	fi

## Validate model configuration
validate-models:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Model Configuration Validation$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Available models from backend:$(NC)"
	@curl -sf http://localhost:8001/api/models | jq -r '.allowed_models[]' 2>/dev/null || \
		(echo "$(RED) API not responding$(NC)" && exit 1)
	@echo ""
	@echo "$(YELLOW)2. Registry models in container:$(NC)"
	@docker exec $(PROJECT_NAME)-api grep -E "^  \"Saptiva" /app/prompts/registry.yaml | sed 's/://g' | sed 's/"//g'
	@echo ""
	@echo "$(YELLOW)3. Checking model consistency:$(NC)"
	@BACKEND_MODELS=$$(curl -sf http://localhost:8001/api/models | jq -r '.allowed_models[]' 2>/dev/null); \
	for model in Turbo Cortex Ops Legacy Coder; do \
		echo "$$BACKEND_MODELS" | grep -q "Saptiva $$model" && \
			echo "  $(GREEN) Saptiva $$model$(NC)" || \
			echo "  $(RED) Saptiva $$model (missing from allowed_models)$(NC)"; \
	done
	@echo ""

## Rebuild API container with updated registry.yaml
rebuild-with-registry:
	@echo "$(YELLOW)Rebuilding API with updated registry.yaml...$(NC)"
	@echo ""
	@echo "$(BLUE)This will:$(NC)"
	@echo "  1. Build new API image (includes latest registry.yaml)"
	@echo "  2. Stop current API container"
	@echo "  3. Start new container with updated configuration"
	@echo ""
	@$(DOCKER_COMPOSE_DEV) build api
	@$(DOCKER_COMPOSE_DEV) down api
	@$(DOCKER_COMPOSE_DEV) up -d api
	@echo ""
	@echo "$(GREEN) API rebuilt with latest registry.yaml$(NC)"
	@echo ""
	@echo "$(YELLOW)Verifying...$(NC)"
	@sleep 3
	@$(MAKE) --no-print-directory check-registry

## Show localStorage troubleshooting instructions
check-localstorage:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Frontend localStorage Troubleshooting$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Problem:$(NC)"
	@echo "  Frontend caches model settings in browser localStorage"
	@echo "  Old values persist even after code changes"
	@echo ""
	@echo "$(YELLOW)Symptoms:$(NC)"
	@echo "  • web_search tool activates when it shouldn't"
	@echo "  • Model settings don't match code defaults"
	@echo "  • Tools appear enabled without user action"
	@echo ""
	@echo "$(YELLOW)Quick Fix (Option 1 - Clear All):$(NC)"
	@echo "  1. Open browser DevTools (F12)"
	@echo "  2. Go to Console tab"
	@echo "  3. Run: $(GREEN)localStorage.clear(); location.reload()$(NC)"
	@echo ""
	@echo "$(YELLOW)Quick Fix (Option 2 - Edit Specific):$(NC)"
	@echo "  1. Open browser DevTools (F12)"
	@echo "  2. Go to Application → Local Storage → http://localhost:3000"
	@echo "  3. Find key: $(GREEN)copilotos-bridge-store$(NC)"
	@echo "  4. Edit JSON and change:"
	@echo "     $(GREEN)\"toolsEnabled\": {\"web_search\": false, \"deep_research\": false}$(NC)"
	@echo "  5. Refresh page"
	@echo ""
	@echo "$(YELLOW)Quick Fix (Option 3 - Incognito):$(NC)"
	@echo "  • Open app in incognito mode (Ctrl+Shift+N / Cmd+Shift+N)"
	@echo "  • Fresh start, no cached data"
	@echo ""
	@echo "$(YELLOW)Permanent Fix:$(NC)"
	@echo "  See: $(BLUE)docs/COMMON_ISSUES.md$(NC) for migration strategy"
	@echo ""

## Comprehensive model troubleshooting
troubleshoot-models:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)▸ Model Troubleshooting Guide$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW) Running diagnostics...$(NC)"
	@echo ""
	@echo "$(YELLOW)═══ 1. Backend Health ═══$(NC)"
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 && \
		echo "  $(GREEN) API is healthy$(NC)" || \
		(echo "  $(RED) API not responding$(NC)" && echo "  Fix: $(GREEN)make dev$(NC)")
	@echo ""
	@echo "$(YELLOW)═══ 2. Available Models ═══$(NC)"
	@curl -sf http://localhost:8001/api/models | jq -r '.allowed_models[]' | sed 's/^/  /'
	@echo ""
	@echo "$(YELLOW)═══ 3. Registry Configuration ═══$(NC)"
	@$(MAKE) --no-print-directory check-registry 2>&1 | tail -10
	@echo ""
	@echo "$(YELLOW)═══ 4. Recent Errors ═══$(NC)"
	@docker logs $(PROJECT_NAME)-api --tail=20 2>&1 | grep -iE "error|warning|exception" | tail -5 || \
		echo "  $(GREEN) No recent errors$(NC)"
	@echo ""
	@echo "$(YELLOW)═══ Common Issues & Fixes ═══$(NC)"
	@echo ""
	@echo "$(RED)Issue:$(NC) Model shows as 'not available'"
	@echo "  $(GREEN)Fix:$(NC) Check CHAT_ALLOWED_MODELS in envs/.env"
	@echo "  $(GREEN)Fix:$(NC) Run: make rebuild-api"
	@echo ""
	@echo "$(RED)Issue:$(NC) Registry changes not reflected"
	@echo "  $(GREEN)Fix:$(NC) Run: make rebuild-with-registry"
	@echo ""
	@echo "$(RED)Issue:$(NC) Tools activating unexpectedly"
	@echo "  $(GREEN)Fix:$(NC) Run: make check-localstorage"
	@echo ""
	@echo "$(RED)Issue:$(NC) Model using wrong parameters"
	@echo "  $(GREEN)Fix:$(NC) Run: make rebuild-with-registry"
	@echo "  $(GREEN)Verify:$(NC) Run: make validate-models"
	@echo ""
	@echo "$(YELLOW)Full troubleshooting guide:$(NC) $(BLUE)docs/COMMON_ISSUES.md$(NC)"
	@echo ""

## Quick fix: Rebuild container with latest files
# REMOVED: fix-stale-container - Use 'make rebuild-with-registry' directly instead

## Instructions for clearing frontend cache
fix-tools-cache:
	@$(MAKE) check-localstorage

# ============================================================================
# UTILITIES
# ============================================================================

.PHONY: all $(VENV_DIR)
.SECONDARY:
SHELL := /bin/bash
