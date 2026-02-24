#!/bin/bash
# ════════════════════════════════════════════════════════════════
# Volo — Server Setup Script
# Run this on a fresh Ubuntu 22.04 VPS
#
# Usage:  ssh root@209.97.155.190 'bash -s' < server-setup.sh
# Or:     scp server-setup.sh root@209.97.155.190:~ && ssh root@209.97.155.190 './server-setup.sh'
# ════════════════════════════════════════════════════════════════

set -euo pipefail

DOMAIN="volo.kingpinstrategies.com"
SERVER_IP="209.97.155.190"
REPO="https://github.com/Illuminaticonsulting/volo.git"
APP_DIR="/opt/volo"
SWAP_SIZE="2G"

echo ""
echo "══════════════════════════════════════════════"
echo "  Volo Server Setup — $DOMAIN"
echo "  Server: $SERVER_IP"
echo "══════════════════════════════════════════════"
echo ""

# ── 1. System Updates ──────────────────────────
echo "▶ [1/7] Updating system..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

# ── 2. Add Swap (needed for 1 vCPU builds) ─────
echo "▶ [2/7] Setting up ${SWAP_SIZE} swap..."
if [ ! -f /swapfile ]; then
    fallocate -l "$SWAP_SIZE" /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap created"
else
    echo "✅ Swap already exists"
fi

# ── 3. Install Docker ──────────────────────────
echo "▶ [3/7] Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Verify Docker Compose plugin
if ! docker compose version &>/dev/null; then
    apt-get install -y -qq docker-compose-plugin
fi
echo "   $(docker --version)"
echo "   $(docker compose version)"

# ── 4. Firewall ────────────────────────────────
echo "▶ [4/7] Configuring firewall..."
apt-get install -y -qq ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
echo "✅ Firewall configured (SSH, HTTP, HTTPS)"

# ── 5. Clone Repo ──────────────────────────────
echo "▶ [5/7] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo "   Updating existing repo..."
    cd "$APP_DIR"
    git pull origin main || git pull origin master || true
else
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi
echo "✅ Code at $APP_DIR"

# ── 6. Create .env.prod ───────────────────────
echo "▶ [6/7] Setting up environment..."
if [ ! -f "$APP_DIR/.env.prod" ]; then
    # Generate random secrets
    APP_SECRET=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 32)
    PG_PASS=$(openssl rand -hex 16)
    REDIS_PASS=$(openssl rand -hex 16)

    cat > "$APP_DIR/.env.prod" << ENVEOF
# ══ Volo Production Environment ══
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
    echo "   ⚠️  IMPORTANT: You still need to add your ANTHROPIC_API_KEY!"
    echo "   Edit: nano $APP_DIR/.env.prod"
else
    echo "✅ .env.prod already exists"
fi

# ── 7. SSL Certificate ────────────────────────
echo "▶ [7/7] Setting up SSL certificate..."

# First, check DNS
echo "   Checking DNS for $DOMAIN..."
RESOLVED_IP=$(dig +short "$DOMAIN" 2>/dev/null || echo "")
if [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
    echo ""
    echo "   ⚠️  DNS not pointing here yet!"
    echo "   Current: $DOMAIN → ${RESOLVED_IP:-'(no record)'}"
    echo "   Expected: $DOMAIN → $SERVER_IP"
    echo ""
    echo "   Go to your DNS provider and add:"
    echo "   Type: A"
    echo "   Name: volo"
    echo "   Value: $SERVER_IP"
    echo "   TTL: 300"
    echo ""
    echo "   After DNS propagates, run this to get SSL:"
    echo "   cd $APP_DIR && bash get-ssl.sh"
    echo ""

    # Create a helper script to get SSL later
    cat > "$APP_DIR/get-ssl.sh" << 'SSLEOF'
#!/bin/bash
set -euo pipefail
DOMAIN="volo.kingpinstrategies.com"
APP_DIR="/opt/volo"

echo "▶ Getting SSL certificate for $DOMAIN..."

# Start a temporary nginx for the ACME challenge
docker run -d --name temp-nginx \
    -p 80:80 \
    -v volo_certbot_www:/var/www/certbot \
    nginx:alpine sh -c 'mkdir -p /var/www/certbot && nginx -g "daemon off;"'

sleep 2

# Write a simple config for ACME challenge
docker exec temp-nginx sh -c "cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'Waiting for SSL...'; add_header Content-Type text/plain; }
}
EOF
nginx -s reload"

sleep 1

# Get the certificate
docker run --rm \
    -v volo_certbot_certs:/etc/letsencrypt \
    -v volo_certbot_www:/var/www/certbot \
    certbot/certbot certonly \
    --webroot -w /var/www/certbot \
    -d "$DOMAIN" \
    --email admin@kingpinstrategies.com \
    --agree-tos \
    --non-interactive

# Stop temporary nginx
docker stop temp-nginx && docker rm temp-nginx

echo "✅ SSL certificate obtained!"
echo ""
echo "Now start Volo:"
echo "  cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d --build"
SSLEOF
    chmod +x "$APP_DIR/get-ssl.sh"
else
    echo "✅ DNS is correct: $DOMAIN → $SERVER_IP"

    # Get SSL certificate now
    if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ] && ! docker volume inspect volo_certbot_certs &>/dev/null 2>&1; then
        echo "   Obtaining SSL certificate..."

        # Temporary nginx for ACME
        docker run -d --name temp-nginx \
            -p 80:80 \
            -v volo_certbot_www:/var/www/certbot \
            nginx:alpine

        sleep 2

        docker exec temp-nginx sh -c "mkdir -p /var/www/certbot && cat > /etc/nginx/conf.d/default.conf << 'NGEOF'
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'ok'; add_header Content-Type text/plain; }
}
NGEOF
nginx -s reload"

        sleep 1

        docker run --rm \
            -v volo_certbot_certs:/etc/letsencrypt \
            -v volo_certbot_www:/var/www/certbot \
            certbot/certbot certonly \
            --webroot -w /var/www/certbot \
            -d "$DOMAIN" \
            --email admin@kingpinstrategies.com \
            --agree-tos \
            --non-interactive

        docker stop temp-nginx && docker rm temp-nginx
        echo "✅ SSL certificate obtained"
    else
        echo "✅ SSL certificate already exists"
    fi
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ Server setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Add your ANTHROPIC_API_KEY:"
echo "     nano $APP_DIR/.env.prod"
echo ""
echo "  2. Make sure DNS points here:"
echo "     $DOMAIN → $SERVER_IP"
echo ""
echo "  3. Get SSL (if DNS wasn't ready):"
echo "     cd $APP_DIR && bash get-ssl.sh"
echo ""
echo "  4. Start Volo:"
echo "     cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "  5. Check logs:"
echo "     docker compose -f docker-compose.prod.yml logs -f"
echo "══════════════════════════════════════════════"
