"""환경 변수, 모델 셀렉션, 동작 상수."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")
GITHUB_PAT_DEFAULT = os.environ.get("GITHUB_PAT", "")

# Upstage는 단일 모델 (solar-pro3). 비용/품질 분기는 reasoning_effort로.
MODEL_NAME = "solar-pro3"
EFFORT_FAST = "low"   # 작성용 (기/승/결, context compress)
EFFORT_DEEP = "high"  # 추론·판정용 (전 issue_predictor / writer / validator)

MAX_REFINE_ITER = int(os.environ.get("MAX_REFINE_ITER", "3"))
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", "90"))

# Repo size guards (토큰 폭발 방지)
MAX_COMMITS_FETCH = 300
MAX_FILES_FETCH = 30
MAX_FILE_SIZE_KB = 200

CORE_DIRS = ["src", "lib", "app", "internal", "pkg"]
CORE_FILES = [
    "README.md", "README.rst",
    "package.json", "requirements.txt", "pyproject.toml", "Pipfile",
    "go.mod", "Cargo.toml", "build.gradle", "pom.xml",
    "Dockerfile", "docker-compose.yml",
    "CHANGELOG.md", "RELEASES.md",
]

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache"
OUTPUT_DIR = ROOT / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
