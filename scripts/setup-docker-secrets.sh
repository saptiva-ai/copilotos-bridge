#!/bin/bash
# ==============================================
# Docker Secrets Setup for Copilotos Bridge
# ==============================================

set -e

echo "⛨ Setting up Docker Secrets for Copilotos Bridge"
echo "=================================================="

# Status symbols for logs
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Initialize Docker Swarm if not already initialized
if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
    echo -e "${BLUE}Initializing Docker Swarm...${NC}"
    docker swarm init
fi

echo -e "${YELLOW}Security Warning:${NC}"
echo "   This script will prompt you to enter sensitive credentials."
echo "   Make sure you are in a secure environment."
echo

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

# Function to create a secret securely
create_secret() {
    local secret_name="$1"
    local prompt="$2"
    local generate_option="$3"

    if docker secret inspect "$secret_name" > /dev/null 2>&1; then
        echo -e "${YELLOW}Secret '$secret_name' already exists. Skipping...${NC}"
        return 0
    fi

    echo -e "${BLUE}⛨ Creating secret: $secret_name${NC}"

    if [[ "$generate_option" == "generate" ]]; then
        echo "   Would you like to:"
        echo "   1) Generate a secure random value"
        echo "   2) Enter your own value"
        read -p "   Choose (1/2): " -n 1 -r choice
        echo

        if [[ $choice == "1" ]]; then
            # Generate secure random value
            case "$secret_name" in
                *password*)
                    secret_value=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
                    echo "   Generated secure password (25 chars)"
                    ;;
                *key*)
                    secret_value=$(openssl rand -hex 32)
                    echo "   Generated secure key (64 hex chars)"
                    ;;
                *)
                    secret_value=$(openssl rand -base64 24)
                    echo "   Generated secure value (32 chars)"
                    ;;
            esac
        else
            read -s -p "   Enter $prompt: " secret_value
            echo
        fi
    else
        read -s -p "   Enter $prompt: " secret_value
        echo
    fi

    if [[ -z "$secret_value" ]]; then
        echo -e "${RED}Empty value provided. Skipping $secret_name${NC}"
        return 1
    fi

    # Create the secret
    echo "$secret_value" | docker secret create "$secret_name" -
    echo -e "${GREEN}Secret '$secret_name' created successfully${NC}"

    # Clear the variable
    unset secret_value
}

echo -e "${BLUE}Creating required secrets...${NC}"
echo

# Create all required secrets
create_secret "copilotos_mongodb_password" "MongoDB password for copilotos_user" "generate"
create_secret "copilotos_redis_password" "Redis password" "generate"
create_secret "copilotos_jwt_secret_key" "JWT signing secret key" "generate"
create_secret "copilotos_secret_key" "Application secret key" "generate"
create_secret "copilotos_saptiva_api_key" "SAPTIVA API key" "manual"
create_secret "copilotos_mongo_root_password" "MongoDB root password" "generate"

echo
echo -e "${GREEN}◆ All secrets have been created successfully!${NC}"
echo

echo -e "${BLUE}Next steps:${NC}"
echo "1. Deploy using: docker stack deploy -c docker-compose.secure.yml copilotos"
echo "2. Monitor logs: docker service logs -f copilotos_api"
echo "3. Check health: docker service ls"
echo

echo -e "${YELLOW}⛨ Security reminders:${NC}"
echo "- Secrets are stored encrypted in Docker's internal database"
echo "- Rotate secrets regularly using: docker secret rm <name> && docker secret create <name> -"
echo "- Monitor access to Docker daemon (root privileges required)"
echo "- Use 'docker secret ls' to list all secrets"
echo

echo -e "${GREEN}Setup complete!${NC}"