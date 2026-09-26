#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Publish the public game status (turn, schedule, scores) as JSON for the
# landing page. Run at container start and after every turn update.

# Always run as the game user: files written as root (backups, news, the
# world data) would not be writable by the game afterwards
if [ "$(id -u)" = 0 ] && id conquer >/dev/null 2>&1; then
    exec setpriv --reuid=conquer --regid=conquer --init-groups "$0" "$@"
fi

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
PUBLIC_DIR="${PUBLIC_DIR:-$PREFIX/public}"

TURN_SCHEDULE="" TURN_SCHEDULE_LABEL=""
# shellcheck source=/dev/null
[ -f /etc/conquer-web.env ] && . /etc/conquer-web.env

# Time of the next scheduled turn update (Unix time), if any
next_turn=""
if [ -n "$TURN_SCHEDULE" ] && [ "$TURN_SCHEDULE" != off ]; then
    next_turn=$(/usr/local/bin/conquer-next-turn "$TURN_SCHEDULE" 2>/dev/null)
fi

# Result of the last turn update, written by conquer-turn
TURN_STATE="" TURN_STATE_TIME="" TURN_STATE_MESSAGE=""
# shellcheck source=/dev/null
[ -f "$PREFIX/lib/.turn-state" ] && . "$PREFIX/lib/.turn-state"

mkdir -p "$PUBLIC_DIR" || exit 1

scores=$("$PREFIX/bin/conquer" -s 2>/dev/null) || exit 1
tmp=$(mktemp "$PUBLIC_DIR/.status.XXXXXX") || exit 1

# Latest world newspapers. The update after turn N writes news<N>, so the
# newest edition is news<turn-1>. Each file has section headings
# ("1<TAB>IMPORTANT WORLD NEWS") followed by items ("1.<TAB>text").
# Section 3 (every captured sector with its coordinates) is left out.
NEWS_EDITIONS=3
turn=$(sed -n 's/^Conquer .*, Turn \([0-9][0-9]*\)$/\1/p' <<< "$scores" | head -n 1)
news_files=()
for ((n = ${turn:-1} - 1; n >= 0 && ${#news_files[@]} < NEWS_EDITIONS; n--)); do
    [ -s "$PREFIX/lib/news$n" ] && news_files+=("$PREFIX/lib/news$n")
done
news_json=$(awk '
function json(s) {
    gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); gsub(/\t/, " ", s)
    return "\"" s "\""
}
function close_section() {
    if (title != "" && items != "") {
        sections = sections (sections == "" ? "" : ",") "{\"title\":" json(title) ",\"items\":[" items "]}"
    }
    title = ""; items = ""
}
function close_edition() {
    close_section()
    if (edition != "" && sections != "") {
        out = out (out == "" ? "" : ",") "{\"turn\":" edition ",\"sections\":[" sections "]}"
    }
    sections = ""
}
FNR == 1 {
    close_edition()
    edition = FILENAME; sub(/.*news/, "", edition)
    skip = 0
}
/^[0-9]+\t/ {
    close_section()
    split($0, parts, "\t")
    skip = (parts[1] == 3)
    title = substr($0, index($0, "\t") + 1)
    next
}
/^[0-9]+[^\t]*\t/ {
    if (skip || title == "") next
    text = substr($0, index($0, "\t") + 1)
    gsub(/^[ \t]+|[ \t]+$/, "", text)
    if (text != "") items = items (items == "" ? "" : ",") json(text)
}
END { close_edition(); printf "[%s]", out }
' "${news_files[@]}" 2>/dev/null)
[ -n "$news_json" ] || news_json="[]"

# "conquer -s" prints a header line with the season and turn, an optional
# "Last Update:" line, a column header and one row per nation. Monster
# nations (pirates, savages...) have no score and are left out.
# The news JSON goes through the environment: awk -v would interpret the
# backslash escapes inside it
NEWS_JSON="$news_json" awk -v schedule="$TURN_SCHEDULE_LABEL" -v generated="$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    -v state="$TURN_STATE" -v state_time="$TURN_STATE_TIME" -v state_message="$TURN_STATE_MESSAGE" \
    -v next_turn="$next_turn" '
function json(s) {
    gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); gsub(/\t/, " ", s)
    return "\"" s "\""
}
/^Conquer [0-9.]+: / {
    line = $0
    sub(/^Conquer [0-9.]+: /, "", line)
    season = line; sub(/, Turn [0-9]+$/, "", season)
    turn = line; sub(/^.*, Turn /, "", turn)
    next
}
/^Last Update: / { last = $0; sub(/^Last Update: /, "", last); next }
/^id / { next }
NF >= 6 && $1 ~ /^[0-9]+$/ && $6 ~ /^[0-9]+$/ {
    rows[++n] = sprintf("{\"name\":%s,\"race\":%s,\"class\":%s,\"alignment\":%s,\"score\":%d}",
        json($2), json($3), json($4), json($5), $6)
}
END {
    printf "{\"generated\":%s,\"season\":%s,\"turn\":%d,\"last_update\":%s,\"schedule\":%s,",
        json(generated), json(season), turn, json(last), json(schedule)
    printf "\"next_turn\":%s,", (next_turn ~ /^[0-9]+$/ ? next_turn : "null")
    printf "\"turn_state\":{\"state\":%s,\"time\":%s,\"message\":%s},",
        json(state), json(state_time), json(state_message)
    printf "\"news\":%s,\"nations\":[", ENVIRON["NEWS_JSON"]
    for (i = 1; i <= n; i++) printf "%s%s", (i > 1 ? "," : ""), rows[i]
    print "]}"
}' <<< "$scores" > "$tmp" || { rm -f "$tmp"; exit 1; }

chmod 644 "$tmp"
mv -f "$tmp" "$PUBLIC_DIR/status.json"
