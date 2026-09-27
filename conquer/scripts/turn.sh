#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run a Conquer turn update (conqrun -x).
#
#  1. Block new logins and warn players who are in the game. conqrun refuses
#     to update while anyone is logged in, so after TURN_GRACE_MINUTES the
#     remaining game sessions are ended with SIGTERM; the game's own hangup
#     handler saves their orders before exiting.
#  2. Back up the world, keeping the last TURN_BACKUPS archives.
#  3. Run the update, retrying every TURN_RETRY_MINUTES up to
#     TURN_MAX_RETRIES times.
#  4. Record the result, clear the players' "orders done" marks, publish
#     the public status and, if TURN_WEBHOOK_URL is set, post a notification.
#
# Usage: conquer-turn [--now | --if-ready]
#   --now       no grace period and no retries (manual run-turn.sh)
#   --if-ready  early update, only if every player nation marked its orders
#               as done (started by the player menu when TURN_EARLY=on)

# Always run as the game user: files written as root (backups, news, the
# world data) would not be writable by the game afterwards
if [ "$(id -u)" = 0 ] && id conquer >/dev/null 2>&1; then
    exec setpriv --reuid=conquer --regid=conquer --init-groups "$0" "$@"
fi

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
BACKUP_DIR="$PREFIX/backups"
GRACE_MINUTES="${TURN_GRACE_MINUTES:-5}"
KEEP_BACKUPS="${TURN_BACKUPS:-10}"
RETRY_MINUTES="${TURN_RETRY_MINUTES:-10}"
MAX_RETRIES="${TURN_MAX_RETRIES:-18}"

# Present while an update is pending or running; the player menu refuses
# new games while it exists
UPDATING_FLAG=/run/conquer/turn
STATE_FILE="$WORLD_DIR/.turn-state"

IF_READY=""
case "$1" in
    --now) GRACE_MINUTES=0; MAX_RETRIES=0 ;;
    --if-ready) IF_READY=1 ;;
esac

log() {
    echo "[turn $(date '+%Y-%m-%d %H:%M:%S %Z')] $*"
}

current_turn() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1
}

# PIDs of running game sessions (from /proc: procps is not in the image)
game_pids() {
    local comm found=1
    for comm in /proc/[0-9]*/comm; do
        if [ "$(cat "$comm" 2>/dev/null)" = conquer ]; then
            comm=${comm#/proc/}
            echo "${comm%/comm}"
            found=0
        fi
    done
    return $found
}

# Print a message on the terminal of every running game session
warn_players() {
    local pid tty
    for pid in $(game_pids); do
        tty=$(readlink "/proc/$pid/fd/0" 2>/dev/null)
        case "$tty" in
            /dev/pts/*) printf '\r\n\a*** %s ***\r\n' "$1" > "$tty" 2>/dev/null ;;
        esac
    done
}

disconnect_players() {
    local minute
    game_pids > /dev/null || return 0

    for ((minute = GRACE_MINUTES; minute > 0; minute--)); do
        game_pids > /dev/null || return 0
        log "Players in the game, turn update in $minute minute(s)"
        warn_players "Turn update in $minute minute(s): finish your orders and quit with q"
        sleep 60
    done

    game_pids > /dev/null || return 0
    log "Disconnecting remaining players"
    warn_players "Turn update starting now: disconnecting, your orders are saved"
    sleep 3
    # shellcheck disable=SC2046 # word splitting of the PID list is intended
    kill -TERM $(game_pids) 2>/dev/null
    sleep 3
}

backup_world() {
    [ "$KEEP_BACKUPS" -gt 0 ] 2>/dev/null || return 0

    local file
    mkdir -p "$BACKUP_DIR" || return 1
    file="$BACKUP_DIR/world_turn$(current_turn)_$(date +%Y%m%d_%H%M%S).tar.gz"
    # Same layout as backup-world.sh, so restore-world.sh can use it
    tar -czf "$file" -C "$PREFIX" lib/ || { rm -f "$file"; return 1; }
    log "World backed up to $(basename "$file")"

    # Keep only the newest KEEP_BACKUPS archives
    find "$BACKUP_DIR" -maxdepth 1 -name 'world_turn*.tar.gz' -printf '%T@ %p\n' \
        | sort -rn | tail -n +$((KEEP_BACKUPS + 1)) | cut -d' ' -f2- \
        | xargs -r -d '\n' rm -f
}

record_state() {
    printf 'TURN_STATE=%q\nTURN_STATE_TIME=%q\nTURN_STATE_MESSAGE=%q\n' \
        "$1" "$(date '+%Y-%m-%d %H:%M %Z')" "$2" > "$STATE_FILE"
}

notify() {
    [ -n "$TURN_WEBHOOK_URL" ] || return 0
    local text="Conquer: $1"
    text=${text//\\/\\\\}
    text=${text//\"/\\\"}
    # "text" is read by Slack/Mattermost-style webhooks, "content" by Discord
    curl -fsS -m 20 -H 'Content-Type: application/json' \
        -d "{\"text\":\"$text\",\"content\":\"$text\"}" \
        "$TURN_WEBHOOK_URL" > /dev/null || log "Webhook notification failed"
}

# Never run two updates at once (cron and a manual run-turn.sh)
exec 9> /run/conquer/turn.lock
if ! flock -n 9; then
    log "Another turn update is already running"
    exit 1
fi

# Checked under the lock: when several players finish at once, only the
# first early update runs, the others find the marks cleared
if [ -n "$IF_READY" ]; then
    if ! /usr/local/bin/conquer-ready all; then
        log "Early turn update skipped: not every nation is ready"
        exit 0
    fi
    log "Every nation marked its orders as done, running the turn update early"
fi

touch "$UPDATING_FLAG"
trap 'rm -f "$UPDATING_FLAG"' EXIT

disconnect_players
backup_world || log "WARNING: world backup failed, continuing with the update"

attempt=0
while true; do
    log "Running turn update (attempt $((attempt + 1)))"
    output=$("$PREFIX/bin/conqrun" -x -d "$WORLD_DIR" 2>&1)
    status=$?
    [ -n "$output" ] && echo "$output"

    if [ $status -eq 0 ]; then
        turn=$(current_turn)
        log "Turn update completed, now turn $turn"
        record_state ok "Turn $turn started"
        /usr/local/bin/conquer-ready clear
        /usr/local/bin/conquer-status || log "Could not publish game status"
        notify "turn update completed, turn $turn has started"
        exit 0
    fi

    if [ $attempt -ge "$MAX_RETRIES" ]; then
        reason=$(printf '%s\n' "$output" | grep -v '^[[:space:]]*$' | tail -n 1)
        log "Turn update failed after $((attempt + 1)) attempt(s), giving up"
        record_state failed "${reason:-conqrun -x failed}"
        /usr/local/bin/conquer-status || log "Could not publish game status"
        notify "turn update FAILED: ${reason:-conqrun -x failed}"
        exit 1
    fi

    attempt=$((attempt + 1))
    log "Turn update not possible yet, retrying in $RETRY_MINUTES minute(s)"
    sleep $((RETRY_MINUTES * 60))
    # Anyone who got in meanwhile is disconnected without a new grace period
    GRACE_MINUTES=0 disconnect_players
done
