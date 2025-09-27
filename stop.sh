#!/bin/bash

echo "🛑 Stopping Conquer Web..."

# Try to stop using the most likely compose file
if [ -f "docker-compose.local.yml" ] && docker-compose -f docker-compose.local.yml ps -q > /dev/null 2>&1; then
    echo "   Stopping local development containers..."
    docker-compose -f docker-compose.local.yml down
elif [ -f "docker-compose.production.yml" ] && docker-compose -f docker-compose.production.yml ps -q > /dev/null 2>&1; then
    echo "   Stopping production containers..."
    docker-compose -f docker-compose.production.yml down
elif [ -f "docker-compose.yml" ] && docker-compose ps -q > /dev/null 2>&1; then
    echo "   Stopping containers using default compose file..."
    docker-compose down
else
    echo "   No running containers found or compose files missing"
fi

echo "✅ Conquer Web stopped!"