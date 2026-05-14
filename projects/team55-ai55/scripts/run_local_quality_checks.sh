#!/usr/bin/env bash
set -euo pipefail

npm run check:openapi
npm run check:upstage-ready
npm run test:be
npm run test:fe
npm run build:fe
npm run check:fe-bundle
npm run check:e2e-list
npm run check:local-servers
SMOKE_BASE_URL="${SMOKE_BASE_URL:-http://127.0.0.1:8000}" npm run smoke:local
npm run check:audit
git diff --check
