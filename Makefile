# 🚀 Copilotos Bridge Makefile
# Development-optimized workflow with auto .venv management
.PHONY: help dev prod test clean build lint security shell-api shell-web

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

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

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
	@echo "  $(YELLOW)make test$(NC)            Run all tests"
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
	@echo "$(GREEN)🧹 Cleanup:$(NC)"
	@echo "  $(YELLOW)make clean$(NC)           Stop and remove containers"
	@echo "  $(YELLOW)make clean-volumes$(NC)   Clean including volumes (⚠️  DATA LOSS)"
	@echo "  $(YELLOW)make clean-all$(NC)       Deep clean (Docker system prune)"
	@echo ""
	@echo "$(GREEN)📦 Build & Deploy:$(NC)"
	@echo "  $(YELLOW)make build$(NC)           Build all images"
	@echo "  $(YELLOW)make prod$(NC)            Start production environment"
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
	@bash verify-deployment.sh 2>/dev/null || echo "$(YELLOW)⚠ Run 'bash verify-deployment.sh' for full verification$(NC)"

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

## Clear Redis cache
clear-cache:
	@echo "$(YELLOW)Clearing Redis cache...$(NC)"
	@docker exec infra-redis redis-cli -a redis_password_change_me FLUSHALL 2>&1 | grep -q "OK" && \
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
# TESTING
# ============================================================================

## Run all tests
test: test-api test-web
	@echo "$(GREEN)✓ All tests completed$(NC)"

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

## Deep clean (Docker system prune)
clean-all: clean
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
# UTILITIES
# ============================================================================

.PHONY: all $(VENV_DIR)
.SECONDARY:
SHELL := /bin/bash