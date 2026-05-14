from __future__ import annotations

import secrets


def _suffix(length: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def mint_project_id() -> str:
    return f"proj_{_suffix(10)}"


def mint_milestone_id() -> str:
    return f"ms_{_suffix(8)}"


def mint_event_id() -> str:
    return f"evt_{_suffix(10)}"


def mint_risk_suggestion_id() -> str:
    return f"rs_{_suffix(8)}"

