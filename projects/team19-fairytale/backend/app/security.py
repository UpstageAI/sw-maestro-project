from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError as PyJWTInvalidTokenError

from app.config import settings
from app.models.api import TokenPayload

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16
KEY_LENGTH = 32


class InvalidTokenError(ValueError):
    """Raised when an access token is missing required claims or is invalid."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=KEY_LENGTH,
    )
    return "$".join(
        [
            PBKDF2_ALGORITHM,
            str(PBKDF2_ITERATIONS),
            _b64encode(salt),
            _b64encode(derived_key),
        ]
    )


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = stored_password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if algorithm != PBKDF2_ALGORITHM:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _b64decode(salt),
        int(iterations),
        dklen=KEY_LENGTH,
    )
    return hmac.compare_digest(_b64encode(derived_key), expected_hash)


def create_access_token(*, user_id: str, email: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    expires_in = int((expires_at - now).total_seconds())
    return token, expires_in


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        token_payload = TokenPayload.model_validate(payload)
    except PyJWTInvalidTokenError as exc:
        raise InvalidTokenError("Invalid or expired access token.") from exc
    except ValueError as exc:
        raise InvalidTokenError("Invalid access token payload.") from exc

    if token_payload.type != "access":
        raise InvalidTokenError("Unsupported token type.")

    return token_payload
