#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Set the in-game password of a nation, god's included, without knowing
# the old one (a forgotten god password locks the administrator out).
#
#   ./set-nation-password.sh god
#   ./set-nation-password.sh sahara
#   ./set-nation-password.sh god --if-locked   (only if none is set yet:
#                                               worlds from this repository
#                                               ship with god locked)
#
# This is the nation's password inside the game. Web accounts (the
# password asked by the site) are managed with manage-players.sh.

set -e

NATION="$1"
if [ -z "$NATION" ] || { [ -n "$2" ] && [ "$2" != --if-locked ]; }; then
    echo "Usage: $0 NATION [--if-locked]   (god for the game administrator)"
    exit 1
fi

CONTAINER=""
for name in conquer-vps conquer-local; do
    if docker ps --format '{{.Names}}' | grep -qx "$name"; then
        CONTAINER="$name"
        break
    fi
done
if [ -z "$CONTAINER" ]; then
    echo "❌ No running Conquer container found (conquer-vps or conquer-local)"
    exit 1
fi

if [ "$2" = --if-locked ] && docker exec -u conquer "$CONTAINER" conqpasswd -q "$NATION" >/dev/null 2>&1; then
    echo "✅ The password of $NATION is already set"
    exit 0
fi
[ "$NATION" = god ] && echo "The god password opens every nation of the game: make it hard to guess."
echo "Conquer keeps at most 7 characters of a password (god needs at least 4)."
read -r -s -p "New password for $NATION: " password; echo
read -r -s -p "Repeat it: " password2; echo
if [ "$password" != "$password2" ]; then
    echo "❌ The passwords do not match"
    exit 1
fi

# The password goes through standard input, never on a command line
printf '%s\n' "$password" | docker exec -i -u conquer "$CONTAINER" conqpasswd "$NATION"
