# ============================================================================
# OCTAVIOS CHAT - ORCHESTRATED MAKEFILE V2.0
# ============================================================================
# Makefile como orquestador principal con flags, sub-flags y delegación a scripts
# Usa: make <target> [FLAGS] [VARS]
# ============================================================================

.PHONY: help setup dev test db deploy clean docs scripts

# ============================================================================
# CONFIGURATION & FLAGS
# ============================================================================

# Global Flags (pueden usarse con cualquier comando)
V ?= 0                    # Verbose mode: V=1
DRY ?= 0                  # Dry-run mode: DRY=1
FORCE ?= 0                # Force mode (skip confirmations): FORCE=1
QUIET ?= 0                # Quiet mode (minimal output): QUIET=1

# Environment & File Selection
ENV ?=                    # Environment selector: ENV=prod|demo|local
ENV_CANDIDATE := $(if $(ENV),envs/.env.$(ENV),envs/.env)
ENV_FILE := $(if $(wildcard $(ENV_CANDIDATE)),$(ENV_CANDIDATE),envs/.env)

# Service Selection
S ?=                      # Service selector: S=backend|web|db|redis|minio
SVC := $(S)               # Alias

# Test Selection
T ?= all                  # Test target: T=api|web|mcp|e2e|shell|all
TEST_FILE ?=              # Specific test file: TEST_FILE=test_foo.py
TEST_ARGS ?=              # Additional test args: TEST_ARGS="-v -k pattern"
SUITES ?=                 # Parallel suite names: SUITES="e2e_regression integration"

# Database Selection
DB_CMD ?=                 # Database command: DB_CMD=backup|restore|stats|shell
DB_NAME ?=                # Database name (optional)

# Docker Compose Configuration
PROJECT_NAME := octavios-chat
COMPOSE_BASE := infra/docker-compose.yml
COMPOSE_DEV := infra/docker-compose.dev.yml
COMPOSE_PROD := infra/docker-compose.production.yml
COMPOSE_REGISTRY := infra/docker-compose.registry.yml

# Compose Command Builders
# CRITICAL: Always include --env-file to ensure variable interpolation works
# Without this, $MONGODB_USER etc. become empty strings and services fail
REGISTRY ?= 0             # Use registry images: REGISTRY=1
COMPOSE_CMD = docker compose -f $(COMPOSE_BASE) --env-file $(ENV_FILE)
COMPOSE_DEV_CMD = $(COMPOSE_CMD) -f $(COMPOSE_DEV)
COMPOSE_PROD_CMD = $(COMPOSE_CMD) -f $(COMPOSE_PROD) $(if $(filter 1,$(REGISTRY)),-f $(COMPOSE_REGISTRY),)

# Health Check Configuration
HEALTH_TIMEOUT ?= 120
HEALTH_INTERVAL ?= 5
HEALTH_RETRIES ?= 3

# Bun Runtime (optional)
BUN ?= bun
BUN_VERSION ?= 1.2.2
BUN_LOCK := bun.lockb
BUN_INSTALL_FLAGS := $(if $(wildcard $(BUN_LOCK)),--frozen-lockfile,)

# Colors (only if not QUIET)
ifneq ($(QUIET),1)
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
RED    := \033[0;31m
CYAN   := \033[0;36m
BOLD   := \033[1m
NC     := \033[0m
endif

# Verbose/Quiet Mode Helpers
ifeq ($(V),1)
    VERBOSE_FLAG := --verbose
    AT :=
else
    VERBOSE_FLAG :=
    AT := @
endif

ifeq ($(QUIET),1)
    QUIET_FLAG := --quiet
    STDOUT := > /dev/null 2>&1
else
    QUIET_FLAG :=
    STDOUT :=
endif

# Dry-run Helper
ifeq ($(DRY),1)
    DRY_RUN := echo "[DRY-RUN]"
    DRY_FLAG := --dry-run
else
    DRY_RUN :=
    DRY_FLAG :=
endif

# Load environment if exists
ifneq (,$(wildcard $(ENV_FILE)))
    include $(ENV_FILE)
    export
endif

# ============================================================================
# DEFAULT GOAL & HELP
# ============================================================================

.DEFAULT_GOAL := help

help: help.summary help.categories

help.summary:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(BLUE)$(BOLD) 🚀 $(PROJECT_NAME) - Command Center v2.0 $(NC)"
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo ""
	$(AT)echo "$(CYAN)📖 Usage:$(NC) make <target> [FLAGS] [VARS]"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🎛️  Global Flags:$(NC)"
	$(AT)echo "  $(YELLOW)V=1$(NC)              - Verbose mode (show all commands)"
	$(AT)echo "  $(YELLOW)DRY=1$(NC)            - Dry-run mode (show what would be executed)"
	$(AT)echo "  $(YELLOW)FORCE=1$(NC)          - Force mode (skip confirmations)"
	$(AT)echo "  $(YELLOW)QUIET=1$(NC)          - Quiet mode (minimal output)"
	$(AT)echo "  $(YELLOW)ENV=prod|demo$(NC)    - Select environment file (envs/.env.<ENV>)"
	$(AT)echo "  $(YELLOW)S=<service>$(NC)      - Select specific service"
	$(AT)echo "  $(YELLOW)REGISTRY=1$(NC)       - Use Docker Hub images (for prod)"
	$(AT)echo ""
	$(AT)echo "$(CYAN)💡 Examples:$(NC)"
	$(AT)echo "  $(GREEN)make dev$(NC)                    - Start development"
	$(AT)echo "  $(GREEN)make dev V=1$(NC)                - Start development (verbose)"
	$(AT)echo "  $(GREEN)make test T=api V=1$(NC)         - Run API tests (verbose)"
	$(AT)echo "  $(GREEN)make logs S=backend$(NC)         - View backend logs"
	$(AT)echo "  $(GREEN)make db.backup$(NC)              - Backup database"
	$(AT)echo "  $(GREEN)make prod ENV=prod REGISTRY=1$(NC) - Deploy prod with registry images"
	$(AT)echo "  $(GREEN)make help.bun$(NC)               - Bun runtime helpers"
	$(AT)echo ""
	$(AT)echo "$(CYAN)📋 Quick Reference:$(NC)"
	$(AT)echo "  $(YELLOW)make help.dev$(NC)      - Development commands"
	$(AT)echo "  $(YELLOW)make help.test$(NC)     - Testing commands"
	$(AT)echo "  $(YELLOW)make help.db$(NC)       - Database commands"
	$(AT)echo "  $(YELLOW)make help.deploy$(NC)   - Deployment commands"
	$(AT)echo "  $(YELLOW)make help.scripts$(NC)  - Available scripts"
	$(AT)echo ""

help.categories:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(CYAN)📦 Categories:$(NC)"
	$(AT)echo "  🚀 $(BOLD)Lifecycle:$(NC)     setup, dev, prod, stop, restart, clean"
	$(AT)echo "  🧪 $(BOLD)Testing:$(NC)       test, test.<type>, test-local"
	$(AT)echo "  💾 $(BOLD)Database:$(NC)      db.<cmd>"
	$(AT)echo "  🚢 $(BOLD)Deployment:$(NC)    deploy, prod-deploy, registry-deploy"
	$(AT)echo "  🔧 $(BOLD)Development:$(NC)   logs, shell, health, reload-env"
	$(AT)echo "  📊 $(BOLD)Monitoring:$(NC)    status, health, logs-follow"
	$(AT)echo "  🧹 $(BOLD)Cleanup:$(NC)       clean, clean-deep, clean-cache"
	$(AT)echo "  📜 $(BOLD)Scripts:$(NC)       scripts.<category>.<name>"
	$(AT)echo "  ⚡ $(BOLD)Bun Runtime:$(NC)    bun.install, bun.dev-web, bun.test-web"
	$(AT)echo ""
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# Category-specific help
help.dev:
	$(AT)echo "$(CYAN)🚀 Development Commands:$(NC)"
	$(AT)echo "  $(YELLOW)make dev$(NC)                 - Start development (hot reload)"
	$(AT)echo "  $(YELLOW)make dev-rebuild$(NC)         - Rebuild and start dev"
	$(AT)echo "  $(YELLOW)make dev-reset$(NC)           - Full reset (stop, remove, rebuild)"
	$(AT)echo "  $(YELLOW)make logs [S=service]$(NC)    - View logs (last 100 lines)"
	$(AT)echo "  $(YELLOW)make logs-follow [S=svc]$(NC) - Follow logs in real-time"
	$(AT)echo "  $(YELLOW)make shell S=backend$(NC)     - Open shell in container"
	$(AT)echo "  $(YELLOW)make health$(NC)              - Check all services health"
	$(AT)echo "  $(YELLOW)make reload-env S=backend$(NC) - Reload env vars"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🔨 Rebuild Individual Services:$(NC)"
	$(AT)echo "  $(YELLOW)make rebuild.backend$(NC)     - Rebuild backend only"
	$(AT)echo "  $(YELLOW)make rebuild.web$(NC)         - Rebuild web only"
	$(AT)echo "  $(YELLOW)make rebuild.file-manager$(NC) - Rebuild file-manager"

help.test:
	$(AT)echo "$(CYAN)🧪 Testing Commands:$(NC)"
	$(AT)echo "  $(YELLOW)make test$(NC)                - Run all tests"
	$(AT)echo "  $(YELLOW)make test T=api$(NC)          - Run API tests"
	$(AT)echo "  $(YELLOW)make test T=web$(NC)          - Run web tests"
	$(AT)echo "  $(YELLOW)make test T=mcp$(NC)          - Run MCP tests"
	$(AT)echo "  $(YELLOW)make test T=e2e$(NC)          - Run E2E tests"
	$(AT)echo "  $(YELLOW)make test T=shell$(NC)        - Run shell tests"
	$(AT)echo "  $(YELLOW)make test.parallel$(NC)      - Run suite runner (parallel)"
	$(AT)echo "  $(YELLOW)make test.parallel SUITES=\"e2e_regression integration\"$(NC)"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🎯 Specific Tests (dot notation):$(NC)"
	$(AT)echo "  $(YELLOW)make test.api$(NC)            - Run API tests"
	$(AT)echo "  $(YELLOW)make test.web$(NC)            - Run web tests"
	$(AT)echo "  $(YELLOW)make test.mcp$(NC)            - Run MCP tests"
	$(AT)echo "  $(YELLOW)make test.e2e$(NC)            - Run E2E tests"
	$(AT)echo "  $(YELLOW)make test.e2e.pdf$(NC)        - Run E2E + generate PDF evidence report"
	$(AT)echo "  $(YELLOW)make test.e2e.pdf.strict$(NC) - Run E2E + fail if PDF report is missing"
	$(AT)echo "  $(YELLOW)make test.e2e.fast$(NC)       - Run E2E only (skip PDF generation)"
	$(AT)echo "  $(YELLOW)make test.shell$(NC)          - Run shell tests"
	$(AT)echo "  $(YELLOW)make test.audit$(NC)          - Run audit tests"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🧬 Local Tests (with .venv):$(NC)"
	$(AT)echo "  $(YELLOW)make test-local$(NC)          - Run all tests locally"
	$(AT)echo "  $(YELLOW)make test-local FILE=path$(NC) - Run specific test file"

help.db:
	$(AT)echo "$(CYAN)💾 Database Commands:$(NC)"
	$(AT)echo "  $(YELLOW)make db.backup$(NC)           - Backup MongoDB"
	$(AT)echo "  $(YELLOW)make db.restore$(NC)          - Restore from backup"
	$(AT)echo "  $(YELLOW)make db.stats$(NC)            - Show database stats"
	$(AT)echo "  $(YELLOW)make db.shell$(NC)            - Open MongoDB shell"
	$(AT)echo ""

help.deploy:
	$(AT)echo "$(CYAN)🚢 Deployment Commands:$(NC)"
	$(AT)echo "  $(YELLOW)make prod$(NC)                - Full prod deployment (preflight + build + up + health)"
	$(AT)echo "  $(YELLOW)make prod ENV=prod REGISTRY=1$(NC) - Deploy with registry images"
	$(AT)echo "  $(YELLOW)make deploy-registry VERSION=0.1.3$(NC) - Deploy from Docker Hub"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🏗️  Production Steps:$(NC)"
	$(AT)echo "  $(YELLOW)make prod.preflight$(NC)      - Run preflight checks"
	$(AT)echo "  $(YELLOW)make prod.build$(NC)          - Build production images"
	$(AT)echo "  $(YELLOW)make prod.up$(NC)             - Start production containers"
	$(AT)echo "  $(YELLOW)make prod.status$(NC)         - Show production status"

help.scripts:
	$(AT)echo "$(CYAN)📜 Available Script Categories:$(NC)"
	$(AT)echo "  $(YELLOW)scripts/setup/$(NC)           - Project setup & configuration"
	$(AT)echo "  $(YELLOW)scripts/testing/$(NC)         - Testing & validation scripts"
	$(AT)echo "  $(YELLOW)scripts/database/$(NC)        - Database operations & migrations"
	$(AT)echo "  $(YELLOW)scripts/maintenance/$(NC)     - System maintenance & diagnostics"
	$(AT)echo "  $(YELLOW)scripts/security/$(NC)        - Security audits & checks"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🎯 Script Execution (dot notation):$(NC)"
	$(AT)echo "  $(YELLOW)make scripts.setup.env-checker$(NC)      - Run env-checker.sh"
	$(AT)echo "  $(YELLOW)make scripts.testing.validate-mvp$(NC)   - Run validate-mvp.sh"
	$(AT)echo "  $(YELLOW)make scripts.database.backup-mongodb$(NC) - Run backup-mongodb.sh"
	$(AT)echo "  $(YELLOW)make scripts.maintenance.health-check$(NC) - Run health-check.sh"
	$(AT)echo ""
	$(AT)echo "$(CYAN)📖 See:$(NC) scripts/README.md for complete script documentation"

# ============================================================================
# LIFECYCLE COMMANDS
# ============================================================================

setup:
	$(AT)echo "$(YELLOW)🔧 Setting up project...$(NC)"
	$(AT)chmod +x scripts/*.sh scripts/*/*.sh
	$(DRY_RUN) ./scripts/setup/interactive-env-setup.sh development
	$(AT)echo "$(GREEN)✅ Setup complete. Run 'make dev' to start.$(NC)"

env-check env.check:
	$(AT)echo "$(YELLOW)🔍 Validating environment variables...$(NC)"
	$(DRY_RUN) ./scripts/setup/env-checker.sh warn $(VERBOSE_FLAG)

env-info env.info:
	$(AT)echo "$(YELLOW)📋 Environment information...$(NC)"
	$(DRY_RUN) ./scripts/setup/env-checker.sh info

env-strict env.strict:
	$(AT)echo "$(YELLOW)🔒 Strict environment validation...$(NC)"
	$(DRY_RUN) ./scripts/setup/env-checker.sh strict

dev:
	$(AT)echo "$(YELLOW)🟡 Starting development environment...$(NC)"
	$(AT)$(MAKE) --no-print-directory env-check || { echo "$(RED)❌ Env check failed$(NC)"; exit 1; }
	$(DRY_RUN) $(COMPOSE_DEV_CMD) up -d $(QUIET_FLAG)
	$(AT)echo ""
	$(AT)echo "$(GREEN)🟢 Development environment started$(NC)"
	$(AT)echo "  $(BLUE)Frontend:$(NC)     http://localhost:3000"
	$(AT)echo "  $(BLUE)Backend:$(NC)      http://localhost:8000"
	$(AT)echo "  $(BLUE)File Manager:$(NC) http://localhost:8001"
	$(AT)echo "  $(BLUE)Aletheia:$(NC)     http://localhost:8003"
	$(AT)echo ""
ifneq ($(QUIET),1)
	$(AT)sleep 5
	$(AT)$(MAKE) --no-print-directory health
endif

tidewave-local:
	$(AT)echo "$(YELLOW)🌊 Starting backend with Tidewave locally (no Docker)...$(NC)"
	$(DRY_RUN) TIDEWAVE_ENABLED=true uvicorn apps.backend.src.main:app --host 0.0.0.0 --port 8000 --reload

dev-rebuild dev.rebuild:
	$(AT)echo "$(YELLOW)🔨 Rebuilding development environment...$(NC)"
	$(AT)$(MAKE) --no-print-directory env-check
	$(DRY_RUN) $(COMPOSE_DEV_CMD) down
	$(DRY_RUN) $(COMPOSE_DEV_CMD) up -d --build backend web $(QUIET_FLAG)
	$(AT)echo "$(GREEN)✅ Development environment rebuilt$(NC)"

dev-reset dev.reset:
ifneq ($(FORCE),1)
	$(AT)echo "$(RED)⚠️  WARNING: Full reset will stop and rebuild everything!$(NC)"
	$(AT)read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
endif
	$(DRY_RUN) $(COMPOSE_DEV_CMD) down --remove-orphans
	$(DRY_RUN) $(COMPOSE_DEV_CMD) build --no-cache backend web
	$(DRY_RUN) $(COMPOSE_DEV_CMD) up -d
	$(AT)echo "$(GREEN)✅ Complete reset done$(NC)"

stop:
	$(AT)echo "$(YELLOW)🛑 Stopping services...$(NC)"
	$(DRY_RUN) $(COMPOSE_CMD) down $(QUIET_FLAG)
	$(AT)echo "$(GREEN)✅ Services stopped$(NC)"

stop-all:
	$(AT)echo "$(YELLOW)🛑 Stopping and removing all containers...$(NC)"
	$(DRY_RUN) $(COMPOSE_DEV_CMD) down --remove-orphans $(QUIET_FLAG)
	$(AT)echo "$(GREEN)✅ All containers removed$(NC)"

restart:
ifdef SVC
	$(AT)echo "$(YELLOW)♻️  Restarting service: $(SVC)...$(NC)"
	$(DRY_RUN) $(COMPOSE_CMD) restart $(SVC)
else
	$(AT)echo "$(YELLOW)♻️  Restarting all services...$(NC)"
	$(DRY_RUN) $(COMPOSE_CMD) restart
endif
	$(AT)echo "$(GREEN)✅ Restart complete$(NC)"

# ============================================================================
# REBUILD PATTERN (individual services)
# ============================================================================

rebuild.%:
	$(AT)echo "$(YELLOW)🔨 Rebuilding $*...$(NC)"
	$(DRY_RUN) $(COMPOSE_DEV_CMD) up -d --build --no-deps $*
	$(AT)echo "$(GREEN)✅ $* rebuilt$(NC)"

# Aliases for common rebuild targets
rebuild-backend: rebuild.backend
rebuild-web: rebuild.web
rebuild-file-manager: rebuild.file-manager

# ============================================================================
# DEVELOPMENT TOOLS
# ============================================================================

logs:
ifdef SVC
	$(AT)$(COMPOSE_CMD) logs --tail=100 $(SVC)
else
	$(AT)$(COMPOSE_CMD) logs --tail=100
endif

logs-follow:
ifdef SVC
	$(AT)echo "$(YELLOW)📜 Following logs for $(SVC)...$(NC)"
	$(AT)$(COMPOSE_CMD) logs -f --tail=100 $(SVC)
else
	$(AT)echo "$(YELLOW)📜 Following all logs...$(NC)"
	$(AT)$(COMPOSE_CMD) logs -f --tail=100
endif

status ps:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(BLUE)📊 Container Status$(NC)"
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)docker ps --filter "name=$(PROJECT_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

shell:
ifndef SVC
	$(AT)echo "$(RED)❌ Specify service: make shell S=backend$(NC)"
	$(AT)exit 1
endif
	$(AT)if [ "$(SVC)" = "db" ]; then \
		$(COMPOSE_CMD) exec mongodb bash; \
	else \
		$(COMPOSE_CMD) exec $(SVC) bash; \
	fi

health:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(BLUE)🏥 Health Check$(NC)"
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)printf "  $(YELLOW)Backend:$(NC)      "
	$(AT)curl -sf http://localhost:8000/api/health > /dev/null 2>&1 && echo "$(GREEN)✅ Healthy$(NC)" || echo "$(RED)❌ Unhealthy$(NC)"
	$(AT)printf "  $(YELLOW)File Manager:$(NC) "
	$(AT)curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "$(GREEN)✅ Healthy$(NC)" || echo "$(RED)❌ Unhealthy$(NC)"
	$(AT)printf "  $(YELLOW)Frontend:$(NC)     "
	$(AT)curl -sf http://localhost:3000 > /dev/null 2>&1 && echo "$(GREEN)✅ Healthy$(NC)" || echo "$(RED)❌ Unhealthy$(NC)"
	$(AT)printf "  $(YELLOW)MongoDB:$(NC)      "
	$(AT)$(COMPOSE_CMD) exec -T mongodb mongosh --eval 'db.adminCommand("ping")' > /dev/null 2>&1 && echo "$(GREEN)✅ Connected$(NC)" || echo "$(RED)❌ Disconnected$(NC)"
	$(AT)printf "  $(YELLOW)Redis:$(NC)        "
	$(AT)$(COMPOSE_CMD) exec -T redis redis-cli ping > /dev/null 2>&1 && echo "$(GREEN)✅ Connected$(NC)" || echo "$(RED)❌ Disconnected$(NC)"

reload-env:
ifndef SVC
	$(AT)echo "$(RED)❌ Specify service: make reload-env S=backend$(NC)"
	$(AT)exit 1
endif
	$(AT)echo "$(YELLOW)♻️  Reloading environment for $(SVC)...$(NC)"
	$(DRY_RUN) $(COMPOSE_CMD) stop $(SVC)
	$(DRY_RUN) $(COMPOSE_CMD) rm -f $(SVC)
	$(DRY_RUN) $(COMPOSE_CMD) up -d $(SVC)
	$(AT)echo "$(GREEN)✅ Environment reloaded$(NC)"

# ============================================================================
# TESTING (with pattern rules)
# ============================================================================

test:
	$(AT)chmod +x scripts/testing/test-runner.sh
	$(DRY_RUN) ./scripts/testing/test-runner.sh $(T) $(TEST_ARGS) $(VERBOSE_FLAG)

# Dot notation for specific test types
test.%:
	$(AT)$(MAKE) test T=$* $(if $(V),V=$(V)) $(if $(TEST_ARGS),TEST_ARGS="$(TEST_ARGS)")

# Specific test shortcuts
test.api: T := api
test.web: T := web
test.mcp: T := mcp
test.e2e: T := e2e
test.e2e.pdf:
	$(AT)echo "$(YELLOW)🧾 Running Playwright E2E with PDF evidence report...$(NC)"
	$(DRY_RUN) cd apps/web && pnpm run test:e2e:pdf $(if $(TEST_ARGS),-- $(TEST_ARGS),)
test-e2e-pdf: test.e2e.pdf
test.e2e.pdf.strict:
	$(AT)echo "$(YELLOW)🧾 Running Playwright E2E with strict PDF enforcement...$(NC)"
	$(DRY_RUN) cd apps/web && E2E_PDF_STRICT=1 pnpm run test:e2e:pdf $(if $(TEST_ARGS),-- $(TEST_ARGS),)
test-e2e-pdf-strict: test.e2e.pdf.strict
test.e2e.fast:
	$(AT)echo "$(YELLOW)⚡ Running Playwright E2E without PDF generation...$(NC)"
	$(DRY_RUN) cd apps/web && E2E_SKIP_PDF=1 pnpm run test:e2e:pdf $(if $(TEST_ARGS),-- $(TEST_ARGS),)
test-e2e-fast: test.e2e.fast
test.shell: T := shell
test.audit:
	$(DRY_RUN) ./scripts/test_audit_flow.sh $(VERBOSE_FLAG)

test-local:
	$(AT)echo "$(YELLOW)🧪 Running tests locally with .venv...$(NC)"
	$(AT)[ -d "apps/backend/.venv" ] || { echo "$(RED)❌ .venv not found$(NC)"; exit 1; }
ifdef TEST_FILE
	$(DRY_RUN) cd apps/backend && .venv/bin/python -m pytest $(TEST_FILE) $(TEST_ARGS) $(VERBOSE_FLAG)
else
	$(DRY_RUN) cd apps/backend && .venv/bin/python -m pytest tests/ $(TEST_ARGS) $(VERBOSE_FLAG)
endif

# Parallel suite runner (tests/runner)
test.parallel:
	$(DRY_RUN) python -m tests.runner $(if $(SUITES),$(foreach s,$(SUITES),--suite $(s)))

# ============================================================================
# DATABASE (with dot notation)
# ============================================================================

db:
ifndef DB_CMD
	$(AT)echo "$(RED)❌ Specify command: make db DB_CMD=backup$(NC)"
	$(AT)echo "Available: backup, restore, stats, shell"
	$(AT)exit 1
endif
	$(DRY_RUN) ./scripts/database/db-manager.sh $(DB_CMD) $(PROJECT_NAME) $(VERBOSE_FLAG)

# Dot notation for database commands
db.%:
	$(AT)$(MAKE) db DB_CMD=$* $(if $(V),V=$(V))


# ============================================================================
# PRE-DEPLOY VERIFICATION
# ============================================================================
# Run these checks BEFORE every deploy to prevent regressions.
# Usage:
#   make pre-deploy       # Full verification (lint + unit + regression + integration)
#   make pre-deploy.quick # Quick check (regression tests only)
#   make pre-deploy.check # Check services are running

.PHONY: pre-deploy pre-deploy.check pre-deploy.lint pre-deploy.unit pre-deploy.regression pre-deploy.integration pre-deploy.quick

pre-deploy: pre-deploy.check pre-deploy.lint pre-deploy.unit pre-deploy.regression
	$(AT)echo ""
	$(AT)echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(GREEN)✅ PRE-DEPLOY CHECKS PASSED$(NC)"
	$(AT)echo "$(GREEN)   Safe to deploy to production$(NC)"
	$(AT)echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

pre-deploy.check:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(BLUE)🔍 Pre-Deploy Verification$(NC)"
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo ""
	$(AT)echo "$(YELLOW)[0/4] Checking services...$(NC)"
	$(AT)$(COMPOSE_DEV_CMD) ps --format "table {{.Service}}\t{{.Status}}" | grep -q "running" || \
		{ echo "$(RED)❌ Services not running. Run 'make dev' first$(NC)"; exit 2; }
	$(AT)echo "$(GREEN)✓ Services are running$(NC)"

pre-deploy.lint:
	$(AT)echo ""
	$(AT)echo "$(YELLOW)[1/4] Linting...$(NC)"
	$(AT)$(COMPOSE_DEV_CMD) exec -T backend ruff check src/ --quiet || \
		{ echo "$(RED)❌ Lint failed$(NC)"; exit 1; }
	$(AT)echo "$(GREEN)✓ Lint passed$(NC)"

pre-deploy.unit:
	$(AT)echo ""
	$(AT)echo "$(YELLOW)[2/4] Unit Tests...$(NC)"
	$(AT)$(COMPOSE_DEV_CMD) exec -T backend pytest tests/unit -q --tb=line 2>/dev/null || \
		{ echo "$(RED)❌ Unit tests failed$(NC)"; exit 1; }
	$(AT)echo "$(GREEN)✓ Unit tests passed$(NC)"

pre-deploy.regression:
	$(AT)echo ""
	$(AT)echo "$(YELLOW)[3/4] Regression Tests...$(NC)"
	$(AT)$(COMPOSE_DEV_CMD) exec -T backend pytest tests/regression -v -m regression --tb=short 2>/dev/null || \
		{ echo "$(RED)❌ Backend regression tests failed$(NC)"; exit 1; }
	$(AT)echo "$(GREEN)✓ Backend regression tests passed$(NC)"

pre-deploy.integration:
	$(AT)echo ""
	$(AT)echo "$(YELLOW)[4/4] Integration Tests...$(NC)"
	$(AT)$(COMPOSE_DEV_CMD) exec -T backend pytest tests/integration -v --tb=short \
		--ignore=tests/integration/test_mcp_tools_integration.py 2>/dev/null || \
		{ echo "$(RED)❌ Integration tests failed$(NC)"; exit 1; }
	$(AT)echo "$(GREEN)✓ Integration tests passed$(NC)"

pre-deploy.quick:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(BLUE)⚡ Quick Pre-Deploy (regression only)$(NC)"
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)$(MAKE) --no-print-directory pre-deploy.check
	$(AT)$(MAKE) --no-print-directory pre-deploy.regression
	$(AT)echo ""
	$(AT)echo "$(GREEN)✅ Quick pre-deploy passed$(NC)"

# Help for pre-deploy
help.pre-deploy:
	$(AT)echo "$(CYAN)🔒 Pre-Deploy Commands:$(NC)"
	$(AT)echo "  $(YELLOW)make pre-deploy$(NC)            - Full verification before deploy"
	$(AT)echo "  $(YELLOW)make pre-deploy.quick$(NC)      - Quick check (regression only)"
	$(AT)echo "  $(YELLOW)make pre-deploy.regression$(NC) - Run regression tests only"
	$(AT)echo "  $(YELLOW)make pre-deploy.lint$(NC)       - Run linting only"
	$(AT)echo "  $(YELLOW)make pre-deploy.unit$(NC)       - Run unit tests only"
	$(AT)echo ""
	$(AT)echo "$(CYAN)Exit Codes:$(NC)"
	$(AT)echo "  0 - All checks passed, safe to deploy"
	$(AT)echo "  1 - Tests failed, DO NOT deploy"
	$(AT)echo "  2 - Infrastructure issue (services not running)"

# ============================================================================
# DEPLOYMENT
# ============================================================================

prod.preflight preflight-prod:
	$(AT)echo "$(YELLOW)🔍 Running preflight checks...$(NC)"
	$(AT)[ -f "$(ENV_FILE)" ] || { echo "$(RED)❌ Env file not found$(NC)"; exit 1; }
	$(AT)sk=$$(grep '^SECRET_KEY=' $(ENV_FILE) | cut -d= -f2-); \
	  [ -n "$$sk" ] && [ $${#sk} -ge 32 ] || { echo "$(RED)❌ SECRET_KEY invalid$(NC)"; exit 1; }
	$(AT)jk=$$(grep '^JWT_SECRET_KEY=' $(ENV_FILE) | cut -d= -f2-); \
	  [ -n "$$jk" ] && [ $${#jk} -ge 32 ] || { echo "$(RED)❌ JWT_SECRET_KEY invalid$(NC)"; exit 1; }
	$(AT)docker compose version >/dev/null 2>&1 || { echo "$(RED)❌ docker compose unavailable$(NC)"; exit 1; }
	$(AT)echo "$(GREEN)✅ Preflight passed$(NC)"

# === Production Build (Consolidated with FLAGS) ===
# Usage:
#   make prod.build                    # Build all services
#   make prod.build SVC=backend        # Build only backend
#   make prod.build SVC="backend web"  # Build multiple services
#   make prod.build CHANGED=1          # Build only changed services
#   make prod.build REGISTRY=1         # Pull from registry instead of build
#
# Examples:
#   make prod.build SVC=backend
#   make prod.build SVC="backend web file-manager"
#   make prod.build CHANGED=1

# Default services to build/pull
SVC ?= backend web file-manager

prod.build:
	$(AT)echo "$(YELLOW)🔨 Production build...$(NC)"
ifeq ($(CHANGED),1)
	$(AT)echo "$(YELLOW)🔍 Detecting changes...$(NC)"
	$(AT)CHANGED_SVC=$$(./scripts/deploy/detect-changes.sh | tail -1); \
	if [ -z "$$CHANGED_SVC" ]; then \
		echo "$(BLUE)ℹ️  No changes detected$(NC)"; \
	else \
		echo "$(YELLOW)🔨 Building: $$CHANGED_SVC$(NC)"; \
		$(COMPOSE_PROD_CMD) build --no-cache $$CHANGED_SVC; \
		echo "$(GREEN)✅ Changed services built$(NC)"; \
	fi
else ifeq ($(REGISTRY),1)
	$(AT)echo "$(BLUE)📥 Pulling $(SVC) from registry...$(NC)"
	$(DRY_RUN) $(COMPOSE_PROD_CMD) pull $(SVC)
	$(AT)echo "$(GREEN)✅ Registry images pulled$(NC)"
else
	$(AT)echo "$(YELLOW)🔨 Building $(SVC)...$(NC)"
	$(DRY_RUN) $(COMPOSE_PROD_CMD) build --no-cache $(SVC)
	$(AT)echo "$(GREEN)✅ Production images built$(NC)"
endif

# === Production Operations (Consolidated with SVC flag) ===
# Usage:
#   make prod.up                    # Start all services
#   make prod.up SVC=backend        # Start only backend
#   make prod.logs                  # View logs of all services
#   make prod.logs SVC=backend      # View logs of backend only
#   make prod.restart SVC=backend   # Restart backend only

prod.up:
	$(AT)echo "$(YELLOW)🚀 Starting production containers...$(NC)"
ifdef SVC
	$(AT)echo "$(BLUE)   Services: $(SVC)$(NC)"
	$(DRY_RUN) $(COMPOSE_PROD_CMD) up -d $(SVC) $(QUIET_FLAG)
else
	$(DRY_RUN) $(COMPOSE_PROD_CMD) up -d $(QUIET_FLAG)
endif
	$(AT)echo "$(GREEN)✅ Production started$(NC)"

prod.status:
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)echo "$(BLUE)📊 Production Status$(NC)"
	$(AT)echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(AT)$(COMPOSE_PROD_CMD) ps

prod.logs:
ifdef SVC
	$(AT)echo "$(BLUE)📋 Logs for: $(SVC)$(NC)"
	$(AT)$(COMPOSE_PROD_CMD) logs --tail=100 $(SVC)
else
	$(AT)echo "$(BLUE)📋 Logs for all services$(NC)"
	$(AT)$(COMPOSE_PROD_CMD) logs --tail=100
endif

prod.restart:
ifdef SVC
	$(AT)echo "$(YELLOW)🔄 Restarting: $(SVC)$(NC)"
	$(DRY_RUN) $(COMPOSE_PROD_CMD) restart $(SVC)
else
	$(AT)echo "$(YELLOW)🔄 Restarting all services$(NC)"
	$(DRY_RUN) $(COMPOSE_PROD_CMD) restart
endif

wait-healthy:
	$(AT)echo "$(YELLOW)⏱  Waiting for services (timeout: $(HEALTH_TIMEOUT)s)...$(NC)"
	$(AT)end=$$((SECONDS+$(HEALTH_TIMEOUT))); \
	while [ $$SECONDS -lt $$end ]; do \
	  curl -sf http://localhost:8000/api/health >/dev/null 2>&1 && \
	  curl -sf http://localhost:8001/health >/dev/null 2>&1 && \
	  curl -sf http://localhost:3000 >/dev/null 2>&1 && \
	  { echo "$(GREEN)✅ All services healthy$(NC)"; exit 0; }; \
	  sleep $(HEALTH_INTERVAL); \
	done; \
	echo "$(RED)❌ Timeout after $(HEALTH_TIMEOUT)s$(NC)"; exit 1

prod: prod.preflight prod.build prod.up wait-healthy prod.status
	$(AT)echo "$(GREEN)🟢 Production deployment complete$(NC)"

deploy-registry:
ifndef VERSION
	$(AT)echo "$(RED)❌ Specify version: make deploy-registry VERSION=0.1.3$(NC)"
	$(AT)exit 1
endif
	$(AT)echo "$(YELLOW)🚀 Deploying from Docker Hub (version $(VERSION))...$(NC)"
	$(DRY_RUN) ./scripts/deploy/deploy-to-production.sh $(VERSION) $(VERBOSE_FLAG)

# ============================================================================
# CLEANUP
# ============================================================================

clean:
	$(AT)echo "$(YELLOW)🧹 Cleaning containers and cache...$(NC)"
	$(DRY_RUN) $(COMPOSE_CMD) down --remove-orphans $(QUIET_FLAG)
	$(DRY_RUN) rm -rf apps/web/.next
	$(AT)echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-deep:
ifneq ($(FORCE),1)
	$(AT)echo "$(RED)⚠️  WARNING: This will delete all data!$(NC)"
	$(AT)read -p "Type 'DELETE' to confirm: " confirm && [ "$$confirm" = "DELETE" ] || exit 1
endif
	$(DRY_RUN) $(COMPOSE_CMD) down -v --remove-orphans
	$(DRY_RUN) rm -rf apps/web/.next
	$(AT)echo "$(GREEN)✅ Deep cleanup complete$(NC)"

clean-cache:
	$(AT)echo "$(YELLOW)🧹 Cleaning cache files...$(NC)"
	$(DRY_RUN) find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	$(DRY_RUN) find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	$(DRY_RUN) find . -type f -name "*.pyc" -delete 2>/dev/null || true
	$(DRY_RUN) rm -rf apps/web/.next apps/web/.turbo
	$(AT)echo "$(GREEN)✅ Cache cleaned$(NC)"

# ============================================================================
# SCRIPT ORCHESTRATION (dot notation pattern)
# ============================================================================

# Generic script runner: make scripts.<category>.<script>
scripts.%:
	$(eval SCRIPT_PATH := $(subst .,/,$(subst scripts.,,scripts.$*)))
	$(AT)if [ -f "$(SCRIPT_PATH).sh" ]; then \
		echo "$(YELLOW)📜 Running $(SCRIPT_PATH).sh$(NC)"; \
		chmod +x "$(SCRIPT_PATH).sh"; \
		$(DRY_RUN) "./$(SCRIPT_PATH).sh" $(VERBOSE_FLAG); \
	elif [ -f "$(SCRIPT_PATH).py" ]; then \
		echo "$(YELLOW)📜 Running $(SCRIPT_PATH).py$(NC)"; \
		$(DRY_RUN) python "$(SCRIPT_PATH).py" $(VERBOSE_FLAG); \
	else \
		echo "$(RED)❌ Script not found: $(SCRIPT_PATH)$(NC)"; \
		exit 1; \
	fi

# Shortcuts for common scripts
scripts.health: scripts.maintenance.health-check
scripts.backup: scripts.database.backup-mongodb
scripts.validate: scripts.testing.validate-mvp
scripts.audit: scripts.security.security-audit

# ============================================================================
# LEGACY ALIASES (backward compatibility)
# ============================================================================

logs-api: logs S=backend
logs-web: logs S=web
logs-aletheia: logs S=aletheia
shell-api: shell S=backend
shell-web: shell S=web
shell-db: shell S=db
shell-aletheia: shell S=aletheia
test-api: test.api
test-web: test.web
test-mcp: test.mcp
test-all: test
db-backup: db.backup
db-restore: db.restore
create-demo-user:
	$(DRY_RUN) $(COMPOSE_CMD) exec -T backend python scripts/create_demo_user.py
verify: health

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs:
	$(AT)echo "$(CYAN)📚 Documentation:$(NC)"
	$(AT)echo "  scripts/README.md              - Scripts organization"
	$(AT)echo "  docs/ARQUITECTURA_SCRIPTS_Y_DOCKER.md - Architecture docs"
	$(AT)echo "  docs/DEPLOY_ANALISIS_Y_GUIA.md - Deployment guide"
	$(AT)echo ""
	$(AT)echo "$(CYAN)🔗 Quick Links:$(NC)"
	$(AT)echo "  make help.dev          - Development commands"
	$(AT)echo "  make help.test         - Testing commands"
	$(AT)echo "  make help.db           - Database commands"
	$(AT)echo "  make help.deploy       - Deployment commands"
	$(AT)echo "  make help.scripts      - Script orchestration"

# ============================================================================
# INSTALLATION & PACKAGE MANAGEMENT
# ============================================================================

install-web:
	$(AT)echo "$(YELLOW)📦 Installing web dependencies...$(NC)"
	$(DRY_RUN) $(COMPOSE_CMD) exec -T web sh -c "cd /app && pnpm install"
	$(AT)echo "$(GREEN)✅ Dependencies installed$(NC)"

install: install-web
	$(AT)echo "$(GREEN)✅ All dependencies installed$(NC)"

# ============================================================================
# BUN RUNTIME (opt-in)
# ============================================================================

help.bun:
	$(AT)echo "$(CYAN)⚡ Bun Runtime Helpers:$(NC)"
	$(AT)echo "  $(YELLOW)make bun.install$(NC)    - bun install $(BUN_INSTALL_FLAGS)"
	$(AT)echo "  $(YELLOW)make bun.dev-web$(NC)    - Next.js dev server via Bun"
	$(AT)echo "  $(YELLOW)make bun.test-web$(NC)   - Jest frontend tests via Bun"
	$(AT)echo "  $(YELLOW)make bun.build-web$(NC)  - Next.js build via Bun"
	$(AT)echo "  $(YELLOW)make bun.start-web$(NC)  - Start built frontend via Bun"

bun.install:
	$(AT)command -v $(BUN) >/dev/null 2>&1 || { echo "$(RED)❌ Bun $(BUN_VERSION) not found. Install from https://bun.sh/install $(NC)"; exit 1; }
	$(AT)echo "$(YELLOW)📦 Installing workspace deps with Bun (version $(BUN_VERSION))$(NC)"
	$(DRY_RUN) $(BUN) install $(BUN_INSTALL_FLAGS)
	$(AT)echo "$(GREEN)✅ Bun install complete$(NC)"

bun.dev-web:
	$(AT)command -v $(BUN) >/dev/null 2>&1 || { echo "$(RED)❌ Bun not found. Install from https://bun.sh/install$(NC)"; exit 1; }
	$(AT)echo "$(YELLOW)⚡ Starting web dev server with Bun...$(NC)"
	$(DRY_RUN) $(BUN) run bun:dev:web

bun.test-web:
	$(AT)command -v $(BUN) >/dev/null 2>&1 || { echo "$(RED)❌ Bun not found. Install from https://bun.sh/install$(NC)"; exit 1; }
	$(AT)echo "$(YELLOW)🧪 Running web tests with Bun...$(NC)"
	$(DRY_RUN) $(BUN) run bun:test:web

bun.build-web:
	$(AT)command -v $(BUN) >/dev/null 2>&1 || { echo "$(RED)❌ Bun not found. Install from https://bun.sh/install$(NC)"; exit 1; }
	$(AT)echo "$(YELLOW)🏗️  Building web with Bun...$(NC)"
	$(DRY_RUN) $(BUN) run bun:build:web

bun.start-web:
	$(AT)command -v $(BUN) >/dev/null 2>&1 || { echo "$(RED)❌ Bun not found. Install from https://bun.sh/install$(NC)"; exit 1; }
	$(AT)echo "$(YELLOW)🚀 Starting built web with Bun...$(NC)"
	$(DRY_RUN) $(BUN) run bun:start:web
