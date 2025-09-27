#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

# Detect environment and load appropriate config
if [ -f "config/production.env" ]; then
    source config/production.env
    echo "🔄 Renewing certificates for production environment"
elif [ -f "config/local.env" ]; then
    source config/local.env
    echo "🔄 Certificates renewal not needed for local development (self-signed)"
    exit 0
else
    echo "❌ No environment configuration found!"
    exit 1
fi

echo "Domain: $DOMAIN"
echo "Cert type: $CERT_TYPE"

# Only renew if using Let's Encrypt
if [ "$CERT_TYPE" != "letsencrypt" ]; then
    echo "ℹ️  Certificate type is not Let's Encrypt, skipping renewal"
    exit 0
fi

# Check if certificates exist
if [ ! -f "$CERT_PATH/fullchain.pem" ]; then
    echo "❌ No certificates found. Run setup-production-certs.sh first"
    exit 1
fi

# Check certificate expiration (renew if less than 30 days remaining)
if openssl x509 -checkend 2592000 -noout -in "$CERT_PATH/fullchain.pem" > /dev/null 2>&1; then
    echo "✅ Certificate is still valid for more than 30 days, no renewal needed"
    exit 0
fi

echo "🔄 Certificate expires soon, renewing..."

# Create webroot directory if it doesn't exist
mkdir -p "$LETSENCRYPT_WEBROOT"

# Renew certificate
docker run --rm \
  -v "$(pwd)/apache/certs:/etc/letsencrypt" \
  -v "$(pwd)/apache/certs:/var/lib/letsencrypt" \
  -v "$LETSENCRYPT_WEBROOT:$LETSENCRYPT_WEBROOT" \
  certbot/certbot renew \
  --webroot \
  --webroot-path="$LETSENCRYPT_WEBROOT"

# Reload Apache if container is running
if docker ps --format "table {{.Names}}" | grep -q "apache"; then
    echo "🔄 Reloading Apache configuration..."
    docker exec apache apachectl graceful
    echo "✅ Apache reloaded successfully"
fi

echo "✅ Certificate renewal completed!"
