"""checklist_generator node — TOP 3 + 매장 메타 → 점검 To-Do 3~5개 (structured)."""

from __future__ import annotations

import os

from src.graph.trace import measure
from src.llm.upstage import complete_json_with_meta
from src.store import memory


CHECKLIST_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "description": "점검 To-Do 항목. 동사로 시작하는 짧은 명령형.",
            "items": {"type": "string"},
        },
    },
    "required": ["items"],
}


_SYSTEM = (
    "You are a Korean small-business operations consultant. NEVER explain, NEVER ask. "
    "Output ONLY valid JSON matching the json-schema. "
    "Generate 3-5 checklist items in Korean, each starting with a verb (명령형, no honorifics). "
    "Use the store's menu/price context to make items concrete (avoid generic advice like '친절하게 응대하세요'). "
    "Each item should be one short actionable sentence."
)


def checklist_agent_node(state: dict) -> dict:
    place_id = state["place_id"]
    meta = state.get("place_metadata") or memory.get_metadata(place_id)
    top3 = state.get("top3_data") or []

    if not top3:
        return {
            "checklist": [
                "부정 리뷰가 부족하여 점검 항목을 생성할 수 없습니다 (4주간 분석 데이터 부족)."
            ]
        }

    with measure("checklist", "llm") as log:
        top3_str = "\n".join(f"- {t['category']}: {t['freq']}회" for t in top3)
        menus = meta.get("menus") or []
        menu_str = (
            ", ".join(f"{m.get('name')}({m.get('price', '?')}원)" for m in menus[:8])
            or "(미입력)"
        )

        user = (
            f"매장: {meta.get('display_name', place_id)} ({meta.get('category', '미입력')})\n"
            f"가격대: {meta.get('price_range', '미입력')}\n"
            f"대표 메뉴: {menu_str}\n\n"
            f"TOP 3 반복 불만 (최근 4주):\n{top3_str}\n\n"
            f"위 패턴을 보고 이번 주 점검 To-Do 3~5개 생성."
        )

        result, meta_llm = complete_json_with_meta(
            prompt=user,
            system=_SYSTEM,
            schema=CHECKLIST_SCHEMA,
            model=os.getenv("MODEL_CHECKLIST", "solar-pro2"),
        )
        items = result.get("items", [])
        log["summary"] = f"점검 To-Do {len(items)}건 생성"
        log["details"] = {
            **meta_llm,
            "items_count": len(items),
            "top3_input": [t["category"] for t in top3],
        }

    return {"checklist": items, "node_log": [log]}
