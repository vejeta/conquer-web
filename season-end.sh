#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Close a season: keep its final scores in the hall of fame (hall.html).
# Run it after the last turn of the season, before starting a new world.
#
# Usage: ./season-end.sh "Season 1: Return of the Usenet generals"
#
# The final public status is copied to <status dir>/seasons/<slug>.json and
# listed in seasons/index.json, next to status.json (data/public, or the
# STATUS_DIR of the environment file on the VPS).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NAME="$1"
if [ -z "$NAME" ]; then
    sed -n '/^# Usage:/p' "$0" | sed 's/^# //'
    exit 1
fi

STATUS_DIR=""
for env in config/production.env config/local.env; do
    if [ -f "$env" ]; then
        STATUS_DIR=$(sed -n 's/^STATUS_DIR=//p' "$env" | tail -n 1)
        break
    fi
done
STATUS_DIR="${STATUS_DIR:-$SCRIPT_DIR/data/public}"
STATUS="$STATUS_DIR/status.json"
if [ ! -s "$STATUS" ]; then
    echo "❌ No game status at $STATUS"
    exit 1
fi

json_string() {
    local s="${1//\\/\\\\}"
    s="${s//\"/\\\"}"
    printf '"%s"' "$s"
}

slug=$(printf '%s' "$NAME" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//' | cut -c1-60)
[ -n "$slug" ] || slug="season"
ended=$(date -u '+%Y-%m-%d')
SEASONS="$STATUS_DIR/seasons"
mkdir -p "$SEASONS"

{
    printf '{"name":%s,"ended":%s,"final":' "$(json_string "$NAME")" "$(json_string "$ended")"
    cat "$STATUS"
    printf '}\n'
} > "$SEASONS/$slug.json"

# Index of the seasons, newest first
list="$SEASONS/.list"
touch "$list"
awk -F'\t' -v s="$slug" '$1 != s' "$list" > "$list.tmp"
printf '%s\t%s\t%s\n' "$slug" "$ended" "$NAME" >> "$list.tmp"
mv -f "$list.tmp" "$list"
{
    printf '['
    sort -t "$(printf '\t')" -k2,2r "$list" | awk -F'\t' '
        function j(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return "\"" s "\"" }
        { printf "%s{\"slug\":%s,\"ended\":%s,\"name\":%s}", (NR > 1 ? "," : ""), j($1), j($2), j($3) }'
    printf ']\n'
} > "$SEASONS/index.json"
chmod 644 "$SEASONS"/*.json

echo "✅ \"$NAME\" is in the hall of fame ($SEASONS/$slug.json)"
echo "   Start the next season with ./generate-world.sh or ./reset-to-default-world.sh"
