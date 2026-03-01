#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# Volo — Production Deploy Script
# Runs on the droplet as the restricted `deployer` user.
# Triggered by CI via SSH (authorized_keys command= restriction).
#
# What this script does NOT do (one-time ops, run setup.sh instead):
#   - Nginx site config
#   - SSL certificate via certbot
#   - .env.prod creation
#   - Docker / Compose installation
#
# To update this script on the server after changing it here:
#   scp scripts/deploy.sh root@<droplet>:/opt/volo/deploy.sh
#   chmod 750 /opt/volo/deploy.sh && chown root:deployer /opt/volo/deploy.sh
# ════════════════════════════════════════════════════════════

set -euo pipefail

DOMAIN="volo.kingpinstrategies.com"
PROJECT_DIR="/opt/volo"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.prod"
HEALTH_URL="http://127.0.0.1:8001/health"
REGISTRY="ghcr.io/illuminaticonsulting"

echo "══════════════════════════════════════════"
echo "  Volo Deploy — $(date -u +%FT%TZ)"
echo "══════════════════════════════════════════"

cd "$PROJECT_DIR"

# ── 1. Prerequisites ─────────────────────────────────────────
echo ""
echo "▶ Checking prerequisites..."

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ $ENV_FILE not found."
    echo "   Copy it to the droplet: scp .env.prod root@<droplet>:$ENV_FILE"
    exit 1
fi

if ! command -v docker &>/dev/null; then
    echo "❌ Docker not found."
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

DC="$COMPOSE --env-file $ENV_FILE -f $COMPOSE_FILE"

echo "✅ Docker: $(docker --version | head -1)"
echo "✅ Compose: $($COMPOSE version 2>/dev/null | head -1)"

# ── 2. Pull new images from GHCR ─────────────────────────────
echo ""
echo "▶ Pulling new images from GHCR..."

$DC pull api web

# ── 3. Tag current images as :previous (rollback target) ─────
echo ""
echo "▶ Saving current images for rollback..."

for svc in api web; do
    img=$($DC images -q "$svc" 2>/dev/null | head -1 || true)
    if [ -n "$img" ]; then
        docker tag "$img" "${REGISTRY}/volo-${svc}:previous"
        echo "  ✓ volo-${svc}: saved $img as :previous"
    else
        echo "  ℹ volo-${svc}: no running image to save (first deploy?)"
    fi
done

# ── 4. Deploy ─────────────────────────────────────────────────
echo ""
echo "▶ Starting new containers..."

$DC up -d --no-build api web

# ── 5. Health check ───────────────────────────────────────────
echo ""
echo "▶ Health check (10 attempts, 3s interval)..."

for i in $(seq 1 10); do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✅ API healthy on attempt $i"

        echo ""
        echo "▶ Pruning old images..."
        docker image prune -f > /dev/null

        echo ""
        echo "══════════════════════════════════════════"
        echo "  ✅ Deploy successful!"
        echo "  🌐 https://$DOMAIN"
        echo "══════════════════════════════════════════"
        exit 0
    fi
    echo "  Attempt $i/10 — not healthy yet, waiting 3s..."
    sleep 3
done

# ── 6. Rollback ───────────────────────────────────────────────
echo ""
echo "❌ Health check failed after 10 attempts — rolling back..."

for svc in api web; do
    if docker image inspect "${REGISTRY}/volo-${svc}:previous" > /dev/null 2>&1; then
        docker tag "${REGISTRY}/volo-${svc}:previous" "${REGISTRY}/volo-${svc}:latest"
        echo "  ✓ volo-${svc}: restored :previous"
    else
        echo "  ⚠ volo-${svc}: no :previous image to restore"
    fi
done

$DC up -d --no-build api web

echo ""
echo "══════════════════════════════════════════"
echo "  ⚠️  Rollback complete."
echo "  Check logs: $DC logs --tail=100 api"
echo "══════════════════════════════════════════"
exit 1
