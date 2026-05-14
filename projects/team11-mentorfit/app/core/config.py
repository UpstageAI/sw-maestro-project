from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    upstage_api_key: str = ""
    mock_mode: bool = False

    mentor_data_path: str = "data/mentors.json"
    api_base_url: str = "http://localhost:8000"

    candidate_top_k: int = 5
    prefilter_top_n: int = 30  # LLM에 넘기기 전 임베딩으로 걸러낼 후보 수
    candidate_tag_weight: float = 0.4
    candidate_semantic_weight: float = 0.6
    embedding_cache_ttl: int = 86400  # seconds

    mentor_max_teams: int = 3  # 멘토 1인당 최대 담당 가능 팀 수
    matched_list_stale_days: int = 7
    combination_model: str = "solar-pro3"
    report_model: str = "solar-pro3"

    team_profile_llm_model: str = "solar-pro3"
    team_profile_llm_temperature: float = 0.3
    team_profile_llm_max_tokens: int = 8196

    llm_endpoint_rate_limit: int = 30
    llm_endpoint_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def use_semantic(self) -> bool:
        return bool(self.upstage_api_key) and not self.mock_mode


settings = Settings()
