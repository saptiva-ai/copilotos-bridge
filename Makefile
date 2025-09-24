# ========================================
# COPILOTOS BRIDGE MAKEFILE
# ========================================
.PHONY: help dev prod test clean build lint security shell-api shell-web

# Colors for output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
NC := \033[0m

# Configuration
COMPOSE_FILE := infra/docker-compose.yml
PROJECT_NAME := infra

## Show available commands
help:
	@echo "$(GREEN)Copilotos Bridge - Available Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "  $(BLUE)make dev$(NC)         Start development environment"
	@echo "  $(BLUE)make logs$(NC)        Follow logs from all services"
	@echo "  $(BLUE)make stop$(NC)        Stop all services"
	@echo "  $(BLUE)make restart$(NC)     Restart all services"
	@echo "  $(BLUE)make shell-api$(NC)   Shell into API container"
	@echo "  $(BLUE)make shell-web$(NC)   Shell into Web container"
	@echo ""
	@echo "$(YELLOW)Testing & Quality:$(NC)"
	@echo "  $(BLUE)make test$(NC)        Run all tests"
	@echo "  $(BLUE)make test-unit$(NC)   Run unit tests only"
	@echo "  $(BLUE)make test-e2e$(NC)    Run end-to-end tests"
	@echo "  $(BLUE)make lint$(NC)        Run linters"
	@echo "  $(BLUE)make security$(NC)    Run security scans"
	@echo ""
	@echo "$(YELLOW)Build & Deploy:$(NC)"
	@echo "  $(BLUE)make build$(NC)       Build all Docker images"
	@echo "  $(BLUE)make prod$(NC)        Deploy production environment"
	@echo "  $(BLUE)make clean$(NC)       Clean up containers and volumes"
	@echo ""
	@echo "$(YELLOW)Utilities:$(NC)"
	@echo "  $(BLUE)make health$(NC)      Check service health"
	@echo "  $(BLUE)make setup$(NC)       Setup development environment"
	@echo ""
	@echo "$(YELLOW)User Management:$(NC)"
	@echo "  $(BLUE)make create-demo-user$(NC)  Create demo user for testing"
	@echo "  $(BLUE)make list-users$(NC)        List all users in database"
	@echo "  $(BLUE)make delete-demo-user$(NC)  Delete demo user"

# ========================================
# DEVELOPMENT
# ========================================

## Start development environment
dev:
	@echo "$(GREEN)Starting development environment...$(NC)"
	@docker compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)Services started$(NC)"
	@echo "$(BLUE)Frontend: http://localhost:3000$(NC)"
	@echo "$(BLUE)API: http://localhost:8001$(NC)"
	@make --no-print-directory health

## Follow logs from all services
logs:
	@docker compose -f $(COMPOSE_FILE) logs -f

## Stop all services
stop:
	@echo "$(YELLOW)Stopping services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down

## Restart all services
restart:
	@echo "$(YELLOW)Restarting services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) restart

## Shell into API container
shell-api:
	@docker exec -it $(PROJECT_NAME)-api bash

## Shell into Web container
shell-web:
	@docker exec -it $(PROJECT_NAME)-web sh

## Check service health
health:
	@echo "$(YELLOW)Checking service health...$(NC)"
	@echo ""
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(YELLOW)API Health Check:$(NC)"
	@curl -sf http://localhost:8001/api/health 2>/dev/null && echo "$(GREEN)✓ API healthy$(NC)" || echo "$(RED)✗ API not responding$(NC)"
	@echo "$(YELLOW)Frontend Check:$(NC)"
	@curl -sf http://localhost:3000 -I 2>/dev/null >/dev/null && echo "$(GREEN)✓ Frontend healthy$(NC)" || echo "$(RED)✗ Frontend not responding$(NC)"

# ========================================
# TESTING
# ========================================

## Run all tests
test: test-unit test-e2e
	@echo "$(GREEN)All tests completed$(NC)"

## Run unit tests
test-unit:
	@echo "$(YELLOW)Running unit tests...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api python -m pytest tests/ -v --cov=src || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm test || true

## Run integration tests
test-integration:
	@echo "$(YELLOW)Running integration tests...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api python -m pytest tests/integration/ -v || true

## Run E2E tests
test-e2e:
	@echo "$(YELLOW)Running E2E tests...$(NC)"
	@pnpm exec playwright test || true

## Run E2E tests in headed mode
test-e2e-headed:
	@echo "$(YELLOW)Running E2E tests (headed mode)...$(NC)"
	@pnpm exec playwright test --headed || true

## Open Playwright UI
test-e2e-ui:
	@echo "$(YELLOW)Opening Playwright UI...$(NC)"
	@pnpm exec playwright test --ui

## Generate test report
test-report:
	@echo "$(YELLOW)Generating test report...$(NC)"
	@pnpm exec playwright show-report

## Setup test environment
test-setup:
	@echo "$(YELLOW)Setting up test environment...$(NC)"
	@pnpm install
	@pnpm exec playwright install
	@mkdir -p playwright/.auth test-results test-data
	@echo "$(GREEN)Test environment ready$(NC)"

## Clean test artifacts
test-clean:
	@echo "$(YELLOW)Cleaning test artifacts...$(NC)"
	@rm -rf playwright-report test-results playwright/.auth test-data
	@echo "$(GREEN)Test artifacts cleaned$(NC)"

# ========================================
# QUALITY & SECURITY
# ========================================

## Run linters
lint:
	@echo "$(YELLOW)Running linters...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api ruff check . || true
	@docker compose -f $(COMPOSE_FILE) exec api ruff format . || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm lint || true

## Fix lint issues
lint-fix:
	@echo "$(YELLOW)Fixing lint issues...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api ruff check . --fix || true
	@docker compose -f $(COMPOSE_FILE) exec api ruff format . || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm lint --fix || true

## Run security scans
security:
	@echo "$(YELLOW)Running security scans...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api safety check || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm audit || true

## Audit dependencies
audit:
	@echo "$(YELLOW)Auditing dependencies...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api pip-audit || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm audit || true

# ========================================
# BUILD & DEPLOY
# ========================================

## Build all Docker images
build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build --parallel

## Push images to registry
push:
	@echo "$(YELLOW)Pushing images to registry...$(NC)"
	@docker compose -f $(COMPOSE_FILE) push

## Deploy production environment
prod:
	@echo "$(GREEN)Deploying production environment...$(NC)"
	@docker compose -f $(COMPOSE_FILE) --profile production up -d --build
	@echo "$(GREEN)Production environment deployed$(NC)"
	@make --no-print-directory health

## Production logs
prod-logs:
	@docker compose -f $(COMPOSE_FILE) --profile production logs -f

# ========================================
# CLEANUP
# ========================================

## Clean containers and volumes
clean:
	@echo "$(YELLOW)Cleaning up containers and volumes...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans
	@echo "$(GREEN)Cleanup completed$(NC)"

## Deep clean (including unused Docker resources)
clean-all: clean
	@echo "$(YELLOW)Deep cleaning Docker resources...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)Deep cleanup completed$(NC)"

# ========================================
# SETUP & UTILITIES
# ========================================

## Setup development environment
setup:
	@echo "$(GREEN)Setting up development environment...$(NC)"
	@if [ ! -f envs/.env.local ]; then \
		echo "$(YELLOW)Creating environment file...$(NC)"; \
		cp envs/.env.local.example envs/.env.local 2>/dev/null || echo "$(RED)Warning: .env.local.example not found$(NC)"; \
	else \
		echo "$(BLUE)Environment file already exists$(NC)"; \
	fi
	@echo "$(YELLOW)Please configure envs/.env.local with your API keys$(NC)"
	@echo "$(GREEN)Setup completed$(NC)"

## Show Docker resource usage
status:
	@echo "$(YELLOW)Docker Resource Usage:$(NC)"
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@docker system df

## Show container logs for specific service (usage: make service-logs SERVICE=api)
service-logs:
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Usage: make service-logs SERVICE=<api|web|mongodb|redis>$(NC)"; \
		exit 1; \
	fi
	@docker compose -f $(COMPOSE_FILE) logs -f $(PROJECT_NAME)-$(SERVICE)

# ========================================
# DEVELOPMENT UTILITIES
# ========================================

## Connect to MongoDB shell
mongo-shell:
	@docker exec -it $(PROJECT_NAME)-mongodb mongosh

## Connect to Redis CLI
redis-cli:
	@docker exec -it $(PROJECT_NAME)-redis redis-cli

## Show environment variables for debugging
debug-env:
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@docker compose -f $(COMPOSE_FILE) config

## Backup database
backup:
	@echo "$(YELLOW)Creating database backup...$(NC)"
	@mkdir -p backups
	@docker exec $(PROJECT_NAME)-mongodb mongodump --db copilotos --out /tmp/backup
	@docker cp $(PROJECT_NAME)-mongodb:/tmp/backup ./backups/$(shell date +%Y%m%d_%H%M%S)
	@echo "$(GREEN)Backup completed$(NC)"

## Create demo user for testing
create-demo-user:
	@echo "$(YELLOW)Creating demo user...$(NC)"
	@docker exec $(PROJECT_NAME)-api python scripts/create-demo-user.py
	@echo "$(GREEN)Demo user setup completed$(NC)"

## List all users in database
list-users:
	@echo "$(YELLOW)Listing database users...$(NC)"
	@docker exec $(PROJECT_NAME)-mongodb mongosh -u copilotos_user -p secure_password_change_me --authenticationDatabase admin copilotos --eval "db.users.find({}, {username: 1, email: 1, is_active: 1, created_at: 1}).pretty()" --quiet

## Delete demo user
delete-demo-user:
	@echo "$(YELLOW)Deleting demo user...$(NC)"
	@docker exec $(PROJECT_NAME)-mongodb mongosh -u copilotos_user -p secure_password_change_me --authenticationDatabase admin copilotos --eval "db.users.deleteOne({username: 'demo_admin'})" --quiet
	@echo "$(GREEN)Demo user deleted$(NC)"

# Default target
.DEFAULT_GOAL := help

# Prevent make from deleting intermediate files
.SECONDARY:

# Use bash as the shell
SHELL := /bin/bash