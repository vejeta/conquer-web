#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "💾 Conquer World Backup Script"
echo "=============================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_LIB_DIR="$SCRIPT_DIR/data/lib"
BACKUP_DIR="$SCRIPT_DIR/backups"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if world data exists
if [ ! -d "$DOCKER_LIB_DIR" ] || [ ! "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
    echo "❌ No world data found to backup"
    echo "   Expected location: $DOCKER_LIB_DIR"
    exit 1
fi

# Generate backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/world_backup_$TIMESTAMP.tar.gz"

echo "📦 Creating backup of world data..."
echo "   Source: $DOCKER_LIB_DIR"
echo "   Target: $BACKUP_FILE"

# Create backup
cd "$SCRIPT_DIR"
if tar -czf "$BACKUP_FILE" -C data lib/; then
    echo "✅ Backup created successfully!"

    # Show backup info
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo ""
    echo "📊 Backup Information:"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
    echo "   Date: $(date)"

    # Show world summary
    if [ -f "$DOCKER_LIB_DIR/nations" ]; then
        NATION_COUNT=$(wc -l < "$DOCKER_LIB_DIR/nations" 2>/dev/null || echo "unknown")
        echo "   Nations: $NATION_COUNT"
    fi

    echo ""
    echo "💡 To restore this backup later:"
    echo "   ./restore-world.sh $(basename "$BACKUP_FILE")"

    # List all backups
    echo ""
    echo "📁 All available backups:"
    ls -lah "$BACKUP_DIR"/*.tar.gz 2>/dev/null | while read -r line; do
        echo "   $line"
    done || echo "   No other backups found"

else
    echo "❌ Backup failed!"
    exit 1
fi