#!/bin/bash

# Deploy to Vercel without GitHub integration
# This script builds and deploys the web app independently

set -e

echo "▸ Starting Vercel deployment without GitHub integration..."

# Navigate to web app directory
cd "$(dirname "$0")/../apps/web"

# Build the application
echo "▸ Building the application..."
pnpm build

# Deploy to Vercel using CLI (without --prod flag for staging)
echo "▸ Deploying to Vercel..."
if [ "$1" = "production" ]; then
    echo "▸ Deploying to production..."
    npx vercel --prod
else
    echo "▸ Deploying to staging..."
    npx vercel
fi

echo "✔ Deployment completed!"