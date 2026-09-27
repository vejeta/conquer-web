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
# usage: conquer-join [en|es]   (the language, passed on by the menu)

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

UI_LANG=en
[ "${1:-}" = es ] && UI_LANG=es

# The text in the wizard's language: t "English" "Español"
t() {
    if [ "$UI_LANG" = es ]; then printf '%s' "$2"; else printf '%s' "$1"; fi
}

say() { printf '  %s\n' "$*"; }

fail() {
    echo
    say "${yellow}$*${reset}"
    [ -n "$ADMIN_CONTACT" ] && say "$(t Questions: Dudas:) ${bold}${ADMIN_CONTACT}${reset}"
    echo
    read -r -s -n 1 -p "  $(t "Press any key to start again..." "Pulsa una tecla para empezar de nuevo...")"
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
    say "${bold}${green}$(t "Join Conquer" "Únete a Conquer")${reset}"
    echo
}

join() {
    local code account password password2 before after nation turn

    banner
    if [ ! -w "$HTPASSWD_FILE" ]; then
        fail "$(t "Joining is not available on this server right now." "Ahora mismo no se admiten altas en este servidor.")"
        return
    fi
    say "$(t "Welcome. You need an" "Bienvenido. Necesitas un") ${bold}$(t "invite code" "código de invitación")${reset} $(t "from the game administrator." "del administrador del juego.")"
    echo
    read -r -p "  $(t "Invite code: " "Código de invitación: ")" code
    code=$(printf '%s' "$code" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')
    if [ -z "$code" ] || ! grep -qx -- "$code" "$INVITES_FILE" 2>/dev/null; then
        fail "$(t "That invite code is not valid, or it has been used already." "Ese código no es válido o ya se ha usado.")"
        return
    fi

    turn=$(current_turn)
    if [ "${turn:-1}" -gt 5 ]; then
        fail "$(t "This game is at turn $turn: after turn 5 new nations need the administrator. Your code stays valid; ask them to add your nation." "La partida va por el turno $turn: desde el turno 5 las naciones nuevas las crea el administrador. Tu código sigue siendo válido; pídele que añada tu nación.")"
        return
    fi

    echo
    say "$(t "Choose the" "Elige la") ${bold}$(t "player account" "cuenta de jugador")${reset} $(t "you will sign in with on this site" "con la que entrarás en este sitio")"
    say "${dim}$(t "(letters, digits, . _ - ; up to 32 characters)" "(letras, números, . _ - ; hasta 32 caracteres)")${reset}"
    read -r -p "  $(t "Account name: " "Nombre de la cuenta: ")" account
    if ! [[ "$account" =~ ^[A-Za-z0-9_.-]{1,32}$ ]] || [ "$account" = "$JOIN_ACCOUNT" ]; then
        fail "$(t "Please use only letters, digits, dots, dashes and underscores." "Usa solo letras, números, puntos, guiones y guiones bajos.")"
        return
    fi
    if account_exists "$account"; then
        fail "$(t "The account '$account' already exists. Choose another name." "La cuenta '$account' ya existe. Elige otro nombre.")"
        return
    fi
    read -r -s -p "  $(t "Password (at least 8 characters): " "Contraseña (al menos 8 caracteres): ")" password; echo
    read -r -s -p "  $(t "Repeat the password: " "Repite la contraseña: ")" password2; echo
    if [ "$password" != "$password2" ]; then
        fail "$(t "The passwords do not match." "Las contraseñas no coinciden.")"
        return
    fi
    if [ ${#password} -lt 8 ]; then
        fail "$(t "Use at least 8 characters." "Usa al menos 8 caracteres.")"
        return
    fi

    clear
    if [ "$UI_LANG" = es ]; then
        cat <<EOF

  ${bold}Ahora crea tu nación${reset} con el constructor de naciones del juego
  (sus pantallas están en inglés).

  Te pedirá:
    - un ${bold}nombre de nación${reset} (hasta 9 letras) y una ${bold}contraseña de nación${reset}
      (hasta 7 caracteres; el juego te la pide cada vez que juegas)
    - el nombre de tu gobernante, una ${bold}raza${reset}, una ${bold}clase${reset} y una ${bold}alineación${reset}
    - una marca para el mapa: cualquier letra libre de la lista
  Después repartes puntos en tu nación. Muévete con ${bold}j${reset} y ${bold}k${reset}, pulsa
  ${bold}h${reset} para pasar a añadir y ${bold}Espacio${reset} para comprar.
  ${yellow}Consejo:${reset} compra 2 o 3 puntos de ${bold}Treasury${reset} (tesoro); una nación sin
  oro no puede reclutar tropas en su primer turno. ${bold}Esc${reset} termina (el resto
  va a población) y responde ${bold}y${reset} para guardar.

EOF
    else
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
    fi
    read -r -s -n 1 -p "  $(t "Press any key to open the nation builder..." "Pulsa una tecla para abrir el constructor de naciones...")"
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
        fail "$(t "No nation was created, so no account either. Your invite code is still valid." "No se creó ninguna nación, así que tampoco la cuenta. Tu código sigue siendo válido.")"
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
        2) fail "$(t "That invite code was used meanwhile. Ask the administrator about nation $nation." "Ese código se usó mientras tanto. Pregunta al administrador por la nación $nation.")"; return ;;
        *) fail "$(t "Your nation $nation was created, but the account could not be saved. Tell the administrator." "Tu nación $nation se creó, pero la cuenta no se pudo guardar. Avisa al administrador.")"; return ;;
    esac
    echo "[join] account $account created for nation $nation" > /run/conquer/log 2>/dev/null

    clear
    if [ "$UI_LANG" = es ]; then
        cat <<EOF

  ${bold}${green}¡Bienvenido a la partida, soberano de ${nation}!${reset}

  Tu cuenta de jugador ${bold}${account}${reset} está lista.

  Para jugar, vuelve a entrar con ella: cierra esta pestaña (o abre el sitio
  en una ventana privada), pulsa ${bold}Jugar${reset} y usa ${bold}${account}${reset} y tu
  contraseña. Tu nación se abre directamente; su contraseña es la que diste
  en el constructor de naciones.

  ¿Nuevo en Conquer? La opción 7 del menú es un mundo de práctica, y el
  botón Coach te guía por tu primer turno.

EOF
        read -r -s -n 1 -p "  Pulsa una tecla para terminar..."
        return 0
    fi
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
echo "  $(t "Goodbye, and see you on the map." "Hasta pronto, nos vemos en el mapa.")"
