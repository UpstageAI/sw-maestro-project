from fastapi.testclient import TestClient

from app.config import Settings


def test_get_testnet_config_success(client: TestClient):
    resp = client.get('/api/v1/testnet/config')

    assert resp.status_code == 200
    data = resp.json()
    assert data['restBaseUrl'] == 'https://testnet.binance.vision/api'
    assert data['wsStreamUrl'] == 'wss://stream.testnet.binance.vision/ws'
    assert data['wsApiUrl'] == 'wss://ws-api.testnet.binance.vision/ws-api/v3'


def test_get_testnet_config_response_uses_camel_case(client: TestClient):
    resp = client.get('/api/v1/testnet/config')

    assert resp.status_code == 200
    data = resp.json()
    assert 'restBaseUrl' in data
    assert 'wsStreamUrl' in data
    assert 'wsApiUrl' in data


def test_default_cors_origins_include_local_vite_ports():
    assert Settings.model_fields['cors_origins'].default == [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]


def test_local_settings_merge_required_dev_cors_origins():
    settings = Settings(
        binance_testnet_api_key='test_api_key',
        binance_testnet_secret_key='test_secret_key',
        app_env='local',
        cors_origins=['http://localhost:3000'],
    )

    assert settings.cors_origins == [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]


def test_non_local_settings_keep_user_cors_origins():
    settings = Settings(
        binance_testnet_api_key='test_api_key',
        binance_testnet_secret_key='test_secret_key',
        app_env='testnet',
        cors_origins=['http://localhost:3000'],
    )

    assert settings.cors_origins == ['http://localhost:3000']
