#!/bin/bash
# ========================================
# COPILOT OS - LOCAL DEPLOYMENT
# ========================================
# Script para desarrollo local
# Uso: ./scripts/deploy-local.sh

set -e

echo "▸ Iniciando deployment local de Copilot OS..."

# Verificar que estamos en el directorio correcto
if [ ! -f "infra/docker-compose.yml" ]; then
    echo "✖ Error: Ejecutar desde el directorio raíz del proyecto"
    exit 1
fi

# Archivos de compose
COMPOSE_BASE="infra/docker-compose.yml"
COMPOSE_OVERRIDE="infra/docker-compose.override.yml"
ENV_FILE="envs/.env.local"

COMPOSE_ARGS=(-f "$COMPOSE_BASE")
if [ -f "$COMPOSE_OVERRIDE" ]; then
    echo "▸ Usando override: $COMPOSE_OVERRIDE"
    COMPOSE_ARGS+=(-f "$COMPOSE_OVERRIDE")
fi

# Parar servicios existentes
echo "▲  Parando servicios existentes..."
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" down 2>/dev/null || true

# Construir imágenes
echo "▸ Construyendo imágenes..."
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" build

# Levantar servicios
echo "▸  Levantando servicios..."
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" up -d

# Esperar que los servicios estén saludables
echo "▸ Esperando que los servicios estén listos..."
for i in {1..30}; do
    if docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" ps | grep -q "healthy"; then
        echo "✔ Servicios saludables!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "▲  Timeout esperando servicios saludables"
        docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" ps
        exit 1
    fi
    sleep 2
done

# Mostrar estado final
echo ""
echo "▸ Estado de los servicios:"
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" ps

echo ""
echo "◆ Deployment local completado!"
echo "▸ Frontend: http://localhost:3000"
echo "▸ API: http://localhost:8001"
echo "▸  MongoDB: localhost:27017"
echo "✖ Redis: localhost:6379"
echo ""
echo "▸ Para ver logs: docker compose ${COMPOSE_ARGS[*]} --env-file $ENV_FILE logs -f"
echo "▲  Para parar: docker compose ${COMPOSE_ARGS[*]} --env-file $ENV_FILE down"
