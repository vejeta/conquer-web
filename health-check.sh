#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

echo "🏥 Conquer Web Health Check"
echo "=========================="

# Check Docker daemon
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon is not running"
    exit 1
fi

# Check running containers
echo ""
echo "📦 Container Status:"
CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(conquer|apache)" || echo "No containers running")
echo "$CONTAINERS"

# Detect environment
if docker ps --format "table {{.Names}}" | grep -q "conquer-local"; then
    ENV="local"
    DOMAIN="conquer.local"
    source config/local.env 2>/dev/null || true
elif docker ps --format "table {{.Names}}" | grep -q "conquer-production"; then
    ENV="production"
    DOMAIN="conquer.vejeta.com"
    source config/production.env 2>/dev/null || true
else
    echo ""
    echo "ℹ️  No Conquer Web environment is currently running"
    echo "   Start with: ./start-local.sh or ./start-production.sh"
    exit 0
fi

echo ""
echo "🌍 Environment: $ENV"
echo "🌐 Domain: $DOMAIN"

# Check certificate status
echo ""
echo "🔐 Certificate Status:"
if [ -f "$CERT_PATH/fullchain.pem" ]; then
    CERT_EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_PATH/fullchain.pem" | cut -d= -f2)
    CERT_DAYS=$(openssl x509 -checkend 0 -noout -in "$CERT_PATH/fullchain.pem" && echo "Valid" || echo "Expired")
    echo "   Certificate file: ✅ Found"
    echo "   Expiry date: $CERT_EXPIRY"
    echo "   Status: $CERT_DAYS"

    # Check if expiring soon (30 days)
    if ! openssl x509 -checkend 2592000 -noout -in "$CERT_PATH/fullchain.pem" > /dev/null 2>&1; then
        echo "   ⚠️  Certificate expires within 30 days!"
        if [ "$CERT_TYPE" = "letsencrypt" ]; then
            echo "   Run: ./renew-certs.sh"
        fi
    fi
else
    echo "   ❌ Certificate file not found at $CERT_PATH/fullchain.pem"
fi

# Check world data status
echo ""
echo "🌍 World Data Status:"
WORLD_LIB_DIR="$(pwd)/conquer/lib"

if [ -d "$WORLD_LIB_DIR" ]; then
    echo "   World directory: ✅ Found ($WORLD_LIB_DIR)"

    # Check critical files
    CRITICAL_FILES=("data" "nations" ".userlog")
    MISSING_FILES=()

    for file in "${CRITICAL_FILES[@]}"; do
        if [ -f "$WORLD_LIB_DIR/$file" ]; then
            if [ -s "$WORLD_LIB_DIR/$file" ]; then
                echo "   $file: ✅ Present and non-empty"
            else
                echo "   $file: ⚠️  Present but empty"
                MISSING_FILES+=("$file (empty)")
            fi
        else
            echo "   $file: ❌ Missing"
            MISSING_FILES+=("$file")
        fi
    done

    # Check optional files
    OPTIONAL_FILES=("help0" "mesg0" "news0" "rules" "exec0")
    for file in "${OPTIONAL_FILES[@]}"; do
        if [ -f "$WORLD_LIB_DIR/$file" ]; then
            echo "   $file: ✅ Present"
        else
            echo "   $file: ⚠️  Optional file missing"
        fi
    done

    # World summary
    if [ -f "$WORLD_LIB_DIR/nations" ] && [ -s "$WORLD_LIB_DIR/nations" ]; then
        NATION_COUNT=$(wc -l < "$WORLD_LIB_DIR/nations" 2>/dev/null || echo "unknown")
        echo "   Nations count: $NATION_COUNT"
    fi

    if [ -f "$WORLD_LIB_DIR/data" ] && [ -s "$WORLD_LIB_DIR/data" ]; then
        WORLD_SIZE=$(du -h "$WORLD_LIB_DIR/data" 2>/dev/null | cut -f1 || echo "unknown")
        echo "   World data size: $WORLD_SIZE"
    fi

    # Overall world status
    if [ ${#MISSING_FILES[@]} -eq 0 ]; then
        echo "   Overall status: ✅ World data complete"
    else
        echo "   Overall status: ❌ Issues found: ${MISSING_FILES[*]}"
        echo "   💡 Fix with: ./generate-world.sh or ./restore-world.sh"
    fi
else
    echo "   World directory: ❌ Not found ($WORLD_LIB_DIR)"
    echo "   💡 Generate world data with: ./generate-world.sh"
fi

# Check service connectivity
echo ""
echo "🔗 Service Connectivity:"

# Test HTTP port
if curl -s --connect-timeout 5 "http://localhost" > /dev/null 2>&1; then
    echo "   HTTP (port 80): ✅ Responding"
else
    echo "   HTTP (port 80): ❌ Not responding"
fi

# Test HTTPS port
if curl -s -k --connect-timeout 5 "https://localhost" > /dev/null 2>&1; then
    echo "   HTTPS (port 443): ✅ Responding"
else
    echo "   HTTPS (port 443): ❌ Not responding"
fi

# Test domain (if not localhost)
if [ "$DOMAIN" != "localhost" ] && [ "$ENV" = "local" ]; then
    if curl -s -k --connect-timeout 5 "https://$DOMAIN" > /dev/null 2>&1; then
        echo "   Domain ($DOMAIN): ✅ Responding"
    else
        echo "   Domain ($DOMAIN): ❌ Not responding"
        echo "   💡 Make sure '$DOMAIN' is in your /etc/hosts file"
    fi
elif [ "$ENV" = "production" ]; then
    if curl -s --connect-timeout 10 "https://$DOMAIN" > /dev/null 2>&1; then
        echo "   Domain ($DOMAIN): ✅ Responding"
    else
        echo "   Domain ($DOMAIN): ❌ Not responding"
        echo "   💡 Check DNS configuration and firewall settings"
    fi
fi

echo ""
echo "✅ Health check completed!"