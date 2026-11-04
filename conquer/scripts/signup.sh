#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Player accounts for the site (the sign-up page, through conquer-gate).
# An account is written to the file Apache checks and marked in
# lib/.players: "account:?" while the administrator has not approved it,
# "account:+" once it may found a nation (the first time the player plays,
# the menu opens the nation builder). Pending requests are also listed in
# lib/.requests (account, time, language; tab separated). No email address
# or free text is asked for or kept: "scrub" removes what older versions stored.
#
# usage: conquer-signup request ACCOUNT [LANG]              (password on stdin)
#        conquer-signup invite  CODE ACCOUNT                (password on stdin)
#        conquer-signup approve ACCOUNT
#        conquer-signup reject  ACCOUNT
#        conquer-signup assign  ACCOUNT NATION|+|*          (NATION must exist in the world)
#        conquer-signup invites COUNT                       (prints new codes)
#        conquer-signup expire  DAYS                        (removes requests older than DAYS days
#                                                            with their accounts; prints the names)
#        conquer-signup passwd ACCOUNT                      (stdin: current password, new password;
#                                                            exit 2 when the current one is wrong)
#        conquer-signup recovery-init ACCOUNT               (stdin: a recovery code; stores its hash when the
#                                                            account has none; exit 2 it has one, 3 waiting)
#        conquer-signup recovery-renew ACCOUNT              (stdin: current password, new recovery code)
#        conquer-signup reset ACCOUNT                       (stdin: recovery code, new password, new recovery
#                                                            code; exit 2 when the code is wrong)
#        conquer-signup scrub                               (removes the email and message that older
#                                                            versions kept in lib/.requests; prints how
#                                                            many requests it changed)
#        conquer-signup CODE ACCOUNT                        (same as invite)
#
# Recovery codes: only the bcrypt hash of each is kept, in lib/.recovery
# (htpasswd format, mode 600, written to a temporary file and moved into
# place). The site keeps no email address: the code is how a player who
# forgot the password gets the account back. An administrator can still set
# a password by hand: ./manage-players.sh password NAME.
#
# Exit status: 0 done, 2 unknown or used code (invite) or account not
# pending (approve, reject) or unknown account (assign), 3 account name
# taken, 6 no such nation (assign; the nations are printed),  5 sign-up closed (the
# account file cannot be written), 1 anything else. (4 was "too late in
# the game"; an approved account can found its nation at any turn now.)
#
# Administrators can also use: ./manage-players.sh invite|approve|reject

PREFIX="${CONQUER_PREFIX:-/opt/conquer}"
WORLD_DIR="$PREFIX/lib"
INVITES_FILE="$WORLD_DIR/.invites"
PLAYERS_FILE="$WORLD_DIR/.players"
REQUESTS_FILE="$WORLD_DIR/.requests"
# Hashes of the players' recovery codes ("account:bcrypt"), next to the other
# files of the world: the account file's directory is not kept by Docker
RECOVERY_FILE="$WORLD_DIR/.recovery"
HTPASSWD_FILE="${HTPASSWD_FILE:-$PREFIX/auth/htpasswd}"
LOCK_FILE="${CONQUER_RUN:-/run/conquer}/join.lock.accounts"
# Requests waiting for the administrator: past this the page says sign-up is
# closed, so nobody can fill the account file and the disk with accounts
MAX_PENDING=200
TAB=$'\t'

# Remove the line whose first field (separated by $3, default ":") is $2
# from file $1, in place so a bind-mounted file keeps working
drop_line() {
    local rest
    [ -e "$1" ] || return 0
    rest=$(awk -F"${3:-:}" -v key="$2" '$1 != key' "$1") || return 1
    if [ -n "$rest" ]; then printf '%s\n' "$rest" > "$1"; else : > "$1"; fi
}

# Is $2 the first field of file $1?
has_key() {
    awk -F: -v user="$2" '$1 == user { found = 1 } END { exit !found }' "$1" 2>/dev/null
}

# An htpasswd (bcrypt, cost 10) line for account $2 and secret $1
hash_line() {
    printf '%s\n' "$1" | htpasswd -niB -C 10 "$2" | sed '/^$/d'
}

# Does the secret on standard input match the hash of account $2 in file $1?
verify_secret() {
    htpasswd -v -i "$1" "$2" > /dev/null 2>&1
}

# Put line $3 in place of the line of account $2 in file $1 (added when
# there is none), in place so a bind-mounted file keeps working. The caller
# holds the lock.
set_line() {
    local rest
    if has_key "$1" "$2"; then
        rest=$(NEW="$3" awk -F: -v key="$2" '$1 == key { print ENVIRON["NEW"]; next } { print }' "$1") || return 1
    else
        rest=$(cat "$1" 2> /dev/null; printf '%s\n' "$3") || return 1
        rest=$(printf '%s\n' "$rest" | sed '/^$/d')
    fi
    printf '%s\n' "$rest" > "$1"
}

# The same for the recovery file, which is not mounted from elsewhere: the
# new content goes to a temporary file (mode 600) that replaces the old one
set_recovery() {
    local tmp
    tmp=$(mktemp "$RECOVERY_FILE.XXXXXX") || return 1
    if has_key "$RECOVERY_FILE" "$1"; then
        NEW="$2" awk -F: -v key="$1" '$1 == key { print ENVIRON["NEW"]; next } { print }' "$RECOVERY_FILE" > "$tmp" || { rm -f "$tmp"; return 1; }
    else
        { cat "$RECOVERY_FILE" 2> /dev/null; printf '%s\n' "$2"; } | sed '/^$/d' > "$tmp" || { rm -f "$tmp"; return 1; }
    fi
    chmod 600 "$tmp" && mv -f "$tmp" "$RECOVERY_FILE" || { rm -f "$tmp"; return 1; }
}

# A recovery code: XXXX-XXXX-XXXX from the alphabet the gate uses
valid_recovery() {
    [[ "$1" =~ ^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$ ]]
}

# Read and check the password on standard input
read_password() {
    IFS= read -r password || exit 1
    [ ${#password} -ge 8 ] || exit 1
}

# The first character is a letter or digit: "-name" would be read as an
# option by htpasswd, and "." or ".." must never become a directory name
# (the menu's practice world is named after the account). Same rule as
# accountRe in the gate and valid_name in manage-players.sh.
valid_account() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$ ]]
}

# Create web account $1 marked $2 in .players (the caller holds the lock).
# Exits 3 when the name is taken, 1 on any other trouble.
create_account() {
    local line
    has_key "$HTPASSWD_FILE" "$1" && exit 3
    # A recovery code left by an account of the same name that was removed
    # (by hand, in an older version) must not open this one
    drop_line "$RECOVERY_FILE" "$1"
    touch "$PLAYERS_FILE" 2>/dev/null
    has_key "$PLAYERS_FILE" "$1" && exit 3
    [ -w "$PLAYERS_FILE" ] || exit 1
    line=$(printf '%s\n' "$password" | htpasswd -niB -C 10 "$1" | sed '/^$/d') || exit 1
    [ -n "$line" ] || exit 1
    # Everything checked: write the account and its mark
    printf '%s:%s\n' "$1" "$2" >> "$PLAYERS_FILE" || exit 1
    printf '%s\n' "$line" >> "$HTPASSWD_FILE" || { drop_line "$PLAYERS_FILE" "$1"; exit 1; }
}

# Set the .players mark of account $1 to $2, in place
set_mark() {
    local rest
    rest=$(awk -F: -v user="$1" -v mark="$2" 'BEGIN { OFS = ":" } $1 == user { $2 = mark } { print }' "$PLAYERS_FILE") || return 1
    printf '%s\n' "$rest" > "$PLAYERS_FILE"
}

# Print the world's spelling of nation $1 (any case); fails when there is none
world_nation() {
    /usr/local/bin/conquer-status --nations 2>/dev/null | awk -F'\t' -v n="$1" 'tolower($1) == tolower(n) { print $1; found = 1; exit } END { exit !found }'
}

# Is account $1 waiting for approval?
is_pending() {
    awk -F: -v user="$1" '$1 == user && $2 == "?" { found = 1 } END { exit !found }' "$PLAYERS_FILE" 2>/dev/null
}

cmd="$1"
if [[ "$cmd" =~ ^[A-Z0-9]{4}-[A-Z0-9]{4}$ ]] && [ $# -eq 2 ]; then
    set -- invite "$@"
    cmd=invite
fi

mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null

case "$cmd" in
request)
    account="$2"
    valid_account "$account" || exit 3
    case "$3" in
        en|es|de|pl|pt-br|ru|zh) lang="$3" ;;
        *) lang=en ;;
    esac
    read_password
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        if [ -s "$REQUESTS_FILE" ] && [ "$(wc -l < "$REQUESTS_FILE")" -ge "$MAX_PENDING" ]; then exit 5; fi
        create_account "$account" '?'
        touch "$REQUESTS_FILE" 2>/dev/null
        chmod 640 "$REQUESTS_FILE" 2>/dev/null
        printf '%s\t%s\t%s\n' "$account" "$(date +%s)" "$lang" >> "$REQUESTS_FILE" || {
            drop_line "$PLAYERS_FILE" "$account"
            drop_line "$HTPASSWD_FILE" "$account"
            exit 1
        }
    ) 9> "$LOCK_FILE"
    ;;
invite)
    code="$2" account="$3"
    [ -n "$code" ] && valid_account "$account" || exit 3
    read_password
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        grep -qxF -- "$code" "$INVITES_FILE" 2>/dev/null || exit 2
        [ -w "$INVITES_FILE" ] || exit 1
        create_account "$account" '+'
        drop_line "$INVITES_FILE" "$code" || exit 1
    ) 9> "$LOCK_FILE"
    ;;
approve)
    account="$2"
    valid_account "$account" || exit 2
    (
        flock 9 || exit 1
        is_pending "$account" || exit 2
        set_mark "$account" '+' || exit 1
        drop_line "$REQUESTS_FILE" "$account" "$TAB"
    ) 9> "$LOCK_FILE"
    ;;
reject)
    account="$2"
    valid_account "$account" || exit 2
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        is_pending "$account" || exit 2
        drop_line "$HTPASSWD_FILE" "$account" || exit 1
        drop_line "$PLAYERS_FILE" "$account" || exit 1
        drop_line "$RECOVERY_FILE" "$account"
        drop_line "$REQUESTS_FILE" "$account" "$TAB"
    ) 9> "$LOCK_FILE"
    ;;
assign)
    account="$2" target="$3"
    valid_account "$account" || exit 2
    case "$target" in
        '+'|'*') ;;
        *)
            [[ "$target" =~ ^[A-Za-z0-9_.-]{1,9}$ ]] || exit 6
            nation=$(world_nation "$target") || {
                echo "Nations: $(/usr/local/bin/conquer-status --nations 2>/dev/null | cut -f1 | paste -sd' ')"
                exit 6
            }
            target="$nation"
            ;;
    esac
    (
        flock 9 || exit 1
        has_key "$HTPASSWD_FILE" "$account" || exit 2
        touch "$PLAYERS_FILE" 2>/dev/null
        [ -w "$PLAYERS_FILE" ] || exit 1
        if has_key "$PLAYERS_FILE" "$account"; then
            set_mark "$account" "$target" || exit 1
        else
            printf '%s:%s\n' "$account" "$target" >> "$PLAYERS_FILE" || exit 1
        fi
        drop_line "$REQUESTS_FILE" "$account" "$TAB"
        echo "$target"
    ) 9> "$LOCK_FILE"
    ;;
expire)
    days="$2"
    [[ "$days" =~ ^[0-9]+$ ]] && [ "$days" -ge 1 ] || exit 1
    [ -s "$REQUESTS_FILE" ] || exit 0
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        cutoff=$(( $(date +%s) - days * 86400 ))
        mapfile -t requests < "$REQUESTS_FILE"
        for line in "${requests[@]}"; do
            IFS=$'\t' read -r name since _ <<< "$line"
            [[ "$since" =~ ^[0-9]+$ ]] && [ "$since" -lt "$cutoff" ] && valid_account "$name" || continue
            if is_pending "$name"; then
                drop_line "$HTPASSWD_FILE" "$name" || exit 1
                drop_line "$PLAYERS_FILE" "$name" || exit 1
                drop_line "$RECOVERY_FILE" "$name"
                echo "$name"
            fi
            # Also a request line whose account is no longer waiting
            drop_line "$REQUESTS_FILE" "$name" "$TAB"
        done
    ) 9> "$LOCK_FILE"
    ;;
passwd)
    # Change the password of a signed-in account: needs the current one
    account="$2"
    valid_account "$account" || exit 3
    IFS= read -r current || exit 1
    read_password
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        has_key "$HTPASSWD_FILE" "$account" || exit 3
        printf '%s\n' "$current" | verify_secret "$HTPASSWD_FILE" "$account" || exit 2
        line=$(hash_line "$password" "$account") && [ -n "$line" ] || exit 1
        set_line "$HTPASSWD_FILE" "$account" "$line" || exit 1
    ) 9> "$LOCK_FILE"
    ;;
recovery-init)
    # The first recovery code of an approved account
    account="$2"
    valid_account "$account" || exit 3
    IFS= read -r code || exit 1
    valid_recovery "$code" || exit 1
    (
        flock 9 || exit 1
        has_key "$HTPASSWD_FILE" "$account" || exit 3
        is_pending "$account" && exit 3
        has_key "$RECOVERY_FILE" "$account" && exit 2
        line=$(hash_line "$code" "$account") && [ -n "$line" ] || exit 1
        set_recovery "$account" "$line" || exit 1
    ) 9> "$LOCK_FILE"
    ;;
recovery-renew)
    # A new recovery code (the old one stops working): needs the password
    account="$2"
    valid_account "$account" || exit 3
    IFS= read -r current || exit 1
    IFS= read -r code || exit 1
    valid_recovery "$code" || exit 1
    (
        flock 9 || exit 1
        has_key "$HTPASSWD_FILE" "$account" || exit 3
        printf '%s\n' "$current" | verify_secret "$HTPASSWD_FILE" "$account" || exit 2
        line=$(hash_line "$code" "$account") && [ -n "$line" ] || exit 1
        set_recovery "$account" "$line" || exit 1
    ) 9> "$LOCK_FILE"
    ;;
reset)
    # A new password with the recovery code, and a new code for the next time
    account="$2"
    valid_account "$account" || exit 2
    IFS= read -r code || exit 1
    read_password
    IFS= read -r newcode || exit 1
    valid_recovery "$code" || exit 2
    valid_recovery "$newcode" || exit 1
    [ -w "$HTPASSWD_FILE" ] || exit 5
    (
        flock 9 || exit 1
        if ! has_key "$HTPASSWD_FILE" "$account" || ! has_key "$RECOVERY_FILE" "$account"; then
            # Spend the same time as for a wrong code: no hint whether the account exists
            hash_line "$code" "$account" > /dev/null
            exit 2
        fi
        printf '%s\n' "$code" | verify_secret "$RECOVERY_FILE" "$account" || exit 2
        pwline=$(hash_line "$password" "$account") && [ -n "$pwline" ] || exit 1
        codeline=$(hash_line "$newcode" "$account") && [ -n "$codeline" ] || exit 1
        set_line "$HTPASSWD_FILE" "$account" "$pwline" || exit 1
        set_recovery "$account" "$codeline" || exit 1
    ) 9> "$LOCK_FILE"
    ;;
scrub)
    # Requests of older versions held an email and a message (5 columns:
    # account, time, email, message, language): keep account, time, language
    [ -s "$REQUESTS_FILE" ] || { echo 0; exit 0; }
    (
        flock 9 || exit 1
        changed=$(awk -F'\t' '!(NF == 3) { n++ } END { print n + 0 }' "$REQUESTS_FILE")
        if [ "$changed" -gt 0 ]; then
            rest=$(awk -F'\t' 'BEGIN { OFS = "\t" }
                NF >= 5 { print $1, $2, $5; next }
                NF == 3 { print; next }
                { print $1, $2, "en" }' "$REQUESTS_FILE") || exit 1
            if [ -n "$rest" ]; then printf '%s\n' "$rest" > "$REQUESTS_FILE"; else : > "$REQUESTS_FILE"; fi
        fi
        echo "$changed"
    ) 9> "$LOCK_FILE"
    ;;
invites)
    count="$2"
    [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -ge 1 ] && [ "$count" -le 100 ] || exit 1
    (
        flock 9 || exit 1
        touch "$INVITES_FILE" 2>/dev/null
        chmod 640 "$INVITES_FILE" 2>/dev/null
        [ -w "$INVITES_FILE" ] || exit 1
        for ((i = 0; i < count; i++)); do
            code=$(LC_ALL=C tr -dc 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' < /dev/urandom | head -c 8)
            code="${code:0:4}-${code:4:4}"
            printf '%s\n' "$code" >> "$INVITES_FILE" || exit 1
            echo "$code"
        done
    ) 9> "$LOCK_FILE"
    ;;
*)
    exit 1
    ;;
esac
# conquer-gate logs the result
