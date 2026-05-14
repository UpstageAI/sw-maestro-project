# Local Verification Runbook

This runbook is the final local verification path for the PM Agent.

## 1. Start Local Servers

Use the root scripts so FE and BE ports match the audited QA defaults.

```bash
npm run dev:be
```

In another terminal:

```bash
npm run dev:fe
```

Expected ports:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173/`

## 2. Run Local Quality Gates

```bash
npm run qa:local
```

This checks OpenAPI drift, Upstage dry-run readiness, backend tests, frontend contract tests, FE build, bundle size, Playwright scenario discovery, running FE/BE server health, API smoke, audit consistency, and whitespace.

## 3. Verify Live Upstage

After setting `BE/.env` with `UPSTAGE_API_KEY`, run:

```bash
PYTHONPATH=BE BE/.venv/bin/python scripts/check_upstage_readiness.py --require-key --live
```

Expected result:

- Exit code `0`
- JSON includes `"ok": true`
- JSON includes `"configured": true`
- JSON includes `"live_probe": {"ok": true}`

## 4. Run Browser E2E

```bash
E2E_FE_URL=http://127.0.0.1:5173/ E2E_BE_URL=http://127.0.0.1:8000 npm run test:e2e
```

Expected result:

- 5 Playwright scenarios pass.
- No Chromium `bootstrap_check_in ... Permission denied (1100)` launch failure.
- The scenarios cover normal 5-task project, unschedulable capacity, overload plus unassigned risk, circular dependency, and stale G2 schedule approval.

## 5. Completion Decision

The same final gate is available as one command:

```bash
npm run check:completion
```

Only after `npm run qa:local`, the live Upstage probe, and `npm run test:e2e` all pass, or equivalently `npm run check:completion` passes, should the active goal be considered complete.

At that point the agent may call `update_goal` with `status="complete"` and report the final elapsed time. The latest local run has satisfied this gate.
