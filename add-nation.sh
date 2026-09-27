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
echo "Then you can create the player's web account for the site."
echo ""

docker exec -it -u conquer "$CONTAINER" conqrun -a

echo ""
read -r -p "Name of the nation you just created (empty to skip the web account): " nation
if [ -n "$nation" ]; then
    read -r -p "Web account for the player [$nation]: " account
    "$(dirname "$0")/manage-players.sh" add "${account:-$nation}" --nation "$nation"
    echo ""
    echo "Give the player: the web account '${account:-$nation}' with its password,"
    echo "and the nation password. The account opens only this nation."
fi
