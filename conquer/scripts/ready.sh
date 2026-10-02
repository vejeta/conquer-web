#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Players mark their orders as done for the current turn. When every
# player nation has done so, the turn update can run early instead of
# waiting for the schedule (TURN_EARLY, see conquer-turn --if-ready).
#
# Player nations are the ones assigned to web accounts in lib/.players
# (manage-players.sh); without assignments there is nothing to wait for.
# Marks are files lib/.ready/<nation> holding the turn they belong to, so
# marks from an earlier turn never count.
#
# Usage: conquer-ready mark|unmark|is-marked NATION
#        conquer-ready count     prints "<ready> <total>"
#        conquer-ready all       exit status 0 when every nation is ready
#        conquer-ready clear

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
PLAYERS_FILE="$WORLD_DIR/.players"
READY_DIR="$WORLD_DIR/.ready"

current_turn() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1
}

# Nations assigned to a web account that exist in the world, one per line
player_nations() {
    [ -f "$PLAYERS_FILE" ] || return 0
    "$PREFIX/bin/conquer" -s 2>/dev/null | awk -v players="$PLAYERS_FILE" '
        BEGIN {
            while ((getline line < players) > 0) {
                split(line, f, ":")
                if (f[2] != "" && f[2] != "*") wanted[f[2]] = 1
            }
        }
        $1 ~ /^[0-9]+$/ && ($2 in wanted) && !seen[$2]++ { print $2 }'
}

valid_nation() {
    [[ "$1" =~ ^[A-Za-z0-9_.-]{1,9}$ ]]
}

is_marked() {
    local turn
    turn=$(current_turn)
    [ -n "$turn" ] && [ "$(cat "$READY_DIR/$1" 2>/dev/null)" = "$turn" ]
}

count() {
    local nation ready=0 total=0
    while IFS= read -r nation; do
        total=$((total + 1))
        is_marked "$nation" && ready=$((ready + 1))
    done < <(player_nations)
    echo "$ready $total"
}

case "$1" in
    mark)
        valid_nation "$2" || exit 2
        mkdir -p "$READY_DIR" && current_turn > "$READY_DIR/$2"
        ;;
    unmark)
        valid_nation "$2" || exit 2
        rm -f "$READY_DIR/$2"
        ;;
    is-marked)
        valid_nation "$2" || exit 2
        is_marked "$2"
        ;;
    count)
        count
        ;;
    all)
        read -r ready total < <(count)
        [ "$total" -gt 0 ] && [ "$ready" -eq "$total" ]
        ;;
    clear)
        rm -rf "$READY_DIR"
        ;;
    *)
        sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \{0,1\}//' >&2
        exit 2
        ;;
esac
