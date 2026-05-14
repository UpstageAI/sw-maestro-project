#!/usr/bin/env bash
set -euo pipefail

npm run qa:local
PYTHONPATH=BE BE/.venv/bin/python scripts/check_upstage_readiness.py --require-key --live
E2E_FE_URL="${E2E_FE_URL:-http://127.0.0.1:5173/}" E2E_BE_URL="${E2E_BE_URL:-http://127.0.0.1:8000}" npm run test:e2e
