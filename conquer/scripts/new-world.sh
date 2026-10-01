#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Start the world of a new season (run as root in the game container; the
# administrator runs new-season.sh on the server, which calls this).
#
#  - Refused while a turn update runs or a player is in the game.
#  - The world becomes the default world of the image, or the world in
#    WORLD.tar.gz (a lib/ directory, as backup-world.sh and generate-world.sh
#    make it).
#  - The web accounts stay. Each one founds a new nation in the game's
#    builder the next time it plays ("account:+"); administrator accounts
#    ("account:*") stay administrators. Unused invite codes stay.
#  - The orders-done marks, the turn state and the score history start again.
#
# usage: conquer-new-world [WORLD.tar.gz]

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
GAME_USER="${GAME_USER:-conquer}"
LOCK_DIR="${CONQUER_RUN:-/run/conquer}"
NEW="${1:-}"

[ -z "$NEW" ] || [ -f "$NEW" ] || { echo "❌ No world file $NEW" >&2; exit 1; }

# The game sessions of the main world (practice worlds do not count)
in_game() {
    local comm pid
    for comm in /proc/[0-9]*/comm; do
        [ "$(cat "$comm" 2>/dev/null)" = conquer ] || [ "$(cat "$comm" 2>/dev/null)" = conqrun ] || continue
        pid=${comm#/proc/}
        pid=${pid%/comm}
        tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q -- "-d $PREFIX/practice/" && continue
        return 0
    done
    return 1
}

mkdir -p "$LOCK_DIR"
exec 9> "$LOCK_DIR/turn.lock"
flock -n 9 || { echo "❌ A turn update is running: try again in a few minutes" >&2; exit 2; }
if in_game; then
    echo "❌ Someone is in the game: try again when they leave" >&2
    exit 2
fi

keep=$(mktemp -d)
trap 'rm -rf "$keep"' EXIT
for f in .players .invites; do
    [ -f "$WORLD_DIR/$f" ] && cp -p "$WORLD_DIR/$f" "$keep/"
done

# The new world, checked before the old one goes
if [ -n "$NEW" ]; then
    tar xzf "$NEW" -C "$keep" || { echo "❌ Cannot read $NEW: nothing changed" >&2; exit 1; }
    source_dir="$keep/lib"
else
    source_dir="$PREFIX/default-world"
fi
[ -f "$source_dir/nations" ] || { echo "❌ No world in ${NEW:-$source_dir} (lib/nations): nothing changed" >&2; exit 1; }

# Replaced in place (the directory may be a bind mount)
find "$WORLD_DIR" -mindepth 1 -delete
cp -a "$source_dir/." "$WORLD_DIR/"
# State of the old season, if the new world came from a copy of one
rm -f "$WORLD_DIR/.ready" "$WORLD_DIR/.turn-state" "$WORLD_DIR/.score-history" "$WORLD_DIR/lockadd" \
    "$WORLD_DIR/.players" "$WORLD_DIR/.invites"

[ -f "$keep/.invites" ] && cp -p "$keep/.invites" "$WORLD_DIR/"
if [ -f "$keep/.players" ]; then
    awk -F: '$1 != "" { print $1 ":" ($2 == "*" ? "*" : "+") }' "$keep/.players" > "$WORLD_DIR/.players"
fi

chown -R "$GAME_USER:$GAME_USER" "$WORLD_DIR"
"$PREFIX/bin/conqowner" -d "$WORLD_DIR" -s "$(id -u "$GAME_USER")" > /dev/null
echo "✅ New world ready: $("$PREFIX/bin/conquer" -d "$WORLD_DIR" -s 2>/dev/null | sed -n 's/^Conquer [0-9.]*: //p' | head -n 1)"
[ -f "$WORLD_DIR/.players" ] && echo "   $(grep -c ':+$' "$WORLD_DIR/.players") account(s) will found a new nation the next time they play"
exit 0
