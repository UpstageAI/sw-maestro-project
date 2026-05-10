import hashlib
import hmac
import time
from urllib.parse import urlencode

from app.services.binance_auth_service import build_signed_params, make_timestamp, sign_params

SECRET_KEY = "test_secret_key"


def test_make_timestamp_is_recent():
    before = int(time.time() * 1000)
    ts = make_timestamp()
    after = int(time.time() * 1000)
    assert before <= ts <= after


def test_sign_params_matches_hmac():
    params = {"symbol": "BTCUSDT", "side": "BUY", "timestamp": 1715000000000}
    expected = hmac.new(
        SECRET_KEY.encode("utf-8"),
        urlencode(params).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert sign_params(SECRET_KEY, params) == expected


def test_sign_params_changes_with_different_secret():
    params = {"symbol": "BTCUSDT", "timestamp": 1715000000000}
    sig1 = sign_params("secret_a", params)
    sig2 = sign_params("secret_b", params)
    assert sig1 != sig2


def test_build_signed_params_includes_timestamp_and_signature():
    params = {"symbol": "BTCUSDT", "side": "BUY"}
    signed = build_signed_params(SECRET_KEY, params)
    assert "timestamp" in signed
    assert "signature" in signed


def test_build_signed_params_does_not_mutate_original():
    params = {"symbol": "BTCUSDT"}
    build_signed_params(SECRET_KEY, params)
    assert "timestamp" not in params
    assert "signature" not in params


def test_build_signed_params_signature_is_valid():
    params = {"symbol": "BTCUSDT", "side": "SELL"}
    signed = build_signed_params(SECRET_KEY, params)
    params_without_sig = {k: v for k, v in signed.items() if k != "signature"}
    expected_sig = sign_params(SECRET_KEY, params_without_sig)
    assert signed["signature"] == expected_sig
