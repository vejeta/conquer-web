#!/bin/bash
set -e

echo "🔨 Rebuilding Conquer Web containers..."

# Check if any containers are running first
RUNNING_LOCAL=$(docker ps --format "table {{.Names}}" | grep -c "conquer-local" || true)
RUNNING_PROD=$(docker ps --format "table {{.Names}}" | grep -c "conquer-production" || true)

if [ "$RUNNING_LOCAL" -gt 0 ]; then
    echo "   Stopping local containers..."
    docker-compose -f docker-compose.local.yml down
    echo "   Rebuilding local containers..."
    docker-compose -f docker-compose.local.yml build --no-cache
    echo "   Starting local containers..."
    docker-compose -f docker-compose.local.yml up -d
    echo "✅ Local environment rebuilt and restarted!"
elif [ "$RUNNING_PROD" -gt 0 ]; then
    echo "   Stopping production containers..."
    docker-compose -f docker-compose.production.yml down
    echo "   Rebuilding production containers..."
    docker-compose -f docker-compose.production.yml build --no-cache
    echo "   Starting production containers..."
    docker-compose -f docker-compose.production.yml up -d
    echo "✅ Production environment rebuilt and restarted!"
else
    echo "   No containers currently running"
    echo "   Building both environments..."
    docker-compose -f docker-compose.local.yml build --no-cache
    docker-compose -f docker-compose.production.yml build --no-cache
    echo "✅ All containers rebuilt!"
    echo ""
    echo "📋 Start with:"
    echo "   ./start-local.sh     (for local development)"
    echo "   ./start-production.sh (for production)"
fi