#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Create a player account from an invite code (the site's sign-up page,
# through conquer-gate). The account is written to the file Apache checks
# and marked in lib/.players as still without a nation ("account:+"): the
# first time the player plays, the menu opens the nation builder.
#
# usage: conquer-signup CODE ACCOUNT   (the password on standard input)
#
# Exit status: 0 created, 2 unknown or used code, 3 account name taken,
# 4 too late in the game for new nations, 5 sign-up closed (the account
# file cannot be written), 1 anything else.
#
# Administrators create codes with: ./manage-players.sh invite [COUNT]

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
INVITES_FILE="$WORLD_DIR/.invites"
PLAYERS_FILE="$WORLD_DIR/.players"
HTPASSWD_FILE="${HTPASSWD_FILE:-$PREFIX/auth/htpasswd}"
LOCK_FILE=/run/conquer/join.lock.accounts
# New nations may join until this turn; after it only the administrator
# adds them (conqrun asks for god's password)
LAST_JOIN_TURN=5

code="$1" account="$2"
[ -n "$code" ] && [ -n "$account" ] || exit 1
[[ "$account" =~ ^[A-Za-z0-9_.-]{1,32}$ ]] || exit 3
IFS= read -r password || exit 1
[ ${#password} -ge 8 ] || exit 1

[ -w "$HTPASSWD_FILE" ] || exit 5

turn=$("$PREFIX/bin/conquer" -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1)
[ "${turn:-1}" -le "$LAST_JOIN_TURN" ] || exit 4

# Remove line $2 (exact match on the first field) from file $1, in place so
# a bind-mounted file keeps working
drop_line() {
    local rest
    rest=$(awk -F: -v key="$2" '$1 != key' "$1") || return 1
    if [ -n "$rest" ]; then printf '%s\n' "$rest" > "$1"; else : > "$1"; fi
}

mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null
(
    flock 9 || exit 1
    grep -qx -- "$code" "$INVITES_FILE" 2>/dev/null || exit 2
    # Taken: an account of the site, or a name already given to someone
    awk -F: -v user="$account" '$1 == user { found = 1 } END { exit !found }' "$HTPASSWD_FILE" && exit 3
    touch "$PLAYERS_FILE" 2>/dev/null
    awk -F: -v user="$account" '$1 == user { found = 1 } END { exit !found }' "$PLAYERS_FILE" && exit 3
    [ -w "$INVITES_FILE" ] && [ -w "$PLAYERS_FILE" ] || exit 1
    line=$(printf '%s\n' "$password" | htpasswd -niB -C 10 "$account" | sed '/^$/d') || exit 1
    [ -n "$line" ] || exit 1
    # Everything checked: write the account, its mark and use the code up
    printf '%s:+\n' "$account" >> "$PLAYERS_FILE" || exit 1
    printf '%s\n' "$line" >> "$HTPASSWD_FILE" || { drop_line "$PLAYERS_FILE" "$account"; exit 1; }
    drop_line "$INVITES_FILE" "$code" || exit 1
) 9> "$LOCK_FILE"
# conquer-gate logs the result
