#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# OPTIONAL. The rehearsal of the player journey on the live server, for the
# day nobody is playing. The default is the staging stack (tests/e2e/up.sh):
# use this only when you want the real server's Apache, certificates and mail
# in the picture. Run it ON the server, in the repository checkout.
#
# What it does:
#   1. refuses to run without --yes-i-have-a-backup, and refuses while anyone
#      is in the game
#   2. makes a world backup itself (backup-world.sh) and records the existing
#      accounts (names only, never password hashes)
#   3. makes a throwaway administrator account and runs the journey
#      (tests/e2e/test_journey.py) with test accounts named e2e-<random>
#   4. at the end, always: stops the game, restores the world backup, deletes
#      the e2e accounts (web accounts, .players marks, .requests), starts the
#      game and prints what it cleaned
#
# Usage:
#   sudo -v   # the script uses sudo for the account and world files
#   tests/e2e/prod-rehearsal.sh --yes-i-have-a-backup \
#       [--base-url https://your-domain] \
#       [--players 4] [--container conquer-vps]
#
#   --base-url   the site the browsers open (default https://localhost; on a
#                server with a virtual host per domain use your domain)
#                (Players are never mailed. If NOTIFY_EMAIL is set, you still
#                get the administrator's notice for each request: the game has
#                no switch to turn that off.)
#   --players    how many test players (default 4)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_URL="${E2E_BASE_URL:-https://localhost}"
PLAYERS=4
CONTAINER="conquer-vps"
SURE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --yes-i-have-a-backup) SURE=1 ;;
        --base-url) BASE_URL="${2:?--base-url needs a value}"; shift ;;
        --players) PLAYERS="${2:?--players needs a number}"; shift ;;
        --container) CONTAINER="${2:?--container needs a name}"; shift ;;
        *) sed -n '/^# Usage:/,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//' | sed '$d'; exit 2 ;;
    esac
    shift
done

if [ -z "$SURE" ]; then
    echo "This runs a rehearsal on the LIVE world: it founds nations, forces turn" >&2
    echo "updates and then restores a backup it takes first. Nobody should be playing." >&2
    echo "Run it again with --yes-i-have-a-backup if you really want that." >&2
    exit 2
fi
case "$PLAYERS" in ''|*[!0-9]*) echo "--players needs a number" >&2; exit 2 ;; esac

SUDO=""
[ "$(id -u)" = 0 ] || SUDO="sudo"

# The web accounts file: the server's, or the local stack's
HT="${HTPASSWD_FILE:-/etc/apache2/conquer-web.htpasswd}"
[ -f "$HT" ] || HT="$ROOT/data/auth/htpasswd"
mp() { $SUDO env HTPASSWD_FILE="$HT" ./manage-players.sh "$@"; }

docker inspect -f '{{.State.Running}}' "$CONTAINER" 2> /dev/null | grep -qx true \
    || { echo "the game container '$CONTAINER' is not running" >&2; exit 1; }

# Nobody in the game (game sessions in the players' practice worlds do not count)
online=$(docker exec "$CONTAINER" sh -c 'for c in /proc/[0-9]*/comm; do [ "$(cat "$c" 2>/dev/null)" = conquer ] && tr "\0" " " < "${c%/comm}/cmdline" | grep -v -- "-d /opt/conquer/practice/"; done | wc -l' 2> /dev/null || echo 0)
if [ "${online:-0}" -gt 0 ]; then
    echo "$online game session(s) are running: somebody is playing. Try later." >&2
    exit 1
fi

WORK="$ROOT/test-results/e2e/prod-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK"
chmod 700 "$WORK"

# ---- 1. the backup, and what exists now ---------------------------------------
turn_of() { docker exec -u conquer "$CONTAINER" conquer -s 2> /dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1; }
accounts_now() { mp list 2> /dev/null | sed 's/\x1b\[[0-9;]*m//g'; }

echo "== World backup"
$SUDO ./backup-world.sh > "$WORK/backup.log" 2>&1 || { cat "$WORK/backup.log" >&2; echo "backup failed: nothing was touched" >&2; exit 1; }
BACKUP="$($SUDO sh -c 'ls -t backups/world_backup_*.tar.gz | head -n 1')"
[ -n "$BACKUP" ] || { echo "no backup file found: nothing was touched" >&2; exit 1; }
$SUDO tar -tzf "$BACKUP" | grep -q 'lib/data' || { echo "the backup $BACKUP has no world in it" >&2; exit 1; }
BACKUP="$ROOT/$BACKUP"
echo "backup: $BACKUP"
TURN_BEFORE="$(turn_of)"
accounts_now > "$WORK/accounts-before.txt"
$SUDO sh -c 'cut -d: -f1 data/lib/.players 2>/dev/null | sort' > "$WORK/players-before.txt" || true
echo "turn $TURN_BEFORE; accounts recorded in $WORK/accounts-before.txt"

# ---- 4. the cleanup, whatever happens ---------------------------------------------
ADMIN=""
STARTED=""
cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    [ -n "$STARTED" ] || exit "$rc"
    echo
    echo "== Cleaning up"
    docker stop "$CONTAINER" > /dev/null 2>&1 || true
    printf 'y\n' | $SUDO ./restore-world.sh "$BACKUP" > "$WORK/restore.log" 2>&1 \
        && echo "world restored from $(basename "$BACKUP")" \
        || { echo "RESTORE FAILED: see $WORK/restore.log, the backup is $BACKUP" >&2; rc=1; }
    docker start "$CONTAINER" > /dev/null
    local _
    for _ in $(seq 1 60); do
        [ "$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2> /dev/null)" = healthy ] && break
        sleep 3
    done
    # The e2e accounts: web accounts, .players marks and .requests (manage-players.sh remove does all three)
    local removed="" name
    for name in $($SUDO cut -d: -f1 "$HT" 2> /dev/null | grep -E '^e2e-' || true); do
        mp remove "$name" > /dev/null 2>&1 && removed="$removed $name"
    done
    $SUDO sh -c 'rm -rf data/practice/e2e-*' || true
    docker exec "$CONTAINER" conquer-status > /dev/null 2>&1 || true
    echo "e2e accounts removed:${removed:- none}"
    # What is left must be what was there before
    accounts_now > "$WORK/accounts-after.txt"
    $SUDO sh -c 'cut -d: -f1 data/lib/.players 2>/dev/null | sort' > "$WORK/players-after.txt" || true
    if diff -q "$WORK/accounts-before.txt" "$WORK/accounts-after.txt" > /dev/null && diff -q "$WORK/players-before.txt" "$WORK/players-after.txt" > /dev/null; then
        echo "accounts and assignments are as before"
    else
        echo "WARNING: accounts differ from before; compare $WORK/accounts-before.txt and accounts-after.txt" >&2
        rc=1
    fi
    echo "turn: $TURN_BEFORE before, $(turn_of) now"
    [ "$(turn_of)" = "$TURN_BEFORE" ] || { echo "WARNING: the turn is not the one from before" >&2; rc=1; }
    echo "the backup stays in $BACKUP"
    exit "$rc"
}
trap cleanup EXIT INT TERM

# ---- 3. the journey ------------------------------------------------------------------
STARTED=1
ADMIN="e2e-admin-$(openssl rand -hex 3)"
ADMIN_PASSWORD="$(openssl rand -hex 12)"
printf '%s\n' "$ADMIN_PASSWORD" | mp add "$ADMIN" --admin --password-stdin > /dev/null
echo "== Journey with $PLAYERS players at $BASE_URL"

E2E_BASE_URL="$BASE_URL" E2E_ADMIN_USER="$ADMIN" E2E_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    E2E_CONTAINER="$CONTAINER" E2E_PLAYERS="$PLAYERS" E2E_PREFIX="e2e" E2E_MAILPIT_URL="" \
    python3 -m pytest tests/e2e/test_journey.py -p no:cacheprovider -x -q
