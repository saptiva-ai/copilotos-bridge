#!/bin/bash
# ============================================================================
# ENVIRONMENT LOADER FOR DEPLOYMENT
# ============================================================================
# Helper script to load environment variables for deployment scripts
# Usage: source scripts/deploy/load-env.sh [prod|dev]
# ============================================================================

ENV_TYPE="${1:-prod}"

if [ "$ENV_TYPE" = "prod" ]; then
    ENV_FILE="envs/.env.prod"
elif [ "$ENV_TYPE" = "dev" ]; then
    ENV_FILE="envs/.env"
else
    echo "❌ Invalid environment type: $ENV_TYPE"
    echo "Usage: source scripts/deploy/load-env.sh [prod|dev]"
    return 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    return 1
fi

# Export only deployment-related variables (avoid parsing issues with complex values)
export DEPLOY_SERVER=$(grep "^DEPLOY_SERVER=" "$ENV_FILE" | cut -d'=' -f2)
export DEPLOY_PROJECT_DIR=$(grep "^DEPLOY_PROJECT_DIR=" "$ENV_FILE" | cut -d'=' -f2)
export PROD_SERVER_IP=$(grep "^PROD_SERVER_IP=" "$ENV_FILE" | cut -d'=' -f2)
export PROD_SERVER_USER=$(grep "^PROD_SERVER_USER=" "$ENV_FILE" | cut -d'=' -f2)
export PROD_SERVER_HOST=$(grep "^PROD_SERVER_HOST=" "$ENV_FILE" | cut -d'=' -f2)
export PROD_DEPLOY_PATH=$(grep "^PROD_DEPLOY_PATH=" "$ENV_FILE" | cut -d'=' -f2)
export PROD_DOMAIN=$(grep "^PROD_DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)

echo "✅ Environment variables loaded from $ENV_FILE"
echo "   DEPLOY_SERVER: $DEPLOY_SERVER"
echo "   DEPLOY_PROJECT_DIR: $DEPLOY_PROJECT_DIR"
echo "   PROD_DOMAIN: $PROD_DOMAIN"
