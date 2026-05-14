import os
import logging
from typing import Any, Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "local"
    TITLE: str = "Multi-Agent Dating Platform API"
    VERSION: str = "1.0.0"
    APP_HOST: str = "http://localhost:8000"
    OPENAPI_URL: str = "/openapi.json"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    LOG_LEVEL: int = logging.DEBUG

    DB_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # Upstage Solar LLM
    UPSTAGE_API_KEY: str = ""
    UPSTAGE_BASE_URL: str = "https://api.upstage.ai/v1"
    SOLAR_MODEL: str = "solar-pro2"
    SOLAR_TEMPERATURE: float = 0.8
    SOLAR_MAX_TOKENS: int = 200

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def fastapi_kwargs(self) -> Dict[str, Any]:
        return {
            "title": self.TITLE,
            "version": self.VERSION,
            "servers": [
                {"url": self.APP_HOST, "description": os.getenv("ENV", "local")}
            ],
            "openapi_url": self.OPENAPI_URL,
            "docs_url": self.DOCS_URL,
            "redoc_url": self.REDOC_URL,
        }


class TestConfig(Config):
    DB_URL: str = "sqlite+aiosqlite:///./data/test.db"


class LocalConfig(Config): ...


class ProductionConfig(Config):
    LOG_LEVEL: int = logging.INFO
    DOCS_URL: str = ""
    REDOC_URL: str = ""


def get_config() -> Config:
    env = os.getenv("ENV", "local")
    return {
        "test": TestConfig(),
        "local": LocalConfig(),
        "prod": ProductionConfig(),
    }[env]


def is_local() -> bool:
    return get_config().ENV == "local"


config: Config = get_config()
