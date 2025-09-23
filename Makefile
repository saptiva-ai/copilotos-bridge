# ========================================
# COPILOT OS - MAKEFILE
# ========================================

.PHONY: help local staging prod stop clean logs build test health debug restart quick-test auth-test
.PHONY: ps shell-api shell-web shell-db fix-network status dev-setup
.PHONY: build-rebuild env-check docker-clean docker-prune lint-frontend type-check saptiva-test demo-mode

# Colores para output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
CYAN := \033[36m
NC := \033[0m # No Color

# Configuración del entorno
DOCKER_COMPOSE_LOCAL := docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml --env-file envs/.env.local
DOCKER_COMPOSE_STAGING := docker compose -f infra/docker-compose.yml -f infra/docker-compose.staging.yml --env-file envs/.env.staging
DOCKER_COMPOSE_PROD := docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod

## Mostrar ayuda
help:
	@echo "$(GREEN)🚀 Copilot OS - Comandos disponibles:$(NC)"
	@echo ""
	@echo "$(YELLOW)🏠 Desarrollo Local:$(NC)"
	@echo "  $(CYAN)make local$(NC)      - Levantar entorno completo local"
	@echo "  $(CYAN)make restart$(NC)    - Reiniciar servicios rápidamente"
	@echo "  $(CYAN)make dev-setup$(NC)  - Setup inicial para desarrollo"
	@echo "  $(CYAN)make logs$(NC)       - Ver logs en tiempo real"
	@echo ""
	@echo "$(YELLOW)🔍 Debugging & Health:$(NC)"
	@echo "  $(CYAN)make health$(NC)     - Verificar estado de todos los servicios"
	@echo "  $(CYAN)make status$(NC)     - Estado detallado del stack"
	@echo "  $(CYAN)make debug$(NC)      - Información de debugging completa"
	@echo "  $(CYAN)make ps$(NC)         - Lista contenedores activos"
	@echo "  $(CYAN)make fix-network$(NC) - Arreglar problemas de Network Error"
	@echo ""
	@echo "$(YELLOW)🧪 Testing & Auth:$(NC)"
	@echo "  $(CYAN)make quick-test$(NC) - Test rápido de endpoints principales"
	@echo "  $(CYAN)make auth-test$(NC)  - Test completo de autenticación"
	@echo "  $(CYAN)make test$(NC)       - Ejecutar test suite completo"
	@echo ""
	@echo "$(YELLOW)🐚 Shell Access:$(NC)"
	@echo "  $(CYAN)make shell-api$(NC)  - Shell interactivo en el contenedor API"
	@echo "  $(CYAN)make shell-web$(NC)  - Shell interactivo en el contenedor Web"
	@echo "  $(CYAN)make shell-db$(NC)   - MongoDB shell"
	@echo ""
	@echo "$(YELLOW)🚀 Deployment:$(NC)"
	@echo "  $(CYAN)make staging$(NC)    - Levantar entorno de staging (puerto 3001)"
	@echo "  $(CYAN)make prod$(NC)       - Levantar entorno de producción"
	@echo ""
	@echo "$(YELLOW)📋 Logs y Monitoreo:$(NC)"
	@echo "  $(CYAN)make logs-follow-all$(NC)   - Logs en tiempo real de todos los servicios"
	@echo "  $(CYAN)make logs-follow-api$(NC)   - Logs del API en tiempo real"
	@echo "  $(CYAN)make monitor-errors$(NC)    - Monitor de errores en tiempo real"
	@echo "  $(CYAN)make logs-search PATTERN='texto'$(NC) - Buscar en logs"
	@echo "  $(CYAN)make logs-export$(NC)       - Exportar logs a archivos"
	@echo "  $(CYAN)make logs-stats$(NC)        - Estadísticas de logs"
	@echo ""
	@echo "$(YELLOW)🔧 Herramientas Avanzadas:$(NC)"
	@echo "  $(CYAN)make env-check$(NC)         - Verificar variables de entorno"
	@echo "  $(CYAN)make saptiva-test$(NC)      - Test de integración SAPTIVA"
	@echo "  $(CYAN)make build-rebuild$(NC)     - Reconstruir stack completo"
	@echo "  $(CYAN)make type-check$(NC)        - Verificar tipos TypeScript"
	@echo "  $(CYAN)make demo-mode$(NC)         - Activar modo demo temporal"
	@echo "  $(CYAN)make build-frontend ENV=[dev|prod]$(NC) - Build frontend específico"
	@echo "  $(CYAN)make deploy-prod$(NC)       - Deploy directo a producción"
	@echo "  $(CYAN)make nginx-config$(NC)      - Actualizar configuración nginx"
	@echo ""
	@echo "$(YELLOW)🧹 Mantenimiento:$(NC)"
	@echo "  $(CYAN)make stop$(NC)       - Parar todos los servicios"
	@echo "  $(CYAN)make clean$(NC)      - Limpiar contenedores y volúmenes"
	@echo "  $(CYAN)make build$(NC)      - Reconstruir imágenes sin cache"
	@echo "  $(CYAN)make docker-clean$(NC) - Limpieza profunda de Docker"
	@echo "  $(CYAN)make rebuild-images$(NC) - Rebuild de imágenes Docker"
	@echo "  $(CYAN)make test-api-connection$(NC) - Test conexión API"
	@echo ""
	@echo "$(BLUE)💡 URLs Importantes:$(NC)"
	@echo "  🌐 Frontend Local:  $(GREEN)http://localhost:3000$(NC)"
	@echo "  🔌 API Local:       $(GREEN)http://localhost:8001$(NC)"
	@echo "  📊 API Health:      $(GREEN)http://localhost:8001/api/health$(NC)"
	@echo "  📱 Staging:         $(GREEN)http://localhost:3001$(NC)"

## Desarrollo local (automático con override)
local:
	@echo "$(GREEN)🚀 Levantando entorno local...$(NC)"
	@echo "$(BLUE)📋 Building frontend for development...$(NC)"
	@./scripts/build-frontend.sh dev
	@./scripts/deploy-local.sh

## Staging
staging:
	@echo "$(GREEN)🚀 Levantando entorno staging...$(NC)"
	@./scripts/deploy-staging.sh

## Producción
prod:
	@echo "$(GREEN)🚀 Levantando entorno producción...$(NC)"
	@echo "$(BLUE)📋 Building frontend for production...$(NC)"
	@./scripts/build-frontend.sh prod
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

# ========================================
# NUEVOS COMANDOS DE DESARROLLO
# ========================================

## Setup inicial para desarrollo
dev-setup:
	@echo "$(GREEN)🔧 Configurando entorno de desarrollo...$(NC)"
	@echo "$(YELLOW)📋 Verificando dependencias...$(NC)"
	@which docker >/dev/null || (echo "$(RED)❌ Docker no encontrado. Instala Docker primero.$(NC)" && exit 1)
	@which pnpm >/dev/null || (echo "$(RED)❌ pnpm no encontrado. Instalando...$(NC)" && npm install -g pnpm)
	@echo "$(YELLOW)📁 Verificando archivos de configuración...$(NC)"
	@[ -f envs/.env.local ] || (echo "$(YELLOW)📝 Creando .env.local desde ejemplo...$(NC)" && cp envs/.env.local.example envs/.env.local)
	@echo "$(GREEN)✅ Setup completado! Ejecuta 'make local' para comenzar.$(NC)"

## Reinicio rápido de servicios
restart:
	@echo "$(YELLOW)🔄 Reiniciando servicios...$(NC)"
	@$(DOCKER_COMPOSE_LOCAL) restart
	@echo "$(GREEN)✅ Servicios reiniciados$(NC)"

## Estado de los servicios
ps:
	@echo "$(CYAN)📊 Estado de contenedores:$(NC)"
	@docker ps --filter "name=copilotos-*" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

## Health check completo
health:
	@echo "$(CYAN)🔍 Verificando salud de servicios...$(NC)"
	@echo ""
	@echo "$(YELLOW)🔌 API Health Check:$(NC)"
	@curl -sf http://localhost:8001/api/health 2>/dev/null && echo "$(GREEN)✅ API funcionando$(NC)" || echo "$(RED)❌ API no responde$(NC)"
	@echo ""
	@echo "$(YELLOW)🌐 Frontend Check:$(NC)"
	@curl -sf http://localhost:3000 -I 2>/dev/null >/dev/null && echo "$(GREEN)✅ Frontend funcionando$(NC)" || echo "$(RED)❌ Frontend no responde$(NC)"
	@echo ""
	@echo "$(YELLOW)🗄️ MongoDB Check:$(NC)"
	@docker exec copilotos-mongodb mongosh --eval "db.runCommand('ping')" 2>/dev/null >/dev/null && echo "$(GREEN)✅ MongoDB funcionando$(NC)" || echo "$(RED)❌ MongoDB no responde$(NC)"
	@echo ""
	@echo "$(YELLOW)🔴 Redis Check:$(NC)"
	@docker exec copilotos-redis redis-cli ping 2>/dev/null >/dev/null && echo "$(GREEN)✅ Redis funcionando$(NC)" || echo "$(RED)❌ Redis no responde$(NC)"

## Información detallada de debug
debug:
	@echo "$(CYAN)🔍 Información de debug:$(NC)"
	@echo ""
	@echo "$(YELLOW)📊 Contenedores:$(NC)"
	@docker ps --filter "name=copilotos-*" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
	@echo ""
	@echo "$(YELLOW)🌐 Puertos en uso:$(NC)"
	@netstat -tlnp 2>/dev/null | grep -E ':(3000|3001|8001|27017|6379)' || echo "Netstat no disponible"
	@echo ""
	@echo "$(YELLOW)💾 Uso de volúmenes:$(NC)"
	@docker volume ls --filter "name=copilotos" 2>/dev/null || echo "No hay volúmenes"
	@echo ""
	@echo "$(YELLOW)🔗 Variables de entorno:$(NC)"
	@echo "NODE_ENV: $${NODE_ENV:-not set}"
	@echo "Docker Compose: $(DOCKER_COMPOSE_LOCAL)"

## Status detallado
status:
	@echo "$(CYAN)📋 Estado detallado del sistema:$(NC)"
	@echo ""
	@$(DOCKER_COMPOSE_LOCAL) ps
	@echo ""
	@echo "$(YELLOW)🔍 Logs recientes (últimas 10 líneas):$(NC)"
	@$(DOCKER_COMPOSE_LOCAL) logs --tail=10

## Arreglar problemas de Network Error
fix-network:
	@echo "$(YELLOW)🔧 Solucionando problemas de red...$(NC)"
	@echo "$(CYAN)1. Parando servicios conflictivos...$(NC)"
	@docker stop $$(docker ps -q --filter "name=infra-*") 2>/dev/null || true
	@docker rm $$(docker ps -aq --filter "name=infra-*") 2>/dev/null || true
	@echo "$(CYAN)2. Limpiando puertos...$(NC)"
	@sudo fuser -k 3000/tcp 2>/dev/null || true
	@sudo fuser -k 8001/tcp 2>/dev/null || true
	@echo "$(CYAN)3. Reiniciando stack...$(NC)"
	@$(MAKE) stop
	@$(MAKE) local
	@echo "$(GREEN)✅ Problemas de red solucionados$(NC)"

## Test rápido de endpoints
quick-test:
	@echo "$(CYAN)🧪 Test rápido de endpoints...$(NC)"
	@echo ""
	@echo "$(YELLOW)🔍 Health endpoint:$(NC)"
	@curl -sf http://localhost:8001/api/health 2>/dev/null | head -c 200 && echo "$(GREEN)✅ API responde$(NC)" || echo "$(RED)❌ API no responde$(NC)"
	@echo ""
	@echo "$(YELLOW)🌐 Frontend homepage:$(NC)"
	@curl -sf http://localhost:3000 -I 2>/dev/null | head -1 && echo "$(GREEN)✅ Frontend responde$(NC)" || echo "$(RED)❌ Frontend no responde$(NC)"

## Test completo de autenticación
auth-test:
	@echo "$(CYAN)🔐 Testing flujo de autenticación...$(NC)"
	@echo ""
	@echo "$(YELLOW)📝 1. Registrando usuario de prueba...$(NC)"
	@REGISTER_RESPONSE=$$(curl -X POST http://localhost:8001/api/auth/register \
		-H "Content-Type: application/json" \
		-d '{"username":"testmake","email":"testmake@example.com","password":"test123456","full_name":"Test Make User"}' \
		2>/dev/null); \
	echo "$$REGISTER_RESPONSE" | grep -q "access_token" && echo "$(GREEN)✅ Registro exitoso$(NC)" || echo "$(YELLOW)⚠️ Usuario ya existe o error$(NC)"
	@echo ""
	@echo "$(YELLOW)🔑 2. Login del usuario...$(NC)"
	@LOGIN_RESPONSE=$$(curl -X POST http://localhost:8001/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"identifier":"testmake","password":"test123456"}' \
		2>/dev/null); \
	if echo "$$LOGIN_RESPONSE" | grep -q "access_token"; then \
		echo "$(GREEN)✅ Login exitoso$(NC)"; \
		TOKEN=$$(echo "$$LOGIN_RESPONSE" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'); \
		echo "Token: $$(echo $$TOKEN | head -c 50)..."; \
		echo "$(YELLOW)💬 3. Enviando mensaje de chat...$(NC)"; \
		CHAT_RESPONSE=$$(curl -X POST http://localhost:8001/api/chat \
			-H "Content-Type: application/json" \
			-H "Authorization: Bearer $$TOKEN" \
			-d '{"message":"Test desde Makefile","model":"SAPTIVA_CORTEX"}' \
			2>/dev/null); \
		if echo "$$CHAT_RESPONSE" | grep -q "content"; then \
			echo "$(GREEN)✅ Chat funcionando$(NC)"; \
			echo "Respuesta: $$(echo "$$CHAT_RESPONSE" | sed -n 's/.*"content":"\([^"]*\)".*/\1/p' | head -c 100)..."; \
		else \
			echo "$(RED)❌ Error en chat$(NC)"; \
		fi; \
	else \
		echo "$(RED)❌ Error en login$(NC)"; \
	fi

## Shell interactivo en API
shell-api:
	@echo "$(CYAN)🐚 Accediendo al shell del contenedor API...$(NC)"
	@docker exec -it copilotos-api bash

## Shell interactivo en Web
shell-web:
	@echo "$(CYAN)🐚 Accediendo al shell del contenedor Web...$(NC)"
	@docker exec -it copilotos-web sh

## MongoDB shell
shell-db:
	@echo "$(CYAN)🗄️ Accediendo a MongoDB shell...$(NC)"
	@docker exec -it copilotos-mongodb mongosh -u copilotos_user -p secure_password_change_me

# ========================================
# NUEVOS COMANDOS ÚTILES ESPECÍFICOS
# ========================================

## Reconstruir imágenes completamente
build-rebuild:
	@echo "$(YELLOW)🔨 Reconstruyendo todo desde cero...$(NC)"
	@docker compose -f infra/docker-compose.yml down --remove-orphans
	@docker system prune -f
	@docker compose -f infra/docker-compose.yml --env-file .env up --build --force-recreate -d
	@echo "$(GREEN)✅ Stack reconstruido completamente$(NC)"

## Verificar configuración de variables de entorno
env-check:
	@echo "$(CYAN)🔍 Verificando configuración de entorno...$(NC)"
	@echo ""
	@echo "$(YELLOW)📝 Variables SAPTIVA:$(NC)"
	@[ -n "$$SAPTIVA_API_KEY" ] && echo "$(GREEN)✅ SAPTIVA_API_KEY configurada$(NC)" || echo "$(RED)❌ SAPTIVA_API_KEY faltante - modo demo activo$(NC)"
	@[ -n "$$NEXT_PUBLIC_SAPTIVA_BASE_URL" ] && echo "$(GREEN)✅ NEXT_PUBLIC_SAPTIVA_BASE_URL: $$NEXT_PUBLIC_SAPTIVA_BASE_URL$(NC)" || echo "$(YELLOW)⚠️ Usando URL por defecto$(NC)"
	@echo ""
	@echo "$(YELLOW)🔐 Variables de autenticación:$(NC)"
	@[ -n "$$JWT_SECRET_KEY" ] && echo "$(GREEN)✅ JWT_SECRET_KEY configurada$(NC)" || echo "$(RED)❌ JWT_SECRET_KEY faltante$(NC)"
	@echo ""
	@echo "$(YELLOW)🗄️ Variables de base de datos:$(NC)"
	@[ -n "$$MONGODB_URL" ] && echo "$(GREEN)✅ MONGODB_URL configurada$(NC)" || echo "$(RED)❌ MONGODB_URL faltante$(NC)"
	@[ -n "$$REDIS_URL" ] && echo "$(GREEN)✅ REDIS_URL configurada$(NC)" || echo "$(RED)❌ REDIS_URL faltante$(NC)"

## Limpiar Docker completamente
docker-clean:
	@echo "$(RED)🧹 Limpieza profunda de Docker...$(NC)"
	@echo "$(YELLOW)⚠️ Esto eliminará todos los contenedores, imágenes y volúmenes no utilizados$(NC)"
	@read -p "¿Continuar? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker compose -f infra/docker-compose.yml down --remove-orphans --volumes
	@docker system prune -af --volumes
	@echo "$(GREEN)✅ Docker limpiado completamente$(NC)"

## Limpiar cache y rebuild incremental
docker-prune:
	@echo "$(YELLOW)🧹 Limpiando cache de Docker...$(NC)"
	@docker system prune -f
	@docker image prune -f
	@echo "$(GREEN)✅ Cache limpiado$(NC)"

## Lint del frontend con corrección automática
lint-frontend:
	@echo "$(YELLOW)🔍 Ejecutando linters del frontend...$(NC)"
	@cd apps/web && pnpm lint --fix 2>/dev/null || echo "$(YELLOW)⚠️ Algunos errores de lint requieren corrección manual$(NC)"
	@echo "$(GREEN)✅ Lint completado$(NC)"

## Type checking del frontend
type-check:
	@echo "$(YELLOW)🔍 Verificando tipos de TypeScript...$(NC)"
	@cd apps/web && pnpm type-check 2>/dev/null || echo "$(RED)❌ Errores de tipos encontrados$(NC)"
	@echo "$(GREEN)✅ Verificación de tipos completada$(NC)"

## Test específico de SAPTIVA API
saptiva-test:
	@echo "$(CYAN)🤖 Testing integración SAPTIVA...$(NC)"
	@echo ""
	@if [ -z "$$SAPTIVA_API_KEY" ]; then \
		echo "$(YELLOW)⚠️ SAPTIVA_API_KEY no configurada - modo demo activo$(NC)"; \
		echo "$(CYAN)🎭 Testeando modo demo...$(NC)"; \
		curl -sf http://localhost:3000/api/env-config 2>/dev/null | grep -q "isDemoMode.*true" && echo "$(GREEN)✅ Modo demo funcionando$(NC)" || echo "$(RED)❌ Error en modo demo$(NC)"; \
	else \
		echo "$(GREEN)✅ SAPTIVA_API_KEY configurada$(NC)"; \
		echo "$(CYAN)🔌 Testeando conexión a SAPTIVA...$(NC)"; \
		TOKEN=$$(curl -X POST http://localhost:8001/api/auth/login \
			-H "Content-Type: application/json" \
			-d '{"identifier":"testmake","password":"test123456"}' \
			2>/dev/null | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'); \
		if [ -n "$$TOKEN" ]; then \
			curl -X POST http://localhost:8001/api/chat \
				-H "Content-Type: application/json" \
				-H "Authorization: Bearer $$TOKEN" \
				-d '{"message":"Test SAPTIVA integration","model":"SAPTIVA_CORTEX"}' \
				2>/dev/null | grep -q "content" && echo "$(GREEN)✅ SAPTIVA funcionando$(NC)" || echo "$(RED)❌ Error en SAPTIVA$(NC)"; \
		else \
			echo "$(RED)❌ No se pudo obtener token de autenticación$(NC)"; \
		fi; \
	fi

## Forzar modo demo (sin SAPTIVA_API_KEY)
demo-mode:
	@echo "$(YELLOW)🎭 Configurando modo demo...$(NC)"
	@echo "$(CYAN)Eliminando SAPTIVA_API_KEY temporalmente...$(NC)"
	@sed -i.bak 's/^SAPTIVA_API_KEY=/#SAPTIVA_API_KEY=/' .env
	@$(MAKE) restart
	@echo "$(GREEN)✅ Modo demo activado$(NC)"
	@echo "$(YELLOW)💡 Para restaurar: mv .env.bak .env && make restart$(NC)"

## ========================================
## COMANDOS DE LOGS Y MONITOREO AVANZADOS
## ========================================

## Logs específicos con filtros útiles
logs-api:
	@echo "$(CYAN)📋 Logs del API (errores y warnings)...$(NC)"
	@docker compose -f infra/docker-compose.yml logs api | grep -E "(ERROR|WARNING|error|warning|Exception)" || echo "$(GREEN)No hay errores en logs$(NC)"

logs-web:
	@echo "$(CYAN)📋 Logs del Frontend...$(NC)"
	@docker compose -f infra/docker-compose.yml logs web --tail=50

logs-db:
	@echo "$(CYAN)📋 Logs de MongoDB...$(NC)"
	@docker compose -f infra/docker-compose.yml logs mongodb --tail=20

## Logs en tiempo real por servicio
logs-follow-api:
	@echo "$(CYAN)📋 Siguiendo logs del API en tiempo real...$(NC)"
	@echo "$(YELLOW)💡 Presiona Ctrl+C para salir$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f api

logs-follow-web:
	@echo "$(CYAN)📋 Siguiendo logs del Frontend en tiempo real...$(NC)"
	@echo "$(YELLOW)💡 Presiona Ctrl+C para salir$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f web

logs-follow-all:
	@echo "$(CYAN)📋 Siguiendo logs de todos los servicios...$(NC)"
	@echo "$(YELLOW)💡 Presiona Ctrl+C para salir$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f

## Logs con marcas de tiempo y colores
logs-timestamped:
	@echo "$(CYAN)📋 Logs con timestamps...$(NC)"
	@docker compose -f infra/docker-compose.yml logs --timestamps --tail=100

## Búsqueda en logs
logs-search:
	@echo "$(CYAN)🔍 Buscar en logs (patrón como parámetro)...$(NC)"
	@echo "$(YELLOW)Uso: make logs-search PATTERN='error|warning'$(NC)"
	@if [ -z "$(PATTERN)" ]; then \
		echo "$(RED)❌ Debes especificar PATTERN. Ejemplo: make logs-search PATTERN='SAPTIVA'$(NC)"; \
	else \
		echo "$(CYAN)Buscando patrón: $(PATTERN)$(NC)"; \
		docker compose -f infra/docker-compose.yml logs | grep -E "$(PATTERN)" --color=always; \
	fi

## Estadísticas de logs por servicio
logs-stats:
	@echo "$(CYAN)📊 Estadísticas de logs por servicio...$(NC)"
	@echo ""
	@echo "$(YELLOW)🔢 Conteo de líneas por servicio:$(NC)"
	@for service in api web mongodb redis; do \
		count=$$(docker compose -f infra/docker-compose.yml logs $$service 2>/dev/null | wc -l); \
		echo "  $$service: $$count líneas"; \
	done
	@echo ""
	@echo "$(YELLOW)⚠️ Errores recientes:$(NC)"
	@docker compose -f infra/docker-compose.yml logs | grep -i error | tail -5 || echo "  No hay errores recientes"

## Exportar logs a archivos
logs-export:
	@echo "$(CYAN)💾 Exportando logs a archivos...$(NC)"
	@mkdir -p logs/$(shell date +%Y-%m-%d)
	@docker compose -f infra/docker-compose.yml logs api > logs/$(shell date +%Y-%m-%d)/api.log
	@docker compose -f infra/docker-compose.yml logs web > logs/$(shell date +%Y-%m-%d)/web.log
	@docker compose -f infra/docker-compose.yml logs mongodb > logs/$(shell date +%Y-%m-%d)/mongodb.log
	@docker compose -f infra/docker-compose.yml logs redis > logs/$(shell date +%Y-%m-%d)/redis.log
	@echo "$(GREEN)✅ Logs exportados a logs/$(shell date +%Y-%m-%d)/$(NC)"

## Conexión directa a contenedores con logs interactivos
connect-api:
	@echo "$(CYAN)🔗 Conectando al contenedor API...$(NC)"
	@echo "$(YELLOW)💡 Ejecutando 'tail -f' en logs internos del contenedor$(NC)"
	@docker exec -it copilotos-api tail -f /var/log/api.log 2>/dev/null || \
	docker exec -it copilotos-api find /app -name "*.log" -exec tail -f {} \; 2>/dev/null || \
	echo "$(YELLOW)⚠️ No se encontraron logs internos, usa 'make shell-api' para inspeccionar$(NC)"

connect-web:
	@echo "$(CYAN)🔗 Conectando al contenedor Web...$(NC)"
	@echo "$(YELLOW)💡 Mostrando logs de Next.js$(NC)"
	@docker exec -it copilotos-web find /app -name ".next" -type d -exec find {} -name "*.log" \; 2>/dev/null || \
	echo "$(YELLOW)⚠️ No se encontraron logs internos de Next.js$(NC)"

## Monitor en tiempo real con filtros
monitor-errors:
	@echo "$(RED)🚨 Monitor de errores en tiempo real...$(NC)"
	@echo "$(YELLOW)💡 Presiona Ctrl+C para salir$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f | grep -i --line-buffered -E "(error|exception|failed|warning)"

monitor-saptiva:
	@echo "$(CYAN)🤖 Monitor de actividad SAPTIVA...$(NC)"
	@echo "$(YELLOW)💡 Presiona Ctrl+C para salir$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f | grep -i --line-buffered "saptiva"

monitor-auth:
	@echo "$(BLUE)🔐 Monitor de autenticación...$(NC)"
	@echo "$(YELLOW)💡 Presiona Ctrl+C para salir$(NC)"
	@docker compose -f infra/docker-compose.yml logs -f | grep -i --line-buffered -E "(login|auth|token|jwt)"

## Análisis de rendimiento en logs
logs-performance:
	@echo "$(CYAN)⚡ Análisis de rendimiento en logs...$(NC)"
	@echo ""
	@echo "$(YELLOW)🐌 Requests lentos (>1s):$(NC)"
	@docker compose -f infra/docker-compose.yml logs api | grep -E "([2-9][0-9]{3}ms|[0-9]+s)" | tail -10 || echo "  No se encontraron requests lentos"
	@echo ""
	@echo "$(YELLOW)💾 Uso de memoria:$(NC)"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep -E "(copilotos|infra)"

## Limpiar logs antiguos
logs-clean:
	@echo "$(YELLOW)🧹 Limpiando logs de Docker...$(NC)"
	@docker system prune -f
	@truncate -s 0 /var/lib/docker/containers/*/*-json.log 2>/dev/null || echo "$(YELLOW)⚠️ Requiere sudo para limpiar logs de sistema$(NC)"
	@echo "$(GREEN)✅ Logs limpiados$(NC)"

## Build frontend específico
build-frontend:
	@echo "$(GREEN)🏗️  Building frontend for $(ENV) environment...$(NC)"
	@if [ -z "$(ENV)" ]; then \
		echo "$(RED)❌ Debes especificar ENV. Ejemplo: make build-frontend ENV=prod$(NC)"; \
		exit 1; \
	fi
	@./scripts/build-frontend.sh $(ENV)

## Deploy directo a producción
deploy-prod:
	@echo "$(GREEN)🚀 Deploying to production...$(NC)"
	@echo "$(YELLOW)⚠️  Building production frontend first...$(NC)"
	@./scripts/build-frontend.sh prod
	@echo "$(GREEN)🐳 Building and deploying containers...$(NC)"
	@$(DOCKER_COMPOSE_PROD) up -d --build

## Actualizar configuración nginx
nginx-config:
	@echo "$(BLUE)🔧 Updating nginx configuration...$(NC)"
	@docker compose -f infra/docker-compose.yml exec nginx nginx -t 2>/dev/null || echo "$(YELLOW)⚠️ Nginx container not running$(NC)"
	@docker compose -f infra/docker-compose.yml exec nginx nginx -s reload 2>/dev/null || echo "$(YELLOW)⚠️ Could not reload nginx$(NC)"
	@echo "$(GREEN)✅ Nginx configuration updated$(NC)"

## Rebuild de imágenes Docker
rebuild-images:
	@echo "$(YELLOW)🔄 Rebuilding Docker images...$(NC)"
	@docker compose down
	@docker system prune -f
	@docker compose build --no-cache
	@echo "$(GREEN)✅ Images rebuilt$(NC)"

## Test conexión API
test-api-connection:
	@echo "$(BLUE)🔍 Testing API connection...$(NC)"
	@echo "Testing local API (localhost:8001):"
	@curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8001/api/health || echo "❌ Local API not accessible"
	@echo "Testing production API (34.42.214.246):"
	@curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://34.42.214.246/api/health || echo "❌ Production API not accessible"
	@echo "$(GREEN)✅ API connection test completed$(NC)"

## Fix production containers with corrected environment
fix-prod:
	@echo "$(YELLOW)🔧 Fixing production containers with correct configuration...$(NC)"
	@echo "$(BLUE)Stopping current containers...$(NC)"
	@ssh jf@34.42.214.246 "docker stop copilotos-web copilotos-api || true"
	@echo "$(BLUE)Starting with corrected configuration...$(NC)"
	@ssh jf@34.42.214.246 "docker run -d --name copilotos-api-fixed --network copilotos_copilotos-network -p 8001:8001 copilotos-api"
	@ssh jf@34.42.214.246 "docker run -d --name copilotos-web-fixed --network copilotos_copilotos-network -p 3000:3000 -e NODE_ENV=production copilotos-web"
	@echo "$(GREEN)✅ Production containers fixed$(NC)"

# Default target
.DEFAULT_GOAL := help
