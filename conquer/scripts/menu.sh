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
# Language of the menu, from the game page (/play/?arg=es, ttyd --url-arg).
# The argument comes from the browser: only a known language is taken.
UI_LANG=en
[ "${1:-}" = es ] && UI_LANG=es
MIN_ROWS=24

TURN_SCHEDULE=""
TURN_SCHEDULE_LABEL=""
ADMIN_CONTACT=""
TURN_EARLY=""
JOIN_ACCOUNT=""
# shellcheck source=/dev/null
[ -f /etc/conquer-web.env ] && . /etc/conquer-web.env

# The public join account only gets the join wizard (invite codes)
if [ -n "$JOIN_ACCOUNT" ] && [ "$PLAYER" = "$JOIN_ACCOUNT" ]; then
    exec /usr/local/bin/conquer-join "$UI_LANG"
fi

bold=$(tput bold 2>/dev/null)
dim=$(tput dim 2>/dev/null)
yellow=$(tput setaf 3 2>/dev/null)
green=$(tput setaf 2 2>/dev/null)
reset=$(tput sgr0 2>/dev/null)

# The text in the menu's language: t "English" "Español"
t() {
    if [ "$UI_LANG" = es ]; then printf '%s' "$2"; else printf '%s' "$1"; fi
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
    read -r -s -n 1 -p "${dim}$(t "Press any key to return to the menu..." "Pulsa una tecla para volver al menú...")${reset}"
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
        echo "${yellow}${bold}$(t "Your terminal is too small" "Tu terminal es demasiado pequeña"): ${cols}x${rows}${reset}"
        echo
        t "Conquer needs at least ${MIN_COLS} columns x ${MIN_ROWS} rows." \
          "Conquer necesita al menos ${MIN_COLS} columnas x ${MIN_ROWS} filas."; echo
        t "Make the browser window bigger or zoom out (Ctrl and -)." \
          "Agranda la ventana del navegador o reduce el zoom (Ctrl y -)."; echo
        echo
        t "Press any key to check again, or 'c' to continue anyway." \
          "Pulsa una tecla para comprobarlo de nuevo, o 'c' para seguir igualmente."; echo
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
    echo "$ready $(t of de) $total $(t nations naciones)"
}

# Start the turn update now if every nation is done (TURN_EARLY=on). It
# runs in its own session so it survives this browser session.
maybe_run_early_turn() {
    [ "$TURN_EARLY" = on ] || return 1
    conquer-ready all || return 1
    setsid conquer-turn --if-ready < /dev/null >> /run/conquer/log 2>&1 &
    echo
    echo "  ${green}${bold}$(t "Every nation is ready: the turn update starts now." "Todas las naciones están listas: el turno se procesa ahora.")${reset}"
    echo "  $(t "Come back in a few minutes for the new turn." "Vuelve en unos minutos para el nuevo turno.")"
}

# Ask whether the orders are done after a game session
ask_orders_done() {
    local nation="$1" answer
    # The game leaves its login text behind on the screen
    clear
    echo
    read -r -s -n 1 -p "  $(t "Are your orders for this turn done? [y/N] " "¿Has terminado tus órdenes de este turno? [s/N] ")" answer
    echo
    case "$answer" in
        y|Y|s|S)
            conquer-ready mark "$nation"
            publish_status
            echo "  ${green}$(t "Orders marked as done." "Órdenes marcadas como terminadas.")${reset} $(t "You can still change them until the update." "Puedes cambiarlas hasta la actualización.")"
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
        echo "  $(t "Your orders are" "Tus órdenes ya") ${bold}$(t "no longer marked as done" "no están marcadas como terminadas")${reset}."
    else
        conquer-ready mark "$nation"
        publish_status
        echo "  ${green}$(t "Your orders are marked as done for this turn." "Tus órdenes de este turno están marcadas como terminadas.")${reset}"
        if ! maybe_run_early_turn && [ "$TURN_EARLY" = on ]; then
            echo "  $(t "The turn update runs early once every nation is done." "El turno se adelanta en cuanto todas las naciones terminen.")"
        fi
    fi
    pause
}

last_update() {
    if [ -s "$WORLD_DIR/timelog" ]; then
        head -n 1 "$WORLD_DIR/timelog"
    else
        t "not yet" "todavía no"; echo
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
            "") nation="${dim}$(t "no nation assigned yet" "aún sin nación asignada")${reset}" ;;
            "*") nation="${dim}$(t "any nation" "cualquier nación")${reset}" ;;
            *) nation="$(t nation nación) ${bold}${nation}${reset}" ;;
        esac
        echo "  ${dim}$(t "Signed in as:    " "Has entrado como:")${reset} ${bold}${PLAYER}${reset} (${nation})"
    fi
    echo "  ${dim}$(t "Last turn update:" "Último turno:    ")${reset} $(last_update)"
    echo "  ${dim}$(t "Turn schedule:   " "Calendario:      ")${reset} ${TURN_SCHEDULE_LABEL:-$(t "see game administrator" "consulta al administrador")}"
    local next
    if [ -n "$TURN_SCHEDULE" ] && [ "$TURN_SCHEDULE" != off ] \
        && next=$(/usr/local/bin/conquer-next-turn "$TURN_SCHEDULE" 2>/dev/null); then
        echo "  ${dim}$(t "Next turn update:" "Próximo turno:   ")${reset} $(date -d "@$next" "$(t '+%a %d %b %H:%M %Z' '+%d/%m %H:%M %Z')")"
    fi
    local summary nation
    if summary=$(ready_summary); then
        if nation=$(own_nation) && conquer-ready is-marked "$nation"; then
            summary="$summary ${green}($(t "yours: done" "las tuyas: sí"))${reset}"
        elif [ -n "$nation" ]; then
            summary="$summary ${yellow}($(t "yours: not yet" "las tuyas: aún no"))${reset}"
        fi
        echo "  ${dim}$(t "Orders done:     " "Órdenes hechas:  ")${reset} $summary"
    fi
    if [ -e "$UPDATING_FLAG" ]; then
        echo
        echo "  ${yellow}${bold}$(t "A turn update is in progress." "Se está procesando el turno.")${reset} $(t "Please come back in a few minutes." "Vuelve en unos minutos.")"
    else
        local TURN_STATE="" TURN_STATE_TIME="" TURN_STATE_MESSAGE=""
        # shellcheck source=/dev/null
        [ -f "$WORLD_DIR/.turn-state" ] && . "$WORLD_DIR/.turn-state"
        if [ "$TURN_STATE" = failed ]; then
            echo
            echo "  ${yellow}${bold}$(t "The last turn update failed" "Falló la última actualización del turno")${reset} ($TURN_STATE_TIME): ${dim}${TURN_STATE_MESSAGE}${reset}"
            echo "  $(t "The administrator has been notified; your orders are kept for the next update." "El administrador está avisado; tus órdenes se guardan para la próxima.")"
        fi
    fi
    echo
}

show_how_to_join() {
    clear
    if [ "$UI_LANG" = es ]; then
        cat <<EOF
${bold}Cómo unirse a la partida${reset}

Durante la fase de pruebas, el administrador crea las naciones nuevas.

  1. Pide una nación al administrador. Recibirás:
       - una cuenta de jugador para este sitio, vinculada a tu nación
       - la contraseña de tu nación
  2. Entra con tu cuenta de jugador y elige "Jugar" en este menú.
  3. Tu nación se abre directamente: escribe su contraseña.

${bold}Cómo funcionan los turnos${reset}

Conquer se juega por turnos. Puedes entrar tantas veces como quieras para
dar órdenes (mover ejércitos, reclutar, construir, comerciar...). Todas las
órdenes se resuelven a la vez en la próxima actualización del turno:
${TURN_SCHEDULE_LABEL:-consulta al administrador}.

La actualización espera mientras haya jugadores dentro, así que sal del
juego (tecla 'q') cuando termines. Al salir, el menú te pregunta si tus
órdenes están terminadas; también puedes cambiarlo con la opción 6.

Las pantallas del juego están en inglés, como en 1987; la guía y el
tutorial en español de la web explican cada una.
EOF
        if [ "$TURN_EARLY" = on ]; then
            echo
            echo "Cuando todas las naciones marcan sus órdenes como terminadas, el"
            echo "turno se procesa en el acto, sin esperar al calendario."
        fi
        if [ -n "$ADMIN_CONTACT" ]; then
            echo
            echo "Contacto del administrador: ${bold}${ADMIN_CONTACT}${reset}"
        fi
        pause
        return
    fi
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
    if [ "$UI_LANG" = es ]; then
        cat <<EOF
${bold}Teclas principales${reset}   (pulsa '?' dentro del juego para la ayuda completa)

  Movimiento    y k u         Mapa e información
                 \\|/           d   cambiar vista       s   puntuaciones
               h -+- l         N   leer el periódico   R   leer mensajes
                 /|\\           I   información         a   ejércitos
                b j n         (el teclado numérico 1-9 también mueve)

  Acciones      m   mover la unidad       D   reclutar tropas
                p   unidad siguiente      C   construir
                r   cambiar uso sector    B   presupuesto
                S   diplomacia            M   magia
                P   producción            q   salir

  Ctrl-L redibuja la pantalla si se ve desordenada.
EOF
        pause
        return
    fi
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
        echo; echo "  ${yellow}$(t "Could not create your practice world." "No se pudo crear tu mundo de práctica.")${reset}"; pause; return
    fi
    while true; do
        clear
        echo
        echo "  ${bold}${green}$(t "Practice world" "Mundo de práctica")${reset}   ${dim}$(t "only you play here; nothing counts" "aquí solo juegas tú; nada cuenta")${reset}"
        echo
        echo "  ${dim}$(t "Your nation:  " "Tu nación:    ")${reset} ${bold}${PRACTICE_NATION}${reset}   ${dim}$(t password: contraseña:)${reset} ${bold}${PRACTICE_PASSWORD}${reset}"
        echo "  ${dim}$(t "Now:          " "Ahora:        ")${reset} $(practice_turn "$dir")"
        echo
        echo "  $(t "Try anything, run the next turn yourself and see what happens." "Prueba lo que quieras, procesa tú el turno siguiente y mira qué pasa.")"
        echo "  $(t "The Coach button above the game walks you through a first turn." "El botón Coach, encima del juego, te guía por un primer turno.")"
        echo
        echo "  ${bold}1${reset}) $(t "Play the practice nation" "Jugar con la nación de práctica")"
        echo "  ${bold}2${reset}) $(t "Run the next turn now" "Procesar ya el turno siguiente")"
        echo "  ${bold}3${reset}) $(t "Start again with a new world" "Empezar de nuevo con otro mundo")"
        echo "  ${bold}q${reset}) $(t "Back to the main menu" "Volver al menú principal")"
        echo
        read -r -s -n 1 -p "  $(t "Choose an option: " "Elige una opción: ")" choice
        case "$choice" in
            1)
                check_terminal_size
                clear
                run_game -d "$dir" -n "$PRACTICE_NATION"
                ;;
            2)
                clear
                before=$(practice_turn "$dir")
                echo "  $(t "Running the turn update of your practice world..." "Procesando el turno de tu mundo de práctica...")"
                if "$PREFIX/bin/conqrun" -x -d "$dir" > /dev/null 2>&1; then
                    echo "  ${green}$(t Done: Hecho:)${reset} $before -> $(practice_turn "$dir")"
                    echo "  $(t "Play again to read the newspaper (N) and your mail (R)." "Vuelve a jugar para leer el periódico (N) y tu correo (R).")"
                else
                    echo "  ${yellow}$(t "The update did not run." "El turno no se procesó.")${reset} $(t "Quit the practice game first." "Sal antes de la partida de práctica.")"
                fi
                pause
                ;;
            3)
                clear
                read -r -s -n 1 -p "  $(t "Delete your practice world and start again? [y/N] " "¿Borrar tu mundo de práctica y empezar de nuevo? [s/N] ")" choice
                echo
                if [[ "$choice" =~ ^[yYsS]$ ]]; then
                    new_practice_world && echo "  ${green}$(t "A new practice world is ready." "Tu nuevo mundo de práctica está listo.")${reset}"
                    pause
                fi
                ;;
            q|Q) return ;;
        esac
    done
}

show_scores() {
    clear
    (cd "$WORLD_DIR" && "$PREFIX/bin/conquer" -s 2>/dev/null) | less -R -P "$(t "Scores - q to return" "Puntuaciones - q para volver")"
}

play() {
    if [ -e "$UPDATING_FLAG" ]; then
        echo
        echo
        echo "  ${yellow}$(t "A turn update is in progress." "Se está procesando el turno.")${reset} $(t "Please try again in a few minutes." "Inténtalo de nuevo en unos minutos.")"
        pause
        return
    fi
    check_terminal_size
    clear
    local nation
    if ! nation=$(player_nation); then
        echo
        if [ "$UI_LANG" = es ]; then
            echo "  ${yellow}Tu cuenta${PLAYER:+ '$PLAYER'} aún no tiene nación asignada.${reset}"
            echo "  Pide una al administrador (mira \"Cómo unirse\" en el menú)."
        else
            echo "  ${yellow}No nation is assigned to your account${PLAYER:+ '$PLAYER'} yet.${reset}"
            echo "  Ask the game administrator for one (see \"How to join\" in the menu)."
        fi
        pause
        return
    fi
    if [ "$nation" = "*" ]; then
        run_game
    else
        echo "$(t "Opening your nation" "Abriendo tu nación") ${bold}${nation}${reset}."
        run_game -n "$nation"
    fi
    local status=$?
    if [ -e "$UPDATING_FLAG" ]; then
        clear
        echo
        echo "${yellow}$(t "You were disconnected for the turn update." "Se te ha desconectado para procesar el turno.")${reset}"
        t "Your orders were saved. Come back in a few minutes for the new turn." \
          "Tus órdenes están guardadas. Vuelve en unos minutos para el nuevo turno."; echo
        pause
    elif [ $status -ne 0 ]; then
        echo
        echo "${yellow}$(t "Could not enter the game." "No se pudo entrar en el juego.")${reset}"
        t "Check your nation name and password. If a turn update is" \
          "Revisa el nombre y la contraseña de tu nación. Si se está"; echo
        t "running, try again in a few minutes." \
          "procesando el turno, inténtalo de nuevo en unos minutos."; echo
        pause
    elif nation=$(own_nation); then
        ask_orders_done "$nation"
    fi
}

while true; do
    show_banner
    echo "  ${bold}1${reset}) $(t Play Jugar)"
    echo "  ${bold}2${reset}) $(t "How to join / how turns work" "Cómo unirse / cómo funcionan los turnos")"
    echo "  ${bold}3${reset}) $(t "Key reference" "Teclas principales")"
    echo "  ${bold}4${reset}) $(t Scores Puntuaciones)"
    echo "  ${bold}5${reset}) $(t "Full help (in-game help screens)" "Ayuda completa (pantallas de ayuda del juego, en inglés)")"
    if nation=$(own_nation); then
        if conquer-ready is-marked "$nation"; then
            echo "  ${bold}6${reset}) $(t "My orders are not done yet" "Aún no he terminado mis órdenes")"
        else
            echo "  ${bold}6${reset}) $(t "My orders for this turn are done" "He terminado mis órdenes de este turno")"
        fi
    fi
    [ -d "$PRACTICE_TEMPLATE" ] && echo "  ${bold}7${reset}) $(t "Practice world (only you, nothing counts)" "Mundo de práctica (solo tú, nada cuenta)")"
    echo "  ${bold}q${reset}) $(t "Log out" "Salir")"
    echo
    read -r -s -n 1 -p "  $(t "Choose an option: " "Elige una opción: ")" choice
    case "$choice" in
        1|p|P) play ;;
        2) show_how_to_join ;;
        3) show_keys ;;
        4) show_scores ;;
        5) check_terminal_size; run_game -h ;;
        6) [ -e "$UPDATING_FLAG" ] || toggle_orders_done ;;
        7) [ -d "$PRACTICE_TEMPLATE" ] && practice_menu ;;
        q|Q) clear; t "Goodbye, commander." "Hasta pronto, comandante."; echo; exit 0 ;;
    esac
done
