#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Installs fail2ban with a jail for wrong passwords on the site's sign-in form
# (vps/fail2ban/): 8 failures in 10 minutes ban an address for 1 hour, and a
# jail for wrong recovery codes and wrong current passwords at the account
# pages: 5 failures in 1 hour ban an address for 1 hour.
# Run by deploy-to-vps.sh and update-vps.sh; safe to run again (it changes
# nothing, and does not restart fail2ban, when the files are already right).
#
#   sudo ./setup-fail2ban.sh
#   sudo ADMIN_IP=203.0.113.7 ./setup-fail2ban.sh    # an address that is never banned
#
# ADMIN_IP can also be set in config/production.env. 127.0.0.1/8 is never banned.
# It also removes the apache-dos-conquer jail that older versions of
# setup-security.sh installed: it counted every page and asset, and banned
# real players behind a shared address.
#
# For tests: F2B_DIR (default /etc/fail2ban), LOG_DIR (default
# /var/log/apache2), SKIP_APT=1 and SKIP_SERVICE=1 skip the system parts.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
F2B_DIR="${F2B_DIR:-/etc/fail2ban}"
LOG_DIR="${LOG_DIR:-/var/log/apache2}"
CHANGED=""

if [ "$EUID" -ne 0 ] && [ -z "$SKIP_SERVICE" ]; then
    echo "❌ Run it with sudo"
    exit 1
fi

# The address that is never banned: the environment, else production.env
ADMIN_IP="${ADMIN_IP:-}"
if [ -z "$ADMIN_IP" ] && [ -f "$SCRIPT_DIR/config/production.env" ]; then
    ADMIN_IP=$(sed -n 's/^ADMIN_IP=//p' "$SCRIPT_DIR/config/production.env" | tail -n 1 | tr -d "\"'")
fi
IGNORE_IPS="127.0.0.1/8 ::1"
if [ -n "$ADMIN_IP" ]; then
    # Only addresses and networks: the value goes into a configuration file
    if [[ "$ADMIN_IP" =~ ^[0-9a-fA-F:.]+(/[0-9]{1,3})?$ ]]; then
        IGNORE_IPS="$IGNORE_IPS $ADMIN_IP"
    else
        echo "❌ ADMIN_IP='$ADMIN_IP' is not an address (203.0.113.7 or 203.0.113.0/24)"
        exit 1
    fi
fi

if [ -z "$SKIP_APT" ] && ! command -v fail2ban-client > /dev/null 2>&1; then
    echo "📦 Installing fail2ban..."
    apt-get update
    apt-get install -y fail2ban
fi

# install_file SOURCE DEST: copy when different, remember that something changed
install_file() {
    if ! cmp -s "$1" "$2" 2> /dev/null; then
        install -D -m 644 "$1" "$2"
        CHANGED=1
    fi
}

jail=$(mktemp)
trap 'rm -f "$jail"' EXIT
for name in conquer-login conquer-recover; do
    install_file "$SCRIPT_DIR/vps/fail2ban/$name.conf" "$F2B_DIR/filter.d/$name.conf"
    sed "s|IGNORE_IPS|$IGNORE_IPS|" "$SCRIPT_DIR/vps/fail2ban/$name.jail" > "$jail"
    install_file "$jail" "$F2B_DIR/jail.d/$name.local"
done

# fail2ban refuses a jail whose log does not exist yet; Apache makes it at
# its first sign-in (or recovery attempt), so make it empty, as Apache would
for log in conquer_login.log conquer_recover.log; do
    if [ -d "$LOG_DIR" ] && [ ! -e "$LOG_DIR/$log" ]; then
        install -m 640 /dev/null "$LOG_DIR/$log"
        chgrp adm "$LOG_DIR/$log" 2> /dev/null || true
    fi
done

# The old request-counting jail of setup-security.sh
if [ -f "$F2B_DIR/filter.d/apache-dos-conquer.conf" ]; then
    rm -f "$F2B_DIR/filter.d/apache-dos-conquer.conf"
    CHANGED=1
fi
old="$F2B_DIR/jail.d/conquer-web.conf"
if [ -f "$old" ] && grep -q '^\[apache-dos-conquer\]' "$old"; then
    awk '/^\[/ { skip = ($0 == "[apache-dos-conquer]") } !skip' "$old" > "$jail"
    cat "$jail" > "$old"
    CHANGED=1
fi

if [ -z "$SKIP_SERVICE" ]; then
    systemctl enable fail2ban > /dev/null 2>&1 || true
    if ! fail2ban-client -t > /dev/null 2>&1; then
        echo "❌ fail2ban does not accept its configuration: sudo fail2ban-client -t"
        exit 1
    fi
    if [ -n "$CHANGED" ] || ! systemctl is-active --quiet fail2ban; then
        systemctl restart fail2ban
    fi
    # The jails need the logs of the virtual host
    if fail2ban-client status conquer-login > /dev/null 2>&1; then
        echo "✅ fail2ban: jail conquer-login active (8 failed sign-ins in 10 minutes: 1 hour ban; never banned: $IGNORE_IPS)"
    else
        echo "⚠️  fail2ban runs but the jail conquer-login does not: sudo fail2ban-client status; sudo tail /var/log/fail2ban.log"
    fi
    if fail2ban-client status conquer-recover > /dev/null 2>&1; then
        echo "✅ fail2ban: jail conquer-recover active (5 wrong recovery codes or passwords in 1 hour: 1 hour ban)"
    else
        echo "⚠️  fail2ban runs but the jail conquer-recover does not: sudo fail2ban-client status; sudo tail /var/log/fail2ban.log"
    fi
else
    echo "✅ fail2ban files ready in $F2B_DIR${CHANGED:+ (changed)}"
fi
