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

TURN_SCHEDULE="" TURN_SCHEDULE_LABEL="" TURN_EARLY="" SIGNUP="" HTPASSWD_FILE="" ADMIN_CONTACT=""
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

# Nations that marked their orders as done ("<ready> <total>")
read -r ready_count ready_total < <(/usr/local/bin/conquer-ready count 2>/dev/null)

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
# Sign-up with invite codes is open when the game can write the accounts
signup=false
[ "${SIGNUP:-on}" != off ] && [ -n "$HTPASSWD_FILE" ] && [ -w "$HTPASSWD_FILE" ] && signup=true

NEWS_JSON="$news_json" awk -v schedule="$TURN_SCHEDULE_LABEL" -v generated="$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    -v state="$TURN_STATE" -v state_time="$TURN_STATE_TIME" -v state_message="$TURN_STATE_MESSAGE" \
    -v next_turn="$next_turn" -v ready="${ready_count:-0}" -v ready_total="${ready_total:-0}" \
    -v early="$TURN_EARLY" -v signup="$signup" -v contact="$ADMIN_CONTACT" '
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
    if (ready_total > 0)
        printf "\"ready\":{\"done\":%d,\"total\":%d,\"early\":%s},", ready, ready_total, (early == "on" ? "true" : "false")
    else
        printf "\"ready\":null,"
    printf "\"turn_state\":{\"state\":%s,\"time\":%s,\"message\":%s},",
        json(state), json(state_time), json(state_message)
    # Players with an invite code may create their account (signup.html)
    printf "\"signup\":%s,", signup
    # How to reach the administrator, for "How to join" on the landing page
    if (contact != "")
        printf "\"contact\":%s,", json(contact)
    printf "\"news\":%s,\"nations\":[", ENVIRON["NEWS_JSON"]
    for (i = 1; i <= n; i++) printf "%s%s", (i > 1 ? "," : ""), rows[i]
    print "]}"
}' <<< "$scores" > "$tmp" || { rm -f "$tmp"; exit 1; }

chmod 644 "$tmp"
mv -f "$tmp" "$PUBLIC_DIR/status.json"

# Score history for the chart on the landing page: one line per turn and
# nation in lib/.score-history, published as history.json. A new world
# (the turn went back) starts a new history.
HISTORY_FILE="$PREFIX/lib/.score-history"
if [ -n "$turn" ]; then
    last=$(awk -F'\t' '$1 > max { max = $1 } END { print max + 0 }' "$HISTORY_FILE" 2>/dev/null)
    [ "${last:-0}" -gt "$turn" ] && : > "$HISTORY_FILE"
    {
        awk -F'\t' -v t="$turn" '$1 != t' "$HISTORY_FILE" 2>/dev/null
        awk -v t="$turn" 'NF >= 6 && $1 ~ /^[0-9]+$/ && $6 ~ /^[0-9]+$/ { print t "\t" $2 "\t" $6 }' <<< "$scores"
    } | sort -t "$(printf '\t')" -k1,1n -k2,2 > "$HISTORY_FILE.tmp" && mv -f "$HISTORY_FILE.tmp" "$HISTORY_FILE"
    awk -F'\t' '
        { if (!($1 in seen_t)) { seen_t[$1] = 1; turns[++nt] = $1 }
          if (!($2 in seen_n)) { seen_n[$2] = 1; names[++nn] = $2 }
          score[$1, $2] = $3 }
        END {
            printf "{\"turns\":["
            for (i = 1; i <= nt; i++) printf "%s%d", (i > 1 ? "," : ""), turns[i]
            printf "],\"nations\":{"
            for (j = 1; j <= nn; j++) {
                printf "%s\"%s\":[", (j > 1 ? "," : ""), names[j]
                for (i = 1; i <= nt; i++)
                    printf "%s%s", (i > 1 ? "," : ""), ((turns[i], names[j]) in score ? score[turns[i], names[j]] : "null")
                printf "]"
            }
            print "}}"
        }' "$HISTORY_FILE" > "$PUBLIC_DIR/.history.tmp" &&
        chmod 644 "$PUBLIC_DIR/.history.tmp" && mv -f "$PUBLIC_DIR/.history.tmp" "$PUBLIC_DIR/history.json"
fi

# One shareable page per newspaper edition (status/news/<turn>.html), with
# link preview tags for chat apps and social networks. Old editions never
# change; the newest is rewritten, since rulers can still post to it.
mkdir -p "$PUBLIC_DIR/news"
for ((n = ${turn:-1} - 1; n >= 0; n--)); do
    src="$PREFIX/lib/news$n"
    page="$PUBLIC_DIR/news/$n.html"
    [ -s "$src" ] || continue
    [ -f "$page" ] && [ "$n" -lt $((${turn:-1} - 1)) ] && continue
    awk -v turn="$n" '
    function esc(s) { gsub(/&/, "\\&amp;", s); gsub(/</, "\\&lt;", s); gsub(/>/, "\\&gt;", s); gsub(/"/, "\\&quot;", s); return s }
    BEGIN {
        split("Spring Summer Fall Winter", season, " ")
        when = season[(turn - 1) % 4 + 1] " of Year " int((turn - 1) / 4) + 1
        if (turn < 1) when = "Before the first turn"
    }
    /^[0-9]+\t/ {
        split($0, parts, "\t"); skip = (parts[1] == 3)
        if (open) body = body "</ul>\n"
        if (!skip) body = body "<h2>" esc(substr($0, index($0, "\t") + 1)) "</h2>\n<ul>\n"
        open = !skip; next
    }
    /^[0-9]+[^\t]*\t/ {
        if (skip || !open) next
        text = substr($0, index($0, "\t") + 1); gsub(/^[ \t]+|[ \t]+$/, "", text)
        if (text == "") next
        body = body "<li>" esc(text) "</li>\n"
        if (++items <= 3) summary = summary (summary == "" ? "" : "; ") text
    }
    END {
        if (open) body = body "</ul>\n"
        title = "Conquer world news: turn " turn ", " when
        if (summary == "") summary = "The world newspaper of Conquer, the classic multiplayer strategy game."
        print "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">"
        print "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        print "<title>" esc(title) "</title>"
        print "<meta name=\"description\" content=\"" esc(summary) "\">"
        print "<meta property=\"og:title\" content=\"" esc(title) "\">"
        print "<meta property=\"og:description\" content=\"" esc(summary) "\">"
        print "<meta property=\"og:type\" content=\"article\">"
        print "<meta name=\"twitter:card\" content=\"summary\">"
        print "<style>body{margin:0;background:#0d1117;color:#e6edf3;font:17px/1.6 system-ui,sans-serif}"
        print "main{max-width:760px;margin:0 auto;padding:32px 16px 64px}a{color:#3fb950}"
        print ".mast{font:700 clamp(1.8rem,7vw,2.8rem)/1 ui-monospace,\"DejaVu Sans Mono\",monospace;letter-spacing:.25em;color:#3fb950;margin:0 0 6px}"
        print ".when{color:#8b949e;margin:0 0 28px;font-family:ui-monospace,monospace}"
        print "h2{font-size:.85rem;text-transform:uppercase;letter-spacing:.08em;color:#8b949e;border-top:1px solid #30363d;padding-top:14px}"
        print "li+li{margin-top:4px}.cta{margin-top:36px}</style>\n</head>\n<body>\n<main>"
        print "<p class=\"mast\">CONQUER</p>\n<p class=\"when\">World news &middot; turn " turn " &middot; " esc(when) "</p>"
        printf "%s", body
        print "<p class=\"cta\"><a href=\"../../\">The current game and how to join &rarr;</a></p>"
        print "</main>\n</body>\n</html>"
    }' "$src" > "$page.tmp" && chmod 644 "$page.tmp" && mv -f "$page.tmp" "$page"
done
