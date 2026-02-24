#!/bin/bash
# ════════════════════════════════════════════════════════════
# Volo — Production Deployment Script
# Uses system nginx (shared with trading bot)
# Domain: volo.kingpinstrategies.com
# ════════════════════════════════════════════════════════════

set -euo pipefail

DOMAIN="volo.kingpinstrategies.com"
EMAIL="${CERTBOT_EMAIL:-admin@kingpinstrategies.com}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "══════════════════════════════════════════"
echo "  Volo Deployment — $DOMAIN"
echo "══════════════════════════════════════════"

# ── 1. Check prerequisites ──────────────────────────────────
echo ""
echo "▶ Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    echo "❌ Docker not found. Install: https://docs.docker.com/engine/install/"
    exit 1
fi

COMPOSE="docker compose"
if ! docker compose version &>/dev/null 2>&1; then
    if command -v docker-compose &>/dev/null; then
        COMPOSE="docker-compose"
    else
        echo "❌ Docker Compose not found."
        exit 1
    fi
fi

echo "✅ Docker: $(docker --version | head -1)"
echo "✅ Compose: $($COMPOSE version 2>/dev/null | head -1 || echo 'available')"

# Always use --env-file .env.prod for variable interpolation in compose file
DC="$COMPOSE --env-file .env.prod -f docker-compose.prod.yml"

# ── 2. Check .env.prod file ─────────────────────────────────
echo ""
if [ ! -f "$PROJECT_DIR/.env.prod" ]; then
    echo "⚠️  No .env.prod found. Creating template..."
    APP_SECRET=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 32)
    PG_PASS=$(openssl rand -hex 16)
    REDIS_PASS=$(openssl rand -hex 16)

    cat > "$PROJECT_DIR/.env.prod" << ENVEOF
# ── Volo Production Environment ──
APP_ENV=production
APP_SECRET_KEY=${APP_SECRET}
FRONTEND_URL=https://${DOMAIN}
POSTGRES_USER=volo
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=volo
DATABASE_URL=postgresql+asyncpg://volo:${PG_PASS}@postgres:5432/volo
REDIS_PASSWORD=${REDIS_PASS}
REDIS_URL=redis://:${REDIS_PASS}@redis:6379
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
ANTHROPIC_API_KEY=PASTE_YOUR_ANTHROPIC_KEY_HERE
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
TWITTER_REDIRECT_URI=https://${DOMAIN}/api/auth/twitter/callback
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
ENVEOF
    echo "✅ .env.prod created"
    echo "📝 Add your ANTHROPIC_API_KEY: nano $PROJECT_DIR/.env.prod"
    read -p "Press Enter after editing, or Ctrl+C to abort..."
fi

set -a; source "$PROJECT_DIR/.env.prod"; set +a
if [ "${ANTHROPIC_API_KEY:-}" = "PASTE_YOUR_ANTHROPIC_KEY_HERE" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set (AI features won't work)"
fi
echo "✅ .env.prod loaded"

# ── 3. Setup system nginx for Volo ──────────────────────────
echo ""
echo "▶ Configuring system nginx..."

# Install nginx site config
cp "$PROJECT_DIR/nginx/volo-site.conf" /etc/nginx/sites-available/volo

# Enable site
if [ ! -L /etc/nginx/sites-enabled/volo ]; then
    ln -s /etc/nginx/sites-available/volo /etc/nginx/sites-enabled/volo
fi

# Test nginx config
nginx -t 2>&1 && echo "✅ Nginx config valid" || { echo "❌ Nginx config error"; exit 1; }

# Reload nginx
systemctl reload nginx
echo "✅ System nginx configured for $DOMAIN"

# ── 4. Build & Deploy Docker containers ─────────────────────
echo ""
echo "▶ Building and deploying..."

cd "$PROJECT_DIR"

# Pull base images
$DC pull postgres redis 2>/dev/null || true

# Build app images
echo "🔨 Building API..."
$DC build api

echo "🔨 Building Web..."
$DC build web

# Deploy
echo "🚀 Starting services..."
$DC up -d

# ── 5. SSL via system certbot ───────────────────────────────
echo ""
echo "▶ Checking SSL..."

if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "✅ SSL certificate exists"
else
    echo "📜 Getting SSL certificate..."

    # Install certbot if needed
    if ! command -v certbot &>/dev/null; then
        apt-get install -y -qq certbot python3-certbot-nginx
    fi

    # Get cert via nginx plugin (uses existing system nginx)
    certbot --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive --redirect

    echo "✅ SSL certificate obtained & nginx updated"
fi

# ── 6. Health check ──────────────────────────────────────────
echo ""
echo "▶ Waiting for services..."
sleep 10

$DC ps

# Check API
for i in 1 2 3; do
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health 2>/dev/null || echo "000")
    if [ "$API_HEALTH" = "200" ]; then
        echo "✅ API is healthy"
        break
    fi
    [ "$i" -lt 3 ] && sleep 5
done
[ "$API_HEALTH" != "200" ] && echo "⚠️  API: HTTP $API_HEALTH — check: $DC logs api"

# Check site
SITE_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" 2>/dev/null || echo "000")
if [ "$SITE_HEALTH" = "200" ] || [ "$SITE_HEALTH" = "301" ]; then
    echo "✅ Site live at https://$DOMAIN"
else
    SITE_HEALTH_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN" 2>/dev/null || echo "000")
    if [ "$SITE_HEALTH_HTTP" = "200" ] || [ "$SITE_HEALTH_HTTP" = "301" ]; then
        echo "✅ Site live at http://$DOMAIN (SSL pending)"
    else
        echo "⚠️  Site returned HTTP $SITE_HEALTH_HTTP"
    fi
fi

echo ""
echo "══════════════════════════════════════════"
echo "  ✅ Volo is deployed!"
echo ""
echo "  🌐 https://$DOMAIN"
echo ""
echo "  Commands:"
echo "  • Logs:     docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f"
echo "  • Status:   docker compose --env-file .env.prod -f docker-compose.prod.yml ps"
echo "  • Restart:  docker compose --env-file .env.prod -f docker-compose.prod.yml restart"
echo "  • Redeploy: git pull && bash deploy.sh"
echo "══════════════════════════════════════════"
