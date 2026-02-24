#!/bin/bash
# ════════════════════════════════════════════════════════════
# Volo — Production Deployment Script
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
# Auto-generated on $(date -u +%Y-%m-%dT%H:%M:%SZ)

# App
APP_ENV=production
APP_SECRET_KEY=${APP_SECRET}
FRONTEND_URL=https://${DOMAIN}

# Database
POSTGRES_USER=volo
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=volo
DATABASE_URL=postgresql+asyncpg://volo:${PG_PASS}@postgres:5432/volo

# Redis
REDIS_PASSWORD=${REDIS_PASS}
REDIS_URL=redis://:${REDIS_PASS}@redis:6379

# Auth
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# AI (REQUIRED — add your key!)
ANTHROPIC_API_KEY=PASTE_YOUR_ANTHROPIC_KEY_HERE

# X / Twitter OAuth 2.0 (optional — get from developer.x.com)
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
TWITTER_REDIRECT_URI=https://${DOMAIN}/api/auth/twitter/callback

# Google OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
ENVEOF
    echo "✅ .env.prod created with random secrets"
    echo ""
    echo "📝 IMPORTANT: Add your ANTHROPIC_API_KEY:"
    echo "   nano $PROJECT_DIR/.env.prod"
    echo ""
    read -p "Press Enter after editing .env.prod, or Ctrl+C to abort..."
fi

# Validate critical env var
set -a; source "$PROJECT_DIR/.env.prod"; set +a
if [ "${ANTHROPIC_API_KEY:-}" = "PASTE_YOUR_ANTHROPIC_KEY_HERE" ]; then
    echo "⚠️  Reminder: ANTHROPIC_API_KEY is not set in .env.prod (AI features won't work)"
fi
echo "✅ .env.prod loaded"

# ── 3. SSL Certificate (bootstrap) ──────────────────────────
echo ""
echo "▶ Checking SSL certificate..."

HAS_CERTS=false
# Check if cert volume already has certs
if docker volume inspect volo_certbot_certs &>/dev/null 2>&1; then
    # Check if actual cert files exist inside the volume
    CERT_CHECK=$(docker run --rm -v volo_certbot_certs:/etc/letsencrypt alpine \
        sh -c "ls /etc/letsencrypt/live/$DOMAIN/fullchain.pem 2>/dev/null && echo 'found'" 2>/dev/null || echo "")
    if [ "$CERT_CHECK" = "found" ]; then
        HAS_CERTS=true
    fi
fi

if [ "$HAS_CERTS" = true ]; then
    echo "✅ SSL certificates exist"
    NGINX_CONF="nginx.conf"
else
    echo "📜 No SSL certificates yet — starting in HTTP-only mode..."
    NGINX_CONF="nginx-initial.conf"
fi

# ── 4. Build & Deploy ───────────────────────────────────────
echo ""
echo "▶ Building and deploying..."

cd "$PROJECT_DIR"

# Use the right nginx config
cp "$PROJECT_DIR/nginx/$NGINX_CONF" "$PROJECT_DIR/nginx/active.conf"

# Pull base images
$COMPOSE -f docker-compose.prod.yml pull postgres redis 2>/dev/null || true

# Build app images
echo "🔨 Building API..."
$COMPOSE -f docker-compose.prod.yml build api

echo "🔨 Building Web..."
$COMPOSE -f docker-compose.prod.yml build web

# Deploy
echo "🚀 Starting services..."
$COMPOSE -f docker-compose.prod.yml up -d

# ── 5. Get SSL if needed ────────────────────────────────────
if [ "$HAS_CERTS" = false ]; then
    echo ""
    echo "▶ Obtaining SSL certificate from Let's Encrypt..."
    sleep 5  # Wait for nginx to start

    # Run certbot
    docker run --rm \
        -v volo_certbot_certs:/etc/letsencrypt \
        -v volo_certbot_www:/var/www/certbot \
        certbot/certbot certonly \
        --webroot -w /var/www/certbot \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive

    if [ $? -eq 0 ]; then
        echo "✅ SSL certificate obtained!"

        # Switch nginx to HTTPS config
        cp "$PROJECT_DIR/nginx/nginx.conf" "$PROJECT_DIR/nginx/active.conf"
        docker exec volo-nginx nginx -s reload 2>/dev/null || \
            $COMPOSE -f docker-compose.prod.yml restart nginx

        echo "✅ Nginx switched to HTTPS mode"
    else
        echo "⚠️  SSL certificate failed — running on HTTP only"
        echo "   Make sure DNS points $DOMAIN → this server"
        echo "   Then re-run this script"
    fi
fi

# ── 6. Health check ──────────────────────────────────────────
echo ""
echo "▶ Waiting for services to be healthy..."
sleep 10

# Check services via docker
echo ""
$COMPOSE -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || \
    $COMPOSE -f docker-compose.prod.yml ps

# Check API health
for i in 1 2 3; do
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health 2>/dev/null || echo "000")
    if [ "$API_HEALTH" = "200" ]; then
        echo "✅ API is healthy"
        break
    fi
    [ "$i" -lt 3 ] && sleep 5
done
if [ "$API_HEALTH" != "200" ]; then
    echo "⚠️  API returned HTTP $API_HEALTH"
    echo "   Check logs: $COMPOSE -f docker-compose.prod.yml logs api"
fi

# Check via domain
if [ "$HAS_CERTS" = true ]; then
    SITE_URL="https://$DOMAIN"
else
    SITE_URL="http://$DOMAIN"
fi
SITE_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" 2>/dev/null || echo "000")
if [ "$SITE_HEALTH" = "200" ] || [ "$SITE_HEALTH" = "301" ]; then
    echo "✅ Site is reachable at $SITE_URL"
else
    echo "⚠️  Site returned HTTP $SITE_HEALTH at $SITE_URL"
fi

echo ""
echo "══════════════════════════════════════════"
echo "  ✅ Volo is deployed!"
echo ""
echo "  🌐 $SITE_URL"
echo ""
echo "  Useful commands:"
echo "  • Logs:    docker compose -f docker-compose.prod.yml logs -f"
echo "  • API log: docker compose -f docker-compose.prod.yml logs -f api"
echo "  • Status:  docker compose -f docker-compose.prod.yml ps"
echo "  • Restart: docker compose -f docker-compose.prod.yml restart"
echo "  • Redeploy: git pull && bash deploy.sh"
echo "  • Stop:    docker compose -f docker-compose.prod.yml down"
echo "══════════════════════════════════════════"
