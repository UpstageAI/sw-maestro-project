"""pytest conftest — load .env so LangSmith tracing works in tests."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()
