#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🔄 Reset to Default World Script"
echo "================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_LIB_DIR="$SCRIPT_DIR/data/lib"
BACKUP_DIR="$SCRIPT_DIR/backups"
DEFAULT_WORLD_BACKUP="$SCRIPT_DIR/default-world.tar.gz"

# Check if we have a default world backup
if [ ! -f "$DEFAULT_WORLD_BACKUP" ]; then
    echo "❌ Default world backup not found: $DEFAULT_WORLD_BACKUP"
    echo ""
    echo "To create a default world backup:"
    echo "  1. Set up your desired default world with ./generate-world.sh"
    echo "  2. Run: ./reset-to-default-world.sh --create-default"
    echo "  3. Then you can use this script to reset to that default"
    exit 1
fi

# Backup current world if it exists
backup_current() {
    if [ -d "$DOCKER_LIB_DIR" ] && [ "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo "💾 Backing up current world..."

        mkdir -p "$BACKUP_DIR"
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local backup_file="$BACKUP_DIR/world_backup_before_reset_$timestamp.tar.gz"

        cd "$SCRIPT_DIR"
        if tar -czf "$backup_file" -C data lib/; then
            echo "✅ Current world backed up to: $(basename "$backup_file")"
        else
            echo "⚠️  Warning: Failed to backup current world"
        fi
    else
        echo "ℹ️  No current world data to backup"
    fi
}

# Restore default world
restore_default() {
    echo "🔄 Restoring default world..."

    # Create lib directory if it doesn't exist
    mkdir -p "$DOCKER_LIB_DIR"

    # Remove existing world data
    rm -rf "$DOCKER_LIB_DIR"/*
    rm -f "$DOCKER_LIB_DIR"/.*userlog* 2>/dev/null || true

    # Extract default world
    cd "$SCRIPT_DIR"
    if tar -xzf "$DEFAULT_WORLD_BACKUP" -C "$SCRIPT_DIR/data"; then
        echo "✅ Default world restored successfully!"

        # Set proper permissions
        chmod -R 644 "$DOCKER_LIB_DIR"/*
        chmod 755 "$DOCKER_LIB_DIR"

        # Show world info
        echo ""
        echo "📊 Default World Information:"
        if [ -f "$DOCKER_LIB_DIR/nations" ]; then
            local nation_count=$(wc -l < "$DOCKER_LIB_DIR/nations" 2>/dev/null || echo "unknown")
            echo "   Nations: $nation_count"
        fi

        if [ -f "$DOCKER_LIB_DIR/data" ]; then
            local data_size=$(du -h "$DOCKER_LIB_DIR/data" 2>/dev/null | cut -f1 || echo "unknown")
            echo "   World data size: $data_size"
        fi

        echo "   Location: $DOCKER_LIB_DIR"

        return 0
    else
        echo "❌ Failed to restore default world"
        return 1
    fi
}

# Main function
main() {
    echo "This script will reset your world to the default configuration."
    echo ""

    # Show default world info
    echo "📋 Default World Info:"
    local default_size=$(du -h "$DEFAULT_WORLD_BACKUP" | cut -f1)
    echo "   Backup file: $DEFAULT_WORLD_BACKUP"
    echo "   Backup size: $default_size"

    # Check current world
    if [ -d "$DOCKER_LIB_DIR" ] && [ "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo ""
        echo "📊 Current World Info:"
        if [ -f "$DOCKER_LIB_DIR/nations" ]; then
            local current_nations=$(wc -l < "$DOCKER_LIB_DIR/nations" 2>/dev/null || echo "unknown")
            echo "   Nations: $current_nations"
        fi

        echo "   Location: $DOCKER_LIB_DIR"

        echo ""
        echo "⚠️  Warning: This will replace your current world data!"
        read -p "Continue with reset to default? (y/N): " -n 1 -r
        echo

        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Reset cancelled"
            exit 0
        fi

        backup_current
    else
        echo ""
        echo "ℹ️  No current world found, installing default world."
        read -p "Continue? (Y/n): " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "❌ Installation cancelled"
            exit 0
        fi
    fi

    # Perform reset
    if restore_default; then
        echo ""
        echo "🎉 World reset to default completed!"
        echo ""
        echo "📋 Next steps:"
        echo "  1. Restart the game container so it reloads the world:"
        echo "     docker restart conquer-local   (or conquer-vps on the VPS)"
        echo ""
        echo "💾 To create a new backup: ./backup-world.sh"
    else
        echo "❌ Reset failed"
        exit 1
    fi
}

# Usage information
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0"
    echo ""
    echo "Reset world data to the default configuration."
    echo ""
    echo "This script:"
    echo "  - Backs up your current world (if any)"
    echo "  - Restores the default world from default-world.tar.gz"
    echo "  - Sets proper permissions"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  - default-world.tar.gz must exist (create with './reset-to-default-world.sh --create-default')"
    exit 0
fi

# Check if running as create-default mode
if [ "$1" = "--create-default" ]; then
    echo "📦 Creating default world backup from current world..."

    if [ ! -d "$DOCKER_LIB_DIR" ] || [ ! "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo "❌ No current world data found to use as default"
        echo "   Generate a world first with: ./generate-world.sh"
        exit 1
    fi

    cd "$SCRIPT_DIR"
    if tar -czf "$DEFAULT_WORLD_BACKUP" -C data lib/; then
        echo "✅ Default world backup created: $DEFAULT_WORLD_BACKUP"
        echo ""
        echo "💡 You can now use './reset-to-default-world.sh' to reset to this world"
    else
        echo "❌ Failed to create default world backup"
        exit 1
    fi
    exit 0
fi

# Run main function
main "$@"