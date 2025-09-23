#!/bin/bash
# PRODUCTION DEPLOYMENT SCRIPT
set -e
echo "🚀 Deploying production..."
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml --env-file envs/.env.prod up -d
echo "✅ Production deployed"
