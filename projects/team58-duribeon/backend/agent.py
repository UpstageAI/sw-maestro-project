import base64
import json
import logging
import os
import time

from openai import OpenAI

from prompts import SYSTEM_EN, SYSTEM_KO, VISION_EN, VISION_KO
from schemas import Context, Mission, MissionBundle, Verdict
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


def generate_missions(
    ctx: Context,
    rejected_place_ids: list[str] | None = None,
) -> tuple[list[Mission], list[dict]]:
    rejected_place_ids = rejected_place_ids or []
    candidates = query_curation_db(ctx.area, ctx.avoid)
    candidates = [p for p in candidates if p["id"] not in rejected_place_ids]

    # Fallback 1: full-area pool (still respecting rejected_place_ids).
    if len(candidates) < 5:
        backup = [
            p for p in load_seed()
            if p["area"] == ctx.area and p["id"] not in rejected_place_ids
        ]
        for p in backup:
            if p not in candidates:
                candidates.append(p)
            if len(candidates) >= 8:
                break

    # Fallback 2: seed exhausted in this area — recycle rejected places so the
    # LLM always has at least 5 candidates to choose from. The frontend can
    # treat repeats as the user dipping back into already-seen options.
    if len(candidates) < 5:
        full_area = [p for p in load_seed() if p["area"] == ctx.area]
        for p in full_area:
            if p not in candidates:
                candidates.append(p)
            if len(candidates) >= 5:
                break

    system = SYSTEM_KO if ctx.language == "ko" else SYSTEM_EN
    name_key = "name_ko" if ctx.language == "ko" else "name_en"
    desc_key = "desc_ko" if ctx.language == "ko" else "desc_en"
    candidate_lines = [
        {
            "place_id": p["id"],
            "name": p[name_key],
            "category": p["category"],
            "tags": p["tags"],
            "desc": p[desc_key],
        }
        for p in candidates
    ]

    user_payload = {
        "context": {
            "area": ctx.area,
            "group": ctx.group,
            "time_budget": ctx.time_budget,
            "mood": ctx.mood,
            "avoid": ctx.avoid,
        },
        "rejected_place_ids": rejected_place_ids,
        "candidates": candidate_lines,
        "instruction": (
            "위 CANDIDATES의 place_id 중에서만 골라 정확히 5개의 미션을 JSON으로 출력하라. "
            "사용자의 time_budget(시간 여유)에 맞춰 각 미션의 estimated_minutes를 합리적으로 잡아라. "
            "(예: '30분 정도'면 모두 ≤30분, '반나절'이면 60~120분 OK, '하루 종일'이면 자유롭게)"
            if ctx.language == "ko"
            else "Pick from CANDIDATES place_ids only and output exactly 5 missions as JSON. "
                 "Respect the user's time_budget when sizing each mission's estimated_minutes "
                 "(e.g., '~30 min' → all ≤30, 'half day' → 60-120 OK, 'all day' → free)."
        ),
    }

    model = _text_model()
    user_payload_json = json.dumps(user_payload, ensure_ascii=False)

    logger.info("=" * 70)
    logger.info("→ LLM generate_missions (Upstage)")
    logger.info(
        "  model=%s area=%s group=%s time=%s mood=%s avoid=%s lang=%s",
        model, ctx.area, ctx.group, ctx.time_budget, ctx.mood, ctx.avoid, ctx.language,
    )
    logger.info(
        "  rejected=%d candidates=%d (%s)",
        len(rejected_place_ids),
        len(candidates),
        ", ".join(c["id"] for c in candidates),
    )
    logger.info("  user payload (%d chars):", len(user_payload_json))
    for line in json.dumps(user_payload, ensure_ascii=False, indent=2).splitlines():
        logger.info("    %s", line)

    client = _upstage_client()
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload_json},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
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

    data = json.loads(raw)
    bundle = MissionBundle.model_validate(data)

    valid_ids = {p["id"] for p in candidates}
    cleaned: list[Mission] = []
    seen_ids: set[str] = set()
    for m in bundle.missions:
        if m.place_id not in valid_ids:
            continue
        if m.place_id in seen_ids:
            continue
        seen_ids.add(m.place_id)
        cleaned.append(m)

    fallback_filled = 0
    # If the LLM gave us fewer than 5 unique whitelisted missions, fill the
    # remaining slots with deterministic missions built from unused candidates.
    if len(cleaned) < 5:
        used_place_ids = {m.place_id for m in cleaned}
        idx = 0
        for cand in candidates:
            if cand["id"] in used_place_ids:
                continue
            cleaned.append(_fallback_mission(cand, ctx, idx))
            used_place_ids.add(cand["id"])
            idx += 1
            fallback_filled += 1
            if len(cleaned) >= 5:
                break

    logger.info(
        "  cleaned: %d unique missions (LLM %d, fallback %d)",
        len(cleaned),
        len(cleaned) - fallback_filled,
        fallback_filled,
    )
    for i, m in enumerate(cleaned[:5], 1):
        logger.info("    [%d] %s — %s (%s)", i, m.place_id, m.title, m.category)

    if len(cleaned) < 5:
        # Truly nothing to fill from — surface a clean error.
        raise RuntimeError(
            f"only {len(cleaned)} missions producible; check curation seed for area '{ctx.area}'"
        )
    return cleaned[:5], candidates


def regenerate_mission_for_place(
    ctx: Context,
    place_id: str,
    previous_title: str | None = None,
) -> Mission:
    """Generate a fresh mission for a SPECIFIC place. Used by the panel's
    "바꿔" (reroll) button — keeps the same place, swaps mission text only."""
    places = load_places()
    place = next((p for p in places if p["id"] == place_id), None)
    if place is None:
        raise RuntimeError(f"unknown place_id: {place_id!r}")

    is_ko = ctx.language == "ko"
    name = place["name_ko" if is_ko else "name_en"]
    desc = place["desc_ko" if is_ko else "desc_en"]

    system = SYSTEM_KO if is_ko else SYSTEM_EN

    instruction_ko = (
        "위 PLACE에 대해 새로운 미션 1개를 JSON으로 출력하라. 같은 장소지만 "
        "이전 미션과 다른 각도(다른 감각·다른 액션·다른 시간대·다른 사회적 상호작용)로 접근하라. "
        "사용자의 time_budget에 맞춰 estimated_minutes를 잡아라. "
        "출력 형식: {\"mission\": {Mission 스키마 모든 필드}}"
    )
    instruction_en = (
        "Generate ONE new mission for the PLACE above. Same place but a different "
        "angle from the previous one (different sense / action / time-of-day / social "
        "interaction). Size estimated_minutes to fit the user's time_budget. "
        "Output format: {\"mission\": {all Mission schema fields}}"
    )

    user_payload: dict = {
        "context": {
            "area": ctx.area,
            "group": ctx.group,
            "time_budget": ctx.time_budget,
            "mood": ctx.mood,
            "avoid": ctx.avoid,
        },
        "place": {
            "place_id": place["id"],
            "name": name,
            "category": place["category"],
            "tags": place["tags"],
            "desc": desc,
        },
        "instruction": instruction_ko if is_ko else instruction_en,
    }
    if previous_title:
        user_payload["previous_title"] = previous_title

    model = _text_model()
    user_payload_json = json.dumps(user_payload, ensure_ascii=False)

    logger.info("=" * 70)
    logger.info("→ LLM regenerate_mission_for_place (Upstage)")
    logger.info(
        "  model=%s place_id=%s lang=%s prev_title=%s",
        model, place_id, ctx.language, (previous_title or "-"),
    )
    logger.info("  user payload (%d chars):", len(user_payload_json))
    for line in json.dumps(user_payload, ensure_ascii=False, indent=2).splitlines():
        logger.info("    %s", line)

    client = _upstage_client()
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload_json},
        ],
        response_format={"type": "json_object"},
        temperature=0.95,  # higher temperature → more variety on retry
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = resp.choices[0].message.content or "{}"

    logger.info("← LLM response (%d chars, %d ms):", len(raw), elapsed_ms)
    for line in raw.splitlines():
        logger.info("    %s", line)

    data = json.loads(raw)
    # Accept {mission: {...}}, {missions: [{...}]}, or a bare mission object.
    if isinstance(data, dict):
        if "mission" in data and isinstance(data["mission"], dict):
            m_data = data["mission"]
        elif "missions" in data and isinstance(data["missions"], list) and data["missions"]:
            m_data = data["missions"][0]
        else:
            m_data = data

    try:
        mission = Mission.model_validate(m_data)
    except Exception as e:
        logger.info("  validation failed (%s) — using deterministic fallback", e)
        return _fallback_mission(place, ctx, int(time.time()) % 1000)

    # Force place anchoring even if the LLM drifted.
    if mission.place_id != place_id or mission.place_name != name:
        mission = Mission(
            **{**mission.model_dump(), "place_id": place_id, "place_name": name}
        )

    logger.info("  result: %s — %s (%s)", mission.place_id, mission.title, mission.category)
    return mission


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
