#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "⚡ Quick rebuild (config changes only)..."

# Check if any containers are running first
RUNNING_LOCAL=$(docker ps --format "table {{.Names}}" | grep -c "conquer-local" || true)
RUNNING_PROD=$(docker ps --format "table {{.Names}}" | grep -c "conquer-production" || true)

if [ "$RUNNING_LOCAL" -gt 0 ]; then
    echo "   Restarting local containers..."
    docker-compose -f docker-compose.local.yml restart
    echo "✅ Local environment restarted!"
elif [ "$RUNNING_PROD" -gt 0 ]; then
    echo "   Restarting production containers..."
    docker-compose -f docker-compose.production.yml restart
    echo "✅ Production environment restarted!"
else
    echo "   No containers currently running, use regular build..."
    ./rebuild.sh
fi

echo ""
echo "⚡ Quick restart completed - only restarts containers without rebuilding"
echo "   Use './rebuild.sh' for code changes that need image rebuilding"