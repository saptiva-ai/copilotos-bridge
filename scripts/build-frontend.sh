#!/bin/bash
# Frontend Build Script for Development and Production
# Usage: ./scripts/build-frontend.sh [dev|prod]

set -e

ENV_TYPE=${1:-dev}
BUILD_DATE=$(date '+%Y-%m-%d %H:%M:%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "🏗️  Building frontend for environment: $ENV_TYPE"
echo "📅 Build date: $BUILD_DATE"
echo "🔧 Git SHA: $GIT_SHA"

cd apps/web

case "$ENV_TYPE" in
  "dev"|"development")
    echo "🛠️  Development build"
    echo "Using .env.local configuration"
    cp .env.local .env
    pnpm build
    ;;
  "prod"|"production")
    echo "🚀 Production build"
    echo "Using .env.production configuration"
    cp .env.production .env
    # Add build metadata
    echo "" >> .env
    echo "# Build metadata" >> .env
    echo "NEXT_PUBLIC_BUILD_DATE=\"$BUILD_DATE\"" >> .env
    echo "NEXT_PUBLIC_GIT_SHA=\"$GIT_SHA\"" >> .env
    pnpm build
    ;;
  *)
    echo "❌ Unknown environment: $ENV_TYPE"
    echo "Usage: $0 [dev|prod]"
    exit 1
    ;;
esac

echo "✅ Frontend build completed for $ENV_TYPE environment"