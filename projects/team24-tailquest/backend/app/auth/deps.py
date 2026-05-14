"""FastAPI dependencies for resolving the authenticated user.

Two flavors:
  - `current_user`  — required; raises 401 with WWW-Authenticate on any miss
  - `optional_user` — returns None instead of raising (for endpoints that
                      need to behave differently for guests vs members)

The token is read from the standard `Authorization: Bearer <jwt>` header.
Resolution path: header → JWT decode → `user_store.get_by_id`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import Header, HTTPException, status

from app.auth.jwt import decode_token
from app.services import user_store


_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def _strip_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


async def current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _strip_bearer(authorization)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
            headers=_UNAUTHORIZED_HEADERS,
        )
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었거나 유효하지 않습니다.",
            headers=_UNAUTHORIZED_HEADERS,
        )
    user = await asyncio.to_thread(user_store.get_by_id, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return user


async def optional_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | None:
    token = _strip_bearer(authorization)
    if token is None:
        return None
    user_id = decode_token(token)
    if user_id is None:
        return None
    return await asyncio.to_thread(user_store.get_by_id, user_id)


__all__ = ["current_user", "optional_user"]
