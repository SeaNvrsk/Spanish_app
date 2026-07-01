#!/usr/bin/env bash
# Install / update the app inside ~/db_reader/.fam (hidden from casual discovery).
# Run on the Ubuntu server as user ubuntu:
#   curl -sL ... | bash   OR   bash deploy/setup-db-reader.sh
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/db_reader/.fam}"
REPO="${REPO:-https://github.com/SeaNvrsk/Spanish_app.git}"
PORT="${PORT:-8010}"
PUBLIC_PATH="${PUBLIC_PATH:-}"

echo "→ Install dir: $INSTALL_DIR"

mkdir -p "$(dirname "$INSTALL_DIR")"

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "→ Updating existing clone…"
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "→ Cloning repository…"
  git clone "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Secret URL path (saved for nginx + rebuilds)
if [ -z "$PUBLIC_PATH" ]; then
  if [ -f "$INSTALL_DIR/.public_path" ]; then
    PUBLIC_PATH="$(cat "$INSTALL_DIR/.public_path")"
  else
    PUBLIC_PATH="/$(openssl rand -hex 4)"
    echo "$PUBLIC_PATH" > "$INSTALL_DIR/.public_path"
    chmod 600 "$INSTALL_DIR/.public_path"
  fi
fi
echo "$PUBLIC_PATH" > "$INSTALL_DIR/.public_path"
echo "→ Secret URL path: $PUBLIC_PATH"

# Backend
cd "$INSTALL_DIR/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt

# .env
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cp "$INSTALL_DIR/backend/.env.example" "$INSTALL_DIR/.env"
  SECRET=$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$INSTALL_DIR/.env"
  echo "" >> "$INSTALL_DIR/.env"
  echo "PUBLIC_PATH=$PUBLIC_PATH" >> "$INSTALL_DIR/.env"
  echo "VITE_BASE_PATH=$PUBLIC_PATH/" >> "$INSTALL_DIR/.env"
  echo ""
  echo "⚠️  Edit $INSTALL_DIR/.env — add OPENAI_API_KEY and CORS_ORIGINS"
fi

# Frontend build with hidden base path
cd "$INSTALL_DIR/frontend"

node_major() {
  node -v 2>/dev/null | sed 's/v//' | cut -d. -f1
}

ensure_node20() {
  if ! command -v node >/dev/null 2>&1 || [ "$(node_major)" -lt 20 ] 2>/dev/null; then
    echo "→ Installing Node.js 20 (current: $(node -v 2>/dev/null || echo 'not installed'))…"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
  echo "→ Node $(node -v), npm $(npm -v)"
}

ensure_node20
npm ci --silent
VITE_BASE_PATH="${PUBLIC_PATH}/" npm run build

# Tests
cd "$INSTALL_DIR"
if ./scripts/prod_tests.sh; then
  echo "→ Prod tests: OK"
else
  echo "⚠️  Some prod tests failed (check OPENAI_API_KEY in .env)"
fi

# systemd
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Installed to: $INSTALL_DIR"
echo "Secret URL:   https://YOUR_DOMAIN${PUBLIC_PATH}"
echo "(path saved in $INSTALL_DIR/.public_path)"
echo ""
echo "Next steps (once):"
echo "  1. nano $INSTALL_DIR/.env   # OPENAI_API_KEY, CORS_ORIGINS=https://your-domain"
echo "  2. sudo cp $INSTALL_DIR/deploy/espanol-db-reader.service /etc/systemd/system/espanol.service"
echo "  3. sudo systemctl daemon-reload && sudo systemctl enable --now espanol"
echo "  4. Add nginx location (see deploy/nginx-hidden-path.conf, replace PUBLIC_PATH)"
echo "  5. sudo nginx -t && sudo systemctl reload nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
