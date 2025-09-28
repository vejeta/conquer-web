#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🚀 Conquer Web VPS Deployment Script"
echo "===================================="
echo ""

# Configuration
PROJECT_DIR="/home/conquer/conquer-web"
APACHE_SITES_DIR="/etc/apache2/sites-available"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_NAME="conquer-web"

# Read configuration from production.env
if [ -f "$PROJECT_DIR/config/production.env" ]; then
    source "$PROJECT_DIR/config/production.env"
    DOMAIN_NAME="$DOMAIN"
    LETSENCRYPT_EMAIL_CONFIG="$LETSENCRYPT_EMAIL"
else
    echo "❌ Production environment not configured"
    echo "   Run first: cd $PROJECT_DIR && ./setup-environment.sh"
    exit 1
fi

# Check if running as root for system configuration
check_privileges() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ This script needs to run as root for system configuration"
        echo "   Run with: sudo $0"
        exit 1
    fi
}

# Check if project directory exists
check_project() {
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Project directory not found: $PROJECT_DIR"
        echo "   Clone the project first:"
        echo "   cd /home/conquer && git clone https://github.com/vejeta/conquer-web.git"
        exit 1
    fi
}

# Check if environment is configured
check_environment() {
    if [ ! -f "$PROJECT_DIR/config/production.env" ]; then
        echo "❌ Production environment not configured"
        echo "   Run first: cd $PROJECT_DIR && ./setup-environment.sh"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    echo "📦 Installing/updating system dependencies..."

    # Update package list
    apt update

    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        echo "   Installing Docker..."
        apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt update
        apt install -y docker-ce docker-ce-cli containerd.io
    fi

    # Install Docker Compose if not present
    if ! command -v docker-compose &> /dev/null; then
        echo "   Installing Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi

    # Install other dependencies
    apt install -y certbot python3-certbot-apache curl

    echo "✅ Dependencies installed"
}

# Configure Apache modules
configure_apache() {
    echo "🔧 Configuring Apache..."

    # Enable required modules
    a2enmod ssl
    a2enmod proxy
    a2enmod proxy_http
    a2enmod proxy_wstunnel
    a2enmod rewrite
    a2enmod headers

    # Add security configuration
    cat > /etc/apache2/conf-available/conquer-security.conf << 'EOF'
# Security configuration for Conquer Web
ServerTokens Prod
ServerSignature Off

# Additional security headers for all sites
Header always unset X-Powered-By
Header always unset Server
EOF

    # Enable security configuration
    a2enconf conquer-security

    echo "✅ Apache modules and security configured"
}

# Setup Apache virtual host
setup_virtual_host() {
    echo "🌐 Setting up Apache virtual host for $DOMAIN_NAME..."

    # Create virtual host configuration from template
    sed "s/DOMAIN_NAME/$DOMAIN_NAME/g" "$PROJECT_DIR/vps/virtualhost.conf.template" > "$APACHE_SITES_DIR/$DOMAIN_NAME.conf"

    # Enable site
    a2ensite "$DOMAIN_NAME"

    # Test configuration
    if apache2ctl configtest; then
        echo "✅ Apache configuration valid"
        systemctl reload apache2
    else
        echo "❌ Apache configuration invalid"
        exit 1
    fi
}

# Setup SSL certificate
setup_ssl() {
    echo "🔒 Setting up SSL certificate for $DOMAIN_NAME..."

    # Check if certificate already exists
    if certbot certificates | grep -q "$DOMAIN_NAME"; then
        echo "✅ SSL certificate already exists"
        return 0
    fi

    echo "   Obtaining Let's Encrypt certificate..."

    # Stop Apache temporarily for standalone authentication
    systemctl stop apache2

    # Get certificate
    if certbot certonly --standalone -d "$DOMAIN_NAME" --email "$LETSENCRYPT_EMAIL_CONFIG" --agree-tos --no-eff-email --non-interactive; then
        echo "✅ SSL certificate obtained"
    else
        echo "❌ Failed to obtain SSL certificate"
        systemctl start apache2
        exit 1
    fi

    # Start Apache
    systemctl start apache2
}

# Build Docker container
build_container() {
    echo "🐳 Building Docker container..."

    cd "$PROJECT_DIR"

    # Source environment variables
    source config/production.env

    # Build container
    docker build -t conquer-game ./conquer

    echo "✅ Docker container built"
}

# Setup systemd service
setup_systemd_service() {
    echo "⚙️  Setting up systemd service..."

    cat > "$SYSTEMD_DIR/$SERVICE_NAME.service" << EOF
[Unit]
Description=Conquer Web Game Server
Documentation=https://github.com/vejeta/conquer-web
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=oneshot
RemainAfterExit=yes
User=conquer
Group=conquer
WorkingDirectory=$PROJECT_DIR

# Environment configuration
Environment=COMPOSE_PROJECT_NAME=conquer-vps
Environment=COMPOSE_FILE=docker-compose.vps.yml
EnvironmentFile=$PROJECT_DIR/config/production.env

# Service commands
ExecStartPre=/bin/bash -c 'cd $PROJECT_DIR && /usr/bin/docker-compose -f docker-compose.vps.yml down || true'
ExecStart=/bin/bash -c 'cd $PROJECT_DIR && /usr/bin/docker-compose -f docker-compose.vps.yml up -d'
ExecStop=/bin/bash -c 'cd $PROJECT_DIR && /usr/bin/docker-compose -f docker-compose.vps.yml down'

# Security settings
NoNewPrivileges=false
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=conquer-web

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    # Enable service
    systemctl enable "$SERVICE_NAME"

    echo "✅ Systemd service configured"
}

# Start services
start_services() {
    echo "🚀 Starting services..."

    # Start Conquer Web service
    systemctl start "$SERVICE_NAME"

    # Wait a moment for startup
    sleep 5

    # Check status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✅ Conquer Web service started"
    else
        echo "❌ Failed to start Conquer Web service"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi

    # Reload Apache to activate virtual host
    systemctl reload apache2

    echo "✅ All services started"
}

# Setup automatic certificate renewal
setup_auto_renewal() {
    echo "📅 Setting up automatic certificate renewal..."

    # Add cron job for certificate renewal
    (crontab -l 2>/dev/null; echo "0 2 * * 0 /usr/bin/certbot renew --apache --quiet") | crontab -

    echo "✅ Automatic certificate renewal configured"
}

# Verify deployment
verify_deployment() {
    echo "🔍 Verifying deployment..."

    # Check Docker container
    if docker ps | grep -q "conquer-vps"; then
        echo "✅ Docker container running"
    else
        echo "❌ Docker container not running"
        docker ps -a | grep conquer-vps
    fi

    # Check Apache
    if systemctl is-active --quiet apache2; then
        echo "✅ Apache running"
    else
        echo "❌ Apache not running"
        systemctl status apache2
    fi

    # Check SSL certificate
    if certbot certificates | grep -q "$DOMAIN_NAME"; then
        echo "✅ SSL certificate valid"
    else
        echo "⚠️  SSL certificate issues"
    fi

    # Test HTTP connection
    if curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN_NAME | grep -q "301"; then
        echo "✅ HTTP redirect working"
    else
        echo "⚠️  HTTP redirect issues"
    fi

    # Test HTTPS connection (if cert is ready)
    if curl -s -k -o /dev/null -w "%{http_code}" https://$DOMAIN_NAME | grep -q "200"; then
        echo "✅ HTTPS connection working"
    else
        echo "⚠️  HTTPS connection issues"
    fi
}

# Show deployment summary
show_summary() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo "======================="
    echo ""
    echo "📋 Service Information:"
    echo "   URL: https://$DOMAIN_NAME"
    echo "   Container: conquer-vps"
    echo "   Service: $SERVICE_NAME"
    echo ""
    echo "🔧 Management Commands:"
    echo "   sudo systemctl status $SERVICE_NAME     # Check status"
    echo "   sudo systemctl restart $SERVICE_NAME    # Restart service"
    echo "   sudo systemctl stop $SERVICE_NAME       # Stop service"
    echo "   docker logs conquer-vps                 # View container logs"
    echo "   sudo journalctl -u $SERVICE_NAME -f     # View service logs"
    echo ""
    echo "📁 Important Paths:"
    echo "   Project: $PROJECT_DIR"
    echo "   Apache config: $APACHE_SITES_DIR/$DOMAIN_NAME.conf"
    echo "   SSL cert: /etc/letsencrypt/live/$DOMAIN_NAME/"
    echo "   Service: $SYSTEMD_DIR/$SERVICE_NAME.service"
    echo ""
    echo "🔒 Security Notes:"
    echo "   - SSL certificate auto-renewal configured"
    echo "   - Container only accessible via localhost"
    echo "   - Security headers configured in Apache"
    echo ""
    echo "📚 Next Steps:"
    echo "   1. Test the game at https://$DOMAIN_NAME"
    echo "   2. Configure firewall if needed"
    echo "   3. Set up monitoring/alerting"
    echo "   4. Create regular backups with: cd $PROJECT_DIR && ./backup-world.sh"
}

# Main execution
main() {
    echo "This script will deploy Conquer Web on your VPS with existing Apache."
    echo ""
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 0
    fi

    check_privileges
    check_project
    check_environment
    install_dependencies
    configure_apache
    setup_virtual_host
    setup_ssl
    build_container
    setup_systemd_service
    start_services
    setup_auto_renewal
    verify_deployment
    show_summary
}

# Run main function
main "$@"