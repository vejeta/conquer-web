#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run a Conquer turn update (conqrun -x).
#
# conqrun refuses to update while any player is logged in, so retry every
# TURN_RETRY_MINUTES up to TURN_MAX_RETRIES times before giving up.
#
# Usage: conquer-turn [--now]   (--now: single attempt, no retries)

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
RETRY_MINUTES="${TURN_RETRY_MINUTES:-10}"
MAX_RETRIES="${TURN_MAX_RETRIES:-18}"

if [ "$1" = "--now" ]; then
    MAX_RETRIES=0
fi

log() {
    echo "[turn $(date '+%Y-%m-%d %H:%M:%S %Z')] $*"
}

attempt=0
while true; do
    log "Running turn update (attempt $((attempt + 1)))"
    output=$("$PREFIX/bin/conqrun" -x -d "$PREFIX/lib" 2>&1)
    status=$?
    [ -n "$output" ] && echo "$output"

    if [ $status -eq 0 ]; then
        log "Turn update completed"
        exit 0
    fi

    if [ $attempt -ge "$MAX_RETRIES" ]; then
        log "Turn update failed after $((attempt + 1)) attempt(s), giving up"
        exit 1
    fi

    attempt=$((attempt + 1))
    log "Turn update not possible yet, retrying in $RETRY_MINUTES minute(s)"
    sleep $((RETRY_MINUTES * 60))
done
