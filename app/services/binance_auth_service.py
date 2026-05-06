import hashlib
import hmac
import time
from urllib.parse import urlencode


def make_timestamp() -> int:
    return int(time.time() * 1000)


def sign_params(secret_key: str, params: dict) -> str:
    query_string = urlencode(params)
    return hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_signed_params(secret_key: str, params: dict) -> dict:
    signed = dict(params)
    signed["timestamp"] = make_timestamp()
    signed["signature"] = sign_params(secret_key, signed)
    return signed
