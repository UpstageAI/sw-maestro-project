"""Gateway 미들웨어 — ADR-0006 / ADR-0011 정합.

흐름: request → internal_secret_middleware → jwt_middleware → endpoint.
/health는 두 미들웨어 모두 우회 (Railway healthcheck용, ADR-0011).

JWT 검증된 sub은 request.state.user_id로 endpoint에 전달. LangSmith trace
메타데이터(owner_id_hash)에서도 사용 (Phase 3-C).
"""
from typing import Awaitable, Callable

import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from jwt import InvalidTokenError, PyJWKClient

from .config import get_settings

PUBLIC_PATHS = frozenset({"/health"})

_Next = Callable[[Request], Awaitable[Response]]


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """shared-types ErrorBody 정합 응답."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


# --------------------------------------------------------------
# X-Internal-Secret 검증
# --------------------------------------------------------------


async def internal_secret_middleware(request: Request, call_next: _Next) -> Response:
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    settings = get_settings()
    provided = request.headers.get("X-Internal-Secret")
    if provided != settings.internal_shared_secret:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHENTICATED",
            "invalid or missing internal secret",
        )
    return await call_next(request)


# --------------------------------------------------------------
# Bearer JWT 검증 (Supabase JWKS)
# --------------------------------------------------------------

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        # PyJWKClient는 cache_keys=True 시 lifespan(초) 만큼 TTL 캐싱.
        _jwks_client = PyJWKClient(
            settings.jwks_url,
            cache_keys=True,
            lifespan=300,
        )
    return _jwks_client


async def jwt_middleware(request: Request, call_next: _Next) -> Response:
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHENTICATED",
            "missing bearer token",
        )

    token = auth.removeprefix("Bearer ").strip()

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
    except InvalidTokenError as e:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHENTICATED",
            f"invalid token: {e}",
        )

    sub = decoded.get("sub")
    if not sub:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHENTICATED",
            "sub claim missing",
        )

    request.state.user_id = sub
    return await call_next(request)
