#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Generate a self-signed certificate for local development.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="${DOMAIN:-conquer.local}"
CERT_DIR="$SCRIPT_DIR/apache/certs/live/$DOMAIN"

if ! command -v openssl >/dev/null 2>&1; then
    echo "❌ openssl is required to generate certificates"
    exit 1
fi

mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -newkey rsa:2048 -days "${CERT_DAYS:-365}" \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1" \
    -addext "basicConstraints=critical,CA:FALSE"

chmod 600 "$CERT_DIR/privkey.pem"
echo "✅ Self-signed certificate created in $CERT_DIR"
