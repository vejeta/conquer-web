#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copy what must never be lost to another machine: the world (nations,
# players' links, invite codes), the web accounts, the settings and the
# Apache virtual host. The copies update-vps.sh and the turn updates keep
# stay on this server, and would be lost with it.
#
# Usage (on the VPS, with sudo):
#   sudo ./offsite-backup.sh                 make a copy and send it now
#   sudo ./offsite-backup.sh --install-cron  send one every day at 04:17
#   sudo ./offsite-backup.sh --remove-cron   stop the daily copies
#   sudo ./offsite-backup.sh --setup-key     make the SSH key the copies use
#   sudo ./offsite-backup.sh --decrypt FILE  decrypt a copy (writes FILE without .enc)
#
# Settings: config/backup.env (see config/backup.env.template)
#   BACKUP_TARGET    where the copies go: user@host:/path (SSH) or a local
#                    directory (another disk, a mounted share)
#   BACKUP_KEEP      how many copies the target keeps (default 30)
#   BACKUP_SSH_KEY   SSH key for the target (default /root/.ssh/conquer-backup)
#   BACKUP_SSH_PORT  SSH port of the target (default 22)
#   BACKUP_PASSWORD_FILE  if set, copies are encrypted with this password
#                    (openssl, AES-256): keep the password somewhere else too
#
# A copy is conquer-<host>-<date>.tar.gz(.enc), with:
#   world.tgz            /opt/conquer/lib of the game, taken while no turn
#                        update runs (restore with restore-world.sh)
#   conquer-web.htpasswd the web accounts
#   production.env       the settings
#   apache/              the virtual host files of the site

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG="${OFFSITE_CONFIG:-$SCRIPT_DIR/config/backup.env}"
SETTINGS="${OFFSITE_SETTINGS:-$SCRIPT_DIR/config/production.env}"
HTPASSWD="${HTPASSWD_FILE:-/etc/apache2/conquer-web.htpasswd}"
APACHE_SITES="${APACHE_SITES:-/etc/apache2/sites-available}"
CONTAINER="${CONTAINER:-conquer-vps}"
LOCAL_DIR="${OFFSITE_LOCAL_DIR:-/root/conquer-backups/offsite}"
CRON_FILE=/etc/cron.d/conquer-offsite-backup
LOG=/var/log/conquer-offsite-backup.log

usage() {
    sed -n '/^# Usage/,/^# A copy is/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
    exit 1
}

[ "$EUID" -eq 0 ] || [ -n "$OFFSITE_TEST" ] || { echo "❌ Run it with sudo"; exit 1; }

BACKUP_TARGET="" BACKUP_KEEP=30 BACKUP_SSH_KEY=/root/.ssh/conquer-backup BACKUP_SSH_PORT=22 BACKUP_PASSWORD_FILE=""
# shellcheck source=/dev/null
[ -f "$CONFIG" ] && . "$CONFIG"

ssh_opts() {
    printf '%s\n' -i "$BACKUP_SSH_KEY" -p "$BACKUP_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new
}

case "${1:-}" in
    --install-cron)
        [ -n "$BACKUP_TARGET" ] || { echo "❌ Set BACKUP_TARGET in $CONFIG first"; exit 1; }
        printf '# Daily copy of the Conquer world and accounts to %s\n17 4 * * * root %s >> %s 2>&1\n' \
            "$BACKUP_TARGET" "$SCRIPT_DIR/offsite-backup.sh" "$LOG" > "$CRON_FILE"
        chmod 644 "$CRON_FILE"
        echo "✅ A copy goes to $BACKUP_TARGET every day at 04:17 (log: $LOG)"
        exit 0 ;;
    --remove-cron)
        rm -f "$CRON_FILE"
        echo "✅ Daily copies stopped"
        exit 0 ;;
    --setup-key)
        if [ ! -f "$BACKUP_SSH_KEY" ]; then
            mkdir -p "$(dirname "$BACKUP_SSH_KEY")"
            ssh-keygen -q -t ed25519 -N "" -C "conquer-backup@$(hostname)" -f "$BACKUP_SSH_KEY"
        fi
        echo "Add this line to ~/.ssh/authorized_keys of the user in BACKUP_TARGET, on the other machine:"
        echo
        cat "$BACKUP_SSH_KEY.pub"
        echo
        echo "Then check it with: sudo $0"
        exit 0 ;;
    --decrypt)
        [ -n "$2" ] && [ -f "$2" ] || usage
        [ -n "$BACKUP_PASSWORD_FILE" ] || { echo "❌ BACKUP_PASSWORD_FILE is not set in $CONFIG"; exit 1; }
        openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$BACKUP_PASSWORD_FILE" \
            -in "$2" -out "${2%.enc}"
        echo "✅ ${2%.enc}"
        exit 0 ;;
    "") ;;
    *) usage ;;
esac

[ -n "$BACKUP_TARGET" ] || { echo "❌ Set BACKUP_TARGET in $CONFIG (see config/backup.env.template)"; exit 1; }
[[ "$BACKUP_KEEP" =~ ^[0-9]+$ ]] && [ "$BACKUP_KEEP" -ge 1 ] || { echo "❌ BACKUP_KEEP must be a number"; exit 1; }

echo "[$(date '+%F %T')] Off-site copy to $BACKUP_TARGET"
DOMAIN=$(sed -n 's/^DOMAIN=//p' "$SETTINGS" 2>/dev/null | tr -d '"'"'"'')
name="conquer-$(hostname -s)-$(date +%Y%m%d-%H%M%S)"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/$name"

# The world, from the game container under the lock of the turn updates, so
# the copy is never taken halfway through one; from data/lib otherwise
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
    docker exec "$CONTAINER" flock /run/conquer/turn.lock tar czf - -C /opt/conquer lib > "$stage/$name/world.tgz"
else
    tar czf "$stage/$name/world.tgz" -C "${OFFSITE_DATA_DIR:-$SCRIPT_DIR/data}" lib
fi
# A copy without the world is worth nothing: stop before sending it
if ! tar tzf "$stage/$name/world.tgz" 2>/dev/null | grep -qx 'lib/nations'; then
    echo "❌ The world was not copied (no lib/nations in it): nothing sent"
    exit 1
fi
[ -f "$HTPASSWD" ] && cp -p "$HTPASSWD" "$stage/$name/conquer-web.htpasswd"
[ -f "$SETTINGS" ] && cp -p "$SETTINGS" "$stage/$name/production.env"
if [ -n "$DOMAIN" ] && compgen -G "$APACHE_SITES/$DOMAIN*.conf" > /dev/null; then
    mkdir "$stage/$name/apache"
    cp -p "$APACHE_SITES/$DOMAIN"*.conf "$stage/$name/apache/"
fi

mkdir -p "$LOCAL_DIR"
chmod 700 "$LOCAL_DIR"
file="$LOCAL_DIR/$name.tar.gz"
tar czf "$file" -C "$stage" "$name"
if [ -n "$BACKUP_PASSWORD_FILE" ]; then
    [ -s "$BACKUP_PASSWORD_FILE" ] || { echo "❌ $BACKUP_PASSWORD_FILE is empty or missing"; exit 1; }
    openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass "file:$BACKUP_PASSWORD_FILE" \
        -in "$file" -out "$file.enc"
    rm -f "$file"
    file="$file.enc"
fi
chmod 600 "$file"
echo "   $(basename "$file") ($(du -h "$file" | cut -f1))"

# Send it, then keep the newest BACKUP_KEEP copies at the target
if [[ "$BACKUP_TARGET" == *:* ]]; then
    host="${BACKUP_TARGET%%:*}" path="${BACKUP_TARGET#*:}"
    mapfile -t opts < <(ssh_opts)
    # shellcheck disable=SC2029  # the path is meant to expand here
    ssh "${opts[@]}" "$host" "mkdir -p '$path'"
    rsync -a -e "ssh ${opts[*]}" "$file" "$BACKUP_TARGET/"
    # shellcheck disable=SC2029
    ssh "${opts[@]}" "$host" "cd '$path' && ls -1t conquer-*.tar.gz* 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | xargs -r rm -f --"
else
    mkdir -p "$BACKUP_TARGET"
    cp -p "$file" "$BACKUP_TARGET/"
    (cd "$BACKUP_TARGET" && find . -maxdepth 1 -name 'conquer-*.tar.gz*' -printf '%T@ %f\n' | sort -rn \
        | tail -n +$((BACKUP_KEEP + 1)) | cut -d' ' -f2- | xargs -r rm -f --)
fi

# Here, the last three are enough
find "$LOCAL_DIR" -maxdepth 1 -name 'conquer-*.tar.gz*' -printf '%T@ %p\n' | sort -rn | tail -n +4 \
    | cut -d' ' -f2- | xargs -r rm -f --
echo "✅ Copy sent to $BACKUP_TARGET (keeping the last $BACKUP_KEEP there)"
