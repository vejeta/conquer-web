#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

# Parse command line arguments
FORCE_REBUILD=false
QUICK_RESTART=false

case "${1:-}" in
    "--force"|"-f")
        FORCE_REBUILD=true
        echo "🔨 Force rebuilding Conquer Web containers (no cache)..."
        ;;
    "--quick"|"-q")
        QUICK_RESTART=true
        echo "⚡ Quick restart (config changes only, no rebuild)..."
        ;;
    "--help"|"-h")
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --force, -f    Force rebuild without cache"
        echo "  --quick, -q    Quick restart without rebuild"
        echo "  --help, -h     Show this help"
        exit 0
        ;;
    "")
        echo "🔨 Rebuilding Conquer Web containers (using cache)..."
        echo "   💡 Options: --force (no cache), --quick (restart only)"
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "   Use --help for usage information"
        exit 1
        ;;
esac

# Check if any containers are running first
RUNNING_LOCAL=$(docker ps --format "table {{.Names}}" | grep -c "conquer-local" || true)
RUNNING_VPS=$(docker ps --format "table {{.Names}}" | grep -c "conquer-vps" || true)

# Quick restart mode - just restart containers
if [ "$QUICK_RESTART" = true ]; then
    if [ "$RUNNING_LOCAL" -gt 0 ]; then
        echo "   Restarting local containers..."
        docker-compose -f docker-compose.local.yml restart
        echo "✅ Local environment restarted!"
    elif [ "$RUNNING_VPS" -gt 0 ]; then
        echo "   Restarting VPS containers..."
        docker-compose -f docker-compose.vps.yml restart
        echo "✅ VPS environment restarted!"
    else
        echo "   No containers running, switching to full rebuild..."
        QUICK_RESTART=false
    fi

    if [ "$QUICK_RESTART" = true ]; then
        echo ""
        echo "⚡ Quick restart completed - containers restarted without rebuilding"
        exit 0
    fi
fi

# Set build flags for full rebuild
if [ "$FORCE_REBUILD" = true ]; then
    BUILD_FLAGS="--no-cache"
else
    BUILD_FLAGS=""
fi

# Stop running containers for rebuild
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