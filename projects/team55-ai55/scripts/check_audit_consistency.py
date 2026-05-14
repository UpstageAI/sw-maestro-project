from __future__ import annotations

import json
import re
import sys
from pathlib import Path


AUDIT_PATH = Path("docs/implementation-audit.md")
RUNBOOK_PATH = Path("docs/local-verification-runbook.md")
README_PATH = Path("README.md")

DONE_CRITERIA_TOKENS = [
    "3 RiskCheck",
    "5 Priority factors",
    "G2 gate",
    "5 E2E scenarios",
    "Schema Pass Rate",
    "Same snapshot 5 times deterministic",
    "LLM Reranker safety",
    "Soft Checks safety",
    "Forbidden-word regression",
    "Latency P95",
    "localStorage export/import",
    "발표 데모",
]


def fail(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, sort_keys=True))
    return 1


def main() -> int:
    text = AUDIT_PATH.read_text(encoding="utf-8")
    if not RUNBOOK_PATH.exists():
        return fail("Missing local verification runbook: docs/local-verification-runbook.md")
    if not README_PATH.exists():
        return fail("Missing root local handoff README: README.md")
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")
    required_sections = [
        "## Prompt-to-Artifact Checklist",
        "## Evidence Checklist",
        "## Current Verification Commands",
        "## Done Criteria Audit",
        "## Review Cycle Log",
        "## Completion Evidence",
        "## Known Gaps",
    ]
    for section in required_sections:
        if section not in text:
            return fail(f"Missing audit section: {section}")

    cycles = [int(match.group(1)) for match in re.finditer(r"^\| (\d+) \|", text, re.MULTILINE)]
    if not cycles:
        return fail("Review Cycle Log has no numbered cycles.")
    max_cycle = max(cycles)
    if len(set(cycles)) != max_cycle:
        return fail(f"Review cycles must be contiguous 1..{max_cycle}.")
    if max_cycle < 5:
        return fail("Review Cycle Log must document at least 5 cycles.")

    prompt_cycle_match = re.search(r"Review Cycle Log below documents (\d+) cycles", text)
    if not prompt_cycle_match:
        return fail("Prompt-to-Artifact Checklist must state the documented review cycle count.")
    prompt_cycle_count = int(prompt_cycle_match.group(1))
    if prompt_cycle_count != max_cycle:
        return fail(f"Prompt checklist cycle count {prompt_cycle_count} does not match latest cycle {max_cycle}.")

    done_criteria_block = text.split("## Done Criteria Audit", 1)[1].split("## Review Cycle Log", 1)[0]
    for token in DONE_CRITERIA_TOKENS:
        if token not in done_criteria_block:
            return fail(f"Done Criteria Audit must keep spec criterion token: {token}")

    completion_block = text.split("## Completion Evidence", 1)[1].split("## Known Gaps", 1)[0]
    for token in [
        "npm run check:completion",
        "configured\": true",
        "live_probe\": {\"ok\": true}",
        "5 passed",
        "Browser Playwright E2E",
        "Live Upstage API calls",
        "Full visual QA",
    ]:
        if token not in completion_block:
            return fail(f"Completion Evidence must include: {token}")

    known_gaps_block = text.split("## Known Gaps", 1)[1]
    if "No unresolved gaps" not in known_gaps_block:
        return fail("Known Gaps must state that there are no unresolved gaps.")

    for token in [
        "npm run qa:local",
        "npm run test:e2e",
        "npm run check:completion",
        "--require-key --live",
        "UPSTAGE_API_KEY",
        "update_goal",
    ]:
        if token not in runbook:
            return fail(f"Local verification runbook must include: {token}")

    for token in ["Final completion command", "scripts/check_completion_ready.sh", "npm run check:completion"]:
        if token not in text:
            return fail(f"Implementation audit must include final completion gate token: {token}")

    for token in [
        "http://127.0.0.1:5173/",
        "http://127.0.0.1:8000",
        "UPSTAGE_API_KEY",
        "npm run qa:local",
        "npm run check:completion",
        "completed successfully",
    ]:
        if token not in readme:
            return fail(f"Root README must include local handoff token: {token}")

    print(json.dumps({"ok": True, "latest_cycle": max_cycle}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
