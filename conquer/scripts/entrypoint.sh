#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Container entrypoint: prepare the world volume, schedule turn updates
# and start ttyd serving the player menu under /play.

set -e

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
TURN_SCHEDULE="${TURN_SCHEDULE:-0 20 * * 0}"

# Seed the world on first start only; never overwrite a running game
if [ ! -f "$WORLD_DIR/data" ]; then
    echo "[entrypoint] No world found in $WORLD_DIR, installing default world"
    cp -a "$PREFIX/default-world/." "$WORLD_DIR/"
fi

# Help files must match the compiled binary, refresh them on every start
cp "$PREFIX"/share/help[0-5] "$WORLD_DIR/"

# Schedule turn updates. cron does not inherit the container environment,
# so pass the settings the turn script needs explicitly.
if [ "$TURN_SCHEDULE" != "off" ]; then
    # cron schedules in the system time zone
    if [ -f "/usr/share/zoneinfo/${TZ:-UTC}" ]; then
        ln -snf "/usr/share/zoneinfo/${TZ:-UTC}" /etc/localtime
        echo "${TZ:-UTC}" > /etc/timezone
    fi
    cat > /etc/cron.d/conquer-turn <<EOF
SHELL=/bin/bash
PATH=$PREFIX/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CONQUER_PREFIX=$PREFIX
TZ=${TZ:-UTC}
TURN_RETRY_MINUTES=${TURN_RETRY_MINUTES:-10}
TURN_MAX_RETRIES=${TURN_MAX_RETRIES:-18}
$TURN_SCHEDULE root /usr/local/bin/conquer-turn >> /proc/1/fd/1 2>&1
EOF
    chmod 644 /etc/cron.d/conquer-turn
    cron
    echo "[entrypoint] Turn updates scheduled: '$TURN_SCHEDULE' (${TZ:-UTC})"
else
    echo "[entrypoint] Automatic turn updates disabled (TURN_SCHEDULE=off)"
fi

# Settings shown to players by the menu
cat > /etc/conquer-web.env <<EOF
TURN_SCHEDULE_LABEL="${TURN_SCHEDULE_LABEL:-Weekly, Sundays at 20:00 ${TZ:-UTC}}"
ADMIN_CONTACT="${ADMIN_CONTACT:-}"
EOF

exec ttyd -p 7681 -W -b /play \
    -m "${MAX_CLIENTS:-5}" \
    -c "${TTYD_USERNAME:-conquer}:${TTYD_PASSWORD:-changeme}" \
    -P "${SESSION_TIMEOUT:-1800}" \
    -t titleFixed=Conquer \
    -t fontSize="${TTYD_FONT_SIZE:-16}" \
    -t disableLeaveAlert=true \
    /usr/local/bin/conquer-menu
