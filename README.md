# Conquer Web Setup

A secure, web-based implementation of the classic Conquer strategy game using Docker containers, ttyd (terminal over HTTP), and Apache as a reverse proxy with SSL termination.

## 🎮 Overview

This setup allows multiple players to access the same Conquer game instance through their web browsers, with proper authentication, rate limiting, and security features for safe public deployment.

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

## 📝 License

This setup is provided as-is for educational and gaming purposes. The Conquer game itself maintains its original license terms.