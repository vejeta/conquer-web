# Conquer Web

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

A secure, web-based implementation of the classic Conquer strategy game using Docker containers, ttyd (terminal over HTTP), and Apache as a reverse proxy with SSL termination.

## 🎮 Overview

This setup allows multiple players to access the same Conquer game instance through their web browsers, with proper authentication, rate limiting, and security features for safe public deployment.

**Important**: Conquer requires pre-generated world data to run. See the [World Generation](#-world-generation) section below for setup instructions.

## 🚀 Quick Start

**⚠️ Security Notice**: Always change default usernames and passwords before deployment!

### Option 1: Local Development
For development work on your local machine:

```bash
# Setup environment
./setup-environment.sh
# Choose option 1: Local development

# Start local development environment
docker-compose up -d
```

- **URL**: https://localhost
- **Setup**: Full Docker environment (Apache + Conquer containers)
- **SSL**: Self-signed certificate (accept browser warning)

### Option 2: VPS Production
For deployment on a VPS with existing Apache:

```bash
# Setup environment
./setup-environment.sh
# Choose option 2: VPS production

# Deploy to VPS (run as root)
sudo ./deploy-to-vps.sh
```

- **URL**: https://your-configured-domain.com
- **Setup**: Host Apache + Conquer container
- **SSL**: Let's Encrypt certificate

## 🔧 Configuration

### Authentication Setup

Configure authentication during setup or by editing environment files:

**Local Development** (`config/local.env`):
```bash
TTYD_USERNAME=your_dev_username
TTYD_PASSWORD=your_dev_password
MAX_CLIENTS=10
SESSION_TIMEOUT=3600
```

**VPS Production** (`config/production.env`):
```bash
TTYD_USERNAME=your_username
TTYD_PASSWORD=your_strong_password
MAX_CLIENTS=5
SESSION_TIMEOUT=1800
```

### Changing Settings

**🔐 IMPORTANT**: Change default credentials before first use!

1. **Edit environment file** (see above) - Change `TTYD_USERNAME` and `TTYD_PASSWORD`
2. **Restart containers**:
   - Local: `docker-compose restart`
   - VPS: `sudo systemctl restart conquer-web`

### Security Best Practices

- ✅ **Use strong passwords** - At least 12 characters with mixed case, numbers, symbols
- ✅ **Unique usernames** - Don't use common names like 'admin', 'user', 'conquer'
- ✅ **Change defaults** - Never use 'changeme' or default passwords in production
- ✅ **Regular updates** - Change credentials periodically

## 🌍 World Generation

Conquer requires world data to run. Generate it before first use:

```bash
# Generate world data
./generate-world.sh

# Backup existing world (optional)
./backup-world.sh

# Restore world from backup (optional)
./restore-world.sh backup-YYYY-MM-DD-HHMMSS.tar.gz
```

## 📁 Project Structure

```
conquer-web/
├── conquer/                    # Conquer game Docker container
├── apache/                     # Apache Docker container (local only)
├── vps/                       # VPS-specific configurations
├── config/                    # Environment configurations
├── docker-compose.yml         # Local development setup
├── docker-compose.local.yml   # Local development (explicit)
├── docker-compose.vps.yml     # VPS production setup
├── setup-environment.sh       # Interactive setup script
├── deploy-to-vps.sh          # VPS deployment script
└── generate-world.sh         # World data generation
```

## 🔍 Management

### Local Development

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### VPS Production

```bash
# Check service status
sudo systemctl status conquer-web

# View logs
sudo journalctl -u conquer-web -f

# Restart service
sudo systemctl restart conquer-web

# Stop service
sudo systemctl stop conquer-web
```

## 🔒 Security Features

- **Authentication**: Username/password protection
- **Rate Limiting**: Configurable concurrent user limits
- **Session Management**: Automatic session timeouts
- **SSL/TLS**: HTTPS encryption (Let's Encrypt for VPS)
- **Container Isolation**: Game runs in isolated Docker container
- **Security Headers**: HSTS, CSP, and other security headers
- **Non-root Execution**: Containers run as non-privileged users

## 🛠️ Development

### Local Setup

1. **Install Dependencies**: Docker, Docker Compose
2. **Generate World**: `./generate-world.sh`
3. **Setup Environment**: `./setup-environment.sh` (choose option 1)
4. **Start Development**: `docker-compose up -d`
5. **Access Game**: https://localhost

### VPS Deployment

1. **Prepare VPS**: Debian/Ubuntu with Apache installed
2. **Clone Project**: `git clone https://github.com/vejeta/conquer-web.git`
3. **Setup Environment**: `./setup-environment.sh` (choose option 2)
4. **Deploy**: `sudo ./deploy-to-vps.sh`
5. **Configure DNS**: Point domain to VPS IP

## 📚 Documentation

- [VPS Deployment Guide](DEPLOYMENT.md) - Detailed VPS setup instructions
- [World Management](generate-world.sh) - World data generation and backup
- [License Information](LICENSE.md) - GPL v3+ licensing details

## 🐛 Troubleshooting

### Container Issues
```bash
# Check container logs
docker logs conquer-local        # Local
docker logs conquer-vps          # VPS

# Rebuild containers
docker-compose build --no-cache
```

### VPS Service Issues
```bash
# Check systemd service
sudo systemctl status conquer-web

# Check detailed logs
sudo journalctl -u conquer-web -n 50

# Test Apache configuration
sudo apache2ctl configtest
```

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --apache
```

## 📄 License

This project is licensed under the GPL v3 or later. See [LICENSE.md](LICENSE.md) for details.

## 👥 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## 🙏 Acknowledgments

- **Conquer Game**: Original strategy game implementation
- **ttyd**: Terminal over HTTP technology
- **Docker**: Containerization platform
- **Let's Encrypt**: Free SSL certificates