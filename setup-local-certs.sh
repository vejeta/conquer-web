#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

# Load local environment configuration
source config/local.env

echo "🔐 Setting up self-signed certificates for local development"
echo "Domain: $DOMAIN"

# Create certificate directory
mkdir -p "$CERT_PATH"

# Generate self-signed certificate
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$CERT_PATH/privkey.pem" \
  -out "$CERT_PATH/fullchain.pem" \
  -days $CERT_DAYS \
  -subj "/C=$CERT_COUNTRY/ST=$CERT_STATE/L=$CERT_CITY/O=$CERT_ORG/CN=$DOMAIN"

# Set proper permissions
chmod 600 "$CERT_PATH/privkey.pem"
chmod 644 "$CERT_PATH/fullchain.pem"

echo "✅ Self-signed certificates created successfully!"
echo "   Certificate: $CERT_PATH/fullchain.pem"
echo "   Private Key: $CERT_PATH/privkey.pem"
echo "   Valid for: $CERT_DAYS days"
echo ""
echo "⚠️  Remember: Browsers will show a security warning for self-signed certificates"
echo "   This is normal for local development - just accept the warning"