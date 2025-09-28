#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

echo "🛡️ Conquer Web Security Status Check"
echo "===================================="
echo ""

# Check if fail2ban is installed and running
if ! command -v fail2ban-client &> /dev/null; then
    echo "❌ fail2ban is not installed"
    echo "   Run: sudo ./setup-security-basic.sh or sudo ./setup-security.sh"
    echo ""
else
    echo "📊 fail2ban Status:"
    sudo fail2ban-client status

    echo ""
    echo "🚫 Currently Banned IPs:"
    for jail in $(sudo fail2ban-client status 2>/dev/null | grep "Jail list:" | cut -d: -f2 | tr ',' '\n' | xargs); do
        if sudo fail2ban-client status "$jail" 2>/dev/null | grep -q "Banned IP list"; then
            echo "Jail: $jail"
            sudo fail2ban-client status "$jail" | grep "Banned IP list"
        fi
    done
fi

echo ""
echo "📈 Recent Authentication Failures (last 10):"
if ls /var/log/apache2/conquer_*_access.log 1> /dev/null 2>&1; then
    sudo grep "401" /var/log/apache2/conquer_*_access.log 2>/dev/null | tail -10 || echo "No recent failures found"
else
    echo "No Apache access logs found (conquer_*_access.log)"
fi

echo ""
echo "🔍 Suspicious Activity Check:"
if ls /var/log/apache2/conquer_*_error.log 1> /dev/null 2>&1; then
    sudo grep -i "attack\|hack\|exploit\|scan" /var/log/apache2/conquer_*_error.log 2>/dev/null | tail -5 || echo "No suspicious activity detected"
else
    echo "No Apache error logs found (conquer_*_error.log)"
fi

echo ""
echo "🌐 Apache Security Status:"
if command -v apache2ctl &> /dev/null; then
    # Check if security configurations are enabled
    if apache2ctl -M 2>/dev/null | grep -q "headers"; then
        echo "✅ mod_headers enabled (security headers active)"
    else
        echo "⚠️  mod_headers not enabled"
    fi

    if apache2ctl -M 2>/dev/null | grep -q "rewrite"; then
        echo "✅ mod_rewrite enabled (request filtering active)"
    else
        echo "⚠️  mod_rewrite not enabled"
    fi

    # Check for security configurations
    if ls /etc/apache2/conf-enabled/*security* 1> /dev/null 2>&1; then
        echo "✅ Security configurations enabled:"
        ls /etc/apache2/conf-enabled/*security*
    else
        echo "⚠️  No security configurations found in conf-enabled"
    fi
else
    echo "❌ Apache not found or not accessible"
fi

echo ""
echo "🐳 Docker Container Status:"
if command -v docker &> /dev/null; then
    if docker ps | grep -q "conquer-vps\|conquer-local"; then
        echo "✅ Conquer container running:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(conquer-vps|conquer-local)"
    else
        echo "⚠️  No Conquer containers currently running"
    fi
else
    echo "❌ Docker not found or not accessible"
fi

echo ""
echo "💾 System Resources:"
df -h / | tail -1
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Load: $(uptime | awk -F'load average:' '{print $2}')"

echo ""
echo "🔒 Security Recommendations:"
if ! command -v fail2ban-client &> /dev/null; then
    echo "   - Install fail2ban: sudo ./setup-security-basic.sh"
fi

if ! ls /etc/apache2/conf-enabled/*security* 1> /dev/null 2>&1; then
    echo "   - Enable Apache security headers"
fi

echo "   - Monitor logs regularly for suspicious activity"
echo "   - Review banned IPs and whitelist legitimate sources if needed"
echo "   - Keep system and Docker containers updated"

echo ""
echo "📋 Quick Commands:"
echo "   sudo fail2ban-client status [jail-name]     # Check specific jail"
echo "   sudo fail2ban-client unbanip [ip]           # Unban IP"
echo "   sudo tail -f /var/log/fail2ban.log         # Monitor real-time"
echo "   sudo journalctl -u conquer-web -f          # Check service logs"