#!/usr/bin/env bash
# Production-style local server: built frontend + API on http://localhost:8010
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "Building frontend…"
  (cd "$ROOT/frontend" && [ -d node_modules ] || npm install && npm run build)
fi

echo "Open http://localhost:8010"
exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
