#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Manage the web accounts players use to open the game at /play/.
# Apache checks them (basic auth against an htpasswd file) and tells ttyd
# who signed in; an account named like a nation opens that nation directly.
#
# Usage:
#   ./manage-players.sh add NAME [--password-stdin]   create or reset an account
#   ./manage-players.sh remove NAME                   delete an account
#   ./manage-players.sh list                          list accounts
#
# The account file is data/auth/htpasswd for the local setup and
# /etc/apache2/conquer-web.htpasswd on the VPS (run with sudo there).
# Set HTPASSWD_FILE to use another file.

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

usage() {
    sed -n '/^# Usage:/,/^# Set HTPASSWD_FILE/p' "$0" | sed 's/^# \{0,1\}//'
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

remove_line() {
    local tmp
    [ -f "$HTPASSWD_FILE" ] || return 0
    tmp=$(mktemp "$HTPASSWD_FILE.XXXXXX")
    awk -F: -v user="$1" '$1 != user' "$HTPASSWD_FILE" > "$tmp"
    cat "$tmp" > "$HTPASSWD_FILE"
    rm -f "$tmp"
}

cmd_add() {
    local name="$1" password password2 line
    valid_name "$name" || { echo "❌ Invalid name: use letters, digits, . _ - (max 32)"; exit 1; }

    if [ "$2" = "--password-stdin" ]; then
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
    remove_line "$name"
    printf '%s\n' "$line" >> "$HTPASSWD_FILE"
    echo "✅ Account '$name' saved in $HTPASSWD_FILE"
}

cmd_remove() {
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    if ! awk -F: -v user="$1" '$1 == user { found = 1 } END { exit !found }' "$HTPASSWD_FILE" 2>/dev/null; then
        echo "❌ No account named '$1'"
        exit 1
    fi
    remove_line "$1"
    echo "✅ Account '$1' removed"
}

cmd_list() {
    if [ ! -s "$HTPASSWD_FILE" ]; then
        echo "No accounts yet ($HTPASSWD_FILE)"
        return
    fi
    cut -d: -f1 "$HTPASSWD_FILE" | sort
}

case "${1:-}" in
    add) [ -n "$2" ] || usage; cmd_add "$2" "$3" ;;
    remove) [ -n "$2" ] || usage; cmd_remove "$2" ;;
    list) cmd_list ;;
    *) usage ;;
esac
