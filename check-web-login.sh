#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Give a web account a new generated password and test the whole login path
# of a VPS deployment: the account file, Apache and the game's terminal
# (ttyd). Says which of them rejects the login.
#
#   sudo ./check-web-login.sh [ACCOUNT]      (default: conquer)
#
# The password is only shown at the end, on this terminal.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NAME="${1:-conquer}"
CONTAINER=conquer-vps
DOMAIN=""
[ -f "$SCRIPT_DIR/config/production.env" ] && DOMAIN=$(sed -n 's/^DOMAIN=//p' "$SCRIPT_DIR/config/production.env" | tr -d '"'"'"'')
DOMAIN="${DOMAIN:-conquer.vejeta.com}"
VHOST="/etc/apache2/sites-enabled/$DOMAIN.conf"
ERROR_LOG="/var/log/apache2/conquer_ssl_error.log"

ok() { echo "✅ $*"; }
bad() { echo "❌ $*"; }
info() { echo "   $*"; }

[ "$EUID" -eq 0 ] || { bad "Run it with sudo"; exit 1; }
command -v htpasswd >/dev/null || { bad "htpasswd missing: apt install apache2-utils"; exit 1; }

# 1. The account file Apache checks for /play/
echo "== 1. Account file"
if [ ! -f "$VHOST" ]; then
    bad "No virtual host $VHOST: run deploy-to-vps.sh"
    exit 1
fi
FILE=$(sed -n 's/^[[:space:]]*AuthUserFile[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}.*/\1/p' "$VHOST" | head -1)
[ -n "$FILE" ] || { bad "The virtual host has no AuthUserFile"; exit 1; }
info "Apache checks $FILE"
others=$(grep -rn '^[[:space:]]*AuthUserFile' /etc/apache2/sites-enabled /etc/apache2/conf-enabled 2>/dev/null | grep -v "$FILE")
if [ -n "$others" ]; then
    info "Other account files in the enabled configuration (they may also ask for a password):"
    echo "$others" | sed 's/^/     /'
fi

# 2. A new password, saved and checked in that file
echo "== 2. New password for '$NAME'"
PASSWORD=$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-14)
if ! printf '%s\n' "$PASSWORD" | HTPASSWD_FILE="$FILE" "$SCRIPT_DIR/manage-players.sh" add "$NAME" --password-stdin >/dev/null; then
    bad "manage-players.sh could not save it"
    exit 1
fi
if htpasswd -vb "$FILE" "$NAME" "$PASSWORD" >/dev/null 2>&1; then
    ok "Saved in $FILE and checked"
else
    bad "The file does not accept the new password"
    exit 1
fi
if sudo -u www-data test -r "$FILE"; then
    ok "Apache (www-data) can read it"
else
    bad "Apache (www-data) cannot read it: chgrp www-data $FILE; chmod 640 $FILE"
fi

# 3. Apache, asked on this server with the site's name
echo "== 3. Apache (https://$DOMAIN/play/)"
before=$(wc -l < "$ERROR_LOG" 2>/dev/null || echo 0)
code=$(printf 'user = "%s:%s"\n' "$NAME" "$PASSWORD" | curl -s -K - -o /dev/null -w '%{http_code}' \
    --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/play/")
sleep 1
news=$(tail -n +"$((before + 1))" "$ERROR_LOG" 2>/dev/null | grep -i 'auth' | tail -3)
case "$code" in
    200) ok "Login accepted (HTTP 200)" ;;
    401)
        if [ -n "$news" ]; then
            bad "Apache rejects the password (HTTP 401):"
            echo "$news" | sed 's/^/     /'
        else
            bad "HTTP 401, but Apache logged no failure: the game terminal behind it rejected the login (see 4)"
        fi ;;
    000) bad "No answer from Apache on 127.0.0.1:443" ;;
    *) bad "HTTP $code" ;;
esac

# 4. The game's terminal (ttyd) behind Apache
echo "== 4. Game terminal (ttyd on 127.0.0.1:7681)"
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    bad "Container $CONTAINER not running. Running containers:"
    docker ps --format '     {{.Names}}  {{.Image}}  {{.Status}}'
else
    info "$(docker ps --filter "name=^$CONTAINER\$" --format 'Image {{.Image}}, created {{.CreatedAt}}, {{.Status}}')"
    args=$(docker exec "$CONTAINER" cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ')
    if echo "$args" | grep -q -- ' -c '; then
        bad "ttyd has its own password (-c): this is the old container. Rebuild it:"
        info "  docker-compose -f docker-compose.vps.yml up -d --build"
    elif echo "$args" | grep -q -- '-H X-WEBAUTH-USER'; then
        ok "ttyd trusts Apache's login (-H X-WEBAUTH-USER)"
    else
        info "ttyd command: ${args:-unknown}"
    fi
    code=$(curl -s -o /dev/null -w '%{http_code}' -H "X-WEBAUTH-USER: $NAME" http://127.0.0.1:7681/play/)
    [ "$code" = 200 ] && ok "ttyd answers /play/ (HTTP 200)" || bad "ttyd answers /play/ with HTTP $code"
fi

echo
echo "🔑 Password for '$NAME': $PASSWORD"
echo "   Keep it; do not paste it anywhere. Try it in a private browser window."
echo "   If fail2ban blocked you: fail2ban-client set apache-auth-conquer unbanip <your IP>"
