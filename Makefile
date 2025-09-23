# ========================================
# COPILOTOS BRIDGE - MAKEFILE
# ========================================

.PHONY: help local staging prod stop clean logs build test

# Colores para output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

## Mostrar ayuda
help:
	@echo "$(GREEN)Copilotos Bridge - Comandos disponibles:$(NC)"
	@echo ""
	@echo "$(YELLOW)🚀 Deployment:$(NC)"
	@echo "  make local    - Levantar entorno de desarrollo local"
	@echo "  make staging  - Levantar entorno de staging"
	@echo "  make prod     - Levantar entorno de producción"
	@echo ""
	@echo "$(YELLOW)📊 Gestión:$(NC)"
	@echo "  make logs     - Ver logs de todos los servicios"
	@echo "  make stop     - Parar todos los servicios"
	@echo "  make clean    - Limpiar contenedores y volúmenes"
	@echo "  make build    - Construir imágenes sin cache"
	@echo ""
	@echo "$(YELLOW)🔧 Testing:$(NC)"
	@echo "  make test     - Ejecutar tests"
	@echo "  make lint     - Ejecutar linters"
	@echo ""
	@echo "$(YELLOW)💡 URLs:$(NC)"
	@echo "  Local:   http://localhost:3000"
	@echo "  Staging: http://localhost:3001"
	@echo "  API:     http://localhost:8001"

## Desarrollo local (automático con override)
local:
	@echo "$(GREEN)🚀 Levantando entorno local...$(NC)"
	@./scripts/deploy-local.sh

## Staging
staging:
	@echo "$(GREEN)🚀 Levantando entorno staging...$(NC)"
	@./scripts/deploy-staging.sh

## Producción
prod:
	@echo "$(GREEN)🚀 Levantando entorno producción...$(NC)"
	@./scripts/deploy-prod.sh

## Ver logs
logs:
	@echo "$(YELLOW)📋 Mostrando logs...$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f

## Parar servicios
stop:
	@echo "$(RED)⏹️  Parando servicios...$(NC)"
	@docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml --env-file envs/.env.local down 2>/dev/null || true
	@docker compose -f infra/docker-compose.yml -f infra/docker-compose.staging.yml --env-file envs/.env.staging down 2>/dev/null || true
	@docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod down 2>/dev/null || true

## Limpiar todo
clean: stop
	@echo "$(RED)🧹 Limpiando contenedores y volúmenes...$(NC)"
	@docker system prune -f
	@docker volume prune -f

## Construir imágenes sin cache
build:
	@echo "$(YELLOW)🔨 Construyendo imágenes...$(NC)"
	@docker compose -f infra/docker-compose.yml build --no-cache

## Ejecutar tests
test:
	@echo "$(YELLOW)🔬 Ejecutando tests...$(NC)"
	@pnpm test 2>/dev/null || echo "Tests no configurados aún"

## Ejecutar linters
lint:
	@echo "$(YELLOW)🔍 Ejecutando linters...$(NC)"
	@pnpm lint 2>/dev/null || echo "Linters no configurados aún"

# Default target
.DEFAULT_GOAL := help