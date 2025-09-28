#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

# Detect which environment is running
if docker ps --format "table {{.Names}}" | grep -q "conquer-local"; then
    COMPOSE_FILE="docker-compose.local.yml"
    echo "📋 Showing logs for LOCAL environment"
elif docker ps --format "table {{.Names}}" | grep -q "conquer-vps"; then
    COMPOSE_FILE="docker-compose.vps.yml"
    echo "📋 Showing logs for VPS environment"
else
    echo "❌ No Conquer Web containers are running"
    echo "   Start the application first with:"
    echo "   Local: docker-compose up -d"
    echo "   VPS: sudo systemctl start conquer-web"
    exit 1
fi

echo "Environment: $(basename $COMPOSE_FILE .yml | sed 's/docker-compose\.//')"
echo "Press Ctrl+C to exit log viewing"
echo ""

# Show logs with timestamps, follow mode
docker-compose -f "$COMPOSE_FILE" logs -f --timestamps