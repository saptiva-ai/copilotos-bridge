#!/bin/bash
# Temporary script to start services with env vars loaded

export SECRET_KEY=$(grep '^SECRET_KEY=' envs/.env | cut -d'=' -f2)
export JWT_SECRET_KEY=$(grep '^JWT_SECRET_KEY=' envs/.env | cut -d'=' -f2)
export NODE_ENV=production

echo "Starting services with environment variables loaded..."
echo "SECRET_KEY: ${SECRET_KEY:0:8}... (${#SECRET_KEY} chars)"
echo "JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:8}... (${#JWT_SECRET_KEY} chars)"

docker compose -f infra/docker-compose.yml -f infra/docker-compose.production.yml up -d
