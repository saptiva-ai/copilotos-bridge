# 🚀 Copilotos Bridge Makefile
# Development-optimized workflow with auto .venv management
.PHONY: help dev prod test test-all clean build lint security shell-api shell-web \
        push-registry push-registry-fast deploy-registry deploy-prod \
        db-migrate db-backup db-restore db-stats db-collections db-fix-drafts \
        redis-stats redis-monitor debug-containers debug-api debug-models \
        debug-file-sync debug-endpoints debug-logs-errors debug-network debug-full \
        diag troubleshoot resources resources-monitor docker-cleanup docker-cleanup-aggressive \
        build-optimized deploy-optimized

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

# Emojis for logs
RED := 🔴
GREEN := 🟢
YELLOW := 🟡
BLUE := 🔵
NC := "" # No Color

# ============================================================================
# DEFAULT & HELP
# ============================================================================

.DEFAULT_GOAL := help

## Show available commands with descriptions
help:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🤖 Copilotos Bridge - Development Command Center$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(GREEN)🚀 Quick Start:$(NC)"
	@echo "  $(YELLOW)make setup$(NC)        First-time setup (env files, .venv, dependencies)"
	@echo "  $(YELLOW)make dev$(NC)          Start development environment (with hot reload)"
	@echo "  $(YELLOW)make create-user$(NC)  Create demo user (username: demo, pass: Demo123!)"
	@echo "  $(YELLOW)make logs$(NC)         View live logs from all services"
	@echo ""
	@echo "$(RED)⚠️  Common Issue: Code Changes Not Reflected?$(NC)"
	@echo "  $(YELLOW)make rebuild-api$(NC)   Rebuild API with --no-cache (fixes Docker cache issues)"
	@echo "  $(YELLOW)make rebuild-all$(NC)   Rebuild all services (when env vars change)"
	@echo "  $(BLUE)Why?$(NC) Docker caches layers. Use --no-cache + down/up to force fresh build."
	@echo ""
	@echo "$(GREEN)💻 Development:$(NC)"
	@echo "  $(YELLOW)make dev$(NC)          Start dev services (docker-compose.dev.yml)"
	@echo "  $(YELLOW)make dev-build$(NC)    Build and start dev services"
	@echo "  $(YELLOW)make stop$(NC)         Stop all services"
	@echo "  $(YELLOW)make restart$(NC)      Restart all services"
	@echo "  $(YELLOW)make logs$(NC)         Follow logs from all services"
	@echo "  $(YELLOW)make logs-api$(NC)     Follow API logs only"
	@echo "  $(YELLOW)make logs-web$(NC)     Follow web logs only"
	@echo "  $(YELLOW)make status$(NC)       Show service status"
	@echo ""
	@echo "$(GREEN)🔐 Authentication & Users:$(NC)"
	@echo "  $(YELLOW)make create-demo-user$(NC)  Create demo user (demo/Demo1234)"
	@echo "  $(YELLOW)make delete-demo-user$(NC)  Delete demo user"
	@echo "  $(YELLOW)make list-users$(NC)        List all users"
	@echo "  $(YELLOW)make test-login$(NC)        Test login with demo credentials"
	@echo "  $(YELLOW)make get-token$(NC)         Get JWT token for demo user"
	@echo "  $(YELLOW)make clear-cache$(NC)       Clear Redis cache"
	@echo ""
	@echo "$(GREEN)🛠️  Container Access:$(NC)"
	@echo "  $(YELLOW)make shell-api$(NC)       Bash shell in API container"
	@echo "  $(YELLOW)make shell-web$(NC)       Shell in web container"
	@echo "  $(YELLOW)make shell-db$(NC)        MongoDB shell"
	@echo "  $(YELLOW)make shell-redis$(NC)     Redis CLI"
	@echo ""
	@echo "$(GREEN)🧪 Testing:$(NC)"
	@echo "  $(YELLOW)make test$(NC)            Run all tests (Docker containers)"
	@echo "  $(YELLOW)make test-all$(NC)        Run complete test suite (backend + frontend)"
	@echo "  $(YELLOW)make test-api$(NC)        Run API unit tests"
	@echo "  $(YELLOW)make test-web$(NC)        Run web unit tests"
	@echo "  $(YELLOW)make test-e2e$(NC)        Run E2E tests with Playwright"
	@echo "  $(YELLOW)make health$(NC)          Check service health"
	@echo ""
	@echo "$(GREEN)🔍 Code Quality:$(NC)"
	@echo "  $(YELLOW)make lint$(NC)            Run linters (Python + TypeScript)"
	@echo "  $(YELLOW)make lint-fix$(NC)        Auto-fix lint issues"
	@echo "  $(YELLOW)make security$(NC)        Run security scans"
	@echo "  $(YELLOW)make verify$(NC)          Full verification (setup, health, auth)"
	@echo ""
	@echo "$(GREEN)🗄️  Database Operations:$(NC)"
	@echo "  $(YELLOW)make db-migrate$(NC)      Run database migrations"
	@echo "  $(YELLOW)make db-backup$(NC)       Backup MongoDB database"
	@echo "  $(YELLOW)make db-restore$(NC)      Restore database from backup"
	@echo "  $(YELLOW)make db-stats$(NC)        Show database statistics"
	@echo "  $(YELLOW)make db-collections$(NC)  List collections and counts"
	@echo "  $(YELLOW)make db-fix-drafts$(NC)   Fix orphaned draft conversations"
	@echo "  $(YELLOW)make redis-stats$(NC)     Show Redis memory and key stats"
	@echo "  $(YELLOW)make redis-monitor$(NC)   Monitor Redis commands in real-time"
	@echo ""
	@echo "$(GREEN)🐛 Debugging & Diagnostics:$(NC)"
	@echo "  $(YELLOW)make diag$(NC)            Quick diagnostic check"
	@echo "  $(YELLOW)make troubleshoot$(NC)    Show troubleshooting options"
	@echo "  $(YELLOW)make debug-full$(NC)      Complete diagnostic report"
	@echo "  $(YELLOW)make debug-containers$(NC) Container status and resources"
	@echo "  $(YELLOW)make debug-api$(NC)       API configuration and packages"
	@echo "  $(YELLOW)make debug-models$(NC)    Inspect model fields"
	@echo "  $(YELLOW)make debug-file-sync$(NC) Check file sync (volume mounts)"
	@echo "  $(YELLOW)make debug-network$(NC)   Test container connectivity"
	@echo "  $(YELLOW)make debug-endpoints$(NC) Test API endpoints"
	@echo "  $(YELLOW)make debug-logs-errors$(NC) Show recent errors in logs"
	@echo ""
	@echo "$(GREEN)🧹 Cleanup:$(NC)"
	@echo "  $(YELLOW)make clean$(NC)           Stop and remove containers"
	@echo "  $(YELLOW)make clean-volumes$(NC)   Clean including volumes (⚠️  DATA LOSS)"
	@echo "  $(YELLOW)make clean-all$(NC)       Deep clean (Docker system prune)"
	@echo ""
	@echo "$(GREEN)📊 Resource Optimization:$(NC)"
	@echo "  $(YELLOW)make resources$(NC)                Show Docker resource usage summary"
	@echo "  $(YELLOW)make resources-monitor$(NC)        Real-time resource monitoring"
	@echo "  $(YELLOW)make docker-cleanup$(NC)           Safe cleanup (build cache, dangling images)"
	@echo "  $(YELLOW)make docker-cleanup-aggressive$(NC) Aggressive cleanup (⚠️  removes unused images)"
	@echo "  $(YELLOW)make build-optimized$(NC)          Build with optimized Dockerfiles"
	@echo "  $(YELLOW)make deploy-optimized$(NC)         Deploy with optimized images"
	@echo ""
	@echo "$(GREEN)📦 Build & Deploy:$(NC)"
	@echo "  $(YELLOW)make build$(NC)                Build all images"
	@echo "  $(YELLOW)make prod$(NC)                 Start production environment"
	@echo ""
	@echo "$(GREEN)🚀 Quick Deploy (Recommended):$(NC)"
	@echo "  $(YELLOW)make deploy-quick$(NC)         ⚡ Ultra-fast (incremental build, ~3-5 min)"
	@echo "  $(YELLOW)make deploy-clean$(NC)         🧹 Clean build (--no-cache, ~12-15 min, guaranteed fresh)"
	@echo "  $(YELLOW)make deploy-tar-fast$(NC)      📦 Fast (skip build, use existing images)"
	@echo "  $(YELLOW)make deploy-status$(NC)        📊 Check production server status"
	@echo ""
	@echo "$(GREEN)📦 Full Deploy Options:$(NC)"
	@echo "  $(YELLOW)make deploy-tar$(NC)           Complete tar deployment (build+transfer+deploy)"
	@echo "  $(YELLOW)make deploy-build-only$(NC)    Build images only (no deploy)"
	@echo "  $(YELLOW)make deploy-server-only$(NC)   Deploy to server only (assumes tar files exist)"
	@echo ""
	@echo "$(GREEN)🔄 Registry Deploy (Advanced):$(NC)"
	@echo "  $(YELLOW)make push-registry$(NC)        Push images to Docker registry"
	@echo "  $(YELLOW)make push-registry-fast$(NC)   Push without rebuilding"
	@echo "  $(YELLOW)make deploy-registry$(NC)      Deploy from registry (on server)"
	@echo "  $(YELLOW)make deploy-prod$(NC)          Complete workflow (build+push+guide)"
	@echo ""
	@echo "$(GREEN)🧹 Maintenance:$(NC)"
	@echo "  $(YELLOW)make clear-cache$(NC)          Clear server cache (Redis + restart)"
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  Demo Credentials: $(NC)$(YELLOW)demo / Demo1234$(NC)"
	@echo "$(BLUE)  Frontend:        $(NC)$(YELLOW)http://localhost:3000$(NC)"
	@echo "$(BLUE)  API:             $(NC)$(YELLOW)http://localhost:8001$(NC)"
	@echo "$(BLUE)  API Docs:        $(NC)$(YELLOW)http://localhost:8001/docs$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# ============================================================================
# SETUP & INITIALIZATION
# ============================================================================

## Create Python virtual environment
$(VENV_DIR):
	@echo "$(YELLOW)Creating Python virtual environment...$(NC)"
	@$(PYTHON_SYS) -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip setuptools wheel
	@echo "$(GREEN)✓ Virtual environment created$(NC)"

## Install Python dependencies
venv-install: $(VENV_DIR)
	@echo "$(YELLOW)Installing Python dependencies...$(NC)"
	@if [ -f apps/api/requirements.txt ]; then \
		$(PIP) install -r apps/api/requirements.txt; \
	fi
	@echo "$(GREEN)✓ Python dependencies installed$(NC)"

## Ensure environment file exists
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

## First-time setup: env files, venv, permissions
setup: ensure-env venv-install
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🎉 Setup completed!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Review $(DEV_ENV_FILE) and add your API keys"
	@echo "  2. Run: $(GREEN)make dev$(NC)"
	@echo "  3. Run: $(GREEN)make create-demo-user$(NC)"
	@echo "  4. Visit: $(BLUE)http://localhost:3000$(NC)"
	@echo ""

# ============================================================================
# DEVELOPMENT
# ============================================================================

## Start development environment with hot reload
## Note: .next uses anonymous Docker volume to prevent permission issues
dev: ensure-env
	@echo "$(YELLOW)Starting development environment...$(NC)"
	@$(DOCKER_COMPOSE_DEV) up -d
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  ✓ Services started$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "  $(BLUE)Frontend:$(NC) $(YELLOW)http://localhost:3000$(NC)"
	@echo "  $(BLUE)API:$(NC)      $(YELLOW)http://localhost:8001$(NC)"
	@echo "  $(BLUE)Docs:$(NC)     $(YELLOW)http://localhost:8001/docs$(NC)"
	@echo ""
	@echo "$(YELLOW)Waiting for services to be healthy...$(NC)"
	@sleep 10
	@$(MAKE) --no-print-directory health

## Build and start development environment
dev-build: ensure-env
	@echo "$(YELLOW)Building and starting development environment...$(NC)"
	@$(DOCKER_COMPOSE_DEV) up -d --build
	@echo "$(GREEN)✓ Services built and started$(NC)"
	@sleep 10
	@$(MAKE) --no-print-directory health

## Rebuild API container without cache
rebuild-api: ensure-env
	@echo "$(YELLOW)Rebuilding API container without cache...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --no-cache api
	@$(DOCKER_COMPOSE_DEV) down api
	@$(DOCKER_COMPOSE_DEV) up -d api
	@echo "$(GREEN)✓ API container rebuilt and restarted$(NC)"
	@echo "$(BLUE)ℹ️  Container recreated with fresh code and env vars$(NC)"

## Rebuild all containers without cache
rebuild-all: ensure-env
	@echo "$(YELLOW)Rebuilding all containers without cache...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --no-cache
	@$(DOCKER_COMPOSE_DEV) down
	@$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN)✓ All containers rebuilt and restarted$(NC)"
	@echo "$(BLUE)ℹ️  All containers recreated with fresh code and env vars$(NC)"

## Clean Next.js cache and volumes
## Removes both host .next directory and Docker anonymous volumes
clean-next: stop
	@echo "$(YELLOW)Cleaning Next.js cache and volumes...$(NC)"
	@rm -rf apps/web/.next 2>/dev/null || true
	@docker volume ls -qf "dangling=true" | xargs -r docker volume rm 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_next_cache $(PROJECT_NAME)_next_standalone_cache $(PROJECT_NAME)_web-next-cache 2>/dev/null || true
	@echo "$(GREEN)✓ Next.js cache cleaned$(NC)"

## Clean all caches and volumes
clean-cache: stop
	@echo "$(YELLOW)Cleaning all caches and volumes...$(NC)"
	@rm -rf apps/web/.next 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_next_cache $(PROJECT_NAME)_next_standalone_cache $(PROJECT_NAME)_web-next-cache 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_mongodb_data $(PROJECT_NAME)_mongodb_config $(PROJECT_NAME)_redis_data 2>/dev/null || echo "$(YELLOW)⚠ Database volumes not removed (use 'make clean-all' to remove them)$(NC)"
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

## Nuclear option: clean everything including database
clean-all: stop
	@echo "$(RED)⚠ WARNING: This will delete ALL data including database!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Cleaning everything...$(NC)"; \
		rm -rf apps/web/.next 2>/dev/null || true; \
		$(DOCKER_COMPOSE_DEV) down -v --remove-orphans; \
		docker volume prune -f; \
		echo "$(GREEN)✓ Everything cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

## Fresh start: clean and rebuild
fresh: clean-next dev
	@echo "$(GREEN)✓ Fresh start completed!$(NC)"

## Stop all services
stop:
	@echo "$(YELLOW)Stopping services...$(NC)"
	@$(DOCKER_COMPOSE_DEV) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

## Restart all services
restart:
	@echo "$(YELLOW)Restarting services...$(NC)"
	@$(DOCKER_COMPOSE_DEV) restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

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
	@echo "$(BLUE)  Health Check$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@printf "  $(YELLOW)API Health:$(NC)        "
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 && \
		echo "$(GREEN)✓ Healthy$(NC)" || \
		echo "$(RED)✗ Not responding$(NC)"
	@printf "  $(YELLOW)Frontend:$(NC)          "
	@curl -sf http://localhost:3000/healthz > /dev/null 2>&1 && \
		echo "$(GREEN)✓ Healthy$(NC)" || \
		echo "$(RED)✗ Not responding$(NC)"
	@printf "  $(YELLOW)MongoDB:$(NC)           "
	@$(DOCKER_COMPOSE_DEV) exec -T mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1 && \
		echo "$(GREEN)✓ Connected$(NC)" || \
		echo "$(RED)✗ Not connected$(NC)"
	@printf "  $(YELLOW)Redis:$(NC)             "
	@$(DOCKER_COMPOSE_DEV) exec -T redis redis-cli ping > /dev/null 2>&1 && \
		echo "$(GREEN)✓ Connected$(NC)" || \
		echo "$(RED)✗ Not connected$(NC)"
	@echo ""

## Full verification (setup + health + auth)
verify: health
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  Verification Tests$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@bash scripts/verify-deployment.sh 2>/dev/null || echo "$(YELLOW)⚠ Run 'bash scripts/verify-deployment.sh' for full verification$(NC)"

# ============================================================================
# AUTHENTICATION & USERS
# ============================================================================

## Create demo user (username: demo, password: Demo1234)
create-demo-user:
	@echo "$(YELLOW)Creating demo user...$(NC)"
	@echo ""
	@echo "  $(BLUE)Username:$(NC) $(GREEN)demo$(NC)"
	@echo "  $(BLUE)Password:$(NC) $(GREEN)Demo1234$(NC)"
	@echo "  $(BLUE)Email:$(NC)    $(GREEN)demo@example.com$(NC)"
	@echo ""
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 || \
		(echo "$(RED)✗ API not ready. Run 'make dev' first$(NC)" && exit 1)
	@curl -X POST http://localhost:8001/api/auth/register \
		-H "Content-Type: application/json" \
		-d '{"username":"demo","email":"demo@example.com","password":"Demo1234"}' \
		2>/dev/null | grep -q "access_token" && \
		echo "$(GREEN)✓ Demo user created successfully!$(NC)" || \
		(echo "$(YELLOW)⚠ User may already exist. Try 'make delete-demo-user' first$(NC)" && exit 1)
	@echo ""
	@echo "$(GREEN)You can now login at:$(NC) $(BLUE)http://localhost:3000/login$(NC)"

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
asyncio.run(main())" 2>&1 | grep -E "Deleted" || echo "$(RED)✗ Failed to delete user$(NC)"
	@echo "$(GREEN)✓ Demo user deleted$(NC)"
	@echo "$(YELLOW)Run 'make clear-cache' to clear Redis cache$(NC)"

## List all users in database
list-users:
	@echo "$(BLUE)Database Users:$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec mongodb mongosh copilotos \
		--eval "db.users.find({}, {username: 1, email: 1, is_active: 1, created_at: 1}).forEach(printjson)" \
		--quiet 2>/dev/null || echo "$(RED)✗ Cannot connect to database$(NC)"

## Test login with demo credentials
test-login:
	@echo "$(YELLOW)Testing login with demo credentials...$(NC)"
	@curl -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"demo","password":"Demo1234"}' \
		2>/dev/null | grep -q "access_token" && \
		echo "$(GREEN)✓ Login successful!$(NC)" || \
		(echo "$(RED)✗ Login failed$(NC)" && echo "$(YELLOW)Try: make clear-cache && make delete-demo-user && make create-demo-user$(NC)")

## Clear server cache (Redis + restart web container) - For production deployments
clear-cache:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🧹 Clearing Server Cache$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/clear-server-cache.sh

## Clear local Redis cache (for development)
clear-redis-local:
	@echo "$(YELLOW)Clearing local Redis cache...$(NC)"
	@docker exec $(PROJECT_NAME)-redis redis-cli -a redis_password_change_me FLUSHALL 2>&1 | grep -q "OK" && \
		echo "$(GREEN)✓ Redis cache cleared$(NC)" || \
		echo "$(RED)✗ Failed to clear cache$(NC)"

## Get JWT token for demo user
get-token:
	@echo "$(YELLOW)Getting JWT token for demo user...$(NC)"
	@TOKEN=$$(curl -s -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"demo","password":"Demo1234"}' | \
		grep -o '"access_token":"[^"]*"' | cut -d'"' -f4); \
	if [ -n "$$TOKEN" ]; then \
		echo "$(GREEN)✓ Token obtained$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Export to use in requests:$(NC)"; \
		echo "  export TOKEN=\"$$TOKEN\""; \
		echo ""; \
		echo "$(YELLOW)Example usage:$(NC)"; \
		echo "  curl -H \"Authorization: Bearer \$$TOKEN\" http://localhost:8001/api/chat"; \
	else \
		echo "$(RED)✗ Failed to get token$(NC)"; \
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
		echo "$(GREEN)✓ Migration completed$(NC)"; \
	else \
		echo "$(RED)✗ Migration script not found$(NC)"; \
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
	echo "$(GREEN)✓ Backup created: $$BACKUP_FILE$(NC)"

## Restore MongoDB database from backup
db-restore:
	@echo "$(RED)⚠️  WARNING: This will restore database from backup!$(NC)"
	@read -p "Backup file path: " BACKUP_FILE; \
	if [ ! -f "$$BACKUP_FILE" ]; then \
		echo "$(RED)✗ Backup file not found$(NC)"; \
		exit 1; \
	fi; \
	docker cp $$BACKUP_FILE $(PROJECT_NAME)-mongodb:/tmp/restore.archive; \
	docker exec $(PROJECT_NAME)-mongodb mongorestore \
		--uri="mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin" \
		--archive=/tmp/restore.archive \
		--drop; \
	echo "$(GREEN)✓ Database restored$(NC)"

## Show database statistics
db-stats:
	@echo "$(BLUE)Database Statistics:$(NC)"
	@echo ""
	@$(DOCKER_COMPOSE_DEV) exec mongodb mongosh copilotos \
		--eval "db.stats()" \
		--quiet 2>/dev/null || echo "$(RED)✗ Cannot connect to database$(NC)"

## List all collections and document counts
db-collections:
	@echo "$(BLUE)Collections:$(NC)"
	@echo ""
	@$(DOCKER_COMPOSE_DEV) exec mongodb mongosh copilotos \
		--eval "db.getCollectionNames().forEach(function(c) { print(c + ': ' + db[c].countDocuments({})); })" \
		--quiet 2>/dev/null || echo "$(RED)✗ Cannot connect to database$(NC)"

## Fix orphaned draft conversations
db-fix-drafts:
	@echo "$(YELLOW)Fixing orphaned draft conversations...$(NC)"
	@if [ -f scripts/fix-orphaned-drafts.py ]; then \
		docker cp scripts/fix-orphaned-drafts.py $(PROJECT_NAME)-api:/tmp/; \
		docker exec $(PROJECT_NAME)-api python3 /tmp/fix-orphaned-drafts.py; \
		echo "$(GREEN)✓ Drafts fixed$(NC)"; \
	else \
		echo "$(RED)✗ Fix script not found$(NC)"; \
	fi

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
	@echo "$(BLUE)  Container Debug Information$(NC)"
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
	@echo "$(BLUE)  API Container Debug$(NC)"
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
	@echo "$(BLUE)  Model Field Inspection$(NC)"
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
" 2>/dev/null || echo "$(RED)✗ Failed to inspect model$(NC)"
	@echo ""

## Verify file checksums inside container vs local
debug-file-sync:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  File Synchronization Check$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking models/chat.py:$(NC)"
	@LOCAL_MD5=$$(md5sum apps/api/src/models/chat.py | cut -d' ' -f1); \
	CONTAINER_MD5=$$(docker exec $(PROJECT_NAME)-api md5sum /app/src/models/chat.py | cut -d' ' -f1); \
	echo "  Local:     $$LOCAL_MD5"; \
	echo "  Container: $$CONTAINER_MD5"; \
	if [ "$$LOCAL_MD5" = "$$CONTAINER_MD5" ]; then \
		echo "  $(GREEN)✓ Files match$(NC)"; \
	else \
		echo "  $(RED)✗ Files differ!$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Checking routers/conversations.py:$(NC)"
	@LOCAL_MD5=$$(md5sum apps/api/src/routers/conversations.py | cut -d' ' -f1); \
	CONTAINER_MD5=$$(docker exec $(PROJECT_NAME)-api md5sum /app/src/routers/conversations.py | cut -d' ' -f1); \
	echo "  Local:     $$LOCAL_MD5"; \
	echo "  Container: $$CONTAINER_MD5"; \
	if [ "$$LOCAL_MD5" = "$$CONTAINER_MD5" ]; then \
		echo "  $(GREEN)✓ Files match$(NC)"; \
	else \
		echo "  $(RED)✗ Files differ!$(NC)"; \
	fi
	@echo ""

## Test API endpoints with authentication
debug-endpoints:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  API Endpoint Testing$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@printf "  $(YELLOW)/api/health:$(NC)       "
	@curl -sf http://localhost:8001/api/health > /dev/null 2>&1 && \
		echo "$(GREEN)✓ OK$(NC)" || echo "$(RED)✗ FAIL$(NC)"
	@printf "  $(YELLOW)/api/models:$(NC)       "
	@curl -sf http://localhost:8001/api/models > /dev/null 2>&1 && \
		echo "$(GREEN)✓ OK$(NC)" || echo "$(RED)✗ FAIL$(NC)"
	@echo ""
	@echo "$(YELLOW)Testing authenticated endpoints...$(NC)"
	@TOKEN=$$(curl -s -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"demo","password":"Demo1234"}' 2>/dev/null | \
		grep -o '"access_token":"[^"]*"' | cut -d'"' -f4); \
	if [ -n "$$TOKEN" ]; then \
		echo "  $(GREEN)✓ Authentication successful$(NC)"; \
		printf "  $(YELLOW)/api/sessions:$(NC)     "; \
		curl -sf -H "Authorization: Bearer $$TOKEN" \
			"http://localhost:8001/api/sessions?limit=1" > /dev/null 2>&1 && \
			echo "$(GREEN)✓ OK$(NC)" || echo "$(RED)✗ FAIL$(NC)"; \
		printf "  $(YELLOW)/api/conversations:$(NC) "; \
		curl -sf -H "Authorization: Bearer $$TOKEN" \
			"http://localhost:8001/api/conversations?limit=1" > /dev/null 2>&1 && \
			echo "$(GREEN)✓ OK$(NC)" || echo "$(RED)✗ FAIL$(NC)"; \
	else \
		echo "  $(RED)✗ Authentication failed$(NC)"; \
		echo "  $(YELLOW)Run 'make create-demo-user' first$(NC)"; \
	fi
	@echo ""

## Show recent API logs with errors highlighted
debug-logs-errors:
	@echo "$(YELLOW)Recent API errors (last 50 lines):$(NC)"
	@$(DOCKER_COMPOSE_DEV) logs --tail=50 api 2>&1 | grep -iE "error|exception|traceback|failed" || \
		echo "$(GREEN)✓ No recent errors found$(NC)"

## Network debugging - show container connectivity
debug-network:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  Network Connectivity$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Testing container-to-container connectivity:$(NC)"
	@printf "  $(YELLOW)API -> MongoDB:$(NC)  "
	@docker exec $(PROJECT_NAME)-api nc -zv mongodb 27017 2>&1 | grep -q "open" && \
		echo "$(GREEN)✓ Connected$(NC)" || echo "$(RED)✗ Cannot connect$(NC)"
	@printf "  $(YELLOW)API -> Redis:$(NC)    "
	@docker exec $(PROJECT_NAME)-api nc -zv redis 6379 2>&1 | grep -q "open" && \
		echo "$(GREEN)✓ Connected$(NC)" || echo "$(RED)✗ Cannot connect$(NC)"
	@printf "  $(YELLOW)Web -> API:$(NC)      "
	@docker exec $(PROJECT_NAME)-web wget --spider -q http://api:8001/api/health 2>&1 && \
		echo "$(GREEN)✓ Connected$(NC)" || echo "$(RED)✗ Cannot connect$(NC)"
	@echo ""

## Full diagnostic report
debug-full: debug-containers debug-api debug-models debug-file-sync debug-network debug-endpoints
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  ✓ Full diagnostic completed$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

## Quick diagnostic check (runs script)
diag:
	@bash scripts/quick-diagnostic.sh

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

## Run all tests (inside Docker containers)
test: test-api test-web
	@echo "$(GREEN)✓ All tests completed$(NC)"

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

# ============================================================================
# CLEANUP
# ============================================================================

## Stop and remove containers
clean:
	@echo "$(YELLOW)Cleaning up containers...$(NC)"
	@$(DOCKER_COMPOSE_DEV) down --remove-orphans
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

## Clean including volumes (⚠️ DATA LOSS)
clean-volumes:
	@echo "$(RED)⚠️  WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE_DEV) down -v --remove-orphans; \
		echo "$(GREEN)✓ Volumes cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

## Deep clean (Docker system prune) - DEPRECATED, use clean-all above
clean-docker: clean
	@echo "$(YELLOW)Deep cleaning Docker resources...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)✓ Deep cleanup completed$(NC)"

# ============================================================================
# BUILD & PRODUCTION
# ============================================================================

## Build all images
build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	@$(DOCKER_COMPOSE_DEV) build --parallel
	@echo "$(GREEN)✓ Build completed$(NC)"

## Start production environment
prod:
	@echo "$(YELLOW)Starting production environment...$(NC)"
	@$(DOCKER_COMPOSE_BASE) --profile production up -d --build
	@echo "$(GREEN)✓ Production environment started$(NC)"

# ============================================================================
# DEPLOYMENT TO PRODUCTION
# ============================================================================

## Push images to Docker registry (build + tag + push)
push-registry:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  📤 Pushing to Docker Registry$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/push-to-registry.sh

## Push without rebuilding (use existing images)
push-registry-fast:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  📤 Pushing to Docker Registry (Fast Mode)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/push-to-registry.sh --no-build

## Deploy from registry on production server (run on server)
deploy-registry:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🚀 Deploying from Docker Registry$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/deploy-from-registry.sh

## Complete deployment workflow (local: build+push, then instructions)
deploy-prod: push-registry
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  ✅ Images pushed to registry!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)📋 Next Steps (on production server):$(NC)"
	@echo ""
	@echo "  $(BLUE)ssh jf@34.42.214.246$(NC)"
	@echo "  $(BLUE)cd /home/jf/copilotos-bridge$(NC)"
	@echo "  $(BLUE)git pull origin main$(NC)"
	@echo "  $(BLUE)make deploy-registry$(NC)"
	@echo ""
	@echo "$(YELLOW)Or use the deploy script directly:$(NC)"
	@echo "  $(BLUE)./scripts/deploy-from-registry.sh$(NC)"
	@echo ""

## Deploy using tar file transfer (automated, no registry needed)
deploy-tar:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  📦 Deploying with TAR Transfer$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/deploy-with-tar.sh

## Deploy tar (skip build, use existing images)
deploy-tar-fast:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  📦 Deploying with TAR (Fast Mode)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/deploy-with-tar.sh --skip-build

## Ultra-fast deployment (incremental build + parallel transfer)
deploy-quick:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  ⚡ Quick Deploy (Incremental Build)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@./scripts/deploy-with-tar.sh --incremental

## Full clean build deployment (guaranteed fresh compilation)
deploy-clean:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🧹 Clean Deploy (Full Rebuild, --no-cache)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(YELLOW)⚠  This will take ~12-15 minutes but guarantees fresh compilation$(NC)"
	@echo ""
	@./scripts/deploy-with-tar.sh

## Build only (no deploy) - useful for testing
deploy-build-only:
	@echo "$(YELLOW)Building images with cache...$(NC)"
	@cd infra && env UID=$(LOCAL_UID) GID=$(LOCAL_GID) docker compose build api web
	@docker tag infra-api:latest copilotos-api:latest
	@docker tag infra-web:latest copilotos-web:latest
	@echo "$(GREEN)✓ Build completed$(NC)"

## Deploy only (assumes images already built and exported)
deploy-server-only:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🚀 Server-Side Deploy Only$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@ssh jf@34.42.214.246 "cd /home/jf/copilotos-bridge/infra && docker compose down && \
		cd /home/jf/copilotos-bridge && \
		gunzip -c copilotos-api.tar.gz | docker load && \
		gunzip -c copilotos-web.tar.gz | docker load && \
		cd infra && docker compose up -d && \
		sleep 10 && curl -sS http://localhost:8001/api/health | jq '.'"

## Check deployment status on server
deploy-status:
	@echo "$(BLUE)Production Server Status:$(NC)"
	@echo ""
	@ssh jf@34.42.214.246 "echo '=== Git Status ===' && cd /home/jf/copilotos-bridge && git log -1 --format='%h - %s (%ar)' && echo && echo '=== Containers ===' && docker ps --format 'table {{.Names}}\t{{.Status}}' | grep copilotos && echo && echo '=== API Health ===' && curl -sS http://localhost:8001/api/health | jq '.'"

# ============================================================================
# RESOURCE OPTIMIZATION
# ============================================================================

## Show Docker resource usage summary
resources:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)  📊 Docker Resources Summary$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@echo "$(YELLOW)🐳 Docker Disk Usage:$(NC)"
	@docker system df
	@echo ""
	@echo "$(YELLOW)💾 Container Resources:$(NC)"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
	@echo ""
	@echo "$(YELLOW)💡 System Memory:$(NC)"
	@free -h || echo "Command not available on this system"
	@echo ""
	@echo "$(YELLOW)🧹 Reclaimable Space:$(NC)"
	@echo "  • Run '$(GREEN)make docker-cleanup$(NC)' to free up space safely"
	@echo "  • Run '$(GREEN)make docker-cleanup-aggressive$(NC)' for deep cleanup"
	@echo ""

## Monitor Docker resources in real-time
resources-monitor:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)  📊 Real-time Resource Monitor (Ctrl+C to stop)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@watch -n 2 'docker stats --no-stream'

## Safe Docker cleanup (build cache, dangling images, stopped containers)
docker-cleanup:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)  🧹 Docker Safe Cleanup$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@chmod +x scripts/docker-cleanup.sh
	@./scripts/docker-cleanup.sh

## Aggressive Docker cleanup (removes all unused images and volumes)
docker-cleanup-aggressive:
	@echo "$(RED)⚠️  WARNING: This will remove ALL unused Docker images and volumes!$(NC)"
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
	@echo "$(GREEN)✓ Aggressive cleanup completed!$(NC)"
	@echo ""
	@docker system df

## Build images with optimization flags
build-optimized:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)  🏗️  Building Optimized Docker Images$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@echo "$(YELLOW)Optimizations enabled:$(NC)"
	@echo "  • Multi-stage builds"
	@echo "  • Alpine base images where possible"
	@echo "  • Build cache utilization"
	@echo "  • Layer optimization"
	@echo ""
	@echo "$(YELLOW)Building API (FastAPI)...$(NC)"
	@$(DOCKER_COMPOSE_BASE) build --build-arg BUILDKIT_INLINE_CACHE=1 api
	@echo ""
	@echo "$(YELLOW)Building Web (Next.js)...$(NC)"
	@$(DOCKER_COMPOSE_BASE) build --build-arg BUILDKIT_INLINE_CACHE=1 web
	@echo ""
	@echo "$(GREEN)✓ Optimized images built successfully!$(NC)"
	@echo ""
	@echo "$(YELLOW)Image sizes:$(NC)"
	@docker images | grep -E "copilotos-(api|web)" | grep latest

## Deploy with optimized images (clean build + resource limits)
deploy-optimized:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo "$(BLUE)  🚀 Optimized Deployment Workflow$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $(NC)"
	@echo ""
	@echo "$(YELLOW)Step 1: Cleanup old artifacts...$(NC)"
	@docker builder prune -af --filter "until=168h" || true
	@echo ""
	@echo "$(YELLOW)Step 2: Building optimized images...$(NC)"
	@$(MAKE) build-optimized
	@echo ""
	@echo "$(YELLOW)Step 3: Deploying with resource limits...$(NC)"
	@$(MAKE) deploy-clean
	@echo ""
	@echo "$(GREEN)✓ Optimized deployment completed!$(NC)"
	@echo ""
	@echo "$(YELLOW)Post-deployment cleanup...$(NC)"
	@docker image prune -f
	@echo ""
	@$(MAKE) resources

# ============================================================================
# UTILITIES
# ============================================================================

.PHONY: all $(VENV_DIR)
.SECONDARY:
SHELL := /bin/bash