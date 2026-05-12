from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_mode: str = "mock"
    stock_data_mode: str = ""

    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    kis_token_cache_path: str = ".cache/kis_auth.json"

    upstage_api_key: str = ""
    upstage_api_base: str = "https://api.upstage.ai/v1"
    llm_model: str = "solar-mini"


settings = Settings()
