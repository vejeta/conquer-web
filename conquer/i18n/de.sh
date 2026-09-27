# shellcheck shell=bash disable=SC2034,SC2154
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Texte des Spielermenüs und des Beitritts-Assistenten, auf Deutsch. Jeder
# Text, der hier fehlt, wird auf Englisch angezeigt (en.sh). Siehe README.md.

MSG[language]="Deutsch"

# Spielermenü (menu.sh)
MSG[menu_pause]="${dim}Drücke eine Taste, um zum Menü zurückzukehren...${reset}"
MSG[menu_too_small]="${yellow}${bold}Dein Terminal ist zu klein: %s${reset}"
MSG[menu_needs_size]="Conquer braucht mindestens %s Spalten x %s Zeilen.
Vergrößere das Browserfenster oder verkleinere die Ansicht (Strg und -).

Drücke eine Taste, um erneut zu prüfen, oder 'c' für trotzdem weiter."
MSG[menu_ready_count]="%s von %s Nationen"
MSG[menu_all_ready]="  ${green}${bold}Alle Nationen sind fertig: Die Zugauswertung startet jetzt.${reset}
  Schau in ein paar Minuten für den neuen Zug wieder vorbei."
MSG[menu_ask_done]="  Sind deine Befehle für diesen Zug fertig? [j/N] "
MSG[menu_yes]="jJyY"
MSG[menu_marked]="  ${green}Befehle als fertig markiert.${reset} Bis zur Auswertung sind sie änderbar."
MSG[menu_unmarked]="  Deine Befehle sind ${bold}nicht mehr als fertig markiert${reset}."
MSG[menu_marked_turn]="  ${green}Deine Befehle für diesen Zug sind als fertig markiert.${reset}"
MSG[menu_early_note]="  Die Zugauswertung läuft früher, sobald alle Nationen fertig sind."
MSG[menu_not_yet]="noch nicht"
MSG[menu_no_nation]="${dim}noch keine Nation zugewiesen${reset}"
MSG[menu_any_nation]="${dim}beliebige Nation${reset}"
MSG[menu_nation]="Nation ${bold}%s${reset}"
MSG[menu_signed_in]="  ${dim}Angemeldet als:    ${reset} ${bold}%s${reset} (%s)"
MSG[menu_last_update]="  ${dim}Letzte Auswertung: ${reset} %s"
MSG[menu_schedule]="  ${dim}Zugplan:           ${reset} %s"
MSG[menu_schedule_unknown]="siehe Spielleiter"
MSG[menu_next_update]="  ${dim}Nächste Auswertung:${reset} %s"
MSG[menu_date_format]="+%d.%m. %H:%M %Z"
MSG[menu_orders_done]="  ${dim}Befehle fertig:    ${reset} %s"
MSG[menu_yours_done]="${green}(deine: fertig)${reset}"
MSG[menu_yours_not_yet]="${yellow}(deine: noch nicht)${reset}"
MSG[menu_updating]="  ${yellow}${bold}Eine Zugauswertung läuft gerade.${reset} Schau in ein paar Minuten wieder vorbei."
MSG[menu_update_failed]="  ${yellow}${bold}Die letzte Zugauswertung ist fehlgeschlagen${reset} (%s): ${dim}%s${reset}
  Der Spielleiter ist informiert; deine Befehle bleiben erhalten."
MSG[menu_how_to_join]="${bold}So machst du mit${reset}

In der Testphase legt der Spielleiter neue Nationen an.

  1. Bitte den Spielleiter um eine Nation. Du bekommst:
       - ein Spielerkonto für diese Seite, verknüpft mit deiner Nation
       - das Passwort deiner Nation
  2. Melde dich mit deinem Spielerkonto an und wähle \"Spielen\" im Menü.
  3. Deine Nation öffnet sich direkt: Gib ihr Passwort ein.

${bold}So funktionieren die Züge${reset}

Conquer wird in Zügen gespielt. Du kannst dich so oft anmelden, wie du
willst, um Befehle zu geben (Armeen bewegen, ausheben, bauen, handeln...).
Alle Befehle werden gemeinsam bei der nächsten Zugauswertung ausgeführt:
%s.

Die Auswertung wartet, solange Spieler angemeldet sind. Verlass das Spiel
also bitte (Taste 'q'), wenn du fertig bist. Beim Verlassen fragt das Menü,
ob deine Befehle fertig sind; das kannst du auch mit Option 6 ändern.

Die Spielbildschirme sind auf Englisch, wie 1987; das Tutorial auf der
Webseite erklärt jeden davon auf Deutsch."
MSG[menu_how_early]="Sobald alle Nationen ihre Befehle als fertig markiert haben, läuft die
Zugauswertung sofort, statt auf den Zugplan zu warten."
MSG[menu_admin_contact]="Kontakt zum Spielleiter: ${bold}%s${reset}"
MSG[menu_keys]="${bold}Tastenübersicht${reset}   (im Spiel zeigt '?' die vollständige Hilfe)

  Bewegung      y k u         Karte & Info
                 \\|/           d   Ansicht wechseln    s   Punktestand
               h -+- l         N   Zeitung lesen       R   Nachrichten lesen
                 /|\\           I   Reichsübersicht     a   Armeebericht
                b j n         (der Ziffernblock 1-9 bewegt auch)

  Aktionen      m   Einheit bewegen       D   Truppen ausheben
                p   nächste Einheit       C   bauen
                r   Sektor umwidmen       B   Haushalt
                S   Diplomatie            M   Magie
                P   Produktion            q   beenden

  Strg-L zeichnet den Bildschirm neu, wenn er durcheinander aussieht."
MSG[menu_practice_failed]="  ${yellow}Deine Übungswelt konnte nicht angelegt werden.${reset}"
MSG[menu_practice_title]="  ${bold}${green}Übungswelt${reset}   ${dim}hier spielst nur du; nichts zählt${reset}"
MSG[menu_practice_nation]="  ${dim}Deine Nation: ${reset} ${bold}%s${reset}   ${dim}Passwort:${reset} ${bold}%s${reset}"
MSG[menu_practice_now]="  ${dim}Jetzt:        ${reset} %s"
MSG[menu_practice_intro]="  Probier alles aus, starte den nächsten Zug selbst und sieh, was passiert.
  Der Knopf Coach über dem Spiel führt dich durch einen ersten Zug."
MSG[menu_practice_play]="Die Übungsnation spielen"
MSG[menu_practice_turn]="Den nächsten Zug jetzt auswerten"
MSG[menu_practice_reset]="Mit einer neuen Welt neu anfangen"
MSG[menu_back]="Zurück zum Hauptmenü"
MSG[menu_choose]="  Wähle eine Option: "
MSG[menu_practice_running]="  Die Zugauswertung deiner Übungswelt läuft..."
MSG[menu_practice_done]="  ${green}Fertig:${reset} %s -> %s
  Spiel wieder, um die Zeitung (N) und deine Post (R) zu lesen."
MSG[menu_practice_not_run]="  ${yellow}Die Auswertung ist nicht gelaufen.${reset} Verlass zuerst das Übungsspiel."
MSG[menu_practice_ask_reset]="  Übungswelt löschen und neu anfangen? [j/N] "
MSG[menu_practice_ready]="  ${green}Eine neue Übungswelt ist bereit.${reset}"
MSG[menu_scores_prompt]="Punktestand - q für zurück"
MSG[menu_updating_try_later]="  ${yellow}Eine Zugauswertung läuft gerade.${reset} Versuch es in ein paar Minuten noch mal."
MSG[menu_unassigned]="  ${yellow}Deinem Konto%s ist noch keine Nation zugewiesen.${reset}
  Bitte den Spielleiter um eine (siehe \"So machst du mit\" im Menü)."
MSG[menu_opening]="Deine Nation ${bold}%s${reset} wird geöffnet."
MSG[menu_disconnected]="${yellow}Du wurdest für die Zugauswertung getrennt.${reset}
Deine Befehle sind gespeichert. Schau in ein paar Minuten für den neuen Zug
wieder vorbei."
MSG[menu_cannot_enter]="${yellow}Das Spiel konnte nicht gestartet werden.${reset}
Prüfe Namen und Passwort deiner Nation. Läuft gerade eine
Zugauswertung, versuch es in ein paar Minuten noch mal."
MSG[menu_play]="Spielen"
MSG[menu_join]="So machst du mit / so funktionieren die Züge"
MSG[menu_key_reference]="Tastenübersicht"
MSG[menu_scores]="Punktestand"
MSG[menu_help]="Vollständige Hilfe (Hilfeseiten des Spiels, auf Englisch)"
MSG[menu_not_done]="Meine Befehle sind noch nicht fertig"
MSG[menu_done]="Meine Befehle für diesen Zug sind fertig"
MSG[menu_practice]="Übungswelt (nur du, nichts zählt)"
MSG[menu_log_out]="Abmelden"
MSG[menu_goodbye]="Leb wohl, Feldherr."

# Beitritts-Assistent (join.sh)
MSG[join_questions]="Fragen: ${bold}%s${reset}"
MSG[join_again]="  Drücke eine Taste, um neu anzufangen..."
MSG[join_title]="${bold}${green}Bei Conquer mitmachen${reset}"
MSG[join_closed]="Auf diesem Server ist ein Beitritt gerade nicht möglich."
MSG[join_welcome]="Willkommen. Du brauchst einen ${bold}Einladungscode${reset} vom Spielleiter."
MSG[join_code]="  Einladungscode: "
MSG[join_bad_code]="Dieser Einladungscode ist ungültig oder wurde schon benutzt."
MSG[join_too_late]="Diese Partie ist bei Zug %s: Nach Zug 5 legt der Spielleiter neue
  Nationen an. Dein Code bleibt gültig; bitte ihn, deine Nation anzulegen."
MSG[join_choose_account]="Wähle das ${bold}Spielerkonto${reset}, mit dem du dich auf dieser Seite anmeldest
  ${dim}(Buchstaben, Ziffern, . _ - ; bis zu 32 Zeichen)${reset}"
MSG[join_account]="  Kontoname: "
MSG[join_bad_account]="Bitte nur Buchstaben, Ziffern, Punkte, Binde- und Unterstriche verwenden."
MSG[join_account_exists]="Das Konto '%s' gibt es schon. Wähle einen anderen Namen."
MSG[join_password]="  Passwort (mindestens 8 Zeichen): "
MSG[join_password_again]="  Passwort wiederholen: "
MSG[join_password_mismatch]="Die Passwörter stimmen nicht überein."
MSG[join_password_short]="Verwende mindestens 8 Zeichen."
MSG[join_builder]="
  ${bold}Jetzt baust du deine Nation${reset} mit dem Nationenbaukasten des Spiels
  (seine Bildschirme sind auf Englisch).

  Er fragt nach:
    - einem ${bold}Nationsnamen${reset} (bis zu 9 Buchstaben) und einem ${bold}Nationspasswort${reset}
      (bis zu 7 Zeichen; das Spiel fragt bei jedem Spielen danach)
    - dem Namen deines Herrschers, einem ${bold}Volk${reset}, einer ${bold}Klasse${reset} und einer
      ${bold}Gesinnung${reset}
    - einem Kartenzeichen: ein freier Buchstabe aus der Liste
  Dann verteilst du Punkte auf deine Nation. Bewege dich mit ${bold}j${reset} und ${bold}k${reset},
  drücke ${bold}h${reset}, um aufs Hinzufügen umzuschalten, und die ${bold}Leertaste${reset} zum Kaufen.
  ${yellow}Tipp:${reset} Kauf 2 oder 3 Punkte ${bold}Treasury${reset} (Schatzkammer); eine Nation ohne
  Gold kann in ihrem ersten Zug keine Truppen ausheben. ${bold}Esc${reset} schließt ab
  (der Rest geht an die Bevölkerung), dann mit ${bold}y${reset} speichern.
"
MSG[join_open_builder]="  Drücke eine Taste, um den Nationenbaukasten zu öffnen..."
MSG[join_no_nation]="Es wurde keine Nation angelegt, also auch kein Konto.
  Dein Einladungscode bleibt gültig."
MSG[join_code_used]="Dieser Einladungscode wurde inzwischen benutzt.
  Frag den Spielleiter nach der Nation %s."
MSG[join_not_saved]="Deine Nation %s wurde angelegt, aber das Konto konnte nicht
  gespeichert werden. Sag dem Spielleiter Bescheid."
MSG[join_done]="
  ${bold}${green}Willkommen im Spiel, Herrscher von %s!${reset}

  Dein Spielerkonto ${bold}%s${reset} ist bereit.

  Um zu spielen, melde dich damit neu an: Schließ diesen Browser-Tab (oder
  öffne die Seite in einem privaten Fenster), klicke auf ${bold}Jetzt spielen${reset}
  und nutze ${bold}%s${reset} und dein Passwort. Deine Nation öffnet sich direkt;
  ihr Passwort ist das, das du im Nationenbaukasten vergeben hast.

  Neu bei Conquer? Option 7 im Menü ist eine Übungswelt, und der Knopf
  Coach führt dich durch deinen ersten Zug.
"
MSG[join_finish]="  Drücke eine Taste zum Beenden..."
MSG[join_goodbye]="  Leb wohl, wir sehen uns auf der Karte."
