import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("BINANCE_TESTNET_API_KEY", "test_api_key")
os.environ.setdefault("BINANCE_TESTNET_SECRET_KEY", "test_secret_key")

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
