#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🌍 Conquer World Generation Script"
echo "=================================="
echo ""

# Configuration
TEMP_DIR=$(mktemp -d)
CONQUER_REPO="https://github.com/vejeta/conquer.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_LIB_DIR="$SCRIPT_DIR/conquer/lib"

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Check dependencies
check_dependencies() {
    echo "📋 Checking dependencies..."

    local missing_deps=()

    if ! command -v git >/dev/null 2>&1; then
        missing_deps+=("git")
    fi

    if ! command -v make >/dev/null 2>&1; then
        missing_deps+=("build-essential")
    fi

    if ! command -v gcc >/dev/null 2>&1; then
        missing_deps+=("gcc")
    fi

    # Check for ncurses development headers
    if ! pkg-config --exists ncurses 2>/dev/null && ! pkg-config --exists ncursesw 2>/dev/null; then
        if [ ! -f /usr/include/ncurses.h ] && [ ! -f /usr/include/ncurses/ncurses.h ]; then
            missing_deps+=("libncurses5-dev or libncursesw5-dev")
        fi
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "❌ Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Install with:"
        echo "  sudo apt-get update"
        echo "  sudo apt-get install git build-essential libncurses5-dev libncursesw5-dev"
        echo ""
        exit 1
    fi

    echo "✅ All dependencies found"
}

# Backup existing world data
backup_existing_world() {
    if [ -d "$DOCKER_LIB_DIR" ] && [ "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo "📦 Backing up existing world data..."

        local backup_dir="$SCRIPT_DIR/backups"
        mkdir -p "$backup_dir"

        local timestamp
        timestamp=$(date +%Y%m%d_%H%M%S)
        local backup_file="$backup_dir/world_backup_$timestamp.tar.gz"

        cd "$SCRIPT_DIR"
        tar -czf "$backup_file" -C conquer lib/

        echo "✅ Existing world backed up to: $backup_file"
        return 0
    else
        echo "ℹ️  No existing world data found"
        return 1
    fi
}

# Clone and compile Conquer
setup_conquer() {
    echo "🔄 Cloning Conquer repository..."
    cd "$TEMP_DIR"
    git clone "$CONQUER_REPO" conquer

    echo "🔨 Compiling Conquer..."
    cd conquer/gpl-release

    # Compile with error handling
    if ! make; then
        echo "❌ Compilation failed!"
        echo "💡 Try installing missing dependencies:"
        echo "   sudo apt-get install build-essential libncurses5-dev libncursesw5-dev"
        exit 1
    fi

    echo "✅ Conquer compiled successfully"
}

# Interactive world generation
generate_world() {
    echo ""
    echo "🌍 Starting world generation..."
    echo ""
    echo "You will now enter the Conquer world generation interface."
    echo "This is an interactive process where you can:"
    echo "  - Set world size and geography"
    echo "  - Create and configure nations"
    echo "  - Set initial resources and relationships"
    echo "  - Configure game rules"
    echo ""
    echo "💡 Tips:"
    echo "  - Map size must be at most 256x256 (the engine stores coordinates"
    echo "    in 8 bits; larger maps misplace armies). For about 15 players:"
    echo "    112x112 with 60% water and 7 computer nations (the shipped world)"
    echo "  - At most 35 nations in all: every computer nation in lib/nations"
    echo "    takes a player's place"
    echo "  - Press Ctrl+C to exit if you need to restart"
    echo "  - The process will create lib/ directory with world data"
    echo ""
    read -p "Ready to start world generation? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ World generation cancelled"
        exit 1
    fi

    cd "$TEMP_DIR/conquer/gpl-release"

    echo "🚀 Launching world generation interface..."
    echo "========================================"

    # Run world generation
    if ! ./conqrun -m; then
        echo ""
        echo "❌ World generation failed or was cancelled"
        echo "💡 You can run this script again to retry"
        exit 1
    fi

    echo ""
    echo "✅ World generation completed!"
}

# Validate generated world data
validate_world() {
    echo "🔍 Validating generated world data..."

    local lib_dir="$TEMP_DIR/conquer/gpl-release/lib"

    if [ ! -d "$lib_dir" ]; then
        echo "❌ No lib/ directory found after world generation"
        return 1
    fi

    local required_files=("data" "nations" ".userlog")
    local missing_files=()

    for file in "${required_files[@]}"; do
        if [ ! -f "$lib_dir/$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -ne 0 ]; then
        echo "❌ Missing required files: ${missing_files[*]}"
        return 1
    fi

    # Check file sizes (they should not be empty)
    if [ ! -s "$lib_dir/data" ]; then
        echo "❌ World data file is empty"
        return 1
    fi

    echo "✅ World data validation passed"
    return 0
}

# Copy world data to Docker context
install_world() {
    echo "📁 Installing world data..."

    local source_lib="$TEMP_DIR/conquer/gpl-release/lib"

    # Create target directory
    mkdir -p "$DOCKER_LIB_DIR"

    # Remove old world data
    rm -rf "${DOCKER_LIB_DIR:?}"/*
    rm -f "$DOCKER_LIB_DIR/.*" 2>/dev/null || true

    # Copy new world data
    cp -r "$source_lib"/* "$DOCKER_LIB_DIR/"

    # Copy hidden files (.userlog)
    if [ -f "$source_lib/.userlog" ]; then
        cp "$source_lib/.userlog" "$DOCKER_LIB_DIR/"
    fi

    # Set proper permissions
    chmod -R 644 "$DOCKER_LIB_DIR"/*
    chmod 755 "$DOCKER_LIB_DIR"

    echo "✅ World data installed to: $DOCKER_LIB_DIR"
}

# Show world information
show_world_info() {
    echo ""
    echo "📊 World Data Summary"
    echo "===================="

    if [ -f "$DOCKER_LIB_DIR/nations" ]; then
        local nation_count
        nation_count=$(wc -l < "$DOCKER_LIB_DIR/nations" 2>/dev/null || echo "unknown")
        echo "Nations: $nation_count"
    fi

    if [ -f "$DOCKER_LIB_DIR/data" ]; then
        local data_size
        data_size=$(du -h "$DOCKER_LIB_DIR/data" 2>/dev/null | cut -f1 || echo "unknown")
        echo "World data size: $data_size"
    fi

    echo "Location: $DOCKER_LIB_DIR"
    echo ""

    echo "📋 Files created:"
    ls -la "$DOCKER_LIB_DIR"
}

# Main execution
main() {
    echo "This script will generate a new Conquer world and install it for use with Docker."
    echo ""

    # Confirm action
    if [ -d "$DOCKER_LIB_DIR" ] && [ "$(ls -A "$DOCKER_LIB_DIR" 2>/dev/null)" ]; then
        echo "⚠️  Warning: This will replace your existing world data!"
        echo "   Current world location: $DOCKER_LIB_DIR"
        echo ""
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Operation cancelled"
            exit 1
        fi

        # Backup existing world
        backup_existing_world || true
    fi

    echo ""
    check_dependencies
    setup_conquer
    generate_world

    if validate_world; then
        install_world
        show_world_info

        echo "🎉 World generation complete!"
        echo ""
        echo "📋 Next steps:"
        echo "  The new world is the default world shipped in the image (conquer/lib)."
        echo "  The running game keeps its own copy in data/lib, so to switch to it:"
        echo "  1. Backup the current game: ./backup-world.sh"
        echo "  2. Remove the live world:   rm -rf data/lib"
        echo "  3. Rebuild and start:       ./rebuild.sh --force"
        echo ""
        echo "💾 To backup this world later: ./backup-world.sh"
    else
        echo "❌ World validation failed. Please try again."
        exit 1
    fi
}

# Run main function
main "$@"