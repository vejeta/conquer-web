#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

# Detect which environment is running
if docker ps --format "table {{.Names}}" | grep -q "conquer-local"; then
    COMPOSE_FILE="docker-compose.local.yml"
    echo "📋 Showing logs for LOCAL environment"
elif docker ps --format "table {{.Names}}" | grep -q "conquer-production"; then
    COMPOSE_FILE="docker-compose.production.yml"
    echo "📋 Showing logs for PRODUCTION environment"
else
    echo "❌ No Conquer Web containers are running"
    echo "   Start the application first with:"
    echo "   ./start-local.sh     (for local development)"
    echo "   ./start-production.sh (for production)"
    exit 1
fi

echo "Environment: $(basename $COMPOSE_FILE .yml | sed 's/docker-compose\.//')"
echo "Press Ctrl+C to exit log viewing"
echo ""

# Show logs with timestamps, follow mode
docker-compose -f "$COMPOSE_FILE" logs -f --timestamps