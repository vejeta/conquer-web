# VPS Deployment Guide

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

This guide explains how to deploy Conquer Web on a Debian VPS with an existing Apache installation.

## Prerequisites

- Debian VPS with root access
- Apache2 already installed and running
- Domain name pointing to your VPS (e.g., game.example.com)
- Basic knowledge of Linux system administration

## Overview

Instead of using Docker's built-in Apache container, we'll:
1. Run only the Conquer game container
2. Use your existing Apache as a reverse proxy
3. Configure SSL with Let's Encrypt
4. Set up automatic startup and management

## Step 1: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install additional tools
sudo apt install -y git certbot python3-certbot-apache
```

## Step 2: Clone and Setup Project

```bash
# Clone the project (as conquer user)
cd /home/conquer
git clone https://github.com/vejeta/conquer-web.git
cd conquer-web

# Setup environment
./setup-environment.sh
# Choose option 2 (VPS production)
# Enter your domain: game.example.com
# Enter your email: admin@example.com
# Choose STRONG username and password for game access (NEVER use defaults!)
```

## Step 3: Configure Apache Virtual Host

Enable required Apache modules:

```bash
sudo a2enmod ssl
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod rewrite
sudo a2enmod headers
```

The virtual host configuration will be automatically created from the template during deployment.

## Step 4: DNS Configuration

Ensure your domain points to your VPS:

```bash
# Check current DNS
dig game.example.com

# Should return your VPS IP address
# If not, update your DNS records:
# Type: A
# Name: game (or @)
# Value: YOUR_VPS_IP
# TTL: 300 (or default)
```

## Step 5: SSL Certificate Setup

```bash
# Stop Apache temporarily
sudo systemctl stop apache2

# Get Let's Encrypt certificate (replace with your domain and email)
sudo certbot certonly --standalone -d game.example.com --email admin@example.com --agree-tos --no-eff-email

# Start Apache
sudo systemctl start apache2

# Enable site (replace with your domain)
sudo a2ensite game.example.com
sudo systemctl reload apache2
```

## Step 6: Build and Start Conquer Container

```bash
cd /home/conquer/conquer-web

# Build the Conquer container (without Apache)
docker build -t conquer-game ./conquer

# Create docker-compose file for VPS deployment
cp docker-compose.production.yml docker-compose.vps.yml

# Edit to remove Apache container (see VPS-specific compose file)
```

## Step 7: Create VPS-Specific Docker Compose

Create `/home/conquer/conquer-web/docker-compose.vps.yml`:

```yaml
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

services:
  conquer:
    build:
      context: ./conquer
    container_name: conquer-vps
    environment:
      - TTYD_USERNAME=${TTYD_USERNAME:-conquer}
      - TTYD_PASSWORD=${TTYD_PASSWORD:-changeme}
      - MAX_CLIENTS=${MAX_CLIENTS:-5}
      - SESSION_TIMEOUT=${SESSION_TIMEOUT:-1800}
    restart: unless-stopped
    ports:
      - "127.0.0.1:7681:7681"  # Only bind to localhost
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Step 8: Create Systemd Service

```bash
sudo nano /etc/systemd/system/conquer-web.service
```

Add the service configuration (see next section).

## Step 9: Start and Enable Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start and enable service
sudo systemctl enable conquer-web
sudo systemctl start conquer-web

# Check status
sudo systemctl status conquer-web
```

## Step 10: Verify Deployment

```bash
# Check container is running
docker ps

# Check Apache status
sudo systemctl status apache2

# Check logs
sudo journalctl -u conquer-web -f

# Test connection (replace with your domain)
curl -k https://game.example.com
```

## Management Commands

```bash
# View logs
sudo journalctl -u conquer-web -f

# Restart service
sudo systemctl restart conquer-web

# Stop service
sudo systemctl stop conquer-web

# Update deployment
cd /home/conquer/conquer-web
git pull
sudo systemctl restart conquer-web

# Backup world data
cd /home/conquer/conquer-web
./backup-world.sh

# Renew SSL certificate (automatic via cron)
sudo certbot renew --apache
```

## Security Considerations

1. **Firewall**: Ensure only ports 80, 443, and SSH are open
2. **Updates**: Keep system and Docker updated
3. **Monitoring**: Set up log monitoring
4. **Backups**: Regular world data backups
5. **Access**: Use strong passwords for game access

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs conquer-vps

# Check environment
source config/production.env
echo $TTYD_USERNAME
```

### Apache errors
```bash
# Check Apache logs
sudo tail -f /var/log/apache2/error.log

# Test configuration
sudo apache2ctl configtest
```

### SSL issues
```bash
# Check certificate
sudo certbot certificates

# Renew manually
sudo certbot renew --apache --dry-run
```

### Domain not resolving
```bash
# Check DNS (replace with your domain)
dig game.example.com
nslookup game.example.com

# Check Apache virtual host
sudo apache2ctl -S
```

## Monitoring and Maintenance

### Set up automatic certificate renewal
```bash
# Add to crontab
sudo crontab -e

# Add this line:
0 2 * * 0 /usr/bin/certbot renew --apache --quiet
```

### Set up log rotation
```bash
# Docker logs are already rotated by default
# Apache logs handled by logrotate

# Check Docker container health
docker stats conquer-vps
```

### Update procedure
```bash
#!/bin/bash
# update-conquer.sh

cd /home/conquer/conquer-web
git pull
sudo systemctl stop conquer-web
docker build -t conquer-game ./conquer
sudo systemctl start conquer-web
```

This deployment method leverages your existing Apache installation while running the game in a Docker container for easy management and isolation.

## Enhanced Security (Recommended)

After completing the basic deployment, enhance security with automated protection:

```bash
# Run the security enhancement script
cd /home/conquer/conquer-web
sudo ./setup-security.sh
```

This will configure:
- **fail2ban** - Automatic IP banning for brute force attacks
- **Enhanced rate limiting** - Protection against DoS attacks
- **Advanced Apache security** - Additional security headers and request filtering
- **Log monitoring** - Automated security monitoring

See [SECURITY.md](SECURITY.md) for detailed security configuration and maintenance.