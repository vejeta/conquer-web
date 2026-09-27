#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Player menu shown in the browser terminal. Returns here after each game
# session instead of dropping the connection.

export TERM=xterm-256color

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
MIN_COLS=80
UPDATING_FLAG=/run/conquer/turn
PLAYERS_FILE="$WORLD_DIR/.players"
# Web account the player signed in with (set by ttyd from the proxy header)
PLAYER="${TTYD_USER:-}"
MIN_ROWS=24

TURN_SCHEDULE=""
TURN_SCHEDULE_LABEL=""
ADMIN_CONTACT=""
TURN_EARLY=""
# shellcheck source=/dev/null
[ -f /etc/conquer-web.env ] && . /etc/conquer-web.env

bold=$(tput bold 2>/dev/null)
dim=$(tput dim 2>/dev/null)
yellow=$(tput setaf 3 2>/dev/null)
green=$(tput setaf 2 2>/dev/null)
reset=$(tput sgr0 2>/dev/null)

# The game engine reports and auto-repairs inconsistent world data on start
# ("file main.c: line N: nation[X] army[Y] ... (water)"). Those lines are
# diagnostics for the administrator, not for players, so drop them.
# Login prompts are also written to stderr without a trailing newline, so
# filter byte by byte and only hold back text that may start a diagnostic.
FILTER_DIAGNOSTICS='
$| = 1;
my $buf = "";
while (sysread(STDIN, my $chunk, 4096)) {
    $buf .= $chunk;
    while ($buf =~ s/^([^\n]*\n)//) {
        my $line = $1;
        print $line unless $line =~ /^files? \S+: line \d+: /;
    }
    if ($buf ne "" && index("files ", $buf) != 0 && $buf !~ /^files? /) {
        print $buf;
        $buf = "";
    }
}
print $buf;
'

run_game() {
    "$PREFIX/bin/conquer" "$@" 2> >(perl -e "$FILTER_DIAGNOSTICS" >&2)
    local status=$?
    wait $! 2>/dev/null
    # A game ended by a signal (turn update) leaves curses' raw mode behind
    stty sane 2>/dev/null
    tput sgr0 2>/dev/null
    return $status
}

pause() {
    echo
    read -r -s -n 1 -p "${dim}Press any key to return to the menu...${reset}"
}

# Conquer draws an 80x24 screen; curses misbehaves on anything smaller
check_terminal_size() {
    local rows cols key
    while true; do
        read -r rows cols < <(stty size 2>/dev/null)
        if [ "${cols:-0}" -ge $MIN_COLS ] && [ "${rows:-0}" -ge $MIN_ROWS ]; then
            return 0
        fi
        clear
        echo "${yellow}${bold}Your terminal is too small: ${cols}x${rows}${reset}"
        echo
        echo "Conquer needs at least ${MIN_COLS} columns x ${MIN_ROWS} rows."
        echo "Make the browser window bigger or zoom out (Ctrl and -)."
        echo
        echo "Press any key to check again, or 'c' to continue anyway."
        read -r -s -n 1 key
        [ "$key" = "c" ] && return 0
    done
}

# Is $1 the name of a nation in the world?
is_nation() {
    (cd "$WORLD_DIR" && "$PREFIX/bin/conquer" -s 2>/dev/null) \
        | awk -v n="$1" '$1 ~ /^[0-9]+$/ && $2 == n { found = 1 } END { exit !found }'
}

# Nation the signed-in account may open, "*" for any (administrators).
# Assignments ("account:nation", manage-players.sh) live with the world;
# an account without one opens the nation named like it. Worlds without an
# assignment file keep the old open behaviour: any account, any nation.
player_nation() {
    local nation
    if [ -n "$PLAYER" ] && [ -f "$PLAYERS_FILE" ]; then
        nation=$(awk -F: -v user="$PLAYER" '$1 == user { print $2; exit }' "$PLAYERS_FILE")
        if [ -n "$nation" ]; then
            echo "$nation"
            return 0
        fi
    fi
    if [ -n "$PLAYER" ] && is_nation "$PLAYER"; then
        echo "$PLAYER"
        return 0
    fi
    [ -f "$PLAYERS_FILE" ] && return 1
    echo "*"
}

# Nation whose orders this account can mark as done (not administrators)
own_nation() {
    local nation
    [ -f "$PLAYERS_FILE" ] || return 1
    nation=$(player_nation) && [ "$nation" != "*" ] && echo "$nation"
}

# Line for the banner: how many nations have finished their orders
ready_summary() {
    local ready total
    read -r ready total < <(conquer-ready count 2>/dev/null)
    [ "${total:-0}" -gt 0 ] || return 1
    echo "$ready of $total nations"
}

# Start the turn update now if every nation is done (TURN_EARLY=on). It
# runs in its own session so it survives this browser session.
maybe_run_early_turn() {
    [ "$TURN_EARLY" = on ] || return 1
    conquer-ready all || return 1
    setsid conquer-turn --if-ready < /dev/null >> /run/conquer/log 2>&1 &
    echo
    echo "  ${green}${bold}Every nation is ready: the turn update starts now.${reset}"
    echo "  Come back in a few minutes for the new turn."
}

# Ask whether the orders are done after a game session
ask_orders_done() {
    local nation="$1" answer
    echo
    read -r -s -n 1 -p "  Are your orders for this turn done? [y/N] " answer
    echo
    case "$answer" in
        y|Y)
            conquer-ready mark "$nation"
            publish_status
            echo "  ${green}Orders marked as done.${reset} You can still change them until the update."
            maybe_run_early_turn
            pause
            ;;
        *)
            conquer-ready is-marked "$nation" || return 0
            conquer-ready unmark "$nation"
            publish_status
            ;;
    esac
}

# Refresh the landing page's count of finished nations
publish_status() {
    conquer-status > /dev/null 2>&1 &
}

toggle_orders_done() {
    local nation
    nation=$(own_nation) || return
    clear
    echo
    if conquer-ready is-marked "$nation"; then
        conquer-ready unmark "$nation"
        publish_status
        echo "  Your orders are ${bold}no longer marked as done${reset}."
    else
        conquer-ready mark "$nation"
        publish_status
        echo "  ${green}Your orders are marked as done for this turn.${reset}"
        if ! maybe_run_early_turn && [ "$TURN_EARLY" = on ]; then
            echo "  The turn update runs early once every nation is done."
        fi
    fi
    pause
}

last_update() {
    if [ -s "$WORLD_DIR/timelog" ]; then
        head -n 1 "$WORLD_DIR/timelog"
    else
        echo "not yet"
    fi
}

show_banner() {
    clear
    echo "${bold}${green}"
    echo "   ____                                       "
    echo "  / ___|___  _ __   __ _ _   _  ___ _ __      "
    echo " | |   / _ \\| '_ \\ / _\` | | | |/ _ \\ '__|  "
    echo " | |__| (_) | | | | (_| | |_| |  __/ |        "
    echo "  \\____\\___/|_| |_|\\__, |\\__,_|\\___|_|    "
    echo "                      |_|                     "
    echo "${reset}"
    if [ -n "$PLAYER" ]; then
        local nation
        nation=$(player_nation)
        case "$nation" in
            "") nation="${dim}no nation assigned yet${reset}" ;;
            "*") nation="${dim}any nation${reset}" ;;
            *) nation="nation ${bold}${nation}${reset}" ;;
        esac
        echo "  ${dim}Signed in as:    ${reset} ${bold}${PLAYER}${reset} (${nation})"
    fi
    echo "  ${dim}Last turn update:${reset} $(last_update)"
    echo "  ${dim}Turn schedule:   ${reset} ${TURN_SCHEDULE_LABEL:-see game administrator}"
    local next
    if [ -n "$TURN_SCHEDULE" ] && [ "$TURN_SCHEDULE" != off ] \
        && next=$(/usr/local/bin/conquer-next-turn "$TURN_SCHEDULE" 2>/dev/null); then
        echo "  ${dim}Next turn update:${reset} $(date -d "@$next" '+%a %d %b %H:%M %Z')"
    fi
    local summary nation
    if summary=$(ready_summary); then
        if nation=$(own_nation) && conquer-ready is-marked "$nation"; then
            summary="$summary ${green}(yours: done)${reset}"
        elif [ -n "$nation" ]; then
            summary="$summary ${yellow}(yours: not yet)${reset}"
        fi
        echo "  ${dim}Orders done:     ${reset} $summary"
    fi
    if [ -e "$UPDATING_FLAG" ]; then
        echo
        echo "  ${yellow}${bold}A turn update is in progress.${reset} Please come back in a few minutes."
    else
        local TURN_STATE="" TURN_STATE_TIME="" TURN_STATE_MESSAGE=""
        # shellcheck source=/dev/null
        [ -f "$WORLD_DIR/.turn-state" ] && . "$WORLD_DIR/.turn-state"
        if [ "$TURN_STATE" = failed ]; then
            echo
            echo "  ${yellow}${bold}The last turn update failed${reset} ($TURN_STATE_TIME): ${dim}${TURN_STATE_MESSAGE}${reset}"
            echo "  The administrator has been notified; your orders are kept for the next update."
        fi
    fi
    echo
}

show_how_to_join() {
    clear
    cat <<EOF
${bold}How to join the game${reset}

During the test phase new nations are created by the game administrator.

  1. Ask the administrator for a nation. You will receive:
       - a player account for this site, linked to your nation
       - your nation password
  2. Sign in with your player account and choose "Play" in this menu.
  3. Your nation opens directly: type your nation password.

${bold}How turns work${reset}

Conquer is played in turns. You can log in as often as you like to give
orders (move armies, draft, build, trade...). All orders are resolved
together at the next turn update: ${TURN_SCHEDULE_LABEL:-see game administrator}.

The update waits while players are logged in, so please quit the game
(press 'q') when you are done. When you quit, the menu asks whether your
orders are done; you can also change that with option 6.
EOF
    if [ "$TURN_EARLY" = on ]; then
        echo
        echo "When every nation has marked its orders as done, the turn update"
        echo "runs right away instead of waiting for the schedule."
    fi
    if [ -n "$ADMIN_CONTACT" ]; then
        echo
        echo "Administrator contact: ${bold}${ADMIN_CONTACT}${reset}"
    fi
    pause
}

show_keys() {
    clear
    cat <<EOF
${bold}Quick key reference${reset}   (press '?' inside the game for full help)

  Movement      y k u         Map & info
                 \\|/           d   change display      s   score
               h -+- l         N   read newspaper      R   read messages
                 /|\\           I   campaign info       a   army report
                b j n         (numeric keypad 1-9 also moves)

  Actions       m   move selected unit    D   draft troops
                p   pick next unit        C   construct
                r   redesignate sector    B   budget
                S   diplomacy             M   magic
                P   production            q   quit

  Ctrl-L redraws the screen if it looks garbled.
EOF
    pause
}

show_scores() {
    clear
    (cd "$WORLD_DIR" && "$PREFIX/bin/conquer" -s 2>/dev/null) | less -R -P "Scores - q to return"
}

play() {
    if [ -e "$UPDATING_FLAG" ]; then
        echo
        echo
        echo "  ${yellow}A turn update is in progress.${reset} Please try again in a few minutes."
        pause
        return
    fi
    check_terminal_size
    clear
    local nation
    if ! nation=$(player_nation); then
        echo
        echo "  ${yellow}No nation is assigned to your account${PLAYER:+ '$PLAYER'} yet.${reset}"
        echo "  Ask the game administrator for one (see \"How to join\" in the menu)."
        pause
        return
    fi
    if [ "$nation" = "*" ]; then
        run_game
    else
        echo "Opening your nation ${bold}${nation}${reset}."
        run_game -n "$nation"
    fi
    local status=$?
    if [ -e "$UPDATING_FLAG" ]; then
        clear
        echo
        echo "${yellow}You were disconnected for the turn update.${reset}"
        echo "Your orders were saved. Come back in a few minutes for the new turn."
        pause
    elif [ $status -ne 0 ]; then
        echo
        echo "${yellow}Could not enter the game.${reset}"
        echo "Check your nation name and password. If a turn update is"
        echo "running, try again in a few minutes."
        pause
    elif nation=$(own_nation); then
        ask_orders_done "$nation"
    fi
}

while true; do
    show_banner
    echo "  ${bold}1${reset}) Play"
    echo "  ${bold}2${reset}) How to join / how turns work"
    echo "  ${bold}3${reset}) Key reference"
    echo "  ${bold}4${reset}) Scores"
    echo "  ${bold}5${reset}) Full help (in-game help screens)"
    if nation=$(own_nation); then
        if conquer-ready is-marked "$nation"; then
            echo "  ${bold}6${reset}) My orders are not done yet"
        else
            echo "  ${bold}6${reset}) My orders for this turn are done"
        fi
    fi
    echo "  ${bold}q${reset}) Log out"
    echo
    read -r -s -n 1 -p "  Choose an option: " choice
    case "$choice" in
        1|p|P) play ;;
        2) show_how_to_join ;;
        3) show_keys ;;
        4) show_scores ;;
        5) check_terminal_size; run_game -h ;;
        6) [ -e "$UPDATING_FLAG" ] || toggle_orders_done ;;
        q|Q) clear; echo "Goodbye, commander."; exit 0 ;;
    esac
done
