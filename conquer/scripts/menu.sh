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
# Private practice worlds, one per account, copied from a template world
# with a ready nation (see practice_menu)
PRACTICE_ROOT="$PREFIX/practice"
PRACTICE_TEMPLATE="$PREFIX/practice-world"
PRACTICE_NATION=trainee
PRACTICE_PASSWORD=train1
# Web account the player signed in with (set by ttyd from the proxy header)
PLAYER="${TTYD_USER:-}"
MIN_ROWS=24

TURN_SCHEDULE=""
TURN_SCHEDULE_LABEL=""
ADMIN_CONTACT=""
TURN_EARLY=""
JOIN_ACCOUNT=""
# shellcheck source=/dev/null
[ -f /etc/conquer-web.env ] && . /etc/conquer-web.env

# The public join account only gets the join wizard (invite codes), in
# the language the game page asked for
if [ -n "$JOIN_ACCOUNT" ] && [ "$PLAYER" = "$JOIN_ACCOUNT" ]; then
    exec /usr/local/bin/conquer-join "${1:-}"
fi

bold=$(tput bold 2>/dev/null)
dim=$(tput dim 2>/dev/null)
yellow=$(tput setaf 3 2>/dev/null)
green=$(tput setaf 2 2>/dev/null)
reset=$(tput sgr0 2>/dev/null)

# Texts in the language of the game page (/play/?arg=es, ttyd --url-arg)
# shellcheck source=i18n.sh
. /usr/local/lib/conquer-i18n.sh
load_texts "${1:-}"

# "Yes" to a question: the language's own key or y
is_yes() {
    [ -n "$1" ] && [[ "$(tr_raw menu_yes)yY" == *"$1"* ]]
}

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
    read -r -s -n 1 -p "$(t menu_pause)"
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
        t menu_too_small "${cols}x${rows}"; echo
        echo
        t menu_needs_size "$MIN_COLS" "$MIN_ROWS"; echo
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
    t menu_ready_count "$ready" "$total"
}

# Start the turn update now if every nation is done (TURN_EARLY=on). It
# runs in its own session so it survives this browser session.
maybe_run_early_turn() {
    [ "$TURN_EARLY" = on ] || return 1
    conquer-ready all || return 1
    setsid conquer-turn --if-ready < /dev/null >> /run/conquer/log 2>&1 &
    echo
    t menu_all_ready; echo
}

# Ask whether the orders are done after a game session
ask_orders_done() {
    local nation="$1" answer
    # The game leaves its login text behind on the screen
    clear
    echo
    read -r -s -n 1 -p "$(t menu_ask_done)" answer
    echo
    if is_yes "$answer"; then
        conquer-ready mark "$nation"
        publish_status
        t menu_marked; echo
        maybe_run_early_turn
        pause
    elif conquer-ready is-marked "$nation"; then
        conquer-ready unmark "$nation"
        publish_status
    fi
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
        t menu_unmarked; echo
    else
        conquer-ready mark "$nation"
        publish_status
        t menu_marked_turn; echo
        if ! maybe_run_early_turn && [ "$TURN_EARLY" = on ]; then
            t menu_early_note; echo
        fi
    fi
    pause
}

last_update() {
    if [ -s "$WORLD_DIR/timelog" ]; then
        head -n 1 "$WORLD_DIR/timelog"
    else
        t menu_not_yet; echo
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
            "") nation=$(t menu_no_nation) ;;
            "*") nation=$(t menu_any_nation) ;;
            *) nation=$(t menu_nation "$nation") ;;
        esac
        t menu_signed_in "$PLAYER" "$nation"; echo
    fi
    t menu_last_update "$(last_update)"; echo
    t menu_schedule "${TURN_SCHEDULE_LABEL:-$(t menu_schedule_unknown)}"; echo
    local next
    if [ -n "$TURN_SCHEDULE" ] && [ "$TURN_SCHEDULE" != off ] \
        && next=$(/usr/local/bin/conquer-next-turn "$TURN_SCHEDULE" 2>/dev/null); then
        t menu_next_update "$(date -d "@$next" "$(tr_raw menu_date_format)")"; echo
    fi
    local summary nation
    if summary=$(ready_summary); then
        if nation=$(own_nation) && conquer-ready is-marked "$nation"; then
            summary="$summary $(t menu_yours_done)"
        elif [ -n "$nation" ]; then
            summary="$summary $(t menu_yours_not_yet)"
        fi
        t menu_orders_done "$summary"; echo
    fi
    if [ -e "$UPDATING_FLAG" ]; then
        echo
        t menu_updating; echo
    else
        local TURN_STATE="" TURN_STATE_TIME="" TURN_STATE_MESSAGE=""
        # shellcheck source=/dev/null
        [ -f "$WORLD_DIR/.turn-state" ] && . "$WORLD_DIR/.turn-state"
        if [ "$TURN_STATE" = failed ]; then
            echo
            t menu_update_failed "$TURN_STATE_TIME" "$TURN_STATE_MESSAGE"; echo
        fi
    fi
    echo
}

show_how_to_join() {
    clear
    t menu_how_to_join "${TURN_SCHEDULE_LABEL:-$(t menu_schedule_unknown)}"; echo
    if [ "$TURN_EARLY" = on ]; then
        echo
        t menu_how_early; echo
    fi
    if [ -n "$ADMIN_CONTACT" ]; then
        echo
        t menu_admin_contact "$ADMIN_CONTACT"; echo
    fi
    pause
}

show_keys() {
    clear
    t menu_keys; echo
    pause
}

# Practice world of the signed-in account
practice_dir() {
    local name="${PLAYER:-guest}"
    echo "$PRACTICE_ROOT/${name//[^A-Za-z0-9_.-]/_}"
}

new_practice_world() {
    local dir
    dir=$(practice_dir)
    rm -rf "$dir"
    mkdir -p "$PRACTICE_ROOT" &&
        cp -a "$PRACTICE_TEMPLATE" "$dir" &&
        cp "$PREFIX"/share/help[0-5] "$dir"/ &&
        "$PREFIX/bin/conqowner" -d "$dir" -s "$(id -u)" > /dev/null
}

practice_turn() {
    "$PREFIX/bin/conquer" -d "$1" -s 2>/dev/null | sed -n 's/^Conquer .*: \(.*\)$/\1/p' | head -n 1
}

practice_menu() {
    local dir choice before
    dir=$(practice_dir)
    if [ ! -f "$dir/data" ] && ! new_practice_world; then
        echo; t menu_practice_failed; echo; pause; return
    fi
    while true; do
        clear
        echo
        t menu_practice_title; echo
        echo
        t menu_practice_nation "$PRACTICE_NATION" "$PRACTICE_PASSWORD"; echo
        t menu_practice_now "$(practice_turn "$dir")"; echo
        echo
        t menu_practice_intro; echo
        echo
        echo "  ${bold}1${reset}) $(t menu_practice_play)"
        echo "  ${bold}2${reset}) $(t menu_practice_turn)"
        echo "  ${bold}3${reset}) $(t menu_practice_reset)"
        echo "  ${bold}q${reset}) $(t menu_back)"
        echo
        read -r -s -n 1 -p "$(t menu_choose)" choice
        case "$choice" in
            1)
                check_terminal_size
                clear
                run_game -d "$dir" -n "$PRACTICE_NATION"
                ;;
            2)
                clear
                before=$(practice_turn "$dir")
                t menu_practice_running; echo
                if "$PREFIX/bin/conqrun" -x -d "$dir" > /dev/null 2>&1; then
                    t menu_practice_done "$before" "$(practice_turn "$dir")"; echo
                else
                    t menu_practice_not_run; echo
                fi
                pause
                ;;
            3)
                clear
                read -r -s -n 1 -p "$(t menu_practice_ask_reset)" choice
                echo
                if is_yes "$choice"; then
                    new_practice_world && t menu_practice_ready && echo
                    pause
                fi
                ;;
            q|Q) return ;;
        esac
    done
}

show_scores() {
    clear
    # LESSSECURE: no shell (!), editor (v) or other files (:e) from the
    # pager, or a player would get a shell inside the game container
    (cd "$WORLD_DIR" && "$PREFIX/bin/conquer" -s 2>/dev/null) \
        | LESSSECURE=1 LESSKEY=/dev/null less -R -P "$(tr_raw menu_scores_prompt)"
}

play() {
    if [ -e "$UPDATING_FLAG" ]; then
        echo
        echo
        t menu_updating_try_later; echo
        pause
        return
    fi
    check_terminal_size
    clear
    local nation
    if ! nation=$(player_nation); then
        echo
        t menu_unassigned "${PLAYER:+ '$PLAYER'}"; echo
        pause
        return
    fi
    if [ "$nation" = "*" ]; then
        run_game
    else
        t menu_opening "$nation"; echo
        run_game -n "$nation"
    fi
    local status=$?
    if [ -e "$UPDATING_FLAG" ]; then
        clear
        echo
        t menu_disconnected; echo
        pause
    elif [ $status -ne 0 ]; then
        echo
        t menu_cannot_enter; echo
        pause
    elif nation=$(own_nation); then
        ask_orders_done "$nation"
    fi
}

while true; do
    show_banner
    echo "  ${bold}1${reset}) $(t menu_play)"
    echo "  ${bold}2${reset}) $(t menu_join)"
    echo "  ${bold}3${reset}) $(t menu_key_reference)"
    echo "  ${bold}4${reset}) $(t menu_scores)"
    echo "  ${bold}5${reset}) $(t menu_help)"
    if nation=$(own_nation); then
        if conquer-ready is-marked "$nation"; then
            echo "  ${bold}6${reset}) $(t menu_not_done)"
        else
            echo "  ${bold}6${reset}) $(t menu_done)"
        fi
    fi
    [ -d "$PRACTICE_TEMPLATE" ] && echo "  ${bold}7${reset}) $(t menu_practice)"
    echo "  ${bold}q${reset}) $(t menu_log_out)"
    echo
    # The terminal is gone (the browser closed): nothing more to read
    read -r -s -n 1 -p "$(t menu_choose)" choice || exit 0
    case "$choice" in
        1|p|P) play ;;
        2) show_how_to_join ;;
        3) show_keys ;;
        4) show_scores ;;
        5) check_terminal_size; run_game -h ;;
        6) [ -e "$UPDATING_FLAG" ] || toggle_orders_done ;;
        7) [ -d "$PRACTICE_TEMPLATE" ] && practice_menu ;;
        q|Q) clear; t menu_goodbye; echo; exit 0 ;;
    esac
done
