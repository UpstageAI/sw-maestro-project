import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

from tavily import TavilyClient

from models.types import CompanyProfile

_CULTURE_KEYWORDS = ["문화", "인재상", "핵심가치", "일하는 방식", "자율", "책임", "협업", "성장", "고객 중심"]

_TECH_KEYWORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#", "Kotlin", "Swift",
    "React", "Vue", "Angular", "Next.js", "Node.js", "Django", "FastAPI", "Spring", "Flask",
    "Kubernetes", "Docker", "AWS", "GCP", "Azure",
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Kafka", "Elasticsearch",
]

_SEARCH_TIMEOUT_SECONDS = 10

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_TTL_SECONDS = 24 * 60 * 60


def search_company(company_name: str) -> CompanyProfile:
    """회사명으로 Tavily 검색 후 CompanyProfile 반환 (24시간 캐시)"""
    cached = _load_cache(company_name)
    if cached is not None:
        return cached

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다")

    client = TavilyClient(api_key=api_key)
    query = f"{company_name} 인재상 기술스택 회사문화 최신뉴스"

    result_holder: list = [None]
    exc_holder: list = [None]

    def _run() -> None:
        try:
            result_holder[0] = client.search(query=query, max_results=5)
        except Exception as e:
            exc_holder[0] = e

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=_SEARCH_TIMEOUT_SECONDS)

    if thread.is_alive():
        raise TimeoutError(f"Tavily 검색 타임아웃 ({_SEARCH_TIMEOUT_SECONDS}초): {company_name}")
    if exc_holder[0]:
        raise exc_holder[0]

    response = result_holder[0]
    results = response.get("results", [])

    if not results:
        profile = CompanyProfile(
            name=company_name,
            tech_stack=[],
            culture="",
            recent_news="검색 결과 없음",
            source_urls=[],
        )
        _save_cache(company_name, profile)
        return profile

    recent_news = "\n\n".join(r["content"] for r in results if r.get("content"))
    source_urls = [r["url"] for r in results if r.get("url")]

    profile = CompanyProfile(
        name=company_name,
        tech_stack=_extract_tech_stack(recent_news),
        culture=_extract_culture(recent_news),
        recent_news=recent_news,
        source_urls=source_urls,
    )

    _save_cache(company_name, profile)
    return profile


def _cache_path(company_name: str) -> Path:
    safe_name = hashlib.md5(company_name.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{safe_name}.json"


def _load_cache(company_name: str) -> CompanyProfile | None:
    path = _cache_path(company_name)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        if time.time() - cached["timestamp"] > CACHE_TTL_SECONDS:
            return None
        data = cached["data"]
        return CompanyProfile(**data)
    except Exception:
        return None


def _extract_culture(text: str) -> str:
    sentences = re.split(r"[.。\n]+", text)
    candidates = [s.strip() for s in sentences if s.strip() and any(kw in s for kw in _CULTURE_KEYWORDS)]
    if not candidates:
        return ""
    return ". ".join(candidates[:3])


def _extract_tech_stack(text: str) -> list[str]:
    found = []
    for keyword in _TECH_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE):
            found.append(keyword)
    return found


def _save_cache(company_name: str, profile: CompanyProfile) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(company_name)
    payload = {
        "timestamp": time.time(),
        "data": {
            "name": profile.name,
            "tech_stack": profile.tech_stack,
            "culture": profile.culture,
            "recent_news": profile.recent_news,
            "source_urls": profile.source_urls,
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
