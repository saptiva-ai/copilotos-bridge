#!/bin/bash
# STAGING DEPLOYMENT SCRIPT
set -e
echo "🚀 Deploying staging..."
COMPOSE_BASE="infra/docker-compose.yml"
COMPOSE_STAGING="infra/docker-compose.staging.yml"
ENV_FILE="envs/.env.staging"

COMPOSE_ARGS=(-f "$COMPOSE_BASE")
if [ -f "$COMPOSE_STAGING" ]; then
  echo "🧩 Usando override de staging: $COMPOSE_STAGING"
  COMPOSE_ARGS+=(-f "$COMPOSE_STAGING")
fi

docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" up -d --build
echo "✅ Staging deployed at http://localhost:3001"
