#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🔄 Conquer World Restore Script"
echo "==============================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_LIB_DIR="$SCRIPT_DIR/conquer/lib"
BACKUP_DIR="$SCRIPT_DIR/backups"

# Function to list available backups
list_backups() {
    echo "📁 Available backups:"
    if ls "$BACKUP_DIR"/*.tar.gz >/dev/null 2>&1; then
        ls -lah "$BACKUP_DIR"/*.tar.gz | while read -r line; do
            echo "   $line"
        done
    else
        echo "   No backups found in $BACKUP_DIR"
        return 1
    fi
}

# Function to validate backup file
validate_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        echo "❌ Backup file not found: $backup_file"
        return 1
    fi

    # Test if it's a valid tar.gz file
    if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
        echo "❌ Invalid backup file (not a valid tar.gz): $backup_file"
        return 1
    fi

    # Check if it contains the expected structure
    if ! tar -tzf "$backup_file" | grep -q "lib/data"; then
        echo "❌ Backup doesn't contain expected world data structure"
        return 1
    fi

    return 0
}

# Function to backup current world before restore
backup_current() {
    if [ -d "$DOCKER_LIB_DIR" ] && [ "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo "💾 Backing up current world before restore..."

        local timestamp=$(date +%Y%m%d_%H%M%S)
        local backup_file="$BACKUP_DIR/world_backup_pre_restore_$timestamp.tar.gz"

        cd "$SCRIPT_DIR"
        if tar -czf "$backup_file" -C conquer lib/; then
            echo "✅ Current world backed up to: $(basename "$backup_file")"
        else
            echo "⚠️  Warning: Failed to backup current world"
        fi
    fi
}

# Function to restore world data
restore_world() {
    local backup_file="$1"

    echo "🔄 Restoring world data from: $(basename "$backup_file")"

    # Create lib directory if it doesn't exist
    mkdir -p "$DOCKER_LIB_DIR"

    # Remove existing world data
    rm -rf "$DOCKER_LIB_DIR"/*
    rm -f "$DOCKER_LIB_DIR"/.*userlog* 2>/dev/null || true

    # Extract backup
    cd "$SCRIPT_DIR"
    if tar -xzf "$backup_file"; then
        echo "✅ World data restored successfully!"

        # Set proper permissions
        chmod -R 644 "$DOCKER_LIB_DIR"/*
        chmod 755 "$DOCKER_LIB_DIR"

        # Show restored world info
        echo ""
        echo "📊 Restored World Information:"
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
        echo "❌ Failed to restore world data"
        return 1
    fi
}

# Main function
main() {
    local backup_file=""

    # Parse command line arguments
    if [ $# -eq 0 ]; then
        echo "No backup file specified."
        echo ""
        list_backups

        if ls "$BACKUP_DIR"/*.tar.gz >/dev/null 2>&1; then
            echo ""
            read -p "Enter backup filename (or 'q' to quit): " backup_filename

            if [ "$backup_filename" = "q" ]; then
                echo "❌ Restore cancelled"
                exit 0
            fi

            # Check if it's just a filename or full path
            if [[ "$backup_filename" =~ ^/ ]]; then
                backup_file="$backup_filename"
            else
                backup_file="$BACKUP_DIR/$backup_filename"
            fi
        else
            echo ""
            echo "❌ No backups available. Create a backup first with:"
            echo "   ./backup-world.sh"
            exit 1
        fi
    else
        backup_file="$1"

        # If it's just a filename, prepend backup directory
        if [[ ! "$backup_file" =~ ^/ ]]; then
            backup_file="$BACKUP_DIR/$backup_file"
        fi
    fi

    # Validate backup file
    if ! validate_backup "$backup_file"; then
        exit 1
    fi

    # Show what will be restored
    echo "📋 Restore Summary:"
    echo "   Backup file: $(basename "$backup_file")"
    echo "   Backup size: $(du -h "$backup_file" | cut -f1)"
    echo "   Target location: $DOCKER_LIB_DIR"

    # Confirm restore
    if [ -d "$DOCKER_LIB_DIR" ] && [ "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo ""
        echo "⚠️  Warning: This will replace your current world data!"
        read -p "Continue with restore? (y/N): " -n 1 -r
        echo

        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Restore cancelled"
            exit 0
        fi

        backup_current
    fi

    # Perform restore
    if restore_world "$backup_file"; then
        echo ""
        echo "🎉 World restore completed!"
        echo ""
        echo "📋 Next steps:"
        echo "  1. Rebuild containers: ./rebuild.sh --force"
        echo "  2. Start the game: ./start-local.sh"
        echo "  3. Access at: https://conquer.local"
    else
        echo "❌ Restore failed"
        exit 1
    fi
}

# Usage information
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [backup_file]"
    echo ""
    echo "Restore Conquer world data from a backup file."
    echo ""
    echo "Options:"
    echo "  backup_file    Path to backup file (optional - will prompt if not provided)"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Interactive restore"
    echo "  $0 world_backup_20250927_120000.tar.gz  # Restore specific backup"
    echo "  $0 /path/to/backup.tar.gz            # Restore from full path"
    exit 0
fi

# Run main function
main "$@"