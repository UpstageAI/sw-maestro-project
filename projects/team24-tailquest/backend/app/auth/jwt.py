"""HS256 JWT encode/decode for the auth router.

Secret resolution:
  - If `settings.jwt_secret` is non-empty, that value is used (so tokens
    survive restarts when the operator wants persistent logins).
  - Otherwise we fall back to a per-process random secret cached at module
    load (mirrors the BOOT_ID pattern in main.py — when the backend reboots
    without a configured secret, all outstanding tokens are invalidated and
    the FE is forced through /login again).

Token payload:
  {"sub": user_id, "exp": now+7d, "iat": now, "iss": "tailquest"}
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt as _jwt

from app.config import get_settings


_TOKEN_TTL_DAYS = 7
_ALG = "HS256"
_ISSUER = "tailquest"


# Per-process fallback when settings.jwt_secret is empty. Computed once at
# import time — restarting the backend rotates this and invalidates tokens.
_FALLBACK_SECRET = secrets.token_urlsafe(32)


def _resolve_secret() -> str:
    cfg = get_settings()
    return cfg.jwt_secret or _FALLBACK_SECRET


def encode_token(user_id: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=_TOKEN_TTL_DAYS)).timestamp()),
        "iss": _ISSUER,
    }
    return _jwt.encode(payload, _resolve_secret(), algorithm=_ALG)


def decode_token(token: str) -> str | None:
    """Decode a bearer token. Returns user_id (sub) or None on any failure."""
    if not token:
        return None
    try:
        payload = _jwt.decode(
            token,
            _resolve_secret(),
            algorithms=[_ALG],
            issuer=_ISSUER,
            options={"require": ["sub", "exp", "iss"]},
        )
    except _jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        return None
    return sub


__all__ = ["encode_token", "decode_token"]
