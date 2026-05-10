from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Fairytale API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    supabase_project_ref: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""
    supabase_db_host: str = ""
    supabase_db_port: int = 5432
    supabase_db_name: str = "postgres"
    supabase_db_user: str = "postgres"
    supabase_db_sslmode: str = "require"
    supabase_db_password: str = ""

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    llm_provider: str = "fake"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    solar_api_key: str = ""
    solar_base_url: str = "https://api.upstage.ai/v1/solar"
    solar_model: str = "solar-pro"

    @property
    def resolved_supabase_url(self) -> str:
        if self.supabase_url:
            return self.supabase_url
        if self.supabase_project_ref:
            return f"https://{self.supabase_project_ref}.supabase.co"
        return ""

    @property
    def resolved_db_host(self) -> str:
        if self.supabase_db_host:
            return self.supabase_db_host
        if self.supabase_project_ref:
            return f"db.{self.supabase_project_ref}.supabase.co"
        return ""

    @property
    def database_url(self) -> str:
        if self.supabase_db_url:
            return self.supabase_db_url

        if not self.supabase_db_password or not self.resolved_db_host:
            return ""

        password = quote_plus(self.supabase_db_password)
        return (
            f"postgresql://{self.supabase_db_user}:{password}"
            f"@{self.resolved_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"
            f"?sslmode={self.supabase_db_sslmode}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
