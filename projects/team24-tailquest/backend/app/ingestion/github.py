"""GitHub markdown collector.

Public fetch via the GitHub REST API. Anonymous calls are rate-limited to
60/h per IP — once that's exhausted the API returns 403 with
"rate limit exceeded". Set `GITHUB_TOKEN` in the backend env to bump the
budget to 5,000/h per token.

Steps:
  1. Parse https://github.com/<owner>/<repo>[/...] → owner, repo
  2. Resolve default branch (HEAD) via /repos/{owner}/{repo}
  3. List the recursive tree of that branch
  4. For every blob whose path ends in .md/.mdx, fetch raw content
  5. Skip files >1MB and obvious binaries

Returns: list[(file_path, content)]
"""

from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

_API = "https://api.github.com"
_RAW_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
_MAX_FILE_BYTES = 1_000_000  # 1MB
_ALLOWED_EXT = (".md", ".mdx", ".markdown")


def _parse_repo_url(url: str) -> tuple[str, str]:
    """Pull (owner, repo) out of a GitHub URL or 'owner/repo' shorthand."""
    url = url.strip()
    if "/" in url and not url.startswith("http"):
        # 'owner/repo' shorthand
        parts = url.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1].rstrip(".git")

    parsed = urlparse(url)
    if "github.com" not in parsed.netloc:
        raise ValueError(f"GitHub URL이 아닙니다: {url}")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"owner/repo를 찾을 수 없습니다: {url}")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


async def _get_default_branch(client: httpx.AsyncClient, owner: str, repo: str) -> str:
    r = await client.get(f"{_API}/repos/{owner}/{repo}")
    r.raise_for_status()
    return r.json().get("default_branch", "main")


async def _list_tree(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str
) -> list[dict[str, Any]]:
    r = await client.get(
        f"{_API}/repos/{owner}/{repo}/git/trees/{branch}",
        params={"recursive": "1"},
    )
    r.raise_for_status()
    body = r.json()
    return body.get("tree", []) or []


async def _fetch_blob_content(
    client: httpx.AsyncClient, owner: str, repo: str, sha: str
) -> str | None:
    """Fetch raw blob content via the blobs API (base64-encoded)."""
    r = await client.get(f"{_API}/repos/{owner}/{repo}/git/blobs/{sha}")
    if r.status_code >= 400:
        log.warning("blob fetch failed %s/%s sha=%s status=%s", owner, repo, sha, r.status_code)
        return None
    body = r.json()
    encoding = body.get("encoding")
    content = body.get("content", "")
    if encoding == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception as e:
            log.warning("base64 decode failed: %s", e)
            return None
    return content


async def fetch_github_md(repo_url: str) -> list[tuple[str, str]]:
    """Recursively gather .md files from a public GitHub repo.

    Skips files >1MB and non-markdown extensions. Returns [(path, content), ...].
    Raises ValueError on bad URL, httpx.HTTPError on API failure.
    """
    owner, repo = _parse_repo_url(repo_url)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tail-question-ingest/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = get_settings().github_token.strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(headers=headers, timeout=_RAW_TIMEOUT) as client:
        branch = await _get_default_branch(client, owner, repo)
        tree = await _list_tree(client, owner, repo, branch)

        results: list[tuple[str, str]] = []
        for entry in tree:
            if entry.get("type") != "blob":
                continue
            path = entry.get("path", "")
            if not path.lower().endswith(_ALLOWED_EXT):
                continue
            size = entry.get("size") or 0
            if size > _MAX_FILE_BYTES:
                log.info("skip large md %s (%d bytes)", path, size)
                continue
            sha = entry.get("sha")
            if not sha:
                continue
            content = await _fetch_blob_content(client, owner, repo, sha)
            if content is None:
                continue
            # Defensive: some blobs declare small size but decode to large strings.
            if len(content.encode("utf-8")) > _MAX_FILE_BYTES:
                continue
            results.append((path, content))

    return results
