# Languages of the player menu

Texts of the player menu (`menu.sh`) and the invite-code wizard
(`join.sh`), one file per language: `en.sh` (English, the reference),
`es.sh` (Spanish)... The image installs them in
`/usr/local/share/conquer-web/i18n/`, and `scripts/i18n.sh` loads English
and then the player's language on top, so a text a language does not have
is shown in English.

The game page passes the visitor's language to the menu in the terminal's
address (`/play/?arg=fr`, ttyd `--url-arg`). The menu takes it only when it
looks like a language code and a file for it exists here.

Each text is a line `MSG[key]="..."`:

- it is a `printf` format: `%s` is filled in by the menu (a nation, a
  turn...), in the order of the English text; write `%%` for a percent sign;
- `${bold}`, `${dim}`, `${yellow}`, `${green}` and `${reset}` are the
  terminal's styles; keep them around the same words;
- `menu_date_format` is a `date` format, not a `printf` one;
- `menu_yes` lists the keys that answer yes in that language (`y` always
  does);
- the screen is 80 columns wide: keep lines under about 76 characters, and
  count wide characters (Chinese, Japanese, Korean) as two.

To add a language, copy `es.sh` to `<code>.sh` (`fr.sh`, `pt-br.sh`...),
translate every text and run `python3 tools/check-i18n.py`.
