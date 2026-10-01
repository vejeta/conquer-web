#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# End the season and start the next one, in one go:
#  1. the final scores go to the hall of fame (season-end.sh);
#  2. a copy of the old world and the accounts is kept;
#  3. the game gets a new world (the default one, or WORLD.tar.gz);
#  4. every player keeps their web account and founds a new nation the
#     next time they play; invite codes stay valid.
#
# Usage: sudo ./new-season.sh "Season 1: The return of the Usenet generals" [--world WORLD.tar.gz] [--yes]
#
# Refused while a turn update runs or someone is in the game. Tell the
# players first: their nations end with the season.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
    sed -n '/^# Usage:/p' "$0" | sed 's/^# //'
    exit 1
}

NAME="" WORLD="" YES=""
while [ $# -gt 0 ]; do
    case "$1" in
        --world) [ -n "$2" ] || usage; WORLD="$2"; shift ;;
        --yes) YES=1 ;;
        -*) usage ;;
        *) [ -z "$NAME" ] || usage; NAME="$1" ;;
    esac
    shift
done
[ -n "$NAME" ] || usage
[ -z "$WORLD" ] || [ -f "$WORLD" ] || { echo "❌ No world file $WORLD"; exit 1; }

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx conquer-vps; then
    CONTAINER=conquer-vps HTPASSWD=/etc/apache2/conquer-web.htpasswd BACKUPS=/root/conquer-backups
    [ "$EUID" -eq 0 ] || { echo "❌ Run it with sudo"; exit 1; }
elif docker ps --format '{{.Names}}' 2>/dev/null | grep -qx conquer-local; then
    CONTAINER=conquer-local HTPASSWD="$SCRIPT_DIR/data/auth/htpasswd" BACKUPS="$SCRIPT_DIR/backups"
else
    echo "❌ The game container is not running"
    exit 1
fi

turn=$(docker exec -u conquer "$CONTAINER" conquer -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9]*\)$/\1/p' | head -n 1)
echo "Season \"$NAME\" ends at turn ${turn:-?}."
echo "Every nation of this world ends with it; the players keep their web accounts"
echo "and found a new nation the next time they play."
if [ -z "$YES" ]; then
    read -r -p "Type yes to go on: " answer
    [ "$answer" = yes ] || { echo "Nothing changed"; exit 1; }
fi

# 1. The hall of fame, from the latest public status
docker exec "$CONTAINER" conquer-status > /dev/null 2>&1 || true
./season-end.sh "$NAME"

# 2. A copy of the old world (taken under the turn lock) and the accounts
copy="$BACKUPS/season-end-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$copy"
chmod 700 "$BACKUPS"
docker exec "$CONTAINER" flock /run/conquer/turn.lock tar czf - -C /opt/conquer lib > "$copy/world.tgz"
[ -f "$HTPASSWD" ] && cp -p "$HTPASSWD" "$copy/"
echo "✅ The old world and the accounts are kept in $copy"

# 3 and 4. The new world, from inside the container
args=()
if [ -n "$WORLD" ]; then
    docker cp "$WORLD" "$CONTAINER:/tmp/new-world.tar.gz"
    args=(/tmp/new-world.tar.gz)
fi
docker exec -u root "$CONTAINER" conquer-new-world "${args[@]}"
[ -n "$WORLD" ] && docker exec -u root "$CONTAINER" rm -f /tmp/new-world.tar.gz
docker exec "$CONTAINER" conquer-status > /dev/null 2>&1 || true
echo "✅ Season \"$NAME\" is in the hall of fame and the new one has begun"
