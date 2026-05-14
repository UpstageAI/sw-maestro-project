"""LangGraph 노드 구현 (PRD US-008 ~ US-012, FR-9 ~ FR-15).

- B: 슬롯 추출 + 변경 의도 휴리스틱 (LLM)
- C: 후속 질문 생성 (LLM)
- D: 9개 슬롯 → SQL WHERE 절 (결정론적, LLM 미사용 — FR-13 안전성 우선)
- E: SQLite 조회 (LLM 미사용)
- F: 자연어 추천 응답 (LLM)
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from graph.llm import invoke_with_retry, make_llm
from graph.normalize import apply_canonical, extract_cpu_keyword
from graph.prompts import NODE_B_SYSTEM, NODE_C_SYSTEM, NODE_F_SYSTEM
from graph.state import (
    SLOT_KEYS,
    LaptopChatState,
    Slots,
    compute_is_complete,
    missing_keys,
)


_CHANGE_INTENT_RE = re.compile(
    r"바꿔|바꿀게|올려|낮춰|수정|변경|대신|말고|아니라|더\s|덜\s|까지"
)


def _last_user_text(state: LaptopChatState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


def _log(node: str, **fields: Any) -> None:
    payload = {"node": node, **fields}
    try:
        line = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        line = str(payload)
    try:
        print(line)
    except UnicodeEncodeError:
        # stdout 인코딩이 cp949 등 BMP 미지원이고 reconfigure 도 실패한 경우의 안전망.
        # ASCII-replace 로 강등해서 출력만 한다 — 그래프 진행은 절대 끊지 않음.
        try:
            print(line.encode("ascii", "replace").decode("ascii"))
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Node B
# ---------------------------------------------------------------------------

class _SlotsModel(BaseModel):
    screen_inch: Any = Field(default=None)
    weight_kg: Any = Field(default=None)
    os: Any = Field(default=None)
    resolution: Any = Field(default=None)
    brightness_nits: Any = Field(default=None)
    cpu: Any = Field(default=None)
    ram_gb: Any = Field(default=None)
    storage_gb: Any = Field(default=None)
    price_krw: Any = Field(default=None)


def _parse_node_b_json(content: str) -> tuple[dict[str, Any], str | None, list[str]]:
    """LLM 응답을 (slots, use_case, picked_from_options) 로 파싱.

    기대 형식: {"slots": {...9개...}, "use_case": "..."|null, "picked_from_options": [...]}
    구버전 평탄 형식도 폴백 허용 (use_case=None, picked=[]).
    """
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    data = json.loads(text)

    if isinstance(data, dict) and "slots" in data and isinstance(data["slots"], dict):
        slots_raw = data["slots"]
        use_case = data.get("use_case")
        picked_raw = data.get("picked_from_options") or []
    else:
        slots_raw = data
        use_case = None
        picked_raw = []

    slots = _SlotsModel(**slots_raw).model_dump()
    if use_case is not None and not isinstance(use_case, str):
        use_case = None
    picked = [k for k in picked_raw if isinstance(k, str) and k in SLOT_KEYS]
    return slots, use_case, picked


def _extract_slots_via_llm(
    user_text: str,
    current_slots: Slots,
    prev_slot_options: dict[str, list[dict[str, Any]]],
    prev_use_case: str | None,
) -> tuple[dict[str, Any], str | None, list[str]]:
    llm = make_llm(role="fast", json_mode=True, temperature=0.1)
    msgs = [
        SystemMessage(content=NODE_B_SYSTEM),
        HumanMessage(
            content=(
                f"현재까지 채워진 슬롯: {json.dumps(current_slots, ensure_ascii=False)}\n"
                f"prev_use_case: {json.dumps(prev_use_case, ensure_ascii=False)}\n"
                f"prev_slot_options (직전 턴에 사용자에게 제시된 옵션): "
                f"{json.dumps(prev_slot_options, ensure_ascii=False)}\n"
                f"사용자 발화: {user_text}\n\n"
                "응답 스키마: {\"slots\": {...9...}, \"use_case\": \"...\"|null, "
                "\"picked_from_options\": [...]} JSON 한 개로만 응답."
            )
        ),
    ]

    last_err: Exception | None = None
    for _ in range(2):
        try:
            resp = invoke_with_retry(llm, msgs, max_attempts=1)
            return _parse_node_b_json(resp.content if hasattr(resp, "content") else str(resp))
        except (json.JSONDecodeError, ValidationError, Exception) as e:  # noqa: BLE001
            last_err = e
    _log("B", warning="llm_extract_failed", error=str(last_err))
    return ({k: None for k in SLOT_KEYS}, None, [])


def _merge_slots(current: Slots, extracted: dict[str, Any], user_text: str) -> Slots:
    has_change_intent = bool(_CHANGE_INTENT_RE.search(user_text))
    merged: Slots = dict(current)  # type: ignore[assignment]
    for key in SLOT_KEYS:
        new_v = extracted.get(key)
        if new_v in (None, ""):
            continue
        old_v = current.get(key)
        if old_v is None:
            merged[key] = new_v  # type: ignore[literal-required]
            continue
        if has_change_intent and str(new_v) != str(old_v):
            merged[key] = new_v  # type: ignore[literal-required]
    return merged


def node_b_evaluate(state: LaptopChatState) -> dict[str, Any]:
    user_text = _last_user_text(state)
    current_slots: Slots = state.get("slots") or {k: None for k in SLOT_KEYS}  # type: ignore[assignment]
    prev_inferred: list[str] = list(state.get("inferred_keys") or [])
    prev_slot_options: dict[str, list[dict[str, Any]]] = dict(state.get("slot_options") or {})
    prev_use_case: str | None = state.get("use_case")

    extracted_raw, detected_use_case, picked_from_options = _extract_slots_via_llm(
        user_text, current_slots, prev_slot_options, prev_use_case
    )
    merged_raw = _merge_slots(current_slots, extracted_raw, user_text)
    cleaned = apply_canonical(dict(merged_raw))
    new_slots: Slots = {k: cleaned.get(k) for k in SLOT_KEYS}  # type: ignore[assignment]

    # inferred_keys (의미: "옵션에서 골라주신 키") 갱신:
    #  1) 이번 턴에 picked_from_options 로 채워진 키를 추가 (단, 새 값이 실제로 채워졌을 때).
    #  2) 사용자가 자유입력으로 명시한 키 (extracted 에 non-null 인데 picked_from_options 에 없음)
    #     는 prev_inferred 에서 제거 (배지 사라짐).
    #  3) 슬롯이 None 인 키는 안전장치로 제거.
    inferred = set(prev_inferred)
    explicit_this_turn = {
        k
        for k in SLOT_KEYS
        if extracted_raw.get(k) not in (None, "") and k not in picked_from_options
    }
    inferred -= explicit_this_turn
    for k in picked_from_options:
        if new_slots.get(k) is not None:
            inferred.add(k)
    inferred = {k for k in inferred if new_slots.get(k) is not None}
    final_inferred = sorted(inferred)

    use_case = detected_use_case if detected_use_case else prev_use_case

    is_complete = compute_is_complete(new_slots)
    turn_count = int(state.get("turn_count") or 0) + 1
    _log(
        "B",
        event="exit",
        slots=new_slots,
        use_case=use_case,
        picked_from_options=picked_from_options,
        inferred_keys=final_inferred,
        is_complete=is_complete,
        turn_count=turn_count,
    )

    # slot_options 는 소비됐으므로 비움 — Node C 가 다음 턴에 새로 채울 것.
    return {
        "slots": new_slots,
        "use_case": use_case,
        "slot_options": {},
        "inferred_keys": final_inferred,
        "is_complete": is_complete,
        "turn_count": turn_count,
    }


# ---------------------------------------------------------------------------
# Node C
# ---------------------------------------------------------------------------

_KEY_LABELS = {
    "screen_inch": "화면 크기(인치)",
    "weight_kg": "무게(kg)",
    "os": "OS(Windows/macOS/FreeDOS/Linux)",
    "resolution": "해상도(예: FHD, QHD, 4K)",
    "brightness_nits": "밝기(니트)",
    "cpu": "CPU(예: 인텔 i5, 애플 M2, 라이젠 7)",
    "ram_gb": "RAM(메모리, GB)",
    "storage_gb": "저장 용량(GB)",
    "price_krw": "예산(원)",
}


def _recent_assistant_questions(state: LaptopChatState, n: int = 3) -> list[str]:
    out: list[str] = []
    for m in reversed(state.get("messages") or []):
        if isinstance(m, AIMessage):
            out.append(str(m.content))
            if len(out) >= n:
                break
    return list(reversed(out))


_GROUPS = {
    "display": ("screen_inch", "resolution", "brightness_nits"),
    "perf": ("cpu", "ram_gb", "storage_gb"),
    "general": ("os", "weight_kg", "price_krw"),
}
_GROUP_PRIORITY = ("display", "perf", "general")


def _pick_group(missing: list[str]) -> list[str]:
    """미충족 슬롯이 가장 많이 남은 그룹의 미충족 키만 우선순위 순으로 반환."""
    missing_set = set(missing)
    best_group: tuple[str, ...] | None = None
    best_count = 0
    for name in _GROUP_PRIORITY:
        keys = _GROUPS[name]
        cnt = sum(1 for k in keys if k in missing_set)
        if cnt > best_count:
            best_count = cnt
            best_group = keys
    if not best_group:
        return missing[:1]
    return [k for k in best_group if k in missing_set]


def _parse_node_c_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Node C response must be a JSON object")
    asked = data.get("asked_slots") or []
    options = data.get("options") or {}
    qmd = data.get("question_markdown") or ""
    if not isinstance(asked, list) or not isinstance(options, dict) or not isinstance(qmd, str):
        raise ValueError("Node C JSON missing required fields")
    asked = [k for k in asked if isinstance(k, str) and k in SLOT_KEYS]
    cleaned_options: dict[str, list[dict[str, Any]]] = {}
    for k in asked:
        opts = options.get(k) or []
        if not isinstance(opts, list):
            continue
        cleaned: list[dict[str, Any]] = []
        for o in opts:
            if isinstance(o, dict) and "value" in o and "label" in o:
                cleaned.append(
                    {
                        "value": o.get("value"),
                        "label": str(o.get("label", "")),
                        "rationale": str(o.get("rationale", "")),
                    }
                )
        if cleaned:
            cleaned_options[k] = cleaned
    if not cleaned_options or not qmd.strip():
        raise ValueError("Node C produced no usable options or question")
    return {
        "asked_slots": [k for k in asked if k in cleaned_options],
        "options": cleaned_options,
        "question_markdown": qmd.strip(),
    }


def node_c_followup(state: LaptopChatState) -> dict[str, Any]:
    slots: Slots = state.get("slots") or {}  # type: ignore[assignment]
    missing = missing_keys(slots)
    target_group = _pick_group(missing)
    use_case = state.get("use_case")
    recent = _recent_assistant_questions(state)
    recent_block = (
        "직전 질문(반복 금지):\n" + "\n".join(f"  · {q}" for q in recent)
        if recent
        else "직전 질문 없음"
    )

    llm = make_llm(role="primary", temperature=0.4)
    msgs = [
        SystemMessage(content=NODE_C_SYSTEM),
        HumanMessage(
            content=(
                f"미충족 슬롯 전체: {missing}\n"
                f"이번 턴에 묶어서 물을 슬롯 후보(같은 그룹): {target_group}\n"
                f"use_case: {json.dumps(use_case, ensure_ascii=False)}\n"
                f"이미 채워진 슬롯: {json.dumps(slots, ensure_ascii=False)}\n"
                f"{recent_block}\n\n"
                "위 정보를 바탕으로 asked_slots / options / question_markdown 을 가진 JSON 으로만 응답하세요."
            )
        ),
    ]

    try:
        resp = invoke_with_retry(llm, msgs, max_attempts=2)
        parsed = _parse_node_c_json(resp.content if hasattr(resp, "content") else str(resp))
        question = parsed["question_markdown"]
        new_slot_options: dict[str, list[dict[str, Any]]] = parsed["options"]
        asked = parsed["asked_slots"]
    except Exception as e:  # noqa: BLE001
        _log("C", warning="llm_options_failed", error=str(e))
        # 폴백: 옵션 없이 자유 질문
        first_missing_label = (
            _KEY_LABELS.get(missing[0], missing[0]) if missing else "추가 정보"
        )
        question = f"{first_missing_label} 는 어떻게 하시면 좋을까요?"
        new_slot_options = {}
        asked = missing[:1]

    _log("C", event="exit", asked_slots=asked, question_preview=question[:80])
    return {
        "messages": [AIMessage(content=question)],
        "last_assistant_question": question,
        "slot_options": new_slot_options,
    }


# ---------------------------------------------------------------------------
# Node D — 결정론적 SQL 변환
# ---------------------------------------------------------------------------

def _build_where(slots: Slots) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if slots.get("price_krw") is not None:
        clauses.append("price_krw <= ?")
        params.append(int(slots["price_krw"]))  # type: ignore[arg-type]

    if slots.get("weight_kg") is not None:
        clauses.append("weight_kg <= ?")
        params.append(float(slots["weight_kg"]))  # type: ignore[arg-type]

    if slots.get("screen_inch") is not None:
        v = float(slots["screen_inch"])  # type: ignore[arg-type]
        clauses.append("screen_inch BETWEEN ? AND ?")
        params.extend([v - 1.0, v + 1.0])

    if slots.get("ram_gb") is not None:
        clauses.append("ram_gb >= ?")
        params.append(int(slots["ram_gb"]))  # type: ignore[arg-type]

    if slots.get("storage_gb") is not None:
        clauses.append("storage_gb >= ?")
        params.append(int(slots["storage_gb"]))  # type: ignore[arg-type]

    if slots.get("brightness_nits") is not None:
        clauses.append("(brightness_nits IS NULL OR brightness_nits >= ?)")
        params.append(int(slots["brightness_nits"]))  # type: ignore[arg-type]

    if slots.get("os"):
        clauses.append("os LIKE ?")
        params.append(f"%{slots['os']}%")

    if slots.get("cpu"):
        keyword = extract_cpu_keyword(str(slots["cpu"])) or str(slots["cpu"])
        clauses.append("cpu LIKE ?")
        params.append(f"%{keyword}%")

    if slots.get("resolution"):
        clauses.append("resolution = ?")
        params.append(str(slots["resolution"]))

    where = " AND ".join(clauses) if clauses else "1=1"
    return where, params


def node_d_sql(state: LaptopChatState) -> dict[str, Any]:
    slots: Slots = state.get("slots") or {}  # type: ignore[assignment]
    where_sql, params = _build_where(slots)
    _log("D", event="exit", where=where_sql, params=params)
    return {"sql_clause": (where_sql, params)}


# ---------------------------------------------------------------------------
# Node E — SQLite 조회
# ---------------------------------------------------------------------------

def node_e_query(state: LaptopChatState) -> dict[str, Any]:
    clause = state.get("sql_clause")
    if not clause:
        _log("E", event="exit", warning="no_sql_clause", matched=0)
        return {"candidates": []}

    where_sql, params = clause
    db_path = os.getenv("DB_PATH", "db/laptops.db")
    sql = (
        f"SELECT id, product_name, screen_inch, weight_kg, os, resolution, "
        f"brightness_nits, cpu, ram_gb, storage_gb, price_krw, "
        f"thumbnail_url, detail_url "
        f"FROM laptops WHERE {where_sql} ORDER BY price_krw ASC LIMIT 5"
    )

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, list(params))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
    except sqlite3.Error as e:
        _log("E", event="exit", error=str(e), matched=0)
        return {"candidates": []}

    _log("E", event="exit", matched=len(rows))
    return {"candidates": rows}


# ---------------------------------------------------------------------------
# Node F — 자연어 응답
# ---------------------------------------------------------------------------

def _format_candidates_for_prompt(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "(후보 0건)"
    lines = []
    for i, c in enumerate(candidates, 1):
        price = c.get("price_krw")
        price_str = f"{price:,}원" if isinstance(price, int) else str(price)
        lines.append(
            f"{i}. {c.get('product_name')} | "
            f"{c.get('screen_inch')}\" / {c.get('weight_kg')}kg / {c.get('os')} / "
            f"{c.get('resolution')} / {c.get('brightness_nits') or '?'}nits / "
            f"{c.get('cpu')} / RAM {c.get('ram_gb')}GB / 저장 {c.get('storage_gb')}GB / "
            f"가격 {price_str}"
        )
    return "\n".join(lines)


_KEY_KOREAN = {
    "screen_inch": "화면 크기",
    "weight_kg": "무게",
    "os": "OS",
    "resolution": "해상도",
    "brightness_nits": "밝기",
    "cpu": "CPU",
    "ram_gb": "RAM",
    "storage_gb": "저장 용량",
    "price_krw": "예산",
}


def node_f_answer(state: LaptopChatState) -> dict[str, Any]:
    slots: Slots = state.get("slots") or {}  # type: ignore[assignment]
    candidates = state.get("candidates") or []
    inferred_keys: list[str] = list(state.get("inferred_keys") or [])

    inferred_summary = (
        ", ".join(
            f"{_KEY_KOREAN.get(k, k)}={slots.get(k)}" for k in inferred_keys if slots.get(k) is not None
        )
        if inferred_keys
        else "(없음)"
    )

    llm = make_llm(role="primary", temperature=0.4)
    msgs = [
        SystemMessage(content=NODE_F_SYSTEM),
        HumanMessage(
            content=(
                f"사용자 조건(슬롯):\n{json.dumps(slots, ensure_ascii=False, indent=2)}\n\n"
                f"사용 목적 추론으로 채워진 슬롯(inferred_keys): {inferred_keys}\n"
                f"추론 요약: {inferred_summary}\n\n"
                f"후보 노트북:\n{_format_candidates_for_prompt(candidates)}\n\n"
                "위 정보로 마크다운 응답을 생성해주세요. inferred_keys 가 비어 있지 않으면 첫 줄에 추론 안내 한 줄을 넣어주세요."
            )
        ),
    ]
    try:
        resp = invoke_with_retry(llm, msgs, max_attempts=2)
        answer = str(resp.content if hasattr(resp, "content") else resp).strip()
    except Exception as e:  # noqa: BLE001
        _log("F", warning="llm_failed", error=str(e))
        if candidates:
            answer = "추천 결과를 정리하는 중 문제가 있었어요. 사이드바의 상세를 참고해주세요."
        else:
            answer = (
                "조건을 만족하는 노트북이 없습니다. 예산이나 무게 조건을 조금 완화해 보시겠어요?"
            )

    _log("F", event="exit", n_candidates=len(candidates))
    return {
        "messages": [AIMessage(content=answer)],
        "final_answer": answer,
    }
