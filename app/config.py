from pydantic_settings import BaseSettings, SettingsConfigDict

_PRODUCTION_HOSTS = [
    "api.binance.com",
    "stream.binance.com",
    "ws-api.binance.com",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    binance_testnet_api_key: str
    binance_testnet_secret_key: str
    binance_testnet_rest_base_url: str = "https://testnet.binance.vision/api"
    binance_testnet_ws_stream_url: str = "wss://stream.testnet.binance.vision/ws"
    binance_testnet_ws_api_url: str = "wss://ws-api.testnet.binance.vision/ws-api/v3"

    database_url: str = "sqlite:///./coin_agent.db"
    ai_service_http_url: str = "http://localhost:8001"
    app_env: str = "local"
    log_level: str = "INFO"

    def model_post_init(self, __context: object) -> None:
        self._validate_no_production_urls()

    def _validate_no_production_urls(self) -> None:
        urls_to_check = [
            self.binance_testnet_rest_base_url,
            self.binance_testnet_ws_stream_url,
            self.binance_testnet_ws_api_url,
        ]
        for url in urls_to_check:
            for host in _PRODUCTION_HOSTS:
                if host in url:
                    raise ValueError(
                        f"Production Binance URL detected: {url}. "
                        "Only Testnet URLs are allowed."
                    )


settings = Settings()
