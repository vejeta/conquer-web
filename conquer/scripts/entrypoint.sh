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

# A container restart during an update leaves the "update running" flag behind
rm -f /run/conquer-turn

# Seed the world on first start only; never overwrite a running game
if [ ! -f "$WORLD_DIR/data" ]; then
    echo "[entrypoint] No world found in $WORLD_DIR, installing default world"
    cp -a "$PREFIX/default-world/." "$WORLD_DIR/"
fi

# Help files must match the compiled binary, refresh them on every start
cp "$PREFIX"/share/help[0-5] "$WORLD_DIR/"

# Every player and the administrator run as this container user. Conquer
# (CHECKUSER) only lets one uid add several nations if it owns the god
# nation, and worlds generated elsewhere belong to another uid.
god_uid=$("$PREFIX/bin/conqowner" -d "$WORLD_DIR")
if [ "$god_uid" != "$(id -u)" ]; then
    echo "[entrypoint] Setting god nation owner from uid $god_uid to $(id -u)"
    "$PREFIX/bin/conqowner" -d "$WORLD_DIR" -s "$(id -u)" >/dev/null
fi

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
TURN_GRACE_MINUTES=${TURN_GRACE_MINUTES:-5}
TURN_BACKUPS=${TURN_BACKUPS:-10}
TURN_WEBHOOK_URL=${TURN_WEBHOOK_URL:-}
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

# Public status for the landing page (turn, schedule, scores)
conquer-status || echo "[entrypoint] Could not publish game status"

# Log level 3 = errors and warnings: ttyd's notice level (7) would print the
# site credential (base64 of user:password) to the container logs
exec ttyd -p 7681 -W -b /play -d "${TTYD_LOG_LEVEL:-3}" \
    -m "${MAX_CLIENTS:-5}" \
    -c "${TTYD_USERNAME:-conquer}:${TTYD_PASSWORD:-changeme}" \
    -P "${SESSION_TIMEOUT:-1800}" \
    -t titleFixed=Conquer \
    -t fontSize="${TTYD_FONT_SIZE:-16}" \
    -t disableLeaveAlert=true \
    /usr/local/bin/conquer-menu
