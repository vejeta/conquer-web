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
MIN_ROWS=24

TURN_SCHEDULE_LABEL=""
ADMIN_CONTACT=""
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
    echo "  ${dim}Last turn update:${reset} $(last_update)"
    echo "  ${dim}Turn schedule:   ${reset} ${TURN_SCHEDULE_LABEL:-see game administrator}"
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
       - your nation name
       - your nation password
  2. Choose "Play" in this menu.
  3. Type your nation name, then your nation password.

${bold}How turns work${reset}

Conquer is played in turns. You can log in as often as you like to give
orders (move armies, draft, build, trade...). All orders are resolved
together at the next turn update: ${TURN_SCHEDULE_LABEL:-see game administrator}.

The update waits while players are logged in, so please quit the game
(press 'q') when you are done.
EOF
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
    run_game
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
    fi
}

while true; do
    show_banner
    echo "  ${bold}1${reset}) Play"
    echo "  ${bold}2${reset}) How to join / how turns work"
    echo "  ${bold}3${reset}) Key reference"
    echo "  ${bold}4${reset}) Scores"
    echo "  ${bold}5${reset}) Full help (in-game help screens)"
    echo "  ${bold}q${reset}) Log out"
    echo
    read -r -s -n 1 -p "  Choose an option: " choice
    case "$choice" in
        1|p|P) play ;;
        2) show_how_to_join ;;
        3) show_keys ;;
        4) show_scores ;;
        5) check_terminal_size; run_game -h ;;
        q|Q) clear; echo "Goodbye, commander."; exit 0 ;;
    esac
done
