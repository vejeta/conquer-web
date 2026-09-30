# shellcheck shell=bash disable=SC2034,SC2154
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Textos del menú del jugador y del asistente de alta, en español. Cada
# texto que falte aquí se muestra en inglés (en.sh). Ver README.md.

MSG[language]="Español"

# Menú del jugador (menu.sh)
MSG[menu_pause]="${dim}Pulsa una tecla para volver al menú...${reset}"
MSG[menu_too_small]="${yellow}${bold}Tu terminal es demasiado pequeña: %s${reset}"
MSG[menu_needs_size]="Conquer necesita al menos %s columnas x %s filas.
Agranda la ventana del navegador o reduce el zoom (Ctrl y -).

Pulsa una tecla para comprobarlo de nuevo, o 'c' para seguir igualmente."
MSG[menu_ready_count]="%s de %s naciones"
MSG[menu_all_ready]="  ${green}${bold}Todas las naciones están listas: el turno se procesa ahora.${reset}
  Vuelve en unos minutos para el nuevo turno."
MSG[menu_ask_done]="  ¿Has terminado tus órdenes de este turno? [s/N] "
MSG[menu_yes]="sSyY"
MSG[menu_marked]="  ${green}Órdenes marcadas como terminadas.${reset} Puedes cambiarlas hasta la actualización."
MSG[menu_unmarked]="  Tus órdenes ya ${bold}no están marcadas como terminadas${reset}."
MSG[menu_marked_turn]="  ${green}Tus órdenes de este turno están marcadas como terminadas.${reset}"
MSG[menu_early_note]="  El turno se adelanta en cuanto todas las naciones terminen."
MSG[menu_not_yet]="todavía no"
MSG[menu_no_nation]="${dim}aún sin nación asignada${reset}"
MSG[menu_any_nation]="${dim}cualquier nación${reset}"
MSG[menu_nation]="nación ${bold}%s${reset}"
MSG[menu_signed_in]="  ${dim}Has entrado como:${reset} ${bold}%s${reset} (%s)"
MSG[menu_last_update]="  ${dim}Último turno:    ${reset} %s"
MSG[menu_schedule]="  ${dim}Calendario:      ${reset} %s"
MSG[menu_schedule_unknown]="consulta al administrador"
MSG[menu_next_update]="  ${dim}Próximo turno:   ${reset} %s"
MSG[menu_date_format]="+%d/%m %H:%M %Z"
MSG[menu_orders_done]="  ${dim}Órdenes hechas:  ${reset} %s"
MSG[menu_yours_done]="${green}(las tuyas: sí)${reset}"
MSG[menu_yours_not_yet]="${yellow}(las tuyas: aún no)${reset}"
MSG[menu_updating]="  ${yellow}${bold}Se está procesando el turno.${reset} Vuelve en unos minutos."
MSG[menu_update_failed]="  ${yellow}${bold}Falló la última actualización del turno${reset} (%s): ${dim}%s${reset}
  El administrador está avisado; tus órdenes se guardan para la próxima."
MSG[menu_how_to_join]="${bold}Cómo unirse a la partida${reset}

Se entra por invitación.

  1. Pide un código de invitación al administrador del juego.
  2. En la página principal, elige \"Crea tu cuenta\", escribe el código y
     elige tu nombre de cuenta y tu contraseña.
  3. Entra con esa cuenta y elige \"Jugar\": el juego te pide fundar tu
     nación, y desde entonces la abre directamente.

${bold}Cómo funcionan los turnos${reset}

Conquer se juega por turnos. Puedes entrar tantas veces como quieras para
dar órdenes (mover ejércitos, reclutar, construir, comerciar...). Todas las
órdenes se resuelven a la vez en la próxima actualización del turno:
%s.

La actualización espera mientras haya jugadores dentro, así que sal del
juego (tecla 'q') cuando termines. Al salir, el menú te pregunta si tus
órdenes están terminadas; también puedes cambiarlo con la opción 6.

Las pantallas del juego están en inglés, como en 1987; la guía y el
tutorial en español de la web explican cada una."
MSG[menu_how_early]="Cuando todas las naciones marcan sus órdenes como terminadas, el
turno se procesa en el acto, sin esperar al calendario."
MSG[menu_admin_contact]="Contacto del administrador: ${bold}%s${reset}"
MSG[menu_keys]="${bold}Teclas principales${reset}   (pulsa '?' dentro del juego para la ayuda completa)

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

  Ctrl-L redibuja la pantalla si se ve desordenada."
MSG[menu_practice_failed]="  ${yellow}No se pudo crear tu mundo de práctica.${reset}"
MSG[menu_practice_title]="  ${bold}${green}Mundo de práctica${reset}   ${dim}aquí solo juegas tú; nada cuenta${reset}"
MSG[menu_practice_nation]="  ${dim}Tu nación:    ${reset} ${bold}%s${reset}   ${dim}contraseña:${reset} ${bold}%s${reset}"
MSG[menu_practice_now]="  ${dim}Ahora:        ${reset} %s"
MSG[menu_practice_intro]="  Prueba lo que quieras, procesa tú el turno siguiente y mira qué pasa.
  El botón Coach, encima del juego, te guía por un primer turno."
MSG[menu_practice_play]="Jugar con la nación de práctica"
MSG[menu_practice_turn]="Procesar ya el turno siguiente"
MSG[menu_practice_reset]="Empezar de nuevo con otro mundo"
MSG[menu_back]="Volver al menú principal"
MSG[menu_choose]="  Elige una opción: "
MSG[menu_practice_running]="  Procesando el turno de tu mundo de práctica..."
MSG[menu_practice_done]="  ${green}Hecho:${reset} %s -> %s
  Vuelve a jugar para leer el periódico (N) y tu correo (R)."
MSG[menu_practice_not_run]="  ${yellow}El turno no se procesó.${reset} Sal antes de la partida de práctica."
MSG[menu_practice_ask_reset]="  ¿Borrar tu mundo de práctica y empezar de nuevo? [s/N] "
MSG[menu_practice_ready]="  ${green}Tu nuevo mundo de práctica está listo.${reset}"
MSG[menu_scores_prompt]="Puntuaciones - q para volver"
MSG[menu_updating_try_later]="  ${yellow}Se está procesando el turno.${reset} Inténtalo de nuevo en unos minutos."
MSG[menu_unassigned]="  ${yellow}Tu cuenta%s aún no tiene nación asignada.${reset}
  Pide una al administrador (mira \"Cómo unirse\" en el menú)."
MSG[menu_opening]="Abriendo tu nación ${bold}%s${reset}."
MSG[menu_disconnected]="${yellow}Se te ha desconectado para procesar el turno.${reset}
Tus órdenes están guardadas. Vuelve en unos minutos para el nuevo turno."
MSG[menu_cannot_enter]="${yellow}No se pudo entrar en el juego.${reset}
Revisa el nombre y la contraseña de tu nación. Si se está
procesando el turno, inténtalo de nuevo en unos minutos."
MSG[menu_play]="Jugar"
MSG[menu_join]="Cómo unirse / cómo funcionan los turnos"
MSG[menu_key_reference]="Teclas principales"
MSG[menu_scores]="Puntuaciones"
MSG[menu_help]="Ayuda completa (pantallas de ayuda del juego, en inglés)"
MSG[menu_not_done]="Aún no he terminado mis órdenes"
MSG[menu_done]="He terminado mis órdenes de este turno"
MSG[menu_practice]="Mundo de práctica (solo tú, nada cuenta)"
MSG[menu_log_out]="Salir"
MSG[menu_goodbye]="Hasta pronto, comandante."

# Asistente de alta (join.sh)
MSG[join_questions]="Dudas: ${bold}%s${reset}"
MSG[join_title]="${bold}${green}Funda tu nación${reset}"
MSG[join_welcome]="Bienvenido, ${bold}%s${reset}. Tu cuenta está lista: ahora funda tu nación."
MSG[join_too_late]="La partida va por el turno %s: después del turno 5 las naciones nuevas las añade el administrador. Pídele que añada la tuya."
MSG[join_builder]="
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
"
MSG[join_open_builder]="  Pulsa una tecla para abrir el constructor de naciones..."
MSG[join_no_nation]="No se ha creado ninguna nación. Elige 1 en el menú para intentarlo de nuevo."
MSG[join_not_saved]="Tu nación %s se ha creado, pero no se ha podido vincular a tu cuenta. Avisa al administrador."
MSG[join_done]="
  ${bold}${green}¡Bienvenido a la partida, soberano de %s!${reset}

  A partir de ahora, elige ${bold}1${reset} en el menú para gobernar tu nación: el juego
  te pedirá la contraseña de nación que acabas de elegir.

  ¿Eres nuevo en Conquer? La opción 7 del menú es un mundo de práctica, y el
  botón Coach te guía en tu primer turno.
"
MSG[join_finish]="  Pulsa una tecla para continuar..."
