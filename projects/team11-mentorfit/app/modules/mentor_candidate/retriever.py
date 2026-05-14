import json
import math
import time
import random
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.upstage import upstage_client
from app.modules.mentor_candidate.schemas import Mentor, TeamProfile

_CACHE_FILE = Path("data/cache/mentor_embeddings_v2.json")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x**2 for x in a))
    norm_b = math.sqrt(sum(x**2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_cache() -> dict:
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


async def _get_embedding(text: str, cache_key: Optional[str] = None) -> Optional[list[float]]:
    if settings.mock_mode:
        return [random.uniform(-1, 1) for _ in range(4096)]

    if not settings.upstage_api_key:
        return None

    if cache_key:
        cache = _load_cache()
        entry = cache.get(cache_key)
        if entry and (time.time() - entry["timestamp"]) < settings.embedding_cache_ttl:
            return entry["embedding"]

    try:
        embedding = await upstage_client.get_embedding(text, model="solar-embedding-1-large-passage")
        
        if cache_key and embedding:
            cache = _load_cache()
            cache[cache_key] = {"embedding": embedding, "timestamp": time.time()}
            _save_cache(cache)
            
        return embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def _mentor_to_text(mentor: Mentor) -> str:
    career_str = ", ".join([f"{c[0]}({c[1]}년)" for c in mentor.career])
    return f"기술스택: {', '.join(mentor.stacks)} 도메인: {', '.join(mentor.domains)} 목표: {mentor.target} 관심사: {mentor.hobbie} 경력: {career_str}"


def _team_to_text(team: TeamProfile) -> str:
    return f"기술스택: {team.skills} R&R: {team.members_rnr} 프로젝트: {team.project_plan_tech_goals} 목표: {team.maestro_program_goals} 필요사항: {team.mentoring_needs} 조건: {team.fit_conditions}"


async def filter_mentors(team_profile: TeamProfile, mentors: list[Mentor], top_n: int = 30) -> list[Mentor]:
    """
    임베딩 코사인 유사도를 기반으로 LLM에 넘길 N명의 멘토를 1차 필터링합니다.
    API 키가 없거나 에러 발생 시 원래 리스트의 앞부분을 그대로 반환합니다.
    """
    team_text = _team_to_text(team_profile)
    team_emb = await _get_embedding(team_text)

    if team_emb is None:
        return mentors[:top_n]

    scored_mentors = []
    for mentor in mentors:
        mentor_text = _mentor_to_text(mentor)
        mentor_emb = await _get_embedding(mentor_text, cache_key=str(mentor.mentor_id))
        
        sim = _cosine_similarity(team_emb, mentor_emb) if mentor_emb else 0.0
        scored_mentors.append((sim, mentor))

    # 유사도 기준 내림차순 정렬
    scored_mentors.sort(key=lambda x: x[0], reverse=True)
    
    # 상위 N명 반환
    return [m for score, m in scored_mentors[:top_n]]
