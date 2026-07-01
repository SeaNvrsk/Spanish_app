#!/usr/bin/env bash
# Run 5 independent production-readiness test suites.
# Usage: ./scripts/prod_tests.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [ ! -d .venv ]; then
  echo "❌ backend/.venv not found — run serve.sh or create venv first"
  exit 1
fi

./.venv/bin/pip install -q pytest httpx

SUITES=(
  tests/test_01_production_config.py
  tests/test_02_curriculum.py
  tests/test_03_schedule.py
  tests/test_04_api_smoke.py
  tests/test_05_deploy_bundle.py
)

FAILED=0
PASSED=0

for suite in "${SUITES[@]}"; do
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "▶ $(basename "$suite" .py)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if ./.venv/bin/pytest "$suite" -v --tb=short; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Result: $PASSED/5 suites passed, $FAILED failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ "$FAILED" -eq 0 ]
