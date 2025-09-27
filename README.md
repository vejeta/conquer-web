# Conquer Web Setup

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

A secure, web-based implementation of the classic Conquer strategy game using Docker containers, ttyd (terminal over HTTP), and Apache as a reverse proxy with SSL termination.

## 🎮 Overview

This setup allows multiple players to access the same Conquer game instance through their web browsers, with proper authentication, rate limiting, and security features for safe public deployment.

**Important**: Conquer requires pre-generated world data to run. See the [World Generation](#-world-generation) section below for setup instructions.

## 🚀 Quick Start

### Local Development
```bash
./start-local.sh
```
- **URL**: https://conquer.local
- **Credentials**: `dev` / `localdev`
- **SSL**: Self-signed certificate (accept browser warning)

### Production Deployment
```bash
./start-production.sh
```
- **URL**: https://conquer.vejeta.com
- **Credentials**: `conquer` / `game2024secure`
- **SSL**: Let's Encrypt certificate

## 🔐 Authentication Setup

### Default Credentials

| Environment | Username | Password | Max Users | Session Timeout |
|-------------|----------|----------|-----------|-----------------|
| **Local**   | `dev`    | `localdev` | 10        | 1 hour          |
| **Production** | `conquer` | `game2024secure` | 5 | 30 minutes |

### Changing Authentication

#### Method 1: Edit Environment Files

**For Local Development:**
```bash
# Edit config/local.env
TTYD_USERNAME=your_username
TTYD_PASSWORD=your_password
MAX_CLIENTS=10
SESSION_TIMEOUT=3600
```

**For Production:**
```bash
# Edit config/production.env
TTYD_USERNAME=your_username
TTYD_PASSWORD=your_strong_password
MAX_CLIENTS=5
SESSION_TIMEOUT=1800
```

#### Method 2: Environment Variables
```bash
# Set before starting
export TTYD_USERNAME=myuser
export TTYD_PASSWORD=mypass
./start-production.sh
```

**⚠️ Important**: After changing credentials, rebuild containers:
```bash
./rebuild.sh
```

## 📁 Project Structure

```
conquer-web/
├── config/
│   ├── local.env          # Local development settings
│   └── production.env     # Production settings
├── apache/
│   ├── local.conf         # Apache config for local (conquer.local)
│   ├── production.conf    # Apache config for production (conquer.vejeta.com)
│   ├── security.conf      # Shared security settings
│   └── certs/             # SSL certificates
├── conquer/
│   ├── Dockerfile         # Conquer game container
│   └── lib/               # Game data files
├── docker-compose.local.yml      # Local development containers
├── docker-compose.production.yml # Production containers
└── Scripts:
    ├── start-local.sh     # 🚀 Start local development
    ├── start-production.sh # 🚀 Start production
    ├── stop.sh           # 🛑 Stop services
    ├── setup-local-certs.sh  # Generate self-signed certificates
    ├── setup-production-certs.sh # Get Let's Encrypt certificates
    ├── renew-certs.sh    # Renew SSL certificates
    ├── logs.sh           # View container logs
    ├── rebuild.sh        # Rebuild containers
    └── health-check.sh   # System health check
```

## 🔧 Environment Configuration

### Local Development (`config/local.env`)
- **Domain**: `conquer.local`
- **Certificates**: Self-signed
- **Security**: Lighter rate limiting
- **Purpose**: Development and testing

### Production (`config/production.env`)
- **Domain**: `conquer.vejeta.com`
- **Certificates**: Let's Encrypt
- **Security**: Strict rate limiting and monitoring
- **Purpose**: Public deployment

## 🛡️ Security Features

### Authentication
- **Basic HTTP Authentication** on ttyd terminal access
- **Configurable credentials** per environment
- **Session timeouts** to prevent abandoned sessions

### Rate Limiting
- **mod_evasive**: DDoS protection
  - Production: 5 pages/second, 5-minute blocks
  - Local: 20 pages/second, 1-minute blocks
- **Connection limits**: Maximum concurrent users
- **Request size limits**: 1MB maximum

### Security Headers
- **HSTS**: Force HTTPS with preload
- **CSP**: Content Security Policy
- **XSS Protection**: Browser-based filtering
- **Anti-Clickjacking**: Frame denial
- **Server Hiding**: Remove version information

### Access Controls
- **Bot blocking**: Prevent crawlers and scrapers
- **File protection**: Block access to sensitive files
- **Path filtering**: Block admin/config endpoints
- **User-Agent validation**: Allow only legitimate browsers

## 🎯 Usage Examples

### Start local development
```bash
./start-local.sh
# Visit: https://conquer.local
# Login: dev / localdev
```

### Deploy to production
```bash
./start-production.sh
# Visit: https://conquer.vejeta.com
# Login: conquer / game2024secure
```

### Monitor services
```bash
./logs.sh              # View real-time logs
./health-check.sh      # Check system status
```

### Maintenance
```bash
./renew-certs.sh       # Renew SSL certificates (production)
./rebuild.sh           # Rebuild after code changes
./stop.sh              # Stop all services
```

## 🎮 How Multiplayer Works

1. **Shared Session**: All players connect to the same game instance
2. **Turn-based Input**: Players coordinate who types commands
3. **Real-time Updates**: Everyone sees the same game state
4. **Nation Control**: Each player controls their own nation

## 🔒 Security Best Practices

### For Production Deployment

1. **Change Default Passwords**:
   ```bash
   # Edit config/production.env
   TTYD_USERNAME=your_secure_username
   TTYD_PASSWORD=your_very_strong_password_2024
   ```

2. **Monitor Logs**:
   ```bash
   ./logs.sh | grep -i "error\|attack\|blocked"
   ```

3. **Regular Updates**:
   ```bash
   # Monthly certificate renewal
   0 2 1 * * /path/to/conquer-web/renew-certs.sh
   ```

4. **Backup Game Data**:
   ```bash
   docker cp conquer-production:/root/conquer/gpl-release/lib ./backups/
   ```

### Recommended Password Policy
- **Minimum 12 characters**
- **Include numbers and symbols**
- **Avoid dictionary words**
- **Change quarterly**

## 🚨 Troubleshooting

### Can't Connect
- Check if containers are running: `docker ps`
- Verify domain resolution: `nslookup conquer.vejeta.com`
- Check logs: `./logs.sh`

### Authentication Issues
- Verify credentials in config files
- Rebuild containers after changes: `./rebuild.sh`
- Check browser isn't caching old credentials

### SSL Certificate Problems
- Local: Regenerate certificates: `./setup-local-certs.sh`
- Production: Check DNS and renew: `./setup-production-certs.sh`

### Multiple Sessions Not Working
- Ensure `-W` flag is present in ttyd command
- Check `MAX_CLIENTS` setting in environment files
- Verify rate limiting isn't blocking connections

## 📊 Monitoring

### Health Check
```bash
./health-check.sh
```
Shows:
- Container status
- Certificate validity
- Service connectivity
- Domain resolution

### Log Analysis
```bash
# View all logs
./logs.sh

# Filter for security events
./logs.sh | grep -E "(blocked|denied|attack)"

# Monitor authentication
./logs.sh | grep -i "auth"
```

## 🎯 Risk Assessment

**Current Security Level**: **LOW-MEDIUM RISK** ✅

**Safe for**:
- Public websites with authentication
- Small gaming communities
- Educational demonstrations

**Additional considerations**:
- Monitor access logs regularly
- Implement IP allowlists for sensitive environments
- Consider additional authentication layers for high-value deployments

## 🌍 World Generation

Conquer requires pre-generated world data files to run. The game world contains nations, geography, and initial game state.

### Understanding World Data

The game depends on several files in `conquer/lib/`:
- **`data`** - Main world database (geography, nations, resources)
- **`.userlog`** - Player session tracking
- **`nations`** - Nation definitions and relationships
- **`help*`**, **`mesg*`**, **`exec*`** - Game text and executable content
- **`news0`**, **`rules`** - Game announcements and rule configurations

### Option 1: Use Existing World Data

This repository includes a pre-generated world that's ready to use:

```bash
# World data is already included in conquer/lib/
./setup-environment.sh  # Configure authentication
./start-local.sh        # Start with existing world
```

### Option 2: Generate New World Data

For a fresh world or custom configuration:

#### Manual Generation (Advanced Users)

1. **Compile Conquer locally**:
   ```bash
   git clone https://github.com/vejeta/conquer.git
   cd conquer/gpl-release
   make
   ```

2. **Generate world data**:
   ```bash
   # Run world generation in maintenance mode
   ./conqrun -m
   # Follow prompts to create nations, set geography, etc.
   # This creates the lib/ directory with world data
   ```

3. **Copy world data to Docker context**:
   ```bash
   # From your local conquer directory
   cp -r lib/ /path/to/conquer-web/conquer/
   cp lib/.userlog /path/to/conquer-web/conquer/lib/
   ```

4. **Rebuild containers**:
   ```bash
   cd /path/to/conquer-web
   ./rebuild.sh --force
   ```

#### Automated Generation (Recommended)

Use the provided automation script:

```bash
./generate-world.sh
```

This script will:
- Clone and compile Conquer locally
- Guide you through world generation
- Automatically copy files to the correct location
- Rebuild containers with new world data

### World Management

#### Backup Current World
```bash
./backup-world.sh
# Creates timestamped backup in backups/
```

#### Restore World from Backup
```bash
./restore-world.sh backup-2025-09-27.tar.gz
```

#### Validate World Data
```bash
./health-check.sh
# Includes world data validation
```

### Troubleshooting World Issues

#### World Generation Fails
- Ensure you have enough disk space (>100MB)
- Check that build tools are installed: `build-essential`, `libncurses5-dev`
- Verify conquer compiles successfully before running `conqrun -m`

#### Game Won't Start
- Check world data files exist: `ls -la conquer/lib/`
- Validate `.userlog` file permissions
- Run `./health-check.sh` for detailed diagnostics

#### Corrupted World Data
- Restore from backup: `./restore-world.sh`
- Or regenerate: `./generate-world.sh`

#### Multiple Worlds
To switch between different worlds:
```bash
# Backup current world
./backup-world.sh

# Generate or restore different world
./generate-world.sh
# OR
./restore-world.sh other-world-backup.tar.gz

# Rebuild with new world
./rebuild.sh
```

### World Configuration Tips

- **Small worlds** (10-20 nations) are easier to manage
- **Medium worlds** (50-100 nations) provide good gameplay
- **Large worlds** (200+ nations) may impact performance
- Consider **game balance** when setting nation resources
- **Document your world settings** for future reference

## 📝 License

This project is licensed under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.

### License Summary

- ✅ **Free to use, modify, and distribute**
- ✅ **Commercial use allowed**
- ❗ **Source code must remain open**
- ❗ **Derivatives must use compatible license**
- ❗ **No warranty provided**

### Full License Information

- **License Text**: See [COPYING](COPYING) for the complete GPL v3.0 license
- **License Summary**: See [LICENSE.md](LICENSE.md) for detailed information
- **SPDX Identifier**: `GPL-3.0-or-later`

### Copyright

```
Copyright (C) 2025 Juan Manuel Méndez Rey

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

### Third-Party Components

This project includes or depends on third-party software with compatible licenses:

- **Conquer Game**: GPL-3.0-or-later (upstream project)
- **ttyd**: MIT License (compatible)
- **Apache HTTP Server**: Apache License 2.0 (compatible)
- **Docker Images**: Various compatible licenses

### REUSE Compliance

This project follows the [REUSE](https://reuse.software/) specification for clear licensing:

```bash
# Check license compliance
pip install reuse
reuse lint
```

All source files contain proper SPDX license headers for automatic license detection and compliance verification.