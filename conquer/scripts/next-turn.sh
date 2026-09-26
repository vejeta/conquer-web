#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Print the Unix time of the next run of a cron schedule, in the time zone
# of the environment (TZ), or nothing if it cannot be computed.
#
# Usage: conquer-next-turn ["MIN HOUR DOM MON DOW"]   (default: $TURN_SCHEDULE)
#
# Supports numbers, "*", lists (1,3), ranges (1-5) and steps (*/15, 1-30/5),
# with cron's rule that when both day of month and day of week are
# restricted, a day matching either one runs. Names (MON, JAN) and "@daily"
# style shortcuts are not supported.

schedule="${1:-$TURN_SCHEDULE}"

# field_matches VALUE SPEC MIN MAX
field_matches() {
    local value=$1 spec=$2 min=$3 max=$4 part range step lo hi
    local -a parts
    IFS=, read -r -a parts <<< "$spec"
    for part in "${parts[@]}"; do
        step=1
        range=$part
        if [[ "$part" == */* ]]; then
            range=${part%/*}
            step=${part#*/}
        fi
        if [ "$range" = "*" ]; then
            lo=$min; hi=$max
        elif [[ "$range" == *-* ]]; then
            lo=${range%-*}; hi=${range#*-}
        elif [ "$step" != 1 ]; then
            lo=$range; hi=$max
        else
            lo=$range; hi=$range
        fi
        [[ "$lo$hi$step" =~ ^[0-9]+$ ]] || return 2
        if [ "$value" -ge "$lo" ] && [ "$value" -le "$hi" ] && [ $(((value - lo) % step)) -eq 0 ]; then
            return 0
        fi
    done
    return 1
}

read -r f_min f_hour f_dom f_mon f_dow extra <<< "$schedule"
if [ -z "$f_dow" ] || [ -n "$extra" ]; then
    exit 1
fi
# Only digits and cron operators are understood
for f in "$f_min" "$f_hour" "$f_dom" "$f_mon" "$f_dow"; do
    [[ "$f" =~ ^[0-9*,/-]+$ ]] || exit 1
done

day_matches() {
    local dom=$1 mon=$2 dow=$3 dom_ok dow_ok
    field_matches "$mon" "$f_mon" 1 12 || return 1
    field_matches "$dom" "$f_dom" 1 31 && dom_ok=1
    # Sunday is both 0 and 7
    { field_matches "$dow" "$f_dow" 0 7 || { [ "$dow" = 0 ] && field_matches 7 "$f_dow" 0 7; }; } && dow_ok=1
    if [ "$f_dom" != "*" ] && [ "$f_dow" != "*" ]; then
        [ -n "$dom_ok" ] || [ -n "$dow_ok" ]
    else
        [ -n "$dom_ok" ] && [ -n "$dow_ok" ]
    fi
}

now=$(date +%s)
# Up to four years ahead, so schedules on February 29 are found too
for ((d = 0; d <= 1470; d++)); do
    read -r ymd dom mon dow <<< "$(date -d "today +$d days" '+%Y-%m-%d %-d %-m %w')"
    day_matches "$dom" "$mon" "$dow" || continue
    for ((h = 0; h < 24; h++)); do
        field_matches "$h" "$f_hour" 0 23 || continue
        for ((m = 0; m < 60; m++)); do
            field_matches "$m" "$f_min" 0 59 || continue
            t=$(date -d "$ymd $h:$m" +%s 2>/dev/null) || continue
            if [ "$t" -gt "$now" ]; then
                echo "$t"
                exit 0
            fi
        done
    done
done
exit 1
