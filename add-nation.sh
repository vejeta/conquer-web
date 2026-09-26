#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Create a new player nation (administrator only).
# Runs the interactive "conqrun -a" inside the running game container.

set -e

CONTAINER=""
for name in conquer-local conquer-vps; do
    if docker ps --format '{{.Names}}' | grep -qx "$name"; then
        CONTAINER="$name"
        break
    fi
done

if [ -z "$CONTAINER" ]; then
    echo "❌ No running Conquer container found (conquer-local or conquer-vps)"
    exit 1
fi

echo "🏰 Adding a new nation in $CONTAINER"
echo ""
echo "You will be asked for the nation name, password, race and class."
echo "Give the player the nation name and password when you are done."
echo ""

exec docker exec -it -u conquer "$CONTAINER" conqrun -a
