#!/bin/bash
set -e

# Load production environment configuration
source config/production.env

echo "🔐 Setting up Let's Encrypt certificates for production"
echo "Domain: $DOMAIN"
echo "Email: $LETSENCRYPT_EMAIL"

# Check if domain is reachable
echo "📋 Checking if domain $DOMAIN is reachable..."
if ! curl -s --connect-timeout 10 "http://$DOMAIN" > /dev/null 2>&1; then
    echo "⚠️  Warning: Domain $DOMAIN is not reachable via HTTP"
    echo "   Make sure:"
    echo "   1. DNS points to this server"
    echo "   2. Firewall allows ports 80 and 443"
    echo "   3. Apache is running on port 80"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Fix domain reachability first."
        exit 1
    fi
fi

# Create certificate directory
mkdir -p "$(dirname "$CERT_PATH")"
mkdir -p "$LETSENCRYPT_WEBROOT"

# Determine staging flag
STAGING_FLAG=""
if [ "$LETSENCRYPT_STAGING" = "true" ]; then
    STAGING_FLAG="--staging"
    echo "🧪 Using Let's Encrypt staging environment"
fi

echo "🚀 Requesting Let's Encrypt certificate..."
echo "   This may take a few moments..."

# Request certificate using webroot method
docker run --rm -it \
  -v "$(pwd)/apache/certs:/etc/letsencrypt" \
  -v "$(pwd)/apache/certs:/var/lib/letsencrypt" \
  -v "$LETSENCRYPT_WEBROOT:$LETSENCRYPT_WEBROOT" \
  certbot/certbot certonly \
  --webroot \
  --webroot-path="$LETSENCRYPT_WEBROOT" \
  -d "$DOMAIN" \
  --agree-tos \
  --no-eff-email \
  --email "$LETSENCRYPT_EMAIL" \
  $STAGING_FLAG

# Reload Apache configuration if container is running
if docker ps --format "table {{.Names}}" | grep -q "apache"; then
    echo "🔄 Reloading Apache configuration..."
    docker exec apache apachectl graceful
fi

echo "✅ Let's Encrypt certificates set up successfully!"
echo "   Certificate: $CERT_PATH/fullchain.pem"
echo "   Private Key: $CERT_PATH/privkey.pem"
echo "   Valid for: 90 days"
echo ""
echo "📅 Set up automatic renewal with:"
echo "   0 2 1 * * /path/to/conquer-web/renew-certs.sh"