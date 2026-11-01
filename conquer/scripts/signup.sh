#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Player accounts for the site (the sign-up page, through conquer-gate).
# An account is written to the file Apache checks and marked in
# lib/.players: "account:?" while the administrator has not approved it,
# "account:+" once it may found a nation (the first time the player plays,
# the menu opens the nation builder). Pending requests are also listed in
# lib/.requests (account, time, email, message; tab separated).
#
# usage: conquer-signup request ACCOUNT [EMAIL] [MESSAGE]   (password on stdin)
#        conquer-signup invite  CODE ACCOUNT                (password on stdin)
#        conquer-signup approve ACCOUNT
#        conquer-signup reject  ACCOUNT
#        conquer-signup invites COUNT                       (prints new codes)
#        conquer-signup CODE ACCOUNT                        (same as invite)
#
# Exit status: 0 done, 2 unknown or used code (invite) or account not
# pending (approve, reject), 3 account name taken, 4 too late in the game
# for new nations (invite only), 5 sign-up closed (the account file cannot
# be written), 1 anything else.
#
# Administrators can also use: ./manage-players.sh invite|approve|reject

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
INVITES_FILE="$WORLD_DIR/.invites"
PLAYERS_FILE="$WORLD_DIR/.players"
REQUESTS_FILE="$WORLD_DIR/.requests"
HTPASSWD_FILE="${HTPASSWD_FILE:-$PREFIX/auth/htpasswd}"
LOCK_FILE="${CONQUER_RUN:-/run/conquer}/join.lock.accounts"
# New nations may join until this turn; after it only the administrator
# adds them (conqrun asks for god's password)
LAST_JOIN_TURN=5
TAB=$'\t'

# Remove the line whose first field (separated by $3, default ":") is $2
# from file $1, in place so a bind-mounted file keeps working
drop_line() {
    local rest
    [ -e "$1" ] || return 0
    rest=$(awk -F"${3:-:}" -v key="$2" '$1 != key' "$1") || return 1
    if [ -n "$rest" ]; then printf '%s\n' "$rest" > "$1"; else : > "$1"; fi
}

# Is $2 the first field of file $1?
has_key() {
    awk -F: -v user="$2" '$1 == user { found = 1 } END { exit !found }' "$1" 2>/dev/null
}

# Text on one line, at most $2 characters
oneline() {
    local s
    s=$(printf '%s' "$1" | tr '\t\r\n' '   ')
    printf '%s' "${s:0:$2}"
}

# Read and check the password on standard input
read_password() {
    IFS= read -r password || exit 1
    [ ${#password} -ge 8 ] || exit 1
}

valid_account() {
    [[ "$1" =~ ^[A-Za-z0-9_.-]{1,32}$ ]]
}

# Create web account $1 marked $2 in .players (the caller holds the lock).
# Exits 3 when the name is taken, 1 on any other trouble.
create_account() {
    local line
    has_key "$HTPASSWD_FILE" "$1" && exit 3
    touch "$PLAYERS_FILE" 2>/dev/null
    has_key "$PLAYERS_FILE" "$1" && exit 3
    [ -w "$PLAYERS_FILE" ] || exit 1
    line=$(printf '%s\n' "$password" | htpasswd -niB -C 10 "$1" | sed '/^$/d') || exit 1
    [ -n "$line" ] || exit 1
    # Everything checked: write the account and its mark
    printf '%s:%s\n' "$1" "$2" >> "$PLAYERS_FILE" || exit 1
    printf '%s\n' "$line" >> "$HTPASSWD_FILE" || { drop_line "$PLAYERS_FILE" "$1"; exit 1; }
}

# Set the .players mark of account $1 to $2, in place
set_mark() {
    local rest
    rest=$(awk -F: -v user="$1" -v mark="$2" 'BEGIN { OFS = ":" } $1 == user { $2 = mark } { print }' "$PLAYERS_FILE") || return 1
    printf '%s\n' "$rest" > "$PLAYERS_FILE"
}

# Is account $1 waiting for approval?
is_pending() {
    awk -F: -v user="$1" '$1 == user && $2 == "?" { found = 1 } END { exit !found }' "$PLAYERS_FILE" 2>/dev/null
}

current_turn() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1
}

cmd="$1"
if [[ "$cmd" =~ ^[A-Z0-9]{4}-[A-Z0-9]{4}$ ]] && [ $# -eq 2 ]; then
    set -- invite "$@"
    cmd=invite
fi

mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null

case "$cmd" in
request)
    account="$2"
    valid_account "$account" || exit 3
    email=$(oneline "$3" 120)
    message=$(oneline "$4" 500)
    read_password
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        create_account "$account" '?'
        touch "$REQUESTS_FILE" 2>/dev/null
        chmod 640 "$REQUESTS_FILE" 2>/dev/null
        printf '%s\t%s\t%s\t%s\n' "$account" "$(date +%s)" "$email" "$message" >> "$REQUESTS_FILE" || {
            drop_line "$PLAYERS_FILE" "$account"
            drop_line "$HTPASSWD_FILE" "$account"
            exit 1
        }
    ) 9> "$LOCK_FILE"
    ;;
invite)
    code="$2" account="$3"
    [ -n "$code" ] && valid_account "$account" || exit 3
    read_password
    [ -w "$HTPASSWD_FILE" ] || exit 5
    turn=$(current_turn)
    [ "${turn:-1}" -le "$LAST_JOIN_TURN" ] || exit 4
    (
        flock 9 || exit 1
        grep -qx -- "$code" "$INVITES_FILE" 2>/dev/null || exit 2
        [ -w "$INVITES_FILE" ] || exit 1
        create_account "$account" '+'
        drop_line "$INVITES_FILE" "$code" || exit 1
    ) 9> "$LOCK_FILE"
    ;;
approve)
    account="$2"
    valid_account "$account" || exit 2
    (
        flock 9 || exit 1
        is_pending "$account" || exit 2
        set_mark "$account" '+' || exit 1
        drop_line "$REQUESTS_FILE" "$account" "$TAB"
    ) 9> "$LOCK_FILE"
    ;;
reject)
    account="$2"
    valid_account "$account" || exit 2
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        is_pending "$account" || exit 2
        drop_line "$HTPASSWD_FILE" "$account" || exit 1
        drop_line "$PLAYERS_FILE" "$account" || exit 1
        drop_line "$REQUESTS_FILE" "$account" "$TAB"
    ) 9> "$LOCK_FILE"
    ;;
invites)
    count="$2"
    [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -ge 1 ] && [ "$count" -le 100 ] || exit 1
    (
        flock 9 || exit 1
        touch "$INVITES_FILE" 2>/dev/null
        chmod 640 "$INVITES_FILE" 2>/dev/null
        [ -w "$INVITES_FILE" ] || exit 1
        for ((i = 0; i < count; i++)); do
            code=$(LC_ALL=C tr -dc 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' < /dev/urandom | head -c 8)
            code="${code:0:4}-${code:4:4}"
            printf '%s\n' "$code" >> "$INVITES_FILE" || exit 1
            echo "$code"
        done
    ) 9> "$LOCK_FILE"
    ;;
*)
    exit 1
    ;;
esac
# conquer-gate logs the result
