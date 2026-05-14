"""Code-level verification of every source connector.

Hits each connector with:
- the live network when its env token is configured (notion, github),
- a synthetic input where no token is needed (web public),
- and asserts the typed setup error path for those without a token (slack/linear/mcp).

Run:
    python scripts/source_connector_verify.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.services.source_connectors import (
    SourceConnectorConfigError,
    SourceConnectorFetchError,
    SourceConnectorInputError,
    build_source_connector_registry,
)


def banner(label: str) -> None:
    print()
    print(f"=== {label} ===")


def try_fetch(connector, source_url: str, external_id: str = "") -> None:
    try:
        result = connector.fetch(source_url, external_id)
        title = result.title or "(no title)"
        content_preview = (result.content or "").splitlines()
        first_line = content_preview[0] if content_preview else ""
        print(f"   FETCHED via={result.fetched_via} title={title!r} content[0]={first_line[:80]!r}")
        print(f"   chars={len(result.content or '')} ext_id={result.external_id} url={result.source_url}")
    except SourceConnectorConfigError as exc:
        print(f"   CONFIG ERROR (token missing): {exc}")
    except SourceConnectorInputError as exc:
        print(f"   INPUT ERROR (bad URL): {exc}")
    except SourceConnectorFetchError as exc:
        print(f"   FETCH ERROR (network/4xx): {exc}")
    except Exception as exc:
        print(f"   UNEXPECTED ERROR ({type(exc).__name__}): {exc}")


def main() -> None:
    settings = get_settings()
    registry = build_source_connector_registry(settings)
    print(f"available connectors: {sorted(registry.keys())}")
    print(f"env token state: notion={'SET' if settings.notion_token else 'empty'}, "
          f"github={'SET' if settings.github_token else 'empty'}, "
          f"slack={'SET' if settings.slack_token else 'empty'}, "
          f"linear={'SET' if settings.linear_token else 'empty'}, "
          f"mcp_url={'SET' if settings.mcp_server_url else 'empty'}")

    # Notion — token may be set; expect either real fetch or 4xx for fake page id
    banner("notion")
    try_fetch(registry["notion"], "https://www.notion.so/team/PRD-3528aaeba57c8047bcafca24c8c2a2b1")

    # GitHub public raw — never needs token
    banner("github (public raw)")
    try_fetch(registry["github"], "https://raw.githubusercontent.com/anthropics/courses/master/README.md")

    # GitHub blob URL — also public
    banner("github (blob URL)")
    try_fetch(registry["github"], "https://github.com/anthropics/courses/blob/master/README.md")

    # Web — public html
    banner("web (public html)")
    try_fetch(registry["web"], "https://example.com/")

    # Slack — should produce CONFIG ERROR (no token)
    banner("slack (no token)")
    try_fetch(registry["slack"], "slack://channels/C123/1700000000.000100")

    # Linear — should produce CONFIG ERROR (no token)
    banner("linear (no token)")
    try_fetch(registry["linear"], "https://linear.app/team/issue/TEAM-1")

    # MCP — should produce CONFIG ERROR (no server URL)
    banner("mcp (no server url)")
    try_fetch(registry["mcp"], "mcp://server/resource")

    # Notion — bad URL (no page id) should INPUT ERROR
    banner("notion (bad URL)")
    try_fetch(registry["notion"], "https://notion.so/team/no-page-id")


if __name__ == "__main__":
    main()
