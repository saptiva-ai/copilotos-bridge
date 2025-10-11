#!/bin/bash

# Copilot OS Setup Script
set -e

echo "▸ Setting up Copilot OS..."

# Check requirements
echo "▸ Checking requirements..."
command -v node >/dev/null 2>&1 || { echo "✖ Node.js is required but not installed. Please install Node.js >= 18.0.0"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "✖ pnpm is required but not installed. Please install pnpm >= 8.0.0"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "✖ Python 3 is required but not installed. Please install Python >= 3.10"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "✖ Docker is required but not installed. Please install Docker"; exit 1; }

echo "✔ All requirements met!"

# Install dependencies
echo "▸ Installing dependencies..."
pnpm install

# Setup environment files
echo "▸ Setting up environment files..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "◆ Created .env from .env.example"
    echo "▲  Please edit .env with your configuration before continuing"
fi

if [ ! -f apps/web/.env.local ]; then
    cp apps/web/.env.local.example apps/web/.env.local
    echo "◆ Created apps/web/.env.local from example"
fi

if [ ! -f apps/api/.env ]; then
    cp apps/api/.env.example apps/api/.env
    echo "◆ Created apps/api/.env from example"
fi

# Build shared package
echo "▸  Building shared package..."
pnpm --filter shared build

# Setup Python virtual environment for API
echo "▸ Setting up Python environment for API..."
cd apps/api
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "◆ Created Python virtual environment"
fi

source venv/bin/activate
pip install -e .
echo "▸ Installed Python dependencies"
cd ../..

# Setup pre-commit hooks (if available)
if command -v pre-commit >/dev/null 2>&1; then
    echo "🪝 Setting up pre-commit hooks..."
    pre-commit install
fi

echo ""
echo "✔ Setup complete!"
echo ""
echo "▸ Next steps:"
echo "   1. Edit .env files with your configuration"
echo "   2. Start required services (PostgreSQL, Redis, Aletheia)"
echo "   3. Run migrations: pnpm db:migrate"
echo "   4. Start development: pnpm dev"
echo ""
echo "▸ Useful commands:"
echo "   pnpm dev          - Start development servers"
echo "   pnpm build        - Build all applications"
echo "   pnpm test         - Run all tests"
echo "   pnpm lint         - Lint all code"
echo "   pnpm docker:up    - Start Docker services"
echo ""