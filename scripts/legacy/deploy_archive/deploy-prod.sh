#!/bin/bash
# PRODUCTION DEPLOYMENT SCRIPT
set -e
echo "▸ Deploying production..."
COMPOSE_BASE="infra/docker-compose.yml"
COMPOSE_PROD="infra/docker-compose.prod.yml"
ENV_FILE="envs/.env.prod"

COMPOSE_ARGS=(-f "$COMPOSE_BASE")
if [ -f "$COMPOSE_PROD" ]; then
  echo "▸ Usando override de producción: $COMPOSE_PROD"
  COMPOSE_ARGS+=(-f "$COMPOSE_PROD")
fi

docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" up -d
echo "✔ Production deployed"
