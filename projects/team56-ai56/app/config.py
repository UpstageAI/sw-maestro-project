import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_UPLOADS_DIR = DEFAULT_DATA_DIR / "uploads"
DEFAULT_ARTIFACTS_DIR = DEFAULT_DATA_DIR / "artifacts"
DEFAULT_SQLITE_PATH = DEFAULT_ARTIFACTS_DIR / "hireproof.db"


class Settings(BaseModel):
    app_name: str = "HireProof MVP"
    data_dir: Path = DEFAULT_DATA_DIR
    uploads_dir: Path = DEFAULT_UPLOADS_DIR
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR
    sqlite_path: Path = DEFAULT_SQLITE_PATH
    evaluator_mode: str = Field(default="mock")
    fallback_to_mock_on_llm_error: bool = True
    upstage_api_key: str | None = None
    upstage_model: str = "solar-pro3"
    upstage_base_url: str = "https://api.upstage.ai/v1"


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file(PROJECT_ROOT / ".env")
    settings = Settings(
        data_dir=_env_path("HIREPROOF_DATA_DIR", DEFAULT_DATA_DIR),
        uploads_dir=_env_path("HIREPROOF_UPLOADS_DIR", DEFAULT_UPLOADS_DIR),
        artifacts_dir=_env_path("HIREPROOF_ARTIFACTS_DIR", DEFAULT_ARTIFACTS_DIR),
        sqlite_path=_env_path("HIREPROOF_SQLITE_PATH", DEFAULT_SQLITE_PATH),
        evaluator_mode=os.getenv("HIREPROOF_EVALUATOR_MODE", "mock"),
        fallback_to_mock_on_llm_error=os.getenv("HIREPROOF_FALLBACK_TO_MOCK_ON_LLM_ERROR", "true").lower() in {"1", "true", "yes", "on"},
        upstage_api_key=os.getenv("HIREPROOF_UPSTAGE_API_KEY"),
        upstage_model=os.getenv("HIREPROOF_UPSTAGE_MODEL", "solar-pro3"),
        upstage_base_url=os.getenv("HIREPROOF_UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
    )
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings
