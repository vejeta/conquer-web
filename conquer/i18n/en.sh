# shellcheck shell=bash disable=SC2034,SC2154
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Texts of the player menu and the join wizard, in English: the reference
# for every other language, and what a language shows for any text it does
# not have. See README.md in this directory.
#
# printf formats: %s is filled in by the program, %% is a percent sign.
# ${bold} ${dim} ${yellow} ${green} ${reset} are the terminal's styles.

MSG[language]="English"

# Player menu (menu.sh)
MSG[menu_pause]="${dim}Press any key to return to the menu...${reset}"
MSG[menu_too_small]="${yellow}${bold}Your terminal is too small: %s${reset}"
MSG[menu_needs_size]="Conquer needs at least %s columns x %s rows.
Make the browser window bigger or zoom out (Ctrl and -).

Press any key to check again, or 'c' to continue anyway."
MSG[menu_ready_count]="%s of %s nations"
MSG[menu_all_ready]="  ${green}${bold}Every nation is ready: the turn update starts now.${reset}
  Come back in a few minutes for the new turn."
MSG[menu_ask_done]="  Are your orders for this turn done? [y/N] "
# The keys that answer yes to the questions, then no
MSG[menu_yes]="yY"
MSG[menu_marked]="  ${green}Orders marked as done.${reset} You can still change them until the update."
MSG[menu_unmarked]="  Your orders are ${bold}no longer marked as done${reset}."
MSG[menu_marked_turn]="  ${green}Your orders are marked as done for this turn.${reset}"
MSG[menu_early_note]="  The turn update runs early once every nation is done."
MSG[menu_not_yet]="not yet"
MSG[menu_no_nation]="${dim}no nation assigned yet${reset}"
MSG[menu_any_nation]="${dim}any nation${reset}"
MSG[menu_nation]="nation ${bold}%s${reset}"
MSG[menu_signed_in]="  ${dim}Signed in as:    ${reset} ${bold}%s${reset} (%s)"
MSG[menu_last_update]="  ${dim}Last turn update:${reset} %s"
MSG[menu_schedule]="  ${dim}Turn schedule:   ${reset} %s"
MSG[menu_schedule_unknown]="see game administrator"
MSG[menu_next_update]="  ${dim}Next turn update:${reset} %s"
# date(1) format of the next turn update (read as is: % is date's own)
MSG[menu_date_format]="+%a %d %b %H:%M %Z"
MSG[menu_orders_done]="  ${dim}Orders done:     ${reset} %s"
MSG[menu_yours_done]="${green}(yours: done)${reset}"
MSG[menu_yours_not_yet]="${yellow}(yours: not yet)${reset}"
MSG[menu_updating]="  ${yellow}${bold}A turn update is in progress.${reset} Please come back in a few minutes."
MSG[menu_update_failed]="  ${yellow}${bold}The last turn update failed${reset} (%s): ${dim}%s${reset}
  The administrator has been notified; your orders are kept for the next update."
MSG[menu_how_to_join]="${bold}How to join the game${reset}

Joining is by invitation.

  1. Ask the game administrator for an invite code.
  2. On the home page, choose \"Create your account\", type the code and
     choose your account name and password.
  3. Sign in with that account and choose \"Play\": the game has you found
     your nation, and from then on opens it directly.

${bold}How turns work${reset}

Conquer is played in turns. You can log in as often as you like to give
orders (move armies, draft, build, trade...). All orders are resolved
together at the next turn update: %s.

The update waits while players are logged in, so please quit the game
(press 'q') when you are done. When you quit, the menu asks whether your
orders are done; you can also change that with option 6."
MSG[menu_how_early]="When every nation has marked its orders as done, the turn update
runs right away instead of waiting for the schedule."
MSG[menu_admin_contact]="Administrator contact: ${bold}%s${reset}"
MSG[menu_keys]="${bold}Quick key reference${reset}   (press '?' inside the game for full help)

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

  Ctrl-L redraws the screen if it looks garbled."
MSG[menu_practice_failed]="  ${yellow}Could not create your practice world.${reset}"
MSG[menu_practice_title]="  ${bold}${green}Practice world${reset}   ${dim}only you play here; nothing counts${reset}"
MSG[menu_practice_nation]="  ${dim}Your nation:  ${reset} ${bold}%s${reset}   ${dim}password:${reset} ${bold}%s${reset}"
MSG[menu_practice_now]="  ${dim}Now:          ${reset} %s"
MSG[menu_practice_intro]="  Try anything, run the next turn yourself and see what happens.
  The Coach button above the game walks you through a first turn."
MSG[menu_practice_play]="Play the practice nation"
MSG[menu_practice_turn]="Run the next turn now"
MSG[menu_practice_reset]="Start again with a new world"
MSG[menu_back]="Back to the main menu"
MSG[menu_choose]="  Choose an option: "
MSG[menu_practice_running]="  Running the turn update of your practice world..."
MSG[menu_practice_done]="  ${green}Done:${reset} %s -> %s
  Play again to read the newspaper (N) and your mail (R)."
MSG[menu_practice_not_run]="  ${yellow}The update did not run.${reset} Quit the practice game first."
MSG[menu_practice_ask_reset]="  Delete your practice world and start again? [y/N] "
MSG[menu_practice_ready]="  ${green}A new practice world is ready.${reset}"
MSG[menu_scores_prompt]="Scores - q to return"
MSG[menu_updating_try_later]="  ${yellow}A turn update is in progress.${reset} Please try again in a few minutes."
MSG[menu_unassigned]="  ${yellow}No nation is assigned to your account%s yet.${reset}
  Ask the game administrator for one (see \"How to join\" in the menu)."
MSG[menu_opening]="Opening your nation ${bold}%s${reset}."
MSG[menu_nations]="Nations of this world: %s"
MSG[menu_nations_hint]="Type one of them (or god) when the game asks \"What nation would you like to be\"."
MSG[menu_disconnected]="${yellow}You were disconnected for the turn update.${reset}
Your orders were saved. Come back in a few minutes for the new turn."
MSG[menu_cannot_enter]="${yellow}Could not enter the game.${reset}
Check your nation name and password. If a turn update is
running, try again in a few minutes."
MSG[menu_play]="Play"
MSG[menu_join]="How to join / how turns work"
MSG[menu_key_reference]="Key reference"
MSG[menu_scores]="Scores"
MSG[menu_help]="Full help (in-game help screens)"
MSG[menu_not_done]="My orders are not done yet"
MSG[menu_done]="My orders for this turn are done"
MSG[menu_practice]="Practice world (only you, nothing counts)"
MSG[menu_log_out]="Log out"
MSG[menu_goodbye]="Goodbye, commander."

# Join wizard (join.sh)
MSG[join_questions]="Questions: ${bold}%s${reset}"
MSG[join_title]="${bold}${green}Found your nation${reset}"
MSG[join_welcome]="Welcome, ${bold}%s${reset}. Your account is ready: now found your nation."
MSG[join_too_late]="This game is at turn %s: after turn 5 new nations need the administrator. Ask them to add yours."
MSG[join_builder]="
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
"
MSG[join_open_builder]="  Press any key to open the nation builder..."
MSG[join_no_nation]="No nation was created. Choose 1 in the menu to try again."
MSG[join_not_saved]="Your nation %s was created, but it could not be linked to your account. Tell the administrator."
MSG[join_done]="
  ${bold}${green}Welcome to the game, ruler of %s!${reset}

  From now on, choose ${bold}1${reset} in the menu to rule your nation: the game asks
  for the nation password you just chose.

  New to Conquer? Option 7 in the menu is a practice world, and the Coach
  button walks you through your first turn.
"
MSG[join_finish]="  Press any key to continue..."
