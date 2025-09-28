#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🛡️ Conquer Web Basic Security Setup"
echo "===================================="
echo ""
echo "This script sets up basic security with proven configurations."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root"
    echo "   Run with: sudo $0"
    exit 1
fi

# Read domain from production config if available
PROJECT_DIR="/home/conquer/conquer-web"
if [ -f "$PROJECT_DIR/config/production.env" ]; then
    source "$PROJECT_DIR/config/production.env"
    DOMAIN_NAME="$DOMAIN"
else
    echo "⚠️  Production environment not found. Using generic configuration."
    DOMAIN_NAME="your-domain"
fi

echo "🔍 Configuring basic security for domain: $DOMAIN_NAME"
echo ""

# Install fail2ban
echo "📦 Installing fail2ban..."
apt update
apt install -y fail2ban

# Create basic fail2ban configuration using standard filters
echo "🔧 Configuring fail2ban with standard filters..."
cat > /etc/fail2ban/jail.d/conquer-web-basic.conf << EOF
# Conquer Web basic fail2ban configuration
# Uses only standard filters to avoid compatibility issues

[apache-auth]
enabled = true
port = http,https
filter = apache-auth
logpath = /var/log/apache2/conquer_*_error.log
maxretry = 3
bantime = 3600
findtime = 600

[apache-badbots]
enabled = true
port = http,https
filter = apache-badbots
logpath = /var/log/apache2/conquer_*_access.log
maxretry = 2
bantime = 86400
findtime = 600

[apache-noscript]
enabled = true
port = http,https
filter = apache-noscript
logpath = /var/log/apache2/conquer_*_access.log
maxretry = 6
bantime = 86400
findtime = 600
EOF

# Enable and start fail2ban
echo "🚀 Starting fail2ban service..."
systemctl enable fail2ban
systemctl restart fail2ban

# Install logwatch
echo "📊 Installing logwatch..."
apt install -y logwatch

# Create basic Apache security configuration
echo "🔒 Adding basic Apache security headers..."
cat > /etc/apache2/conf-available/conquer-security-basic.conf << 'EOF'
# Basic security configuration for Conquer Web

# Security headers
Header always set X-Frame-Options DENY
Header always set X-Content-Type-Options nosniff
Header always set X-XSS-Protection "1; mode=block"
Header always set Referrer-Policy "strict-origin-when-cross-origin"

# Hide server information
Header always unset X-Powered-By
Header always unset Server
ServerTokens Prod

# Block common attack paths
<LocationMatch "(\.php|\.asp|\.jsp|wp-admin|phpmyadmin)">
    Require all denied
</LocationMatch>
EOF

# Enable the basic security configuration
a2enconf conquer-security-basic

# Test configurations
echo "🧪 Testing configurations..."

# Test fail2ban
echo "Testing fail2ban..."
if fail2ban-client -t; then
    echo "✅ fail2ban configuration is valid"
else
    echo "❌ fail2ban configuration has errors"
    echo "Checking standard filters availability:"
    ls -la /etc/fail2ban/filter.d/apache-*.conf
    exit 1
fi

# Test Apache
echo "Testing Apache..."
if apache2ctl configtest; then
    echo "✅ Apache configuration is valid"
    systemctl reload apache2
else
    echo "❌ Apache configuration has errors"
    exit 1
fi

# Create basic monitoring script
echo "📝 Creating basic security monitoring script..."
cat > "$PROJECT_DIR/check-security-basic.sh" << 'EOF'
#!/bin/bash
# Basic security status check

echo "🛡️ Basic Security Status"
echo "========================"
echo ""

# Check fail2ban status
echo "📊 fail2ban Status:"
sudo fail2ban-client status

echo ""
echo "🚫 Currently Banned IPs:"
for jail in apache-auth apache-badbots apache-noscript; do
    if sudo fail2ban-client status "$jail" 2>/dev/null | grep -q "Banned IP list"; then
        echo "Jail: $jail"
        sudo fail2ban-client status "$jail" | grep "Banned IP list"
    fi
done

echo ""
echo "📈 Recent Failed Authentication Attempts:"
sudo grep "401" /var/log/apache2/conquer_*_access.log 2>/dev/null | tail -5 || echo "No recent failures found"

echo ""
echo "💾 System Status:"
df -h / | tail -1
uptime
EOF

chmod +x "$PROJECT_DIR/check-security-basic.sh"
chown conquer:conquer "$PROJECT_DIR/check-security-basic.sh"

echo ""
echo "🎉 Basic security setup completed successfully!"
echo ""
echo "📋 What was configured:"
echo "   ✅ fail2ban with standard Apache filters"
echo "   ✅ Basic Apache security headers"
echo "   ✅ Attack path blocking"
echo "   ✅ Log monitoring with logwatch"
echo "   ✅ Basic security monitoring script"
echo ""
echo "🔧 Management Commands:"
echo "   sudo fail2ban-client status                    # Check status"
echo "   sudo fail2ban-client status apache-auth        # Check auth bans"
echo "   cd $PROJECT_DIR && ./check-security-basic.sh   # Run security check"
echo "   sudo tail -f /var/log/fail2ban.log            # Monitor bans"
echo ""
echo "🔒 Protection enabled against:"
echo "   - Brute force authentication attacks"
echo "   - Bad bots and crawlers"
echo "   - Script injection attempts"
echo "   - Common attack paths"
echo ""
echo "ℹ️  This is a basic security setup. For advanced protection,"
echo "   see SECURITY.md for full configuration options."
echo ""
echo "🛡️ Basic security enhancement complete!"