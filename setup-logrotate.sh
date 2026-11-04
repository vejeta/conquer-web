#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Keeps the site's Apache logs (conquer_*.log in /var/log/apache2: access,
# error, sign-in and recovery logs; they hold client addresses, user agents
# and URLs) for 7 days: /etc/logrotate.d/conquer-web rotates them daily,
# keeps 7 compressed copies and reloads Apache as Debian's own apache2 rule
# does. Run by deploy-to-vps.sh and update-vps.sh; safe to run again (it
# changes nothing when the files are already right).
#
#   sudo ./setup-logrotate.sh
#
# Debian's /etc/logrotate.d/apache2 rotates every *.log of that directory
# (14 days) and logrotate refuses a file that two rules name, so the
# conquer_* logs are taken out of that rule's pattern (it still rotates every
# other log the same way). Docker's own log rotation of the game container
# is set in the compose files and is not touched.
#
# For tests: LOGROTATE_DIR (default /etc/logrotate.d), LOG_DIR (default
# /var/log/apache2) and SKIP_SERVICE=1 (no root needed).

set -e

LOGROTATE_DIR="${LOGROTATE_DIR:-/etc/logrotate.d}"
LOG_DIR="${LOG_DIR:-/var/log/apache2}"
CHANGED=""

if [ "$EUID" -ne 0 ] && [ -z "$SKIP_SERVICE" ]; then
    echo "❌ Run it with sudo"
    exit 1
fi

# Same reload as Debian's apache2 rule
rule=$(mktemp)
trap 'rm -f "$rule"' EXIT
cat > "$rule" << EOF
# Written by setup-logrotate.sh: the site's Apache logs are kept 7 days
$LOG_DIR/conquer_*.log {
	daily
	rotate 7
	compress
	delaycompress
	missingok
	notifempty
	create 640 root adm
	sharedscripts
	postrotate
		if pgrep -f ^/usr/sbin/apache2 > /dev/null; then
			invoke-rc.d apache2 reload 2>&1 | logger -t apache2.logrotate
		fi
	endscript
}
EOF
if ! cmp -s "$rule" "$LOGROTATE_DIR/conquer-web"; then
    install -D -m 644 "$rule" "$LOGROTATE_DIR/conquer-web"
    CHANGED=1
fi

# Debian's rule for all of Apache's logs must not name the same files
stock="$LOGROTATE_DIR/apache2"
if [ -f "$stock" ] && grep -qxF "$LOG_DIR/*.log {" "$stock"; then
    # every name that does not start with "conquer_"
    prefix="conquer_"
    pattern="$LOG_DIR/[!c]*.log"
    for ((i = 1; i < ${#prefix}; i++)); do
        pattern="$pattern $LOG_DIR/${prefix:0:i}[!${prefix:i:1}]*.log"
    done
    tmp=$(mktemp)
    awk -v from="$LOG_DIR/*.log {" -v to="$pattern {" '$0 == from { print to; next } { print }' "$stock" > "$tmp"
    cat "$tmp" > "$stock"
    rm -f "$tmp"
    CHANGED=1
fi

echo "✅ Apache logs of the site are kept 7 days ($LOGROTATE_DIR/conquer-web)${CHANGED:+ (changed)}"
