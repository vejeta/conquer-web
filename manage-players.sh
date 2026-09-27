#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Manage the web accounts players use to open the game at /play/.
# Apache checks them (basic auth against an htpasswd file) and tells ttyd
# who signed in. Each account opens only the nation assigned to it; an
# administrator account ("--admin") may open any nation, including god.
#
# Usage:
#   ./manage-players.sh add NAME [--nation NATION | --admin] [--password-stdin]
#                                           create or reset an account
#   ./manage-players.sh assign NAME NATION  assign a nation to an account
#   ./manage-players.sh assign NAME --admin let an account open any nation
#   ./manage-players.sh remove NAME         delete an account
#   ./manage-players.sh list                list accounts and their nations
#   ./manage-players.sh invite [COUNT]      create invite codes (default 1)
#   ./manage-players.sh invites             list the unused invite codes
#   ./manage-players.sh join-account [NAME] create the public account that
#                                           players with an invite code use
#
# Without an assignment an account opens the nation with the same name, if
# there is one. The account file is data/auth/htpasswd for the local setup
# and /etc/apache2/conquer-web.htpasswd on the VPS (run with sudo there).
# Set HTPASSWD_FILE to use another file.
# Assignments are kept with the world, in data/lib/.players (PLAYERS_FILE).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "$HTPASSWD_FILE" ]; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx conquer-vps \
        || { [ -f config/production.env ] && [ ! -f config/local.env ]; }; then
        HTPASSWD_FILE=/etc/apache2/conquer-web.htpasswd
    else
        HTPASSWD_FILE="$SCRIPT_DIR/data/auth/htpasswd"
    fi
fi

PLAYERS_FILE="${PLAYERS_FILE:-$SCRIPT_DIR/data/lib/.players}"
INVITES_FILE="${INVITES_FILE:-$SCRIPT_DIR/data/lib/.invites}"

usage() {
    sed -n '/^# Usage:/,/^# Assignments are kept/p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

# Print an htpasswd line (bcrypt) for user $1, reading the password on stdin
hash_line() {
    if command -v htpasswd >/dev/null 2>&1; then
        htpasswd -niB "$1"
    else
        # Apache's own tool from the httpd image the local setup already uses
        docker run --rm -i --entrypoint htpasswd httpd:2.4 -niB "$1"
    fi
}

valid_name() {
    [[ "$1" =~ ^[A-Za-z0-9_.-]{1,32}$ ]]
}

# Conquer nation names: up to 9 characters
valid_nation() {
    [[ "$1" =~ ^[A-Za-z0-9_.-]{1,9}$ ]]
}

# Remove the line for account $2 from the "name:..." file $1
remove_line() {
    local file="$1" tmp
    [ -f "$file" ] || return 0
    tmp=$(mktemp "$file.XXXXXX")
    awk -F: -v user="$2" '$1 != user' "$file" > "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"
}

# Files in data/lib belong to the game user (the join wizard in the game
# container writes them too), also when this script runs with sudo
match_world_owner() {
    local owner
    owner=$(stat -c %u "$(dirname "$1")" 2>/dev/null) || return 0
    [ "$(id -u)" = 0 ] && chown "$owner" "$1" 2>/dev/null
    return 0
}

# Assign nation $2 ("*" = any nation) to account $1
set_nation() {
    mkdir -p "$(dirname "$PLAYERS_FILE")"
    touch "$PLAYERS_FILE"
    remove_line "$PLAYERS_FILE" "$1"
    printf '%s:%s\n' "$1" "$2" >> "$PLAYERS_FILE"
    chmod 644 "$PLAYERS_FILE"
    match_world_owner "$PLAYERS_FILE"
}

# Nation argument: --admin or a nation name, printed as stored
nation_arg() {
    if [ "$1" = "--admin" ]; then
        echo "*"
    elif valid_nation "$1"; then
        echo "$1"
    else
        echo "❌ Invalid nation name: use letters, digits, . _ - (max 9)" >&2
        return 1
    fi
}

cmd_add() {
    local name="$1" password password2 line nation="" stdin=""
    valid_name "$name" || { echo "❌ Invalid name: use letters, digits, . _ - (max 32)"; exit 1; }
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --password-stdin) stdin=1 ;;
            --admin) nation="*" ;;
            --nation) nation=$(nation_arg "$2") || exit 1; shift ;;
            *) usage ;;
        esac
        shift
    done

    if [ -n "$stdin" ]; then
        IFS= read -r password
    else
        read -r -s -p "Password for $name (empty = generate one): " password; echo
        if [ -n "$password" ]; then
            read -r -s -p "Repeat password: " password2; echo
            [ "$password" = "$password2" ] || { echo "❌ Passwords do not match"; exit 1; }
        fi
    fi
    if [ -z "$password" ]; then
        password=$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-14)
        echo "🔑 Generated password for $name: $password"
    fi
    if [ ${#password} -lt 8 ]; then
        echo "❌ Use at least 8 characters"
        exit 1
    fi

    line=$(printf '%s\n' "$password" | hash_line "$name")
    mkdir -p "$(dirname "$HTPASSWD_FILE")"
    touch "$HTPASSWD_FILE"
    remove_line "$HTPASSWD_FILE" "$name"
    printf '%s\n' "$line" >> "$HTPASSWD_FILE"
    echo "✅ Account '$name' saved in $HTPASSWD_FILE"
    if [ -n "$nation" ]; then
        set_nation "$name" "$nation"
        describe "$name" "$nation"
    fi
}

describe() {
    if [ "$2" = "*" ]; then
        echo "✅ '$1' is an administrator account: it may open any nation"
    else
        echo "✅ '$1' opens the nation '$2'"
    fi
}

cmd_assign() {
    local nation
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    nation=$(nation_arg "$2") || exit 1
    set_nation "$1" "$nation"
    describe "$1" "$nation"
}

cmd_remove() {
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    if ! awk -F: -v user="$1" '$1 == user { found = 1 } END { exit !found }' "$HTPASSWD_FILE" 2>/dev/null; then
        echo "❌ No account named '$1'"
        exit 1
    fi
    remove_line "$HTPASSWD_FILE" "$1"
    remove_line "$PLAYERS_FILE" "$1"
    echo "✅ Account '$1' removed"
}

cmd_list() {
    if [ ! -s "$HTPASSWD_FILE" ]; then
        echo "No accounts yet ($HTPASSWD_FILE)"
        return
    fi
    # Account and its nation ("-" when none is assigned)
    cut -d: -f1 "$HTPASSWD_FILE" | sort | awk -F: -v players="$PLAYERS_FILE" '
        BEGIN {
            while ((getline line < players) > 0) {
                split(line, f, ":"); nation[f[1]] = f[2]
            }
            printf "%-32s %s\n", "ACCOUNT", "NATION"
        }
        {
            n = ($1 in nation) ? nation[$1] : "-"
            if (n == "*") n = "* (administrator)"
            printf "%-32s %s\n", $1, n
        }'
}

# Invite codes: players type one in the join wizard (sign in with the
# join account) to build their nation and create their own account
cmd_invite() {
    local count="${1:-1}" i code
    [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -ge 1 ] && [ "$count" -le 100 ] || usage
    mkdir -p "$(dirname "$INVITES_FILE")"
    touch "$INVITES_FILE"
    chmod 640 "$INVITES_FILE"
    match_world_owner "$INVITES_FILE"
    for ((i = 0; i < count; i++)); do
        code=$(LC_ALL=C tr -dc 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' < /dev/urandom | head -c 8)
        code="${code:0:4}-${code:4:4}"
        printf '%s\n' "$code" >> "$INVITES_FILE"
        echo "$code"
    done
    echo "✅ $count invite code(s) added; each works once" >&2
}

cmd_invites() {
    if [ ! -s "$INVITES_FILE" ]; then
        echo "No unused invite codes ($INVITES_FILE)"
        return
    fi
    cat "$INVITES_FILE"
}

cmd_join_account() {
    local name="${1:-join}" password
    valid_name "$name" || { echo "❌ Invalid name"; exit 1; }
    password=$(openssl rand -base64 9 | tr -d '/+=' | cut -c1-10)
    printf '%s\n' "$password" | cmd_add "$name" --password-stdin > /dev/null
    remove_line "$PLAYERS_FILE" "$name"
    cat <<EOF
✅ Join account created. Anyone may use it: it only opens the join wizard,
   and joining needs an invite code (./manage-players.sh invite).
   Add these lines to the environment file (config/local.env or
   config/production.env) and restart with ./rebuild.sh --quick:

JOIN_ACCOUNT=$name
JOIN_PASSWORD=$password

   The landing page then shows this account and password to visitors.
EOF
}

case "${1:-}" in
    add) [ -n "$2" ] || usage; shift; cmd_add "$@" ;;
    assign) [ -n "$3" ] || usage; cmd_assign "$2" "$3" ;;
    remove) [ -n "$2" ] || usage; cmd_remove "$2" ;;
    list) cmd_list ;;
    invite) cmd_invite "${2:-1}" ;;
    invites) cmd_invites ;;
    join-account) cmd_join_account "${2:-join}" ;;
    *) usage ;;
esac
