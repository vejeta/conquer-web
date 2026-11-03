#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Take the staging stack down (tests/e2e/up.sh). The world and accounts stay
# in ./data until you pass --wipe-data.
#
# Usage: tests/e2e/down.sh [--wipe-data]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
SUDO=""
[ "$(id -u)" = 0 ] || { command -v sudo > /dev/null && SUDO="sudo"; }

docker compose -f docker-compose.local.yml -f docker-compose.e2e.yml down --remove-orphans
rm -f tests/e2e/.run.env
if [ "${1:-}" = "--wipe-data" ]; then
    $SUDO rm -rf data
    echo "Throwaway world and accounts deleted."
fi
