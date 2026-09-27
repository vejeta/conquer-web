#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Join the game with an invite code, in the browser terminal: shown instead
# of the player menu to the public join account (JOIN_ACCOUNT).
#
#  1. Check the invite code (lib/.invites, one code per line, single use).
#  2. Choose a player account and its password.
#  3. Build the nation with the game's own nation builder (conqrun -a).
#  4. Create the account (the htpasswd file Apache checks), link it to the
#     new nation (lib/.players) and use up the invite code.
#
# Administrators create codes with: ./manage-players.sh invite [COUNT]
#
# usage: conquer-join [LANGUAGE]   (passed on by the menu)

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
INVITES_FILE="$WORLD_DIR/.invites"
PLAYERS_FILE="$WORLD_DIR/.players"
HTPASSWD_FILE="${HTPASSWD_FILE:-$PREFIX/auth/htpasswd}"
LOCK_FILE=/run/conquer/join.lock

ADMIN_CONTACT="" JOIN_ACCOUNT=""
# shellcheck source=/dev/null
[ -f /etc/conquer-web.env ] && . /etc/conquer-web.env

bold=$(tput bold 2>/dev/null)
dim=$(tput dim 2>/dev/null)
yellow=$(tput setaf 3 2>/dev/null)
green=$(tput setaf 2 2>/dev/null)
reset=$(tput sgr0 2>/dev/null)

# Texts in the language passed on by the menu
# shellcheck source=i18n.sh
. /usr/local/lib/conquer-i18n.sh
load_texts "${1:-}"

say() { printf '  %s\n' "$*"; }

fail() {
    echo
    say "${yellow}$*${reset}"
    [ -n "$ADMIN_CONTACT" ] && say "$(t join_questions "$ADMIN_CONTACT")"
    echo
    read -r -s -n 1 -p "$(t join_again)"
    return 1
}

nations() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | awk '$1 ~ /^[0-9]+$/ { print $2 }' | sort
}

current_turn() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1
}

account_exists() {
    awk -F: -v user="$1" '$1 == user { found = 1 } END { exit !found }' "$HTPASSWD_FILE" 2>/dev/null
}

# Remove line $2 (exact match on the first field) from file $1, in place so
# a bind-mounted file keeps working
drop_line() {
    local rest
    rest=$(awk -F: -v key="$2" '$1 != key' "$1") || return 1
    if [ -n "$rest" ]; then printf '%s\n' "$rest" > "$1"; else : > "$1"; fi
}

banner() {
    clear
    echo
    say "$(t join_title)"
    echo
}

join() {
    local code account password password2 before after nation turn

    banner
    if [ ! -w "$HTPASSWD_FILE" ]; then
        fail "$(t join_closed)"
        return
    fi
    say "$(t join_welcome)"
    echo
    read -r -p "$(t join_code)" code
    code=$(printf '%s' "$code" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')
    if [ -z "$code" ] || ! grep -qx -- "$code" "$INVITES_FILE" 2>/dev/null; then
        fail "$(t join_bad_code)"
        return
    fi

    turn=$(current_turn)
    if [ "${turn:-1}" -gt 5 ]; then
        fail "$(t join_too_late "$turn")"
        return
    fi

    echo
    say "$(t join_choose_account)"
    read -r -p "$(t join_account)" account
    if ! [[ "$account" =~ ^[A-Za-z0-9_.-]{1,32}$ ]] || [ "$account" = "$JOIN_ACCOUNT" ]; then
        fail "$(t join_bad_account)"
        return
    fi
    if account_exists "$account"; then
        fail "$(t join_account_exists "$account")"
        return
    fi
    read -r -s -p "$(t join_password)" password; echo
    read -r -s -p "$(t join_password_again)" password2; echo
    if [ "$password" != "$password2" ]; then
        fail "$(t join_password_mismatch)"
        return
    fi
    if [ ${#password} -lt 8 ]; then
        fail "$(t join_password_short)"
        return
    fi

    clear
    t join_builder; echo
    read -r -s -n 1 -p "$(t join_open_builder)"
    before=$(nations)
    (
        # One nation builder at a time
        flock 9 || exit 1
        "$PREFIX/bin/conqrun" -a -d "$WORLD_DIR"
    ) 9> "$LOCK_FILE"
    stty sane 2>/dev/null
    tput sgr0 2>/dev/null
    after=$(nations)
    nation=$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | head -n 1)
    if [ -z "$nation" ]; then
        fail "$(t join_no_nation)"
        return
    fi

    # Account, nation link and the used-up invite, under one lock; check
    # every file first so a failure leaves nothing half done
    (
        flock 9 || exit 1
        grep -qx -- "$code" "$INVITES_FILE" || exit 2
        touch "$PLAYERS_FILE" 2>/dev/null
        [ -w "$INVITES_FILE" ] && [ -w "$PLAYERS_FILE" ] && [ -w "$HTPASSWD_FILE" ] || exit 1
        line=$(printf '%s\n' "$password" | htpasswd -niB "$account" | sed '/^$/d') || exit 1
        [ -n "$line" ] || exit 1
        remaining=$(grep -vx -- "$code" "$INVITES_FILE")
        drop_line "$PLAYERS_FILE" "$account" || exit 1
        printf '%s:%s\n' "$account" "$nation" >> "$PLAYERS_FILE" || exit 1
        printf '%s\n' "$line" >> "$HTPASSWD_FILE" || exit 1
        if [ -n "$remaining" ]; then
            printf '%s\n' "$remaining" > "$INVITES_FILE"
        else
            : > "$INVITES_FILE"
        fi
    ) 9> "$LOCK_FILE.accounts"
    case $? in
        0) ;;
        2) fail "$(t join_code_used "$nation")"; return ;;
        *) fail "$(t join_not_saved "$nation")"; return ;;
    esac
    echo "[join] account $account created for nation $nation" > /run/conquer/log 2>/dev/null

    clear
    t join_done "$nation" "$account" "$account"; echo
    read -r -s -n 1 -p "$(t join_finish)"
    return 0
}

while true; do
    join && break
done
clear
t join_goodbye; echo
