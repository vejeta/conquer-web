#!/bin/bash
set -e

# Load production environment configuration
if [ ! -f config/production.env ]; then
    echo "❌ Production environment file not found!"
    echo "🔧 Run './setup-environment.sh' to create environment configuration"
    exit 1
fi

source config/production.env

# Export environment variables for docker-compose
export TTYD_USERNAME TTYD_PASSWORD MAX_CLIENTS SESSION_TIMEOUT

echo "🎮 Starting Conquer Web (Production)"
echo "Domain: $DOMAIN"
echo "Environment: $ENVIRONMENT"
echo ""

# Check if domain resolves to this server
echo "📋 Checking DNS resolution for $DOMAIN..."
if ! nslookup "$DOMAIN" > /dev/null 2>&1; then
    echo "⚠️  Warning: DNS resolution failed for $DOMAIN"
    echo "   Make sure your domain points to this server's IP address"
    echo ""
fi

# Check if certificates exist
if [ ! -f "$CERT_PATH/fullchain.pem" ] || [ ! -f "$CERT_PATH/privkey.pem" ]; then
    echo "📋 Let's Encrypt certificates not found. Setting them up..."
    ./setup-production-certs.sh
fi

# Start services
echo "🚀 Starting Docker containers..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

echo ""
echo "✅ Conquer Web is running in production!"
echo "🌐 Open your browser to: https://$DOMAIN"
echo ""
echo "📋 Useful commands:"
echo "  ./logs.sh          - View container logs"
echo "  ./stop.sh          - Stop all containers"
echo "  ./renew-certs.sh   - Renew Let's Encrypt certificates"
echo "  ./health-check.sh  - Check service status"
echo ""
echo "📅 Don't forget to set up automatic certificate renewal!"
echo "   Add './renew-certs.sh' to your crontab for monthly renewal"