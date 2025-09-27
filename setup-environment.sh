#!/bin/bash
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
    if [[ $domain =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
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

# Setup local environment
setup_local() {
    echo "📋 Setting up LOCAL development environment..."
    echo ""

    # Get username
    read -p "Enter username for local development [dev]: " LOCAL_USER
    LOCAL_USER=${LOCAL_USER:-dev}

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
EOF

    echo "✅ Local environment configured!"
    echo "   URL: https://conquer.local"
    echo "   Username: $LOCAL_USER"
    echo "   Password: $LOCAL_PASS"
    echo ""
}

# Setup production environment
setup_production() {
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
    read -p "Enter username for production access [conquer]: " PROD_USER
    PROD_USER=${PROD_USER:-conquer}

    # Get password or generate one
    read -p "Enter password for production (or press Enter to generate strong password): " PROD_PASS
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

    # Create production.env
    cat > config/production.env << EOF
# Production Environment Configuration
ENVIRONMENT=production
DOMAIN=$PROD_DOMAIN
APACHE_HTTP_PORT=80
APACHE_HTTPS_PORT=443
CERT_TYPE=letsencrypt
CERT_PATH=./apache/certs/live/$PROD_DOMAIN
APACHE_CONFIG=apache/production.conf
DOCKER_COMPOSE_FILE=docker-compose.production.yml

# Let's Encrypt settings
LETSENCRYPT_EMAIL=$PROD_EMAIL
LETSENCRYPT_WEBROOT=/var/lib/letsencrypt
LETSENCRYPT_STAGING=false

# Security settings
TTYD_USERNAME=$PROD_USER
TTYD_PASSWORD=$PROD_PASS
MAX_CLIENTS=$PROD_MAX_CLIENTS
SESSION_TIMEOUT=$PROD_TIMEOUT
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
echo "Which environment would you like to setup?"
echo "1) Local development only"
echo "2) Production only"
echo "3) Both environments"
echo ""
read -p "Choose option (1-3): " CHOICE

case $CHOICE in
    1)
        setup_local
        ;;
    2)
        setup_production
        ;;
    3)
        setup_local
        setup_production
        ;;
    *)
        echo "❌ Invalid choice"
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