#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Found the nation of a new player: shown by the menu the first time an
# account created on the sign-up page (web/join.html, conquer-signup) plays.
# Such an account is marked "account:+" in lib/.players.
#
#  1. Explain the game's nation builder, then run it (conqrun -a).
#  2. Link the account to the new nation in lib/.players.
#
# usage: conquer-join [LANGUAGE]   (passed on by the menu; the account is
#                                   TTYD_USER, set by ttyd from the proxy)

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
PLAYERS_FILE="$WORLD_DIR/.players"
LOCK_FILE=/run/conquer/join.lock
ACCOUNT="${TTYD_USER:-}"
LAST_JOIN_TURN=5

ADMIN_CONTACT=""
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

stop() {
    echo
    say "${yellow}$*${reset}"
    [ -n "$ADMIN_CONTACT" ] && say "$(t join_questions "$ADMIN_CONTACT")"
    echo
    read -r -s -n 1 -p "$(t join_finish)"
    exit 1
}

nations() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | awk '$1 ~ /^[0-9]+$/ { print $2 }' | sort
}

current_turn() {
    "$PREFIX/bin/conquer" -s 2>/dev/null | sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' | head -n 1
}

# Replace the line of account $1 in lib/.players with "$1:$2", in place so
# a bind-mounted file keeps working
set_nation() {
    local rest
    rest=$(awk -F: -v key="$1" '$1 != key' "$PLAYERS_FILE") || return 1
    { [ -n "$rest" ] && printf '%s\n' "$rest"; printf '%s:%s\n' "$1" "$2"; } > "$PLAYERS_FILE"
}

[ -n "$ACCOUNT" ] || exit 1

clear
echo
say "$(t join_title)"
echo
say "$(t join_welcome "$ACCOUNT")"

turn=$(current_turn)
if [ "${turn:-1}" -gt "$LAST_JOIN_TURN" ]; then
    stop "$(t join_too_late "$turn")"
fi

t join_builder; echo
read -r -s -n 1 -p "$(t join_open_builder)" || exit 0
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
    stop "$(t join_no_nation)"
fi

(
    flock 9 || exit 1
    set_nation "$ACCOUNT" "$nation"
) 9> "$LOCK_FILE.accounts" || stop "$(t join_not_saved "$nation")"
echo "[join] account $ACCOUNT founded the nation $nation" > /run/conquer/log 2>/dev/null &

clear
t join_done "$nation"; echo
read -r -s -n 1 -p "$(t join_finish)"
exit 0
