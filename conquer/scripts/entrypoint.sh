#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Container entrypoint: prepare the world volume, schedule turn updates
# and start ttyd serving the player menu under /play.
#
# Runs as root only to prepare volumes, permissions and cron; ttyd, the
# menu, the game and every turn update run as the unprivileged game user.

set -e

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
GAME_USER=conquer
TURN_SCHEDULE="${TURN_SCHEDULE:-0 20 * * 0}"

GAME_UID=$(id -u "$GAME_USER")
GAME_GID=$(id -g "$GAME_USER")

# Command prefix that drops to the game user (setpriv execs, so with
# "exec" the final process becomes PID 1 and receives docker's signals)
AS_GAME_USER=(setpriv --reuid="$GAME_UID" --regid="$GAME_GID" --init-groups
    env HOME="/home/$GAME_USER" USER="$GAME_USER" LOGNAME="$GAME_USER")

# Runtime state shared by the menu and the turn updates (update flag and
# lock). A container restart during an update would leave the flag behind.
rm -rf /run/conquer
install -d -o "$GAME_USER" -g "$GAME_USER" /run/conquer

# Container log for background jobs. Once PID 1 runs as the game user,
# /proc/1/fd/1 can no longer be opened, so cron jobs write to this FIFO and
# a reader forwards it to the container's stdout (inherited from here).
# Opening it read-write keeps the reader from ever seeing end-of-file.
LOG_FIFO=/run/conquer/log
mkfifo -m 0620 "$LOG_FIFO"
chown "$GAME_USER:$GAME_USER" "$LOG_FIFO"
cat <> "$LOG_FIFO" &

# Seed the world on first start only; never overwrite a running game
if [ ! -f "$WORLD_DIR/data" ]; then
    echo "[entrypoint] No world found in $WORLD_DIR, installing default world"
    cp -a "$PREFIX/default-world/." "$WORLD_DIR/"
fi

# Help files must match the compiled binary, refresh them on every start
cp "$PREFIX"/share/help[0-5] "$WORLD_DIR/"

# The game user must own the world, the published status and the backups
# (worlds from older images or restored backups may belong to root)
mkdir -p "$PREFIX/public" "$PREFIX/backups"
chown -R "$GAME_USER:$GAME_USER" "$WORLD_DIR" "$PREFIX/public" "$PREFIX/backups"

# Every player and the administrator run as the game user. Conquer
# (CHECKUSER) only lets one uid add several nations if it owns the god
# nation, and worlds generated elsewhere belong to another uid.
god_uid=$("$PREFIX/bin/conqowner" -d "$WORLD_DIR")
if [ "$god_uid" != "$GAME_UID" ]; then
    echo "[entrypoint] Setting god nation owner from uid $god_uid to $GAME_UID"
    "$PREFIX/bin/conqowner" -d "$WORLD_DIR" -s "$GAME_UID" >/dev/null
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
$TURN_SCHEDULE $GAME_USER /usr/local/bin/conquer-turn >> $LOG_FIFO 2>&1
EOF
    chmod 644 /etc/cron.d/conquer-turn
    cron
    echo "[entrypoint] Turn updates scheduled: '$TURN_SCHEDULE' (${TZ:-UTC})"
else
    echo "[entrypoint] Automatic turn updates disabled (TURN_SCHEDULE=off)"
fi

# Settings shown to players by the menu
cat > /etc/conquer-web.env <<EOF
TURN_SCHEDULE="$TURN_SCHEDULE"
TURN_SCHEDULE_LABEL="${TURN_SCHEDULE_LABEL:-Weekly, Sundays at 20:00 ${TZ:-UTC}}"
ADMIN_CONTACT="${ADMIN_CONTACT:-}"
EOF

# Public status for the landing page (turn, schedule, scores)
"${AS_GAME_USER[@]}" conquer-status || echo "[entrypoint] Could not publish game status"

# Players sign in at the reverse proxy (Apache, per-player accounts), which
# passes the account name in X-WEBAUTH-USER; ttyd rejects requests without
# it and exports it to the menu as TTYD_USER. Only Apache may reach port
# 7681: it is not published locally and bound to 127.0.0.1 on the VPS.
# Log level 3 = errors and warnings, instead of ttyd's chatty default.
exec "${AS_GAME_USER[@]}" ttyd -p 7681 -W -b /play -d "${TTYD_LOG_LEVEL:-3}" \
    -H X-WEBAUTH-USER \
    -m "${MAX_CLIENTS:-5}" \
    -P "${SESSION_TIMEOUT:-1800}" \
    -t titleFixed=Conquer \
    -t fontSize="${TTYD_FONT_SIZE:-16}" \
    -t disableLeaveAlert=true \
    /usr/local/bin/conquer-menu
