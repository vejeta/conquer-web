#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Staging for the end-to-end rehearsal: the local Docker stack (real Apache,
# form login, the gate, ttyd and the game) plus a mail catcher (Mailpit), on a
# throwaway world and a throwaway administrator account whose password is
# made now and kept in tests/e2e/.run.env (never committed).
#
# Usage: tests/e2e/up.sh [--wipe-data]
#
# It refuses to start on top of an existing world in ./data: that may be
# yours. --wipe-data deletes ./data first (after taking the stack down).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f docker-compose.local.yml -f docker-compose.e2e.yml)
SUDO=""
[ "$(id -u)" = 0 ] || { command -v sudo > /dev/null && SUDO="sudo"; }

WIPE=""
for arg in "$@"; do
    case "$arg" in
        --wipe-data) WIPE=1 ;;
        *) echo "usage: $0 [--wipe-data]" >&2; exit 2 ;;
    esac
done

if [ -e data/lib/data ]; then
    if [ -z "$WIPE" ]; then
        echo "data/lib already holds a world. This rehearsal needs a throwaway one." >&2
        echo "Run: $0 --wipe-data   (deletes ./data of this checkout)" >&2
        exit 1
    fi
    "${COMPOSE[@]}" down --remove-orphans 2> /dev/null || true
    $SUDO rm -rf data
fi

[ -f apache/certs/live/conquer.local/fullchain.pem ] || ./setup-local-certs.sh
mkdir -p data/lib data/public data/backups data/auth data/practice

# Administrator of this run: a name and a password made now
E2E_ADMIN_USER="e2eadmin"
E2E_ADMIN_PASSWORD="$(openssl rand -hex 12)"
rm -f data/auth/htpasswd
printf '%s\n' "$E2E_ADMIN_PASSWORD" | ./manage-players.sh add "$E2E_ADMIN_USER" --admin --password-stdin > /dev/null
(umask 077 && cat > tests/e2e/.run.env <<ENV
E2E_BASE_URL=https://localhost
E2E_ADMIN_USER=$E2E_ADMIN_USER
E2E_ADMIN_PASSWORD=$E2E_ADMIN_PASSWORD
E2E_MAILPIT_URL=http://127.0.0.1:8025
E2E_CONTAINER=conquer-local
E2E_STAGING=1
ENV
)

"${COMPOSE[@]}" up -d --build

echo "Waiting for the game container to be healthy"
for _ in $(seq 1 80); do
    status=$(docker inspect -f '{{.State.Health.Status}}' conquer-local 2> /dev/null || true)
    [ "$status" = healthy ] && break
    sleep 3
done
[ "$status" = healthy ] || { "${COMPOSE[@]}" logs --no-color | tail -50; echo "the game container is not healthy" >&2; exit 1; }

echo "Waiting for the mail catcher"
for _ in $(seq 1 30); do
    curl -fsS -o /dev/null http://127.0.0.1:8025/api/v1/info && break
    sleep 2
done
curl -fsS -o /dev/null http://127.0.0.1:8025/api/v1/info

# The world is seeded by now: the administrator may open any nation
$SUDO ./manage-players.sh assign "$E2E_ADMIN_USER" --admin > /dev/null

echo "Staging is up: https://localhost (admin $E2E_ADMIN_USER), mail at http://127.0.0.1:8025"
echo "Run the rehearsal: set -a; . tests/e2e/.run.env; set +a; python3 -m pytest tests/e2e"
