#!/bin/bash
set -e

# Load local environment configuration
source config/local.env

echo "🎮 Starting Conquer Web (Local Development)"
echo "Domain: $DOMAIN"
echo "Environment: $ENVIRONMENT"
echo ""

# Ensure we have self-signed certificates
if [ ! -f "$CERT_PATH/fullchain.pem" ] || [ ! -f "$CERT_PATH/privkey.pem" ]; then
    echo "📋 Self-signed certificates not found. Generating them..."
    ./setup-local-certs.sh
fi

# Add domain to /etc/hosts if not present
if ! grep -q "127.0.0.1.*$DOMAIN" /etc/hosts; then
    echo "📋 Adding $DOMAIN to /etc/hosts (requires sudo)"
    echo "127.0.0.1   $DOMAIN" | sudo tee -a /etc/hosts
fi

# Start services
echo "🚀 Starting Docker containers..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

echo ""
echo "✅ Conquer Web is running locally!"
echo "🌐 Open your browser to: https://$DOMAIN"
echo "⚠️  You'll need to accept the self-signed certificate warning"
echo ""
echo "📋 Useful commands:"
echo "  ./logs.sh          - View container logs"
echo "  ./stop.sh          - Stop all containers"
echo "  ./health-check.sh  - Check service status"