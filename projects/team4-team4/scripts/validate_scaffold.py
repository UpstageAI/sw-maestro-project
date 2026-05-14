from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "CONTRIBUTING.md",
    "TASKS.md",
    ".env.example",
    "docs/API_CONTRACT.md",
    "docs/PROJECT_STRUCTURE.md",
    "examples/sample_inputs.md",
    "examples/sample_response.json",
    "prompts/system_prompt.md",
    "prompts/claim_prompt.md",
    "backend/app/main.py",
    "backend/app/generator.py",
    "backend/requirements.txt",
    "frontend/package.json",
    "frontend/app/page.tsx",
    "frontend/lib/api.ts",
    "tests/playwright.config.ts",
    ".github/workflows/ci.yml",
]


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {', '.join(missing)}")

    sample = json.loads((ROOT / "examples/sample_response.json").read_text(encoding="utf-8"))
    claims = sample["document"]["claims"]
    if len(claims) != 4:
        raise SystemExit("sample_response.json must include exactly 4 claims")

    print("scaffold-ok")


if __name__ == "__main__":
    main()

