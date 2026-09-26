#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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
        echo "  --quick, -q    Recreate containers with the current config, no rebuild"
        echo "  --help, -h     Show this help"
        echo ""
        echo "The environment is detected from the running containers, or from"
        echo "config/local.env / config/production.env when nothing is running."
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

# Detect environment: running containers first, then available config
if docker ps --format '{{.Names}}' | grep -qx "conquer-vps"; then
    ENV_NAME=vps
elif docker ps --format '{{.Names}}' | grep -qx "conquer-local"; then
    ENV_NAME=local
elif [ -f config/local.env ]; then
    ENV_NAME=local
elif [ -f config/production.env ]; then
    ENV_NAME=vps
else
    echo "❌ No environment configuration found"
    echo "🔧 Run './setup-environment.sh' first"
    exit 1
fi

if [ "$ENV_NAME" = "vps" ]; then
    ENV_FILE=config/production.env
    COMPOSE_FILE=docker-compose.vps.yml
else
    ENV_FILE=config/local.env
    COMPOSE_FILE=docker-compose.local.yml
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ $ENV_FILE not found"
    echo "🔧 Run './setup-environment.sh' first"
    exit 1
fi

# Export every setting so docker-compose uses the configured credentials
# and turn schedule instead of the compose file defaults
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# Live world data directory (seeded by the container on first start)
mkdir -p data/lib data/public data/backups

echo "   Environment: $ENV_NAME ($COMPOSE_FILE, $ENV_FILE)"

if [ "$QUICK_RESTART" = true ]; then
    # "up" recreates containers whose configuration changed; "restart" would not
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate
    echo ""
    echo "⚡ Quick restart completed - containers recreated without rebuilding"
    exit 0
fi

BUILD_FLAGS=""
if [ "$FORCE_REBUILD" = true ]; then
    BUILD_FLAGS="--no-cache"
fi

echo "   Rebuilding containers..."
docker-compose -f "$COMPOSE_FILE" build $BUILD_FLAGS
echo "   Starting containers..."
docker-compose -f "$COMPOSE_FILE" up -d
echo "✅ $ENV_NAME environment rebuilt and restarted!"
echo "   World data in data/lib is preserved"

# Show cache usage tip
if [ "$FORCE_REBUILD" = false ]; then
    echo ""
    echo "🚀 Build completed using Docker layer cache for faster rebuilds"
    echo "   Only changed layers were rebuilt, keeping downloads cached"
fi
