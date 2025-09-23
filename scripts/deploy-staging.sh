#!/bin/bash
# STAGING DEPLOYMENT SCRIPT
set -e
echo "🚀 Deploying staging..."
docker compose -f infra/docker-compose.yml -f infra/docker-compose.staging.yml --env-file envs/.env.staging up -d --build
echo "✅ Staging deployed at http://localhost:3001"