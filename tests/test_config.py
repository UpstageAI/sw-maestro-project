from fastapi.testclient import TestClient


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
