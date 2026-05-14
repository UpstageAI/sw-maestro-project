import base64
import json
import logging
import os
import time

from openai import OpenAI

from prompts import VISION_EN, VISION_KO
from schemas import Context, Mission, Verdict
from seed import load_places


logger = logging.getLogger("duribeon")


_ETA_BY_CATEGORY = {"food": 25, "experience": 35, "place": 20}


def _fallback_mission(cand: dict, ctx: Context, idx: int) -> Mission:
    """Deterministic mission built straight from a curated place. Used to
    fill slots when the LLM repeats place_ids or skips some."""
    is_ko = ctx.language == "ko"
    name = cand["name_ko" if is_ko else "name_en"]
    desc = cand["desc_ko" if is_ko else "desc_en"]
    cat = cand["category"]

    if is_ko:
        if cat == "food":
            title, proof = f"{name}에서 한 입", "메뉴나 음식 사진"
        elif cat == "experience":
            title, proof = f"{name} 직접 체험", "체험 흔적 사진"
        else:
            title, proof = f"{name} 들러보기", "간판이나 공간 사진"
        route = f"{name} 쪽 골목까지 들어가봐."
    else:
        if cat == "food":
            title, proof = f"Try a bite at {name}", "Photo of the menu or dish"
        elif cat == "experience":
            title, proof = f"Try {name} hands-on", "Photo of you doing it"
        else:
            title, proof = f"Drop by {name}", "Photo of the sign or interior"
        route = f"Wander the alley where {name} sits."

    return Mission(
        id=f"fb_{cand['id']}_{idx}",
        title=title[:60],
        hook=desc[:160] if len(desc) >= 4 else f"{desc} ✦",
        place_id=cand["id"],
        place_name=name,
        route_hint=route[:200],
        proof_method=proof[:160],
        estimated_minutes=_ETA_BY_CATEGORY.get(cat, 30),
        category=cat,
    )


def load_seed() -> list[dict]:
    """Backward-compatible alias for the places list."""
    return load_places()


def query_curation_db(area: str, avoid_text: str = "", limit: int = 10) -> list[dict]:
    """Single tool: filter the curation JSON DB by area and avoidance hints."""
    places = [p for p in load_seed() if p["area"] == area]
    avoid_lower = (avoid_text or "").lower()
    blocked_tags = set()
    if any(k in avoid_lower for k in ["매운", "spicy"]):
        blocked_tags.add("spicy")
    if any(k in avoid_lower for k in ["술", "음주", "alcohol", "drink", "wine"]):
        blocked_tags.update({"bar", "wine", "drink"})
    if any(k in avoid_lower for k in ["해산물", "seafood"]):
        blocked_tags.add("seafood")

    if blocked_tags:
        places = [p for p in places if not (set(p["tags"]) & blocked_tags)]
    places.sort(key=lambda p: p.get("offbeat_score", 0), reverse=True)
    return places[:limit]


def detect_language(text: str) -> str:
    if not text:
        return "ko"
    hangul = sum(1 for c in text if "가" <= c <= "힣")
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    return "ko" if hangul >= ascii_letters else "en"


def _upstage_client() -> OpenAI:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY is not set. Copy .env.example to .env and fill it in.")
    base_url = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return OpenAI(api_key=api_key)


def _text_model() -> str:
    return os.getenv("UPSTAGE_TEXT_MODEL", "solar-pro2")


def _vision_model() -> str:
    return os.getenv("OPENAI_VISION_MODEL", "gpt-4o")


def verify_photo(image_bytes: bytes, mission: Mission, language: str) -> Verdict:
    b64 = base64.b64encode(image_bytes).decode()
    system = VISION_KO if language == "ko" else VISION_EN
    text_prompt = (
        f"미션 제목: {mission.title}\n"
        f"미션 훅: {mission.hook}\n"
        f"인증 대상: {mission.proof_method}\n"
        f"장소: {mission.place_name}\n"
        f"위 미션을 이 사진이 만족하는가?"
        if language == "ko"
        else f"Mission title: {mission.title}\n"
             f"Hook: {mission.hook}\n"
             f"Proof target: {mission.proof_method}\n"
             f"Place: {mission.place_name}\n"
             f"Does this photo satisfy the mission?"
    )

    model = _vision_model()
    logger.info("=" * 70)
    logger.info("→ LLM verify_photo (OpenAI)")
    logger.info(
        "  model=%s mission='%s' place=%s lang=%s image_bytes=%d (b64=%d)",
        model, mission.title, mission.place_name, language, len(image_bytes), len(b64),
    )
    logger.info("  text prompt:")
    for line in text_prompt.splitlines():
        logger.info("    %s", line)

    client = _openai_client()
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = resp.choices[0].message.content or "{}"

    logger.info("← LLM response (%d chars, %d ms):", len(raw), elapsed_ms)
    for line in raw.splitlines():
        logger.info("    %s", line)
    if getattr(resp, "usage", None) is not None:
        usage = resp.usage
        logger.info(
            "  usage: prompt=%s completion=%s total=%s",
            getattr(usage, "prompt_tokens", "?"),
            getattr(usage, "completion_tokens", "?"),
            getattr(usage, "total_tokens", "?"),
        )

    return Verdict.model_validate_json(raw)


# Re-export the LangGraph-backed implementations so main.py and other callers
# can keep `from agent import generate_missions, regenerate_mission_for_place`.
# The import sits at the bottom intentionally — the graph nodes lazy-import
# `_fallback_mission` and `query_curation_db` from this module, which are
# both defined above by the time this line runs.
from llm_graphs import generate_missions, regenerate_mission_for_place  # noqa: E402, F401
