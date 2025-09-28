# Security Enhancements Guide

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

This guide provides additional security hardening steps for production deployments of Conquer Web.

## 🛡️ Rate Limiting & Brute Force Protection

### Option 1: fail2ban (Recommended)

fail2ban monitors log files and temporarily bans IPs that show malicious behavior.

#### Installation

```bash
# Install fail2ban
sudo apt update
sudo apt install fail2ban

# Start and enable service
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

#### Configuration for Conquer Web

Create a custom jail for Apache authentication failures:

```bash
sudo nano /etc/fail2ban/jail.d/conquer-web.conf
```

Add the following configuration:

```ini
# Conquer Web fail2ban configuration

[apache-auth-conquer]
enabled = true
port = http,https
filter = apache-auth
logpath = /var/log/apache2/conquer_*_error.log
maxretry = 3
bantime = 3600
findtime = 600
action = iptables-multiport[name=apache-auth-conquer, port="http,https", protocol=tcp]

[apache-dos-conquer]
enabled = true
port = http,https
filter = apache-dos-conquer
logpath = /var/log/apache2/conquer_*_access.log
maxretry = 200
bantime = 1800
findtime = 300
action = iptables-multiport[name=apache-dos-conquer, port="http,https", protocol=tcp]

[ttyd-auth]
enabled = true
port = http,https
filter = ttyd-auth
logpath = /var/log/apache2/conquer_*_error.log
maxretry = 5
bantime = 7200
findtime = 900
action = iptables-multiport[name=ttyd-auth, port="http,https", protocol=tcp]
```

#### Custom Filters

Create filters for ttyd authentication failures and DoS protection:

**ttyd Authentication Filter:**
```bash
sudo nano /etc/fail2ban/filter.d/ttyd-auth.conf
```

```ini
# fail2ban filter for ttyd authentication failures

[Definition]
failregex = ^.* \[client <HOST>:\d+\] client sent HTTP code 401.*
            ^.* \[client <HOST>:\d+\] AH01797: client denied by server configuration.*
            ^.* \[client <HOST>:\d+\] AH01630: client denied by server configuration.*

ignoreregex =
```

**DoS Protection Filter:**
```bash
sudo nano /etc/fail2ban/filter.d/apache-dos-conquer.conf
```

```ini
# fail2ban filter for DoS attacks via Apache access logs

[Definition]
failregex = ^<HOST> -.*"(GET|POST).*" (200|206|301|302) .*$

ignoreregex =
```

#### Test and Activate

```bash
# Test configuration
sudo fail2ban-client -t

# Restart fail2ban
sudo systemctl restart fail2ban

# Check status
sudo fail2ban-client status
sudo fail2ban-client status apache-auth-conquer
```

### Option 2: mod_evasive (Alternative)

mod_evasive provides real-time DoS protection at the Apache level.

#### Installation

```bash
# Install mod_evasive
sudo apt install libapache2-mod-evasive

# Enable module
sudo a2enmod evasive
```

#### Configuration

```bash
sudo nano /etc/apache2/mods-enabled/evasive.conf
```

```apache
<IfModule mod_evasive24.c>
    # Page hit limit per interval
    DOSPageCount        3
    DOSPageInterval     1

    # Site hit limit per interval
    DOSSiteCount        50
    DOSSiteInterval     1

    # Blocking period (seconds)
    DOSBlockingPeriod   3600

    # Hash table size
    DOSHashTableSize    4096

    # Log directory
    DOSLogDir           /var/log/apache2/evasive

    # Email alerts (optional)
    # DOSEmailNotify      admin@yourdomain.com

    # Whitelist localhost and your IP
    DOSWhitelist        127.0.0.1
    DOSWhitelist        ::1
    # DOSWhitelist      YOUR_ADMIN_IP
</IfModule>
```

Create log directory:

```bash
sudo mkdir -p /var/log/apache2/evasive
sudo chown www-data:www-data /var/log/apache2/evasive
```

Restart Apache:

```bash
sudo systemctl restart apache2
```

## 🔒 Additional Apache Security

### Enhanced Security Headers

Add to your Apache virtual host or in `/etc/apache2/conf-available/security.conf`:

```apache
# Additional security headers
Header always set X-Robots-Tag "noindex, nofollow"
Header always set X-Permitted-Cross-Domain-Policies "none"
Header always set Cross-Origin-Embedder-Policy "require-corp"
Header always set Cross-Origin-Opener-Policy "same-origin"
Header always set Cross-Origin-Resource-Policy "same-origin"

# Remove server signatures
Header always unset X-Powered-By
Header always unset Server
ServerTokens Prod
```

### Request Filtering

Add to your virtual host configuration:

```apache
# Block suspicious request patterns
<LocationMatch "(\.php|\.asp|\.jsp|wp-admin|phpmyadmin|\.git|\.env)">
    Require all denied
</LocationMatch>

# Block common attack patterns in URLs
RewriteEngine On
RewriteCond %{QUERY_STRING} (union.*select|concat.*\(|script.*>) [NC,OR]
RewriteCond %{QUERY_STRING} (\.\.\/|\.\.\\|etc\/passwd|boot\.ini) [NC,OR]
RewriteCond %{QUERY_STRING} (<script|javascript:|vbscript:|onload|onerror) [NC]
RewriteRule .* - [F,L]

# Limit request methods (applied globally)
<Location />
    <RequireAll>
        Require method GET POST HEAD OPTIONS
    </RequireAll>
</Location>
```

## 🔍 Monitoring & Alerting

### Log Monitoring with logwatch

```bash
# Install logwatch
sudo apt install logwatch

# Configure for daily reports
sudo nano /etc/logwatch/conf/logwatch.conf
```

Edit the configuration:
```
Detail = High
MailTo = your-email@domain.com
Range = yesterday
Service = All
```

### Real-time Log Monitoring

Monitor authentication attempts in real-time:

```bash
# Watch Apache error logs
sudo tail -f /var/log/apache2/conquer_*_error.log

# Watch fail2ban logs
sudo tail -f /var/log/fail2ban.log

# Monitor active bans
sudo fail2ban-client status apache-auth-conquer
```

## 🛠️ Automated Setup Script

Create an automated security setup script:

```bash
sudo nano /home/conquer/conquer-web/setup-security.sh
```

```bash
#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

echo "🛡️ Conquer Web Security Enhancement Setup"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root"
    echo "   Run with: sudo $0"
    exit 1
fi

# Install fail2ban
echo "📦 Installing fail2ban..."
apt update
apt install -y fail2ban

# Create fail2ban configuration
echo "🔧 Configuring fail2ban..."
cat > /etc/fail2ban/jail.d/conquer-web.conf << 'EOF'
[apache-auth-conquer]
enabled = true
port = http,https
filter = apache-auth
logpath = /var/log/apache2/conquer_*_error.log
maxretry = 3
bantime = 3600
findtime = 600
action = iptables-multiport[name=apache-auth-conquer, port="http,https", protocol=tcp]

[ttyd-auth]
enabled = true
port = http,https
filter = ttyd-auth
logpath = /var/log/apache2/conquer_*_error.log
maxretry = 5
bantime = 7200
findtime = 900
action = iptables-multiport[name=ttyd-auth, port="http,https", protocol=tcp]
EOF

# Create ttyd filter
cat > /etc/fail2ban/filter.d/ttyd-auth.conf << 'EOF'
[Definition]
failregex = ^.* \[client <HOST>:\d+\] client sent HTTP code 401.*
            ^.* \[client <HOST>:\d+\] AH01797: client denied by server configuration.*

ignoreregex =
EOF

# Enable and start fail2ban
systemctl enable fail2ban
systemctl restart fail2ban

# Install logwatch
echo "📊 Installing logwatch..."
apt install -y logwatch

# Test fail2ban configuration
echo "🧪 Testing fail2ban configuration..."
if fail2ban-client -t; then
    echo "✅ fail2ban configuration is valid"
else
    echo "❌ fail2ban configuration has errors"
    exit 1
fi

echo ""
echo "🎉 Security enhancements installed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Check fail2ban status: sudo fail2ban-client status"
echo "2. Monitor logs: sudo tail -f /var/log/fail2ban.log"
echo "3. View banned IPs: sudo fail2ban-client status apache-auth-conquer"
echo "4. Consider setting up email alerts in logwatch"
echo ""
echo "🔒 Your Conquer Web installation is now better protected!"
```

Make it executable:

```bash
chmod +x /home/conquer/conquer-web/setup-security.sh
```

## 🚨 Security Monitoring Commands

### Daily Security Checks

```bash
# Check fail2ban status
sudo fail2ban-client status

# View banned IPs
sudo fail2ban-client status apache-auth-conquer

# Check recent authentication failures
sudo grep "401" /var/log/apache2/conquer_*_access.log | tail -20

# Check for suspicious activity
sudo grep -i "attack\|hack\|exploit" /var/log/apache2/conquer_*_error.log

# Monitor system resources
htop
df -h
```

### Unban IP (if needed)

```bash
# Unban specific IP
sudo fail2ban-client set apache-auth-conquer unbanip 192.168.1.100

# Clear all bans for a jail
sudo fail2ban-client reload apache-auth-conquer
```

## 🎯 Security Testing

### Test Rate Limiting

```bash
# Test with curl (should get banned after few attempts)
for i in {1..10}; do
    curl -u wronguser:wrongpass https://your-domain.com
    sleep 1
done
```

### Monitor During Test

```bash
# Watch fail2ban logs during testing
sudo tail -f /var/log/fail2ban.log

# Check if IP gets banned
sudo fail2ban-client status apache-auth-conquer
```

## 📋 Security Checklist

After implementing these enhancements:

- [ ] fail2ban installed and configured
- [ ] Custom filters for ttyd authentication created
- [ ] Rate limiting tested and working
- [ ] Log monitoring setup
- [ ] Email alerts configured (optional)
- [ ] Security testing performed
- [ ] Documentation updated with admin procedures
- [ ] Backup procedures include security configurations

## 🔄 Maintenance

### Weekly Tasks
- Review fail2ban logs for patterns
- Check banned IP lists
- Monitor authentication failure trends

### Monthly Tasks
- Update security configurations
- Review and rotate logs
- Test backup and restore procedures
- Update fail2ban rules if needed

This completes the security enhancement setup for your Conquer Web installation. Your system now has multiple layers of protection against brute force attacks and suspicious activity.