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
#   ./manage-players.sh password NAME       reset the password of an account
#                                           (same as add NAME)
#   ./manage-players.sh assign NAME NATION  assign a nation of the world to an
#                                           account (see: nations)
#   ./manage-players.sh assign NAME --admin let an account open any nation
#   ./manage-players.sh assign NAME --found the account founds a new nation
#                                           the next time it plays
#   ./manage-players.sh rename NAME NEWNAME rename an account (same password,
#                                           same nation)
#   ./manage-players.sh remove NAME         delete an account
#   ./manage-players.sh list                accounts with their nations, and the
#                                           nations that have no account
#   ./manage-players.sh nations             the nations of the world: name, race,
#                                           class and the account that plays it
#   ./manage-players.sh invite [COUNT]      create invite codes (default 1)
#   ./manage-players.sh invites             list the unused invite codes
#   ./manage-players.sh requests            list the requests waiting for approval
#   ./manage-players.sh approve NAME        approve a request (the player may found
#                                           a nation; players are never mailed)
#   ./manage-players.sh reject NAME         reject a request and delete its account
#
# Without an assignment an account opens the nation with the same name, if
# there is one. The account file is data/auth/htpasswd for the local setup
# and /etc/apache2/conquer-web.htpasswd on the VPS (run with sudo there).
# Set HTPASSWD_FILE to use another file.
# Assignments are kept with the world, in data/lib/.players (PLAYERS_FILE).
# Requests wait in data/lib/.requests (REQUESTS_FILE); the website's /admin/
# page does the same as requests, approve and reject.

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
REQUESTS_FILE="${REQUESTS_FILE:-$SCRIPT_DIR/data/lib/.requests}"
TAB=$'\t'

usage() {
    sed -n '/^# Usage:/,/^# Assignments are kept/p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

# Print an htpasswd line (bcrypt) for user $1, reading the password on stdin
hash_line() {
    # -C 10: the cost the sign-up page uses (htpasswd's default is 5)
    if command -v htpasswd >/dev/null 2>&1; then
        htpasswd -niB -C 10 "$1"
    else
        # Apache's own tool from the httpd image the local setup already uses
        docker run --rm -i --entrypoint htpasswd httpd:2.4 -niB -C 10 "$1"
    fi
}

# The first character is a letter or digit: "-name" would be read as an
# option by htpasswd, and "." or ".." must never become a directory name.
# Same rule as accountRe in the gate and valid_account in signup.sh.
valid_name() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$ ]]
}

# Files in data/lib belong to the game user, who could swap one for a link
# to a file of root's while this script runs with sudo: refuse links
refuse_link() {
    local f
    for f in "$@"; do
        if [ -L "$f" ]; then
            echo "❌ $f is a symbolic link: not touching it" >&2
            exit 1
        fi
    done
}

# Conquer nation names: up to 9 characters
valid_nation() {
    [[ "$1" =~ ^[A-Za-z0-9_.-]{1,9}$ ]]
}

# Remove the line for account $2 from the "name:..." file $1 (fields
# separated by $3 instead of ":", for the tab separated requests)
remove_line() {
    local file="$1" tmp
    refuse_link "$file"
    [ -f "$file" ] || return 0
    tmp=$(mktemp "$file.XXXXXX")
    awk -F"${3:-:}" -v user="$2" '$1 != user' "$file" > "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"
}

# Files in data/lib belong to the game user (the sign-up service in the game
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
    refuse_link "$PLAYERS_FILE"
    touch "$PLAYERS_FILE"
    remove_line "$PLAYERS_FILE" "$1"
    printf '%s:%s\n' "$1" "$2" >> "$PLAYERS_FILE"
    chmod 644 "$PLAYERS_FILE"
    match_world_owner "$PLAYERS_FILE"
}

# Nation argument: --admin, --found or a nation name, printed as stored
nation_arg() {
    if [ "$1" = "--admin" ]; then
        echo "*"
    elif [ "$1" = "--found" ]; then
        echo "+"
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
    refuse_link "$HTPASSWD_FILE"
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
    elif [ "$2" = "+" ]; then
        echo "✅ '$1' founds a new nation in the game's nation builder the next time it plays"
    else
        echo "✅ '$1' opens the nation '$2'"
    fi
}

# The nations of the world, one per line: name<TAB>race<TAB>class. From the
# game container (conquer-status --nations, which reads "conquer -s", the
# source of status.json); without a running container, from the nations of
# data/public/status.json (needs jq). Fails when neither is available.
world_nations() {
    local c out
    if [ -n "$NATIONS_FILE" ]; then cat "$NATIONS_FILE"; return; fi
    for c in conquer-local conquer-vps; do
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$c"; then
            out=$(docker exec -u conquer "$c" conquer-status --nations 2>/dev/null) && [ -n "$out" ] \
                && { printf '%s\n' "$out"; return; }
        fi
    done
    local json="${STATUS_JSON:-$SCRIPT_DIR/data/public/status.json}"
    if [ -r "$json" ] && command -v jq >/dev/null 2>&1; then
        out=$(jq -r '.nations[]? | [.name, .race, .class] | @tsv' "$json" 2>/dev/null | sort -f) \
            && [ -n "$out" ] && { printf '%s\n' "$out"; return; }
    fi
    return 1
}

# Account that plays each nation, as "nation<TAB>account" lines: the
# assignments of .players, and an account without one opens the nation named
# like it (when the world has one)
nation_owners() {
    awk -F: -v players="$PLAYERS_FILE" '
        BEGIN {
            while ((getline line < players) > 0) { split(line, f, ":"); mark[f[1]] = f[2] }
        }
        {
            m = ($1 in mark) ? mark[$1] : ""
            if (m == "") print tolower($1) "\t" $1
            else if (m != "*" && m != "+" && m != "?") print tolower(m) "\t" $1
        }' "$HTPASSWD_FILE" 2>/dev/null
}

cmd_nations() {
    local nations
    nations=$(world_nations) || { echo "❌ Cannot read the nations of the world: the game container is not running and there is no data/public/status.json (needs jq)" >&2; exit 1; }
    printf '%s\n' "$nations" | awk -F'\t' -v owners="$(nation_owners)" '
        BEGIN {
            n = split(owners, o, "\n")
            for (i = 1; i <= n; i++) { split(o[i], f, "\t"); if (f[1] == "") continue; if (f[1] in acc) acc[f[1]] = acc[f[1]] "," f[2]; else acc[f[1]] = f[2] }
            printf "%-10s %-10s %-10s %s\n", "NATION", "RACE", "CLASS", "ACCOUNT"
        }
        NF >= 3 { a = (tolower($1) in acc) ? acc[tolower($1)] : "—"; printf "%-10s %-10s %-10s %s\n", $1, $2, $3, a }' \
        | { read -r head; echo "$head"; sort -f; }
}

cmd_assign() {
    local nation
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    nation=$(nation_arg "$2") || exit 1
    if [ "$nation" != "*" ] && [ "$nation" != "+" ]; then
        local nations canon
        if nations=$(world_nations); then
            canon=$(printf '%s\n' "$nations" | awk -F'\t' -v n="$nation" 'tolower($1) == tolower(n) { print $1; exit }')
            if [ -z "$canon" ]; then
                echo "❌ There is no nation '$nation' in the world. Available nations:" >&2
                printf '%s\n' "$nations" | awk -F'\t' '{ printf "   %-10s %s %s\n", $1, $2, $3 }' >&2
                echo "   (or --found for a new nation, --admin for an administrator)" >&2
                exit 1
            fi
            nation="$canon"
        else
            echo "⚠️  Cannot read the nations of the world: '$nation' is not checked" >&2
        fi
    fi
    set_nation "$1" "$nation"
    describe "$1" "$nation"
}

cmd_remove() {
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    if ! has_account "$1"; then
        echo "❌ No account named '$1'"
        exit 1
    fi
    remove_line "$HTPASSWD_FILE" "$1"
    remove_line "$PLAYERS_FILE" "$1"
    remove_line "$REQUESTS_FILE" "$1" "$TAB"
    echo "✅ Account '$1' removed"
}

has_account() {
    awk -F: -v user="$1" '$1 == user { found = 1 } END { exit !found }' "$HTPASSWD_FILE" 2>/dev/null
}

# Rename account $1 to $2: the password (its hash does not depend on the
# name) and the nation go with it
cmd_rename() {
    local old="$1" new="$2" tmp
    valid_name "$old" && valid_name "$new" || { echo "❌ Invalid name: use letters, digits, . _ - (max 32)"; exit 1; }
    has_account "$old" || { echo "❌ No account named '$old'"; exit 1; }
    ! has_account "$new" || { echo "❌ There is already an account named '$new'"; exit 1; }
    refuse_link "$HTPASSWD_FILE" "$PLAYERS_FILE" "$REQUESTS_FILE"
    for f in "$HTPASSWD_FILE" "$PLAYERS_FILE"; do
        [ -f "$f" ] || continue
        tmp=$(mktemp "$f.XXXXXX")
        awk -F: -v old="$old" -v new="$new" 'BEGIN { OFS = ":" } $1 == old { $1 = new } { print }' "$f" > "$tmp"
        cat "$tmp" > "$f"
        rm -f "$tmp"
    done
    if [ -f "$REQUESTS_FILE" ]; then
        tmp=$(mktemp "$REQUESTS_FILE.XXXXXX")
        awk -F"$TAB" -v old="$old" -v new="$new" 'BEGIN { OFS = FS } $1 == old { $1 = new } { print }' "$REQUESTS_FILE" > "$tmp"
        cat "$tmp" > "$REQUESTS_FILE"
        rm -f "$tmp"
    fi
    echo "✅ Account '$old' is now '$new' (same password)"
    echo "   Browsers remember the old name: sign in again, in a private window if it does not ask"
}

cmd_list() {
    local nations=""
    if [ ! -s "$HTPASSWD_FILE" ]; then
        echo "No accounts yet ($HTPASSWD_FILE)"
    else
        echo "Accounts"
        cut -d: -f1 "$HTPASSWD_FILE" | sort | awk -F: -v players="$PLAYERS_FILE" '
            BEGIN {
                while ((getline line < players) > 0) {
                    split(line, f, ":"); nation[f[1]] = f[2]
                }
                printf "%-32s %s\n", "ACCOUNT", "NATION"
            }
            {
                n = ($1 in nation) ? nation[$1] : "-"
                if (n == "*") n = "* (administrator: may open any nation)"
                if (n == "+") n = "+ (approved, founds its nation the next time it plays)"
                if (n == "?") n = "? (requested, waiting for approval)"
                if (n == "-") n = "- (no nation: opens one named like the account, if it exists)"
                printf "%-32s %s\n", $1, n
            }'
    fi
    echo
    echo "Nations without an account"
    if nations=$(world_nations); then
        printf '%s\n' "$nations" | awk -F'\t' -v owners="$(nation_owners)" '
            BEGIN {
                n = split(owners, o, "\n")
                for (i = 1; i <= n; i++) { split(o[i], f, "\t"); if (f[1] != "") taken[f[1]] = 1 }
                printf "%-10s %-10s %s\n", "NATION", "RACE", "CLASS"
            }
            NF >= 3 && !(tolower($1) in taken) { printf "%-10s %-10s %s\n", $1, $2, $3; found = 1 }
            END { if (!found) print "(none: every nation has an account)" }'
    else
        echo "(cannot read the nations of the world: the game container is not running)"
    fi
    echo
    echo "Marks: * administrator   + approved, founds a nation   ? waiting for approval"
    echo "       - no assignment (opens the nation named like the account, if any)"
    echo "Assign with: $0 assign NAME NATION   (see: $0 nations)"
}

# Invite codes: players type one on the sign-up page (signup.html) to create
# their account; the game then has them found their nation
cmd_invite() {
    local count="${1:-1}" i code
    [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -ge 1 ] && [ "$count" -le 100 ] || usage
    mkdir -p "$(dirname "$INVITES_FILE")"
    refuse_link "$INVITES_FILE"
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

# Is account $1 waiting for approval?
is_pending() {
    awk -F: -v user="$1" '$1 == user && $2 == "?" { found = 1 } END { exit !found }' "$PLAYERS_FILE" 2>/dev/null
}

# Requests for a seat: account, how long ago and language (no email or
# message is kept; conquer-signup scrub removes what older versions stored)
cmd_requests() {
    if [ ! -s "$REQUESTS_FILE" ]; then
        echo "No requests waiting for approval ($REQUESTS_FILE)"
        return
    fi
    awk -F'\t' -v now="$(date +%s)" '
        BEGIN { printf "%-32s %-10s %-6s %s\n", "ACCOUNT", "WAITING", "LANG" }
        {
            age = now - $2
            if (age >= 86400) w = int(age / 86400) " d"
            else if (age >= 3600) w = int(age / 3600) " h"
            else w = int(age / 60) " min"
            lang = (NF >= 5 ? $5 : (NF == 3 ? $3 : ""))
            printf "%-32s %-10s %s\n", $1, w, (lang != "" ? lang : "en")
        }' "$REQUESTS_FILE"
}

# Approve the request of account $1: it may found a nation next time it plays
cmd_approve() {
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    is_pending "$1" || { echo "❌ '$1' has no request waiting for approval (see: $0 requests)"; exit 1; }
    set_nation "$1" "+"
    remove_line "$REQUESTS_FILE" "$1" "$TAB"
    echo "✅ '$1' is approved: it founds a nation in the game the next time it plays"
}

# Reject the request of account $1 and delete the account
cmd_reject() {
    valid_name "$1" || { echo "❌ Invalid name"; exit 1; }
    is_pending "$1" || { echo "❌ '$1' has no request waiting for approval (see: $0 requests)"; exit 1; }
    remove_line "$HTPASSWD_FILE" "$1"
    remove_line "$PLAYERS_FILE" "$1"
    remove_line "$REQUESTS_FILE" "$1" "$TAB"
    echo "✅ Request of '$1' rejected: the account is deleted"
}

case "${1:-}" in
    add|password) [ -n "$2" ] || usage; shift; cmd_add "$@" ;;
    nations) cmd_nations ;;
    assign) [ -n "$3" ] || usage; cmd_assign "$2" "$3" ;;
    rename) [ -n "$3" ] || usage; cmd_rename "$2" "$3" ;;
    remove) [ -n "$2" ] || usage; cmd_remove "$2" ;;
    list) cmd_list ;;
    invite) cmd_invite "${2:-1}" ;;
    invites) cmd_invites ;;
    requests) cmd_requests ;;
    approve) [ -n "$2" ] || usage; cmd_approve "$2" ;;
    reject) [ -n "$2" ] || usage; cmd_reject "$2" ;;
    *) usage ;;
esac
