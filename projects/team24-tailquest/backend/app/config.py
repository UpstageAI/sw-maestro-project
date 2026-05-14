from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    upstage_api_key: str = Field(default="")
    solar_model: str = Field(default="solar-pro3")
    use_mock_llm: bool = Field(default=False)
    allowed_origins: str = Field(default="http://localhost:3000")
    chroma_persist_dir: str = Field(default=".chroma")
    materials_upload_dir: str = Field(default=".materials")
    embedding_model_passage: str = Field(default="solar-embedding-1-large-passage")
    embedding_model_query: str = Field(default="solar-embedding-1-large-query")
    langgraph_state_db: str = Field(
        default=".langgraph_state.db",
        description="v1.1용 SqliteSaver DB 경로. 현재는 MemorySaver 사용 중.",
    )
    sqlite_path: str = Field(
        default="data/tq.db",
        description="세션/턴 영속화용 SQLite 파일 경로 (SQLAlchemy 동기 엔진).",
    )
    tavily_api_key: str = Field(default="")
    use_web_search: bool = Field(default=False)
    enable_llm_tool_calling: bool = Field(
        default=False,
        description=(
            "True 일 때 seed/question_generator 노드가 Solar function-calling 으로 "
            "web_search 도구를 자율적으로 호출. False 면 deterministic fallback만."
        ),
    )
    github_token: str = Field(
        default="",
        description=(
            "(선택) GitHub Personal Access Token. 비어있으면 익명 호출 → IP당 60회/h, "
            "값이 있으면 토큰당 5,000회/h. .md 자료 인입 시 사용."
        ),
    )
    jwt_secret: str = Field(
        default="",
        description=(
            "JWT 서명 키. 비어 있으면 프로세스 시작 시 임의의 secret 을 1회 생성해 "
            "사용 → 서버 재시작 시 모든 토큰 무효화. 운영에서는 .env 로 고정 권장."
        ),
    )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
