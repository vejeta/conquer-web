#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Update a VPS deployment to the latest code of its branch: the web pages
# and, when the game changed, the game container. Passwords (web accounts,
# nations), the world and config/production.env are kept; a copy of them is
# saved first.
#
#   sudo ./update-vps.sh                 # rebuild the game only if conquer/ changed
#   sudo ./update-vps.sh --rebuild       # always rebuild the game
#   sudo ./update-vps.sh --branch master # follow another branch from now on
#
# The server follows the branch it has checked out. --branch switches it
# once (for example to master after a merge); later updates follow it.
#
# For a first installation use deploy-to-vps.sh.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
SERVICE=conquer-web
PROJECT=conquer-vps          # docker-compose project of the systemd service
CONTAINER=conquer-vps
HTPASSWD=/etc/apache2/conquer-web.htpasswd
REBUILD="" BRANCH=""
while [ $# -gt 0 ]; do
    case "$1" in
        --rebuild) REBUILD=1 ;;
        --branch) [ -n "${2:-}" ] || { echo "❌ --branch needs a branch name"; exit 1; }; BRANCH="$2"; shift ;;
        *) sed -n '/^#   sudo/p' "$0" | sed 's/^# //'; exit 1 ;;
    esac
    shift
done

[ "$EUID" -eq 0 ] || { echo "❌ Run it with sudo"; exit 1; }
[ -f config/production.env ] || { echo "❌ config/production.env missing: this is not a VPS deployment"; exit 1; }
DOMAIN=$(sed -n 's/^DOMAIN=//p' config/production.env | tr -d '"'"'"'')
[ -n "$DOMAIN" ] || { echo "❌ DOMAIN is not set in config/production.env"; exit 1; }
WEB_ROOT="/var/www/$DOMAIN"
OWNER=$(stat -c %U .)
# git as the owner of the checkout (as root it refuses a directory it does not own)
g() { sudo -u "$OWNER" git "$@"; }

# 1. A copy of what must never be lost
BACKUP="/root/conquer-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
chmod 700 /root/conquer-backups
cp -p config/production.env "$BACKUP/"
[ -f "$HTPASSWD" ] && cp -p "$HTPASSWD" "$BACKUP/"
tar czf "$BACKUP/world.tgz" data/lib
echo "✅ Copy of accounts, settings and world in $BACKUP"
# Keep the last 10 copies
find /root/conquer-backups -mindepth 1 -maxdepth 1 -type d | sort | head -n -10 | xargs -r rm -rf

# 2. The code
before=$(g rev-parse HEAD)
current=$(g rev-parse --abbrev-ref HEAD)
if [ -n "$BRANCH" ] && [ "$BRANCH" != "$current" ]; then
    g diff --quiet && g diff --cached --quiet \
        || { echo "❌ The checkout has local changes: commit or undo them before switching branch"; exit 1; }
    g fetch origin "$BRANCH" || { echo "❌ No branch $BRANCH on origin"; exit 1; }
    g checkout -q -B "$BRANCH" --track "origin/$BRANCH"
    echo "✅ Now following $BRANCH (was $current)"
fi
echo "   Branch: $(g rev-parse --abbrev-ref HEAD)"
g pull --ff-only
after=$(g rev-parse HEAD)
if [ "$before" = "$after" ]; then
    echo "✅ Code already up to date ($(g log -1 --format='%h %s'))"
else
    echo "✅ Code updated: $(g log --oneline "$before..$after" | wc -l) new commits"
    g log --oneline "$before..$after" | sed 's/^/     /'
fi

# 3. The game container, when the game changed since the last build this
# script made (a "git pull" run by hand before it does not hide changes)
STATE_DIR=/var/lib/conquer-web
built=$(cat "$STATE_DIR/built-commit" 2>/dev/null || true)
if [ -n "$REBUILD" ] || [ -z "$built" ] || ! g cat-file -e "$built^{commit}" 2>/dev/null \
    || ! g diff --quiet "$built" "$after" -- conquer docker-compose.vps.yml; then
    echo "🐳 Rebuilding the game container..."
    docker-compose -p "$PROJECT" -f docker-compose.vps.yml build --pull conquer
    systemctl restart "$SERVICE"
    mkdir -p "$STATE_DIR"
    echo "$after" > "$STATE_DIR/built-commit"
    echo "✅ Game container rebuilt and restarted"
else
    echo "✅ Game unchanged since the last build ($(g log -1 --format=%h "$built")): container not rebuilt"
fi

# 4. The web pages (the game status in status/ is written by the container)
rsync -a --delete --exclude /status/ web/ "$WEB_ROOT/"
sed -i "s|https://conquer.vejeta.com/|https://$DOMAIN/|g" "$WEB_ROOT/index.html"
chmod -R a+rX "$WEB_ROOT"
echo "✅ Web pages installed in $WEB_ROOT"

# 5. Checks
vhost="/etc/apache2/sites-available/$DOMAIN.conf"
if [ -f "$vhost" ] && ! grep -q 'FilesMatch "\\.(html|js|css|json)' "$vhost"; then
    echo "⚠️  $vhost does not ask browsers to check for new pages (Cache-Control)."
    echo "   Visitors may see old texts after updates: see vps/virtualhost.conf.template"
fi
# The practice game of /try/ runs in WebAssembly, which the site's Content
# Security Policy must allow ('wasm-unsafe-eval'): add it to the policy that
# deploy-to-vps.sh wrote, in every Apache file that has it (certbot copies the
# virtual host into a -le-ssl.conf of its own), keeping the old files if
# Apache does not accept the change
old_csp="script-src 'self' 'unsafe-inline';"
# (only this site's files: other sites on the server are left alone)
csp_files=$(grep -rlF "$old_csp" /etc/apache2/sites-available 2>/dev/null | xargs -r grep -lF "$DOMAIN" || true)
if [ -n "$csp_files" ]; then
    for f in $csp_files; do
        cp "$f" "$f.before-wasm"
        sed -i "s|$old_csp|script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval';|" "$f"
    done
    if apache2ctl configtest >/dev/null 2>&1; then
        systemctl reload apache2
        for f in $csp_files; do rm -f "$f.before-wasm"; done
        echo "✅ The site's security policy now lets the practice game (/try/) run ($(echo "$csp_files" | xargs -n1 basename | tr '\n' ' '))"
    else
        for f in $csp_files; do mv "$f.before-wasm" "$f"; done
        echo "⚠️  Could not allow WebAssembly in the Apache configuration (Apache refused the change): see vps/virtualhost.conf.template"
    fi
fi
sleep 2
if curl -sI "https://$DOMAIN/try/" | grep -i '^content-security-policy' | grep -qv 'wasm-unsafe-eval'; then
    echo "⚠️  https://$DOMAIN/ still blocks WebAssembly: the practice game (/try/) cannot start."
    echo "   Look for the Content-Security-Policy line: grep -r Content-Security-Policy /etc/apache2/"
fi
if [ -f "$vhost" ] && ! grep -q '/join/api/' "$vhost"; then
    echo "⚠️  $vhost does not pass the sign-up page to the game (/join/api/)."
    echo "   Add these lines next to \"ProxyPass /play/\", then: apache2ctl configtest && systemctl reload apache2"
    echo "     ProxyPass /join/api/ http://127.0.0.1:7682/join/api/"
    echo "     ProxyPassReverse /join/api/ http://127.0.0.1:7682/join/api/"
fi
if [ -f "$vhost" ] && ! grep -q '/admin/api/' "$vhost"; then
    echo "⚠️  $vhost does not have the administrator page (/admin/): requests for a seat"
    echo "   cannot be approved from the website. Copy these parts from vps/virtualhost.conf.template"
    echo "   (replace DOMAIN_NAME), then: apache2ctl configtest && systemctl reload apache2"
    echo "     ProxyPass /admin/api/ http://127.0.0.1:7682/admin/api/"
    echo "     ProxyPassReverse /admin/api/ http://127.0.0.1:7682/admin/api/"
    echo "     RedirectMatch permanent ^/admin\$ /admin/"
    echo "     AliasMatch \"^/admin/\$\" \"/var/www/$DOMAIN/admin.html\""
    echo "     the <Location \"/admin/\"> block (before <Location \"/play/\">)"
    echo "   and remove \"admin|\" from the <LocationMatch ...phpmyadmin> list."
fi
# The sign-in page of the site (phase 2 of the join flow): Apache needs these
# modules and a passphrase for the session cookie, and the virtual host the
# form login blocks (vps/virtualhost.conf.template, DEPLOYMENT.md "Login")
SESSION_KEY=/etc/apache2/conquer-web.session
login_missing=""
for m in auth_form session session_cookie session_crypto request; do
    a2query -m "$m" >/dev/null 2>&1 || login_missing="$login_missing $m"
done
if [ -n "$login_missing" ] || [ ! -s "$SESSION_KEY" ]; then
    echo "⚠️  Apache is not ready for the sign-in page (/login.html):"
    [ -n "$login_missing" ] && echo "   missing modules:$login_missing"
    [ -s "$SESSION_KEY" ] || echo "   missing passphrase file $SESSION_KEY"
    echo "   Run, then paste the blocks of DEPLOYMENT.md \"Login\" into $vhost:"
    echo "     sudo a2enmod auth_form session session_cookie session_crypto request"
    echo "     sudo sh -c 'openssl rand -base64 48 > $SESSION_KEY' && sudo chmod 600 $SESSION_KEY"
    echo "     sudo apache2ctl configtest && sudo systemctl reload apache2"
elif [ -f "$vhost" ] && ! grep -q 'AuthType form' "$vhost"; then
    echo "⚠️  $vhost still asks for the password with the browser's window (Basic): it has no sign-in page."
    echo "   Replace the <Location \"/admin/\"> and <Location \"/play/\"> blocks and add /login/do, /login/long and"
    echo "   /logout, as in vps/virtualhost.conf.template (DEPLOYMENT.md \"Login\"), then:"
    echo "     sudo apache2ctl configtest && sudo systemctl reload apache2"
elif [ -f "$vhost" ] && ! grep -q "$SESSION_KEY" "$vhost"; then
    echo "⚠️  $vhost does not use $SESSION_KEY: see DEPLOYMENT.md \"Login\""
else
    echo "✅ Sign-in page configured (form login, passphrase in $SESSION_KEY)"
fi
# Abuse limits in the virtual host (vps/virtualhost.conf.template): the log of
# failed sign-ins that fail2ban reads, and a 64 KB limit on the request bodies
# of the sign-up and administrator APIs. Added to this site's files when they
# are missing, keeping the old files if Apache does not accept the change.
login_block=$(mktemp)
body_block=$(mktemp)
cat > "$login_block" << 'EOF'
    # Failed sign-ins, for fail2ban (vps/fail2ban/): mod_auth_form answers a
    # wrong password with a redirect to /login.html?failed=1
    LogFormat "%h %l - %t \"%r\" %>s \"%{Location}o\"" conquer_login
    SetEnvIf Request_URI "^/login/(do|long)$" conquer_login_post
    CustomLog ${APACHE_LOG_DIR}/conquer_login.log conquer_login env=conquer_login_post
EOF
cat > "$body_block" << 'EOF'
    # Request bodies of the sign-up and administrator APIs
    <Location "/join/api/">
        LimitRequestBody 65536
    </Location>
    <Location "/admin/api/">
        LimitRequestBody 65536
    </Location>

EOF
abuse_files=$(grep -rlF "conquer_ssl_access.log" /etc/apache2/sites-available 2>/dev/null | xargs -r grep -lF "$DOMAIN" || true)
abuse_changed=""
for f in $abuse_files; do
    cp "$f" "$f.before-abuse"
    if ! grep -q 'conquer_login' "$f"; then
        awk -v blk="$login_block" '{ print } /CustomLog .*conquer_ssl_access\.log/ { while ((getline line < blk) > 0) print line; close(blk) }' "$f" > "$f.new" && cat "$f.new" > "$f"
        abuse_changed=1
    fi
    if ! grep -q 'LimitRequestBody 65536' "$f"; then
        if grep -q '<Location "/play/">' "$f"; then
            awk -v blk="$body_block" '/<Location "\/play\/">/ && !done { while ((getline line < blk) > 0) print line; close(blk); done = 1 } { print }' "$f" > "$f.new" && cat "$f.new" > "$f"
            abuse_changed=1
        else
            echo "⚠️  $f has no <Location \"/play/\"> block: add the LimitRequestBody 65536 blocks of vps/virtualhost.conf.template by hand"
        fi
    fi
    rm -f "$f.new"
done
rm -f "$login_block" "$body_block"
if [ -n "$abuse_changed" ]; then
    if apache2ctl configtest > /dev/null 2>&1; then
        systemctl reload apache2
        for f in $abuse_files; do rm -f "$f.before-abuse"; done
        echo "✅ Apache now logs failed sign-ins (conquer_login.log) and limits API request bodies to 64 KB"
    else
        for f in $abuse_files; do mv "$f.before-abuse" "$f"; done
        echo "⚠️  Could not add the sign-in log and body limit (Apache refused the change): see vps/virtualhost.conf.template"
    fi
else
    for f in $abuse_files; do rm -f "$f.before-abuse"; done
    if [ -n "$abuse_files" ]; then echo "✅ Sign-in log and API body limits already in the virtual host"; fi
fi
if [ -z "$abuse_files" ]; then
    echo "⚠️  No virtual host of $DOMAIN logs to conquer_ssl_access.log: copy the conquer_login lines and the LimitRequestBody blocks from vps/virtualhost.conf.template"
fi
# fail2ban with the jail for wrong passwords (ADMIN_IP in config/production.env is never banned)
if ./setup-fail2ban.sh; then :; else echo "⚠️  fail2ban was not set up: sudo ./setup-fail2ban.sh"; fi
sleep 3
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    if docker exec "$CONTAINER" cat /proc/1/cmdline | tr '\0' ' ' | grep -q -- '-H X-WEBAUTH-USER' \
        && docker exec "$CONTAINER" test -x /usr/local/bin/conquer-gate; then
        echo "✅ Game container running"
        if ! docker exec -u conquer "$CONTAINER" conqpasswd -q god >/dev/null 2>&1; then
            echo "⚠️  The god password is not set: sudo ./set-nation-password.sh god"
        fi
    else
        echo "❌ The game container is not the current version: run $0 --rebuild"
    fi
else
    echo "❌ Game container not running: systemctl status $SERVICE"
fi
code=$(curl -s -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0 update-vps' "https://$DOMAIN/")
[ "$code" = 200 ] && echo "✅ https://$DOMAIN/ answers" || echo "❌ https://$DOMAIN/ answers HTTP $code"
echo "Web accounts, nation passwords and the world were not changed."
