# =========================================
# MODERN MAKEFILE FOR COPILOT OS
# =========================================
.PHONY: help dev prod test clean build lint security docker-* ci-*

# Colors
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
NC := \033[0m

# Configuration
COMPOSE_FILE := docker-compose.modern.yml
PROJECT_NAME := copilotos

## Show this help message
help:
	@echo "$(GREEN)🚀 Copilot OS - Modern Development Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)📋 Quick Start:$(NC)"
	@echo "  $(BLUE)make dev$(NC)         - Start development environment"
	@echo "  $(BLUE)make test$(NC)        - Run all tests"
	@echo "  $(BLUE)make build$(NC)       - Build all images"
	@echo "  $(BLUE)make clean$(NC)       - Clean up everything"
	@echo ""
	@echo "$(YELLOW)🏗️  Development:$(NC)"
	@echo "  $(BLUE)make dev$(NC)         - Start dev environment with hot reload"
	@echo "  $(BLUE)make logs$(NC)        - Follow logs from all services"
	@echo "  $(BLUE)make shell-api$(NC)   - Shell into API container"
	@echo "  $(BLUE)make shell-web$(NC)   - Shell into Web container"
	@echo ""
	@echo "$(YELLOW)🚀 Production:$(NC)"
	@echo "  $(BLUE)make prod$(NC)        - Deploy production environment"
	@echo "  $(BLUE)make prod-logs$(NC)   - Follow production logs"
	@echo "  $(BLUE)make prod-health$(NC) - Check production health"
	@echo ""
	@echo "$(YELLOW)🧪 Testing:$(NC)"
	@echo "  $(BLUE)make test$(NC)        - Run full test suite"
	@echo "  $(BLUE)make test-unit$(NC)   - Run unit tests only"
	@echo "  $(BLUE)make test-e2e$(NC)    - Run E2E tests with Playwright"
	@echo "  $(BLUE)make test-api$(NC)    - Test API endpoints"
	@echo ""
	@echo "$(YELLOW)🔒 Security & Quality:$(NC)"
	@echo "  $(BLUE)make lint$(NC)        - Run linters (frontend + backend)"
	@echo "  $(BLUE)make security$(NC)    - Run security scans"
	@echo "  $(BLUE)make audit$(NC)       - Audit dependencies"
	@echo ""
	@echo "$(YELLOW)🐳 Docker Management:$(NC)"
	@echo "  $(BLUE)make docker-build$(NC) - Build all Docker images"
	@echo "  $(BLUE)make docker-push$(NC)  - Push images to registry"
	@echo "  $(BLUE)make docker-clean$(NC) - Clean Docker resources"
	@echo ""
	@echo "$(YELLOW)⚙️  CI/CD:$(NC)"
	@echo "  $(BLUE)make ci-test$(NC)     - Run CI test pipeline"
	@echo "  $(BLUE)make ci-build$(NC)    - Run CI build pipeline"
	@echo "  $(BLUE)make ci-deploy$(NC)   - Run CI deploy pipeline"

# =========================================
# DEVELOPMENT COMMANDS
# =========================================

## Start development environment
dev:
	@echo "$(GREEN)🚀 Starting development environment...$(NC)"
	@docker compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)✅ Development environment started$(NC)"
	@echo "$(BLUE)🌐 Frontend: http://localhost:3000$(NC)"
	@echo "$(BLUE)🔌 API: http://localhost:8001$(NC)"
	@make _show-health

## Follow logs from all services
logs:
	@docker compose -f $(COMPOSE_FILE) logs -f

## Shell into API container
shell-api:
	@docker exec -it copilotos-api bash

## Shell into Web container
shell-web:
	@docker exec -it copilotos-web sh

# =========================================
# PRODUCTION COMMANDS
# =========================================

## Deploy production environment
prod:
	@echo "$(GREEN)🚀 Deploying production environment...$(NC)"
	@docker compose -f $(COMPOSE_FILE) --profile production up -d --build
	@echo "$(GREEN)✅ Production environment deployed$(NC)"
	@make prod-health

## Follow production logs
prod-logs:
	@docker compose -f $(COMPOSE_FILE) --profile production logs -f

## Check production health
prod-health:
	@echo "$(YELLOW)🔍 Checking production health...$(NC)"
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@curl -sf http://localhost:8001/api/health || echo "$(RED)❌ API not responding$(NC)"
	@curl -sf http://localhost:3000 -I || echo "$(RED)❌ Frontend not responding$(NC)"

# =========================================
# TESTING COMMANDS
# =========================================

## Run full test suite
test: test-unit test-e2e
	@echo "$(GREEN)✅ All tests completed$(NC)"

## Run unit tests
test-unit:
	@echo "$(YELLOW)🧪 Running unit tests...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api python -m pytest tests/ -v
	@docker compose -f $(COMPOSE_FILE) exec web pnpm test

## Run E2E tests with Playwright
test-e2e:
	@echo "$(YELLOW)🎭 Running E2E tests...$(NC)"
	@docker compose -f $(COMPOSE_FILE) --profile testing up playwright --build

## Test API endpoints
test-api:
	@echo "$(YELLOW)🔌 Testing API endpoints...$(NC)"
	@curl -sf http://localhost:8001/api/health | jq . || echo "$(RED)❌ Health check failed$(NC)"

# =========================================
# QUALITY & SECURITY
# =========================================

## Run linters
lint:
	@echo "$(YELLOW)🔍 Running linters...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api ruff check . || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm lint || true

## Run security scans
security:
	@echo "$(YELLOW)🔒 Running security scans...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api safety check || true
	@docker compose -f $(COMPOSE_FILE) exec web pnpm audit || true

## Audit dependencies
audit: security
	@echo "$(YELLOW)📋 Auditing dependencies...$(NC)"
	@docker compose -f $(COMPOSE_FILE) exec api pip-audit || true

# =========================================
# DOCKER MANAGEMENT
# =========================================

## Build all Docker images
docker-build: build

## Build all images
build:
	@echo "$(YELLOW)🔨 Building Docker images...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build --parallel

## Push images to registry
docker-push:
	@echo "$(YELLOW)📤 Pushing images to registry...$(NC)"
	@docker compose -f $(COMPOSE_FILE) push

## Clean Docker resources
docker-clean:
	@echo "$(YELLOW)🧹 Cleaning Docker resources...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans
	@docker system prune -f
	@docker volume prune -f

## Complete cleanup
clean: docker-clean
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

# =========================================
# CI/CD COMMANDS
# =========================================

## Run CI test pipeline
ci-test:
	@echo "$(YELLOW)🤖 Running CI test pipeline...$(NC)"
	@make build
	@make test-unit
	@make lint
	@make security

## Run CI build pipeline
ci-build:
	@echo "$(YELLOW)🤖 Running CI build pipeline...$(NC)"
	@make docker-build
	@make test

## Run CI deploy pipeline
ci-deploy:
	@echo "$(YELLOW)🤖 Running CI deploy pipeline...$(NC)"
	@make ci-build
	@make docker-push

# =========================================
# UTILITY COMMANDS
# =========================================

## Stop all services
stop:
	@docker compose -f $(COMPOSE_FILE) down

## Restart all services
restart:
	@docker compose -f $(COMPOSE_FILE) restart

## Show service health status
_show-health:
	@echo ""
	@echo "$(YELLOW)🔍 Service Health:$(NC)"
	@sleep 5
	@docker compose -f $(COMPOSE_FILE) ps

## Setup development environment
setup:
	@echo "$(GREEN)🔧 Setting up development environment...$(NC)"
	@cp envs/.env.local.example envs/.env.local 2>/dev/null || echo "Environment file exists"
	@echo "$(YELLOW)📝 Please configure envs/.env.local with your API keys$(NC)"

# Default target
.DEFAULT_GOAL := help