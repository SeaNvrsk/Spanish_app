#!/usr/bin/env bash
# Start backend (FastAPI :8010) and frontend (Vite :5173) together for local dev.
# Vite proxies /api -> :8010, so open http://localhost:5173
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- Backend ---
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi
./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload &
BACK_PID=$!

# --- Frontend ---
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev &
FRONT_PID=$!

trap "kill $BACK_PID $FRONT_PID 2>/dev/null" EXIT
echo "Backend :8010  |  Frontend http://localhost:5173"
wait
