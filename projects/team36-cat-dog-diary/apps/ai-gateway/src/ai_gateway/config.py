"""환경변수 기반 설정. 로컬 dev는 monorepo root .env.local 자동 로드,
Railway prod는 dashboard env vars로 inject (env_file 무시).

ADR-0011 환경변수 명세 정합. dev에서는 Next.js와 변수 공유를 위해
SUPABASE_URL / NEXT_PUBLIC_SUPABASE_URL 둘 다 alias로 수용.

LangChain·OpenAI SDK는 os.environ을 직접 읽으므로 get_settings()에서
명시적으로 export.
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]
ENV_FILE = ROOT_DIR / ".env.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    internal_shared_secret: str = Field(min_length=16)
    supabase_url: str = Field(
        validation_alias=AliasChoices("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"),
    )
    openai_api_key: str = Field(min_length=1)
    langsmith_api_key: str | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "cat-dog-diary-dev"

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()  # type: ignore[call-arg]
    # LangChain ChatOpenAI / openai SDK가 os.environ에서 직접 읽는 값들을 export.
    os.environ["OPENAI_API_KEY"] = s.openai_api_key
    # LangSmith trace는 LANGSMITH_TRACING=true 일 때만 활성화 (ADR-0012).
    if s.langsmith_api_key and s.langsmith_tracing:
        os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    return s
