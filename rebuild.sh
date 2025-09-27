#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

# Parse command line arguments
FORCE_REBUILD=false
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE_REBUILD=true
    echo "🔨 Force rebuilding Conquer Web containers (no cache)..."
else
    echo "🔨 Rebuilding Conquer Web containers (using cache)..."
    echo "   💡 Use './rebuild.sh --force' to rebuild without cache"
fi

# Set build flags based on force rebuild option
if [ "$FORCE_REBUILD" = true ]; then
    BUILD_FLAGS="--no-cache"
else
    BUILD_FLAGS=""
fi

# Check if any containers are running first
RUNNING_LOCAL=$(docker ps --format "table {{.Names}}" | grep -c "conquer-local" || true)
RUNNING_PROD=$(docker ps --format "table {{.Names}}" | grep -c "conquer-production" || true)

if [ "$RUNNING_LOCAL" -gt 0 ]; then
    echo "   Stopping local containers..."
    docker-compose -f docker-compose.local.yml down
    echo "   Rebuilding local containers..."
    docker-compose -f docker-compose.local.yml build $BUILD_FLAGS
    echo "   Starting local containers..."
    docker-compose -f docker-compose.local.yml up -d
    echo "✅ Local environment rebuilt and restarted!"
elif [ "$RUNNING_PROD" -gt 0 ]; then
    echo "   Stopping production containers..."
    docker-compose -f docker-compose.production.yml down
    echo "   Rebuilding production containers..."
    docker-compose -f docker-compose.production.yml build $BUILD_FLAGS
    echo "   Starting production containers..."
    docker-compose -f docker-compose.production.yml up -d
    echo "✅ Production environment rebuilt and restarted!"
else
    echo "   No containers currently running"
    echo "   Building both environments..."
    docker-compose -f docker-compose.local.yml build $BUILD_FLAGS
    docker-compose -f docker-compose.production.yml build $BUILD_FLAGS
    echo "✅ All containers rebuilt!"
    echo ""
    echo "📋 Start with:"
    echo "   ./start-local.sh     (for local development)"
    echo "   ./start-production.sh (for production)"
fi

# Show cache usage tip
if [ "$FORCE_REBUILD" = false ]; then
    echo ""
    echo "🚀 Build completed using Docker layer cache for faster rebuilds"
    echo "   Only changed layers were rebuilt, keeping downloads cached"
fi