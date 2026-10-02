#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

echo "🛑 Stopping Conquer Web..."

# Detect and stop running containers
STOPPED_ANY=false

# Check for local containers
if docker ps --format "table {{.Names}}" | grep -q "conquer-local"; then
    echo "   Stopping local development containers..."
    docker-compose -f docker-compose.local.yml down
    STOPPED_ANY=true
fi

# Check for VPS containers
if docker ps --format "table {{.Names}}" | grep -q "conquer-vps"; then
    echo "   Stopping VPS containers..."
    docker-compose -f docker-compose.vps.yml down
    STOPPED_ANY=true
fi

if [ "$STOPPED_ANY" = false ]; then
    echo "   No running Conquer Web containers found"
fi

echo "✅ Conquer Web stopped!"
