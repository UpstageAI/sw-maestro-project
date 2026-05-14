from __future__ import annotations

import sys

from app.main import create_app
from generate_openapi_types import OUTPUT, render_openapi_types


def main() -> None:
    expected = render_openapi_types(create_app().openapi())
    actual = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if actual != expected:
        print("OpenAPI generated client is stale. Run: npm run generate:openapi", file=sys.stderr)
        raise SystemExit(1)
    print("OpenAPI generated client is up to date.")


if __name__ == "__main__":
    main()
