#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run a turn update now, outside the TURN_SCHEDULE (administrator only).
# The update is refused while players are logged in.

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

echo "⏭️  Running turn update in $CONTAINER"
exec docker exec "$CONTAINER" conquer-turn --now
