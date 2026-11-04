#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Player accounts for the site (the sign-up page, through conquer-gate).
# An account is written to the file Apache checks and marked in
# lib/.players: "account:?" while the administrator has not approved it,
# "account:+" once it may found a nation (the first time the player plays,
# the menu opens the nation builder). Pending requests are also listed in
# lib/.requests (account, time, email, message, language; tab separated).
#
# usage: conquer-signup request ACCOUNT [EMAIL] [MESSAGE] [LANG]   (password on stdin)
#        conquer-signup invite  CODE ACCOUNT                (password on stdin)
#        conquer-signup approve ACCOUNT
#        conquer-signup reject  ACCOUNT
#        conquer-signup assign  ACCOUNT NATION|+|*          (NATION must exist in the world)
#        conquer-signup invites COUNT                       (prints new codes)
#        conquer-signup expire  DAYS                        (removes requests older than DAYS days
#                                                            with their accounts; prints the names)
#        conquer-signup CODE ACCOUNT                        (same as invite)
#
# Exit status: 0 done, 2 unknown or used code (invite) or account not
# pending (approve, reject) or unknown account (assign), 3 account name
# taken, 6 no such nation (assign; the nations are printed),  5 sign-up closed (the
# account file cannot be written), 1 anything else. (4 was "too late in
# the game"; an approved account can found its nation at any turn now.)
#
# Administrators can also use: ./manage-players.sh invite|approve|reject

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
INVITES_FILE="$WORLD_DIR/.invites"
PLAYERS_FILE="$WORLD_DIR/.players"
REQUESTS_FILE="$WORLD_DIR/.requests"
HTPASSWD_FILE="${HTPASSWD_FILE:-$PREFIX/auth/htpasswd}"
LOCK_FILE="${CONQUER_RUN:-/run/conquer}/join.lock.accounts"
# Requests waiting for the administrator: past this the page says sign-up is
# closed, so nobody can fill the account file and the disk with accounts
MAX_PENDING=200
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

# The first character is a letter or digit: "-name" would be read as an
# option by htpasswd, and "." or ".." must never become a directory name
# (the menu's practice world is named after the account). Same rule as
# accountRe in the gate and valid_name in manage-players.sh.
valid_account() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$ ]]
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

# Print the world's spelling of nation $1 (any case); fails when there is none
world_nation() {
    /usr/local/bin/conquer-status --nations 2>/dev/null | awk -F'\t' -v n="$1" 'tolower($1) == tolower(n) { print $1; found = 1; exit } END { exit !found }'
}

# Is account $1 waiting for approval?
is_pending() {
    awk -F: -v user="$1" '$1 == user && $2 == "?" { found = 1 } END { exit !found }' "$PLAYERS_FILE" 2>/dev/null
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
    case "$5" in
        en|es|de|pl|pt-br|ru|zh) lang="$5" ;;
        *) lang=en ;;
    esac
    read_password
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        if [ -s "$REQUESTS_FILE" ] && [ "$(wc -l < "$REQUESTS_FILE")" -ge "$MAX_PENDING" ]; then exit 5; fi
        create_account "$account" '?'
        touch "$REQUESTS_FILE" 2>/dev/null
        chmod 640 "$REQUESTS_FILE" 2>/dev/null
        printf '%s\t%s\t%s\t%s\t%s\n' "$account" "$(date +%s)" "$email" "$message" "$lang" >> "$REQUESTS_FILE" || {
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
    (
        flock 9 || exit 1
        grep -qxF -- "$code" "$INVITES_FILE" 2>/dev/null || exit 2
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
assign)
    account="$2" target="$3"
    valid_account "$account" || exit 2
    case "$target" in
        '+'|'*') ;;
        *)
            [[ "$target" =~ ^[A-Za-z0-9_.-]{1,9}$ ]] || exit 6
            nation=$(world_nation "$target") || {
                echo "Nations: $(/usr/local/bin/conquer-status --nations 2>/dev/null | cut -f1 | paste -sd' ')"
                exit 6
            }
            target="$nation"
            ;;
    esac
    (
        flock 9 || exit 1
        has_key "$HTPASSWD_FILE" "$account" || exit 2
        touch "$PLAYERS_FILE" 2>/dev/null
        [ -w "$PLAYERS_FILE" ] || exit 1
        if has_key "$PLAYERS_FILE" "$account"; then
            set_mark "$account" "$target" || exit 1
        else
            printf '%s:%s\n' "$account" "$target" >> "$PLAYERS_FILE" || exit 1
        fi
        drop_line "$REQUESTS_FILE" "$account" "$TAB"
        echo "$target"
    ) 9> "$LOCK_FILE"
    ;;
expire)
    days="$2"
    [[ "$days" =~ ^[0-9]+$ ]] && [ "$days" -ge 1 ] || exit 1
    [ -s "$REQUESTS_FILE" ] || exit 0
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        cutoff=$(( $(date +%s) - days * 86400 ))
        mapfile -t requests < "$REQUESTS_FILE"
        for line in "${requests[@]}"; do
            IFS=$'\t' read -r name since _ <<< "$line"
            [[ "$since" =~ ^[0-9]+$ ]] && [ "$since" -lt "$cutoff" ] && valid_account "$name" || continue
            if is_pending "$name"; then
                drop_line "$HTPASSWD_FILE" "$name" || exit 1
                drop_line "$PLAYERS_FILE" "$name" || exit 1
                echo "$name"
            fi
            # Also a request line whose account is no longer waiting
            drop_line "$REQUESTS_FILE" "$name" "$TAB"
        done
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
