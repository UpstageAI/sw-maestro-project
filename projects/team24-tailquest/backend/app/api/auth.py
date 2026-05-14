"""Auth endpoints — register / login / logout / me.

Response shape (camelCase to match `frontend/lib/api.ts`):
    AuthResponse  = { token: str, user: UserOut }
    UserOut       = { id, email, displayName, createdAt }

Behavior:
  - POST /auth/register
      201 — creates user + claims any orphan sessions whose
            sessions.user_id == request.email (case-insensitive).
      409 — email already registered.
  - POST /auth/login
      200 — { token, user }
      401 — credentials don't match
  - POST /auth/logout
      204 — no-op server-side; FE drops token.
  - GET  /auth/me
      200 — { id, email, displayName, createdAt }
      401 — missing / expired / invalid token

Token TTL: 7 days (see app.auth.jwt). FE must include it as
`Authorization: Bearer <token>`.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.auth.deps import current_user
from app.auth.jwt import encode_token
from app.log_format import stage
from app.services import user_store


router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- response shapes ----------

class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None = Field(default=None, serialization_alias="displayName")
    created_at: float = Field(default=0.0, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class AuthResponse(BaseModel):
    token: str
    user: UserOut

    model_config = ConfigDict(populate_by_name=True)


# ---------- request shapes ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(
        default=None,
        max_length=64,
        validation_alias="displayName",
        serialization_alias="displayName",
    )

    model_config = ConfigDict(populate_by_name=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(populate_by_name=True)


class ClaimRequest(BaseModel):
    legacy_user_id: str = Field(
        min_length=1,
        max_length=64,
        validation_alias="legacyUserId",
        serialization_alias="legacyUserId",
    )

    model_config = ConfigDict(populate_by_name=True)


class ClaimResponse(BaseModel):
    claimed: int

    model_config = ConfigDict(populate_by_name=True)


# ---------- helpers ----------

def _user_to_out(user: dict[str, Any]) -> UserOut:
    return UserOut(
        id=user["id"],
        email=user["email"],
        display_name=user.get("display_name"),
        created_at=float(user.get("created_at") or 0.0),
    )


# ---------- endpoints ----------

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
    response_model_by_alias=True,
)
async def register(payload: RegisterRequest) -> AuthResponse:
    email = payload.email.lower()
    stage("👤 [AUTH] register attempt", email=email)
    try:
        user = await asyncio.to_thread(
            user_store.create_user,
            email,
            payload.password,
            payload.display_name,
        )
    except ValueError as exc:
        stage("✗ [AUTH] register conflict", email=email, reason=str(exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    # Claim sessions whose user_id was previously the raw email (so users who
    # used the email-as-cookie legacy flow keep their history on first signup).
    claimed = 0
    try:
        claimed = await asyncio.to_thread(
            user_store.claim_orphan_sessions, user["id"], email,
        )
    except Exception:  # noqa: BLE001
        # Claim is best-effort — don't fail registration if the UPDATE blew up.
        pass

    token = encode_token(user["id"])
    stage(
        "✓ [AUTH] register ok",
        email=email,
        user_id=user["id"][:12],
        claimed_sessions=claimed,
    )
    return AuthResponse(token=token, user=_user_to_out(user))


@router.post(
    "/login",
    response_model=AuthResponse,
    response_model_by_alias=True,
)
async def login(payload: LoginRequest) -> AuthResponse:
    email = payload.email.lower()
    stage("👤 [AUTH] login attempt", email=email)
    user = await asyncio.to_thread(user_store.get_by_email, email)
    if user is None or not user_store.verify_password(user, payload.password):
        stage("✗ [AUTH] login rejected", email=email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = encode_token(user["id"])
    stage("✓ [AUTH] login ok", email=email, user_id=user["id"][:12])
    return AuthResponse(token=token, user=_user_to_out(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> Response:
    # Stateless JWT — FE just drops the token. Endpoint exists so the FE has
    # one place to call and so we can later add server-side revocation.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserOut,
    response_model_by_alias=True,
)
async def me(user: dict[str, Any] = Depends(current_user)) -> UserOut:
    return _user_to_out(user)


@router.post(
    "/claim",
    response_model=ClaimResponse,
    response_model_by_alias=True,
)
async def claim(
    payload: ClaimRequest,
    user: dict[str, Any] = Depends(current_user),
) -> ClaimResponse:
    """Attach orphan sessions whose `user_id == legacyUserId` to the caller.

    Idempotent: re-running with the same legacy id after a successful claim
    yields {claimed: 0}. Refuses to claim a legacy id already owned by a
    different registered user (returns 0 rather than stealing).
    """
    legacy_id = payload.legacy_user_id.strip()
    if not legacy_id:
        return ClaimResponse(claimed=0)

    # Stub User row created by migrate_users.py for this legacy id, if any.
    legacy_owner = await asyncio.to_thread(
        user_store.get_by_legacy_user_id, legacy_id,
    )
    rowcount = await asyncio.to_thread(
        user_store.claim_orphan_sessions, user["id"], legacy_id,
    )
    if rowcount and legacy_owner is not None and legacy_owner["id"] != user["id"]:
        # Clear the marker so re-running /auth/claim with the same string no-ops.
        await asyncio.to_thread(
            user_store.clear_legacy_marker, legacy_owner["id"],
        )
    return ClaimResponse(claimed=int(rowcount))


__all__ = ["router"]
