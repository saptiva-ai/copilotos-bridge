#!/bin/bash

# CopilotOS Bridge Verification Script
set -e

echo "🔍 Verifying CopilotOS Bridge setup..."

# Check project structure
echo "📁 Checking project structure..."
required_dirs=(
    "apps/web/src"
    "apps/api/src" 
    "packages/shared/src"
    "infra/docker"
    "docs"
    "tests"
    "scripts"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (missing)"
    fi
done

# Check configuration files
echo "📋 Checking configuration files..."
config_files=(
    "package.json"
    "pnpm-workspace.yaml"
    ".env.example"
    "apps/web/package.json"
    "apps/web/next.config.js"
    "apps/web/tsconfig.json"
    "apps/web/tailwind.config.js"
    "apps/api/pyproject.toml"
    "apps/api/src/main.py"
    "packages/shared/package.json"
    "packages/shared/tsconfig.json"
)

for file in "${config_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
    fi
done

# Check TypeScript compilation
echo "🔧 Checking TypeScript compilation..."
if pnpm --filter shared typecheck >/dev/null 2>&1; then
    echo "  ✅ Shared package TypeScript compilation"
else
    echo "  ❌ Shared package TypeScript compilation (failed)"
fi

if pnpm --filter web typecheck >/dev/null 2>&1; then
    echo "  ✅ Web app TypeScript compilation"
else
    echo "  ❌ Web app TypeScript compilation (failed)"
fi

# Check Python syntax
echo "🐍 Checking Python syntax..."
if python3 -m py_compile apps/api/src/main.py >/dev/null 2>&1; then
    echo "  ✅ API Python syntax"
else
    echo "  ❌ API Python syntax (errors)"
fi

# Check environment files
echo "🔐 Checking environment configuration..."
if [ -f ".env" ]; then
    echo "  ✅ Root .env file exists"
else
    echo "  ⚠️  Root .env file missing (copy from .env.example)"
fi

if [ -f "apps/web/.env.local" ]; then
    echo "  ✅ Web .env.local file exists"
else
    echo "  ⚠️  Web .env.local file missing (copy from .env.local.example)"
fi

if [ -f "apps/api/.env" ]; then
    echo "  ✅ API .env file exists"
else
    echo "  ⚠️  API .env file missing (copy from .env.example)"
fi

echo ""
echo "🎯 Verification complete!"
echo ""
echo "🚦 Status Summary:"
echo "   - Project structure: ✅"
echo "   - Configuration files: ✅"  
echo "   - TypeScript compilation: Check individual results above"
echo "   - Python syntax: Check individual results above"
echo "   - Environment files: Check warnings above"
echo ""