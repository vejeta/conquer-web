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

say() { printf '  %s\n' "$*"; }

fail() {
    echo
    say "${yellow}$*${reset}"
    [ -n "$ADMIN_CONTACT" ] && say "Questions: ${bold}${ADMIN_CONTACT}${reset}"
    echo
    read -r -s -n 1 -p "  Press any key to start again..."
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
    say "${bold}${green}Join Conquer${reset}"
    echo
}

join() {
    local code account password password2 before after nation turn

    banner
    if [ ! -w "$HTPASSWD_FILE" ]; then
        fail "Joining is not available on this server right now."
        return
    fi
    say "Welcome. You need an ${bold}invite code${reset} from the game administrator."
    echo
    read -r -p "  Invite code: " code
    code=$(printf '%s' "$code" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')
    if [ -z "$code" ] || ! grep -qx -- "$code" "$INVITES_FILE" 2>/dev/null; then
        fail "That invite code is not valid, or it has been used already."
        return
    fi

    turn=$(current_turn)
    if [ "${turn:-1}" -gt 5 ]; then
        fail "This game is at turn $turn: after turn 5 new nations need the administrator. Your code stays valid; ask them to add your nation."
        return
    fi

    echo
    say "Choose the ${bold}player account${reset} you will sign in with on this site"
    say "${dim}(letters, digits, . _ - ; up to 32 characters)${reset}"
    read -r -p "  Account name: " account
    if ! [[ "$account" =~ ^[A-Za-z0-9_.-]{1,32}$ ]] || [ "$account" = "$JOIN_ACCOUNT" ]; then
        fail "Please use only letters, digits, dots, dashes and underscores."
        return
    fi
    if account_exists "$account"; then
        fail "The account '$account' already exists. Choose another name."
        return
    fi
    read -r -s -p "  Password (at least 8 characters): " password; echo
    read -r -s -p "  Repeat the password: " password2; echo
    if [ "$password" != "$password2" ]; then
        fail "The passwords do not match."
        return
    fi
    if [ ${#password} -lt 8 ]; then
        fail "Use at least 8 characters."
        return
    fi

    clear
    cat <<EOF

  ${bold}Now build your nation${reset} with the game's nation builder.

  It asks for:
    - a ${bold}nation name${reset} (up to 9 letters) and a ${bold}nation password${reset}
      (up to 7 characters; the game asks for it every time you play)
    - your ruler's name, a ${bold}race${reset}, a ${bold}class${reset} and an ${bold}alignment${reset}
    - a map mark: any free letter from the list
  Then you spend points on your nation. Move with ${bold}j${reset} and ${bold}k${reset}, press
  ${bold}h${reset} to switch to adding, and ${bold}Space${reset} to buy.
  ${yellow}Tip:${reset} buy 2 or 3 points of ${bold}Treasury${reset}; a nation without gold cannot
  draft troops in its first turn. ${bold}Esc${reset} finishes (the rest goes to people),
  then answer ${bold}y${reset} to save.

EOF
    read -r -s -n 1 -p "  Press any key to open the nation builder..."
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
        fail "No nation was created, so no account either. Your invite code is still valid."
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
        2) fail "That invite code was used meanwhile. Ask the administrator about nation $nation."; return ;;
        *) fail "Your nation $nation was created, but the account could not be saved. Tell the administrator."; return ;;
    esac
    echo "[join] account $account created for nation $nation" > /run/conquer/log 2>/dev/null

    clear
    cat <<EOF

  ${bold}${green}Welcome to the game, ruler of ${nation}!${reset}

  Your player account ${bold}${account}${reset} is ready.

  To play, sign in again with it: close this browser tab (or open the site
  in a private window), press ${bold}Play now${reset} and use ${bold}${account}${reset} and your
  password. Your nation opens directly; its password is the one you gave
  in the nation builder.

  New to Conquer? Option 7 in the menu is a practice world, and the Coach
  button walks you through your first turn.

EOF
    read -r -s -n 1 -p "  Press any key to finish..."
    return 0
}

while true; do
    join && break
done
clear
echo "  Goodbye, and see you on the map."
