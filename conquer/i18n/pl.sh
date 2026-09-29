# shellcheck shell=bash disable=SC2034,SC2154
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Teksty menu gracza i kreatora dołączania, po polsku. Każdy tekst, którego
# tu brakuje, jest wyświetlany po angielsku (en.sh). Zobacz README.md.

MSG[language]="Polski"

# Menu gracza (menu.sh)
MSG[menu_pause]="${dim}Naciśnij dowolny klawisz, aby wrócić do menu...${reset}"
MSG[menu_too_small]="${yellow}${bold}Twój terminal jest za mały: %s${reset}"
MSG[menu_needs_size]="Conquer potrzebuje co najmniej %s kolumn x %s wierszy.
Powiększ okno przeglądarki albo pomniejsz widok (Ctrl i -).

Naciśnij dowolny klawisz, aby sprawdzić ponownie, albo 'c', aby mimo to
kontynuować."
MSG[menu_ready_count]="%s z %s"
MSG[menu_all_ready]="  ${green}${bold}Wszystkie narody są gotowe: rozliczenie tury rusza teraz.${reset}
  Wróć za kilka minut na nową turę."
MSG[menu_ask_done]="  Czy twoje rozkazy na tę turę są gotowe? [t/N] "
MSG[menu_yes]="tTyY"
MSG[menu_marked]="  ${green}Rozkazy oznaczone jako gotowe.${reset} Do rozliczenia możesz je zmieniać."
MSG[menu_unmarked]="  Twoje rozkazy ${bold}nie są już oznaczone jako gotowe${reset}."
MSG[menu_marked_turn]="  ${green}Twoje rozkazy na tę turę są oznaczone jako gotowe.${reset}"
MSG[menu_early_note]="  Rozliczenie tury rusza wcześniej, gdy wszystkie narody są gotowe."
MSG[menu_not_yet]="jeszcze nie"
MSG[menu_no_nation]="${dim}jeszcze bez przydzielonego narodu${reset}"
MSG[menu_any_nation]="${dim}dowolny naród${reset}"
MSG[menu_nation]="naród ${bold}%s${reset}"
MSG[menu_signed_in]="  ${dim}Gracz:               ${reset} ${bold}%s${reset} (%s)"
MSG[menu_last_update]="  ${dim}Ostatnie rozliczenie:${reset} %s"
MSG[menu_schedule]="  ${dim}Harmonogram tur:     ${reset} %s"
MSG[menu_schedule_unknown]="zapytaj administratora gry"
MSG[menu_next_update]="  ${dim}Następne rozliczenie:${reset} %s"
MSG[menu_date_format]="+%d.%m %H:%M %Z"
MSG[menu_orders_done]="  ${dim}Rozkazy gotowe:      ${reset} %s"
MSG[menu_yours_done]="${green}(twoje: gotowe)${reset}"
MSG[menu_yours_not_yet]="${yellow}(twoje: jeszcze nie)${reset}"
MSG[menu_updating]="  ${yellow}${bold}Trwa rozliczenie tury.${reset} Wróć za kilka minut."
MSG[menu_update_failed]="  ${yellow}${bold}Ostatnie rozliczenie tury się nie udało${reset} (%s): ${dim}%s${reset}
  Administrator został powiadomiony; twoje rozkazy czekają na następne."
MSG[menu_how_to_join]="${bold}Jak dołączyć do gry${reset}

W fazie testów nowe narody zakłada administrator gry.

  1. Poproś administratora o naród. Dostaniesz:
       - konto gracza na tej stronie, powiązane z twoim narodem
       - hasło twojego narodu
  2. Zaloguj się na konto gracza i wybierz w tym menu \"Graj\".
  3. Twój naród otworzy się od razu: wpisz jego hasło.

${bold}Jak działają tury${reset}

W Conquer gra się turami. Możesz logować się, ile razy chcesz, aby
wydawać rozkazy (ruszać armiami, pobierać wojsko, budować, handlować...).
Wszystkie rozkazy wykonują się naraz przy następnym rozliczeniu tury:
%s.

Rozliczenie czeka, dopóki gracze są zalogowani, więc gdy skończysz,
wyjdź z gry (klawisz 'q'). Przy wyjściu menu zapyta, czy twoje rozkazy
są gotowe; możesz to też zmienić opcją 6.

Ekrany samej gry są po angielsku, jak w 1987 roku; samouczek na stronie
objaśnia każdy z nich po polsku."
MSG[menu_how_early]="Gdy wszystkie narody oznaczą swoje rozkazy jako gotowe, rozliczenie tury
rusza od razu, bez czekania na harmonogram."
MSG[menu_admin_contact]="Kontakt z administratorem: ${bold}%s${reset}"
MSG[menu_keys]="${bold}Ściągawka klawiszy${reset}   (w grze '?' pokazuje pełną pomoc)

  Ruch          y k u         Mapa i informacje
                 \\|/           d   zmiana widoku       s   wyniki
               h -+- l         N   czytaj gazetę       R   czytaj pocztę
                 /|\\           I   przegląd państwa    a   raport armii
                b j n         (klawiatura numeryczna 1-9 też rusza)

  Akcje         m   rusz jednostką        D   pobór wojska
                p   następna jednostka    C   budowa
                r   przeznacz sektor      B   budżet
                S   dyplomacja            M   magia
                P   produkcja             q   wyjście

  Ctrl-L odświeża ekran, jeśli obraz się rozsypie."
MSG[menu_practice_failed]="  ${yellow}Nie udało się założyć twojego świata treningowego.${reset}"
MSG[menu_practice_title]="  ${bold}${green}Świat treningowy${reset}   ${dim}grasz tu tylko ty; nic się nie liczy${reset}"
MSG[menu_practice_nation]="  ${dim}Twój naród:  ${reset} ${bold}%s${reset}   ${dim}hasło:${reset} ${bold}%s${reset}"
MSG[menu_practice_now]="  ${dim}Teraz:       ${reset} %s"
MSG[menu_practice_intro]="  Próbuj wszystkiego, rozliczaj kolejne tury i patrz, co się stanie.
  Przycisk Coach nad grą poprowadzi cię przez pierwszą turę."
MSG[menu_practice_play]="Graj narodem treningowym"
MSG[menu_practice_turn]="Rozlicz następną turę teraz"
MSG[menu_practice_reset]="Zacznij od nowa w nowym świecie"
MSG[menu_back]="Powrót do menu głównego"
MSG[menu_choose]="  Wybierz opcję: "
MSG[menu_practice_running]="  Trwa rozliczenie tury w twoim świecie treningowym..."
MSG[menu_practice_done]="  ${green}Gotowe:${reset} %s -> %s
  Zagraj znowu, aby przeczytać gazetę (N) i pocztę (R)."
MSG[menu_practice_not_run]="  ${yellow}Rozliczenie się nie odbyło.${reset} Najpierw wyjdź z gry treningowej."
MSG[menu_practice_ask_reset]="  Usunąć twój świat treningowy i zacząć od nowa? [t/N] "
MSG[menu_practice_ready]="  ${green}Nowy świat treningowy jest gotowy.${reset}"
MSG[menu_scores_prompt]="Wyniki - q, aby wrócić"
MSG[menu_updating_try_later]="  ${yellow}Trwa rozliczenie tury.${reset} Spróbuj ponownie za kilka minut."
MSG[menu_unassigned]="  ${yellow}Do twojego konta%s nie przydzielono jeszcze narodu.${reset}
  Poproś o niego administratora gry (zobacz \"Jak dołączyć\" w menu)."
MSG[menu_opening]="Otwieram twój naród ${bold}%s${reset}."
MSG[menu_disconnected]="${yellow}Rozłączono cię na czas rozliczenia tury.${reset}
Twoje rozkazy zostały zapisane. Wróć za kilka minut na nową turę."
MSG[menu_cannot_enter]="${yellow}Nie udało się wejść do gry.${reset}
Sprawdź nazwę i hasło swojego narodu. Jeśli trwa rozliczenie
tury, spróbuj ponownie za kilka minut."
MSG[menu_play]="Graj"
MSG[menu_join]="Jak dołączyć / jak działają tury"
MSG[menu_key_reference]="Ściągawka klawiszy"
MSG[menu_scores]="Wyniki"
MSG[menu_help]="Pełna pomoc (ekrany pomocy gry, po angielsku)"
MSG[menu_not_done]="Moje rozkazy nie są jeszcze gotowe"
MSG[menu_done]="Moje rozkazy na tę turę są gotowe"
MSG[menu_practice]="Świat treningowy (tylko ty, nic się nie liczy)"
MSG[menu_log_out]="Wyloguj"
MSG[menu_goodbye]="Do zobaczenia, dowódco."

# Kreator dołączania (join.sh)
MSG[join_questions]="Pytania: ${bold}%s${reset}"
MSG[join_again]="  Naciśnij dowolny klawisz, aby zacząć od nowa..."
MSG[join_title]="${bold}${green}Dołącz do Conquer${reset}"
MSG[join_closed]="Na tym serwerze nie można teraz dołączyć do gry."
MSG[join_welcome]="Witaj. Potrzebujesz ${bold}kodu zaproszenia${reset} od administratora gry."
MSG[join_code]="  Kod zaproszenia: "
MSG[join_bad_code]="Ten kod zaproszenia jest nieważny albo został już użyty.
  Kod zaproszenia wygląda tak: ${bold}K7QM-3XPA${reset}. Wysyła go administrator;
  to nie jest hasło konta do dołączania."
MSG[join_too_late]="Ta rozgrywka jest w turze %s: po turze 5 nowe narody zakłada
  administrator. Kod pozostaje ważny; poproś go o dodanie narodu."
MSG[join_choose_account]="Wybierz ${bold}konto gracza${reset}, na które będziesz logować się na tej stronie
  ${dim}(litery, cyfry, . _ - ; do 32 znaków)${reset}"
MSG[join_account]="  Nazwa konta: "
MSG[join_bad_account]="Używaj tylko liter, cyfr, kropek, łączników i podkreśleń."
MSG[join_account_exists]="Konto '%s' już istnieje. Wybierz inną nazwę."
MSG[join_password]="  Hasło (co najmniej 8 znaków): "
MSG[join_password_again]="  Powtórz hasło: "
MSG[join_password_mismatch]="Hasła się nie zgadzają."
MSG[join_password_short]="Użyj co najmniej 8 znaków."
MSG[join_builder]="
  ${bold}Teraz zbuduj swój naród${reset} w kreatorze narodów gry
  (jego ekrany są po angielsku).

  Kreator zapyta o:
    - ${bold}nazwę narodu${reset} (do 9 liter) i ${bold}hasło narodu${reset}
      (do 7 znaków; gra pyta o nie za każdym razem, gdy grasz)
    - imię twojego władcy, ${bold}rasę${reset}, ${bold}klasę${reset} i ${bold}charakter${reset}
    - znak na mapie: dowolną wolną literę z listy
  Potem rozdzielasz punkty na swój naród. Poruszaj się klawiszami
  ${bold}j${reset} i ${bold}k${reset}, naciśnij ${bold}h${reset}, aby przełączyć na dodawanie, a ${bold}Spację${reset},
  aby kupić.
  ${yellow}Rada:${reset} kup 2 lub 3 punkty ${bold}Treasury${reset} (skarbiec); naród bez złota
  nie może pobrać wojska w pierwszej turze. ${bold}Esc${reset} kończy (reszta idzie
  na ludność), a potem odpowiedz ${bold}y${reset}, aby zapisać.
"
MSG[join_open_builder]="  Naciśnij dowolny klawisz, aby otworzyć kreator narodów..."
MSG[join_no_nation]="Nie utworzono narodu, więc nie powstało też konto.
  Twój kod zaproszenia pozostaje ważny."
MSG[join_code_used]="Ten kod zaproszenia został w międzyczasie użyty.
  Zapytaj administratora o naród %s."
MSG[join_not_saved]="Twój naród %s został utworzony, ale nie udało się zapisać konta.
  Powiadom administratora."
MSG[join_done]="
  ${bold}${green}Witaj w grze, władco narodu %s!${reset}

  Twoje konto gracza ${bold}%s${reset} jest gotowe.

  Aby grać, zaloguj się na nie ponownie: zamknij tę kartę przeglądarki
  (albo otwórz stronę w oknie prywatnym), kliknij ${bold}Graj teraz${reset}
  i podaj ${bold}%s${reset} oraz swoje hasło. Twój naród otworzy się od razu;
  jego hasło to to, które podano w kreatorze narodów.

  Pierwszy raz w Conquer? Opcja 7 w menu to świat treningowy,
  a przycisk Coach poprowadzi cię przez pierwszą turę.
"
MSG[join_finish]="  Naciśnij dowolny klawisz, aby zakończyć..."
MSG[join_goodbye]="  Do zobaczenia na mapie."
