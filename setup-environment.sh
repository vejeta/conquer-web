#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🔧 Conquer Web Environment Setup"
echo "================================"
echo ""

# Function to generate a random password
generate_password() {
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16
}

# Function to validate domain
validate_domain() {
    local domain=$1
    # Allow subdomains: conquer.vejeta.com, example.com, sub.example.co.uk
    if [[ $domain =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate email
validate_email() {
    local email=$1
    if [[ $email =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}

# uid for the game user in the container: the invoking user, never root
game_uid() {
    local uid
    uid=$(id -u)
    if [ "$uid" = 0 ]; then
        uid=${SUDO_UID:-1000}
    fi
    echo "$uid"
}

# Turn update settings shared by both environments
turn_settings() {
    cat << 'SETTINGS'

# Turn updates (cron format: minute hour day-of-month month day-of-week)
# Weekly on Sundays at 20:00 while players learn the game.
# Daily at 20:00 would be "0 20 * * *". Use "off" to disable.
TZ=UTC
TURN_SCHEDULE="0 20 * * 0"
# Human-readable schedule shown to players in the game menu
TURN_SCHEDULE_LABEL="Weekly, Sundays at 20:00 UTC"
# The update waits while players are logged in: retry interval and attempts
TURN_RETRY_MINUTES=10
TURN_MAX_RETRIES=18

# Before a turn update, players still in the game are warned and, after this
# many minutes, disconnected (the game saves their orders)
TURN_GRACE_MINUTES=5
# World backups kept in data/backups (taken before every turn; 0 disables)
TURN_BACKUPS=10
# Optional webhook notified after every turn update (Slack, Mattermost, Discord)
TURN_WEBHOOK_URL=
# Run the turn update early once every player nation has marked its orders
# as done in the game menu (on/off); the schedule still applies as deadline
TURN_EARLY=on
# Sign-up with invite codes on the site (signup.html; codes are made with
# ./manage-players.sh invite): on/off
SIGNUP=on

# Terminal font size in the browser
TTYD_FONT_SIZE=16
SETTINGS
}

# Setup local environment
setup_local() {
    echo "📋 Setting up LOCAL development environment..."
    echo ""

    # Get username
    read -p "Enter username for local development: " LOCAL_USER
    while [ -z "$LOCAL_USER" ]; do
        read -p "Username cannot be empty. Enter username: " LOCAL_USER
    done

    # Get password or generate one
    read -p "Enter password for local development (or press Enter to generate): " LOCAL_PASS
    if [ -z "$LOCAL_PASS" ]; then
        LOCAL_PASS=$(generate_password)
        echo "Generated password: $LOCAL_PASS"
    fi

    # Get max clients
    read -p "Maximum concurrent users for local [10]: " LOCAL_MAX_CLIENTS
    LOCAL_MAX_CLIENTS=${LOCAL_MAX_CLIENTS:-10}

    # Create local.env
    cat > config/local.env << EOF
# Local Development Environment Configuration
ENVIRONMENT=local
DOMAIN=conquer.local
APACHE_HTTP_PORT=80
APACHE_HTTPS_PORT=443
CERT_TYPE=selfsigned
CERT_PATH=./apache/certs/live/conquer.local
APACHE_CONFIG=apache/local.conf
DOCKER_COMPOSE_FILE=docker-compose.local.yml

# Self-signed certificate settings
CERT_COUNTRY=US
CERT_STATE=CA
CERT_CITY="San Francisco"
CERT_ORG="Local Development"
CERT_DAYS=365

# Security settings
TTYD_USERNAME=$LOCAL_USER
TTYD_PASSWORD=$LOCAL_PASS
MAX_CLIENTS=$LOCAL_MAX_CLIENTS
SESSION_TIMEOUT=3600

# Shown to players in the menu under "How to join"
ADMIN_CONTACT=
$(turn_settings)

# uid the game runs as inside the container (owner of data/ on this host)
CONQUER_UID=$(game_uid)
EOF

    echo "✅ Local environment configured!"
    echo "   URL: https://conquer.local"
    echo "   Username: $LOCAL_USER"
    echo "   Password: $LOCAL_PASS"
    echo ""
}

# Setup production environment
setup_vps_production() {
    echo "📋 Setting up PRODUCTION environment..."
    echo ""

    # Get domain
    while true; do
        read -p "Enter your production domain (e.g., game.example.com): " PROD_DOMAIN
        if validate_domain "$PROD_DOMAIN"; then
            break
        else
            echo "❌ Invalid domain format. Please try again."
        fi
    done

    # Get email
    while true; do
        read -p "Enter email for Let's Encrypt certificates: " PROD_EMAIL
        if validate_email "$PROD_EMAIL"; then
            break
        else
            echo "❌ Invalid email format. Please try again."
        fi
    done

    # Get username
    read -p "Enter username for production access (avoid common names like 'admin'): " PROD_USER
    while [ -z "$PROD_USER" ] || [ "$PROD_USER" = "admin" ] || [ "$PROD_USER" = "user" ] || [ "$PROD_USER" = "conquer" ]; do
        echo "⚠️  Please choose a unique, non-default username"
        read -p "Enter username for production access: " PROD_USER
    done

    # Get password or generate one
    read -p "Enter STRONG password for production (or press Enter to generate one): " PROD_PASS
    if [ -z "$PROD_PASS" ]; then
        PROD_PASS=$(generate_password)
        echo "Generated strong password: $PROD_PASS"
    fi

    # Get max clients
    read -p "Maximum concurrent users for production [5]: " PROD_MAX_CLIENTS
    PROD_MAX_CLIENTS=${PROD_MAX_CLIENTS:-5}

    # Get session timeout
    read -p "Session timeout in seconds [1800]: " PROD_TIMEOUT
    PROD_TIMEOUT=${PROD_TIMEOUT:-1800}

    # Contact shown to players who want a nation
    read -p "Administrator contact shown to players (e.g. email, optional): " PROD_CONTACT

    # Create production.env
    cat > config/production.env << EOF
# Production Environment Configuration
ENVIRONMENT=production
DOMAIN=$PROD_DOMAIN
APACHE_HTTP_PORT=80
APACHE_HTTPS_PORT=443
CERT_TYPE=letsencrypt
CERT_PATH=./apache/certs/live/$PROD_DOMAIN
APACHE_CONFIG=vps/virtualhost.conf.template
DOCKER_COMPOSE_FILE=docker-compose.vps.yml

# Let's Encrypt settings
LETSENCRYPT_EMAIL=$PROD_EMAIL
LETSENCRYPT_WEBROOT=/var/lib/letsencrypt
LETSENCRYPT_STAGING=false

# Security settings
TTYD_USERNAME=$PROD_USER
TTYD_PASSWORD=$PROD_PASS
MAX_CLIENTS=$PROD_MAX_CLIENTS
SESSION_TIMEOUT=$PROD_TIMEOUT

# Shown to players in the menu under "How to join"
ADMIN_CONTACT="$PROD_CONTACT"
$(turn_settings)

# uid the game runs as inside the container (owner of data/ on this host)
CONQUER_UID=$(game_uid)
EOF

    echo "✅ Production environment configured!"
    echo "   URL: https://$PROD_DOMAIN"
    echo "   Username: $PROD_USER"
    echo "   Password: $PROD_PASS"
    echo "   Email: $PROD_EMAIL"
    echo ""
    echo "⚠️  IMPORTANT: Save these credentials securely!"
    echo ""
}

# Main menu
echo "🔧 Choose your deployment type:"
echo "1) Local development (Docker Apache + Conquer containers)"
echo "2) VPS production (Host Apache + Conquer container)"
echo ""
read -p "Choose option (1-2): " CHOICE

case $CHOICE in
    1)
        setup_local
        ;;
    2)
        setup_vps_production
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo "🎯 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   - Run './start-local.sh' for local development"
echo "   - Run './start-production.sh' for production deployment"
echo "   - Check './health-check.sh' to verify everything works"
echo ""
echo "🔐 Security reminders:"
echo "   - Environment files are excluded from git"
echo "   - Change passwords regularly"
echo "   - Keep backup of production credentials"
echo "   - Set up certificate renewal cron job for production"