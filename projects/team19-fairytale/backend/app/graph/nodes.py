"""Plan → Write → Critique (→ Revise) 의 agentic 워크플로우 노드들."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from app.exceptions import LLMUnavailableError
from app.graph.state import GraphState, StoryOut, PersonDict, Critique
from app.llm.client import get_chat_model


MAX_REVISIONS = 1            # 비평 미통과 시 다시 쓰는 최대 횟수
PASS_THRESHOLD = 4.0         # 4개 항목 평균 이 점수 이상이면 통과
CRITIQUE_KEYS = ("fairy_tale", "age_vocab", "character_mapping", "safety")


def _clamp_score(v) -> int:
    """채점 값을 1~5 정수 범위로 강제."""
    try:
        i = int(v)
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, i))


# ─────────────────────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _safe_invoke(llm: BaseChatModel, messages: list[BaseMessage], *, stage: str) -> str:
    """LLM 호출을 도메인 예외로 감싸는 유틸. 응답 텍스트만 반환."""
    try:
        msg = llm.invoke(messages)
    except Exception as e:
        raise LLMUnavailableError(
            f"LLM 호출 실패: {type(e).__name__}: {e}", stage=stage,
        ) from e
    return msg.content if hasattr(msg, "content") else str(msg)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _strip_code_fence(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


def _parse_json(raw: str) -> dict:
    """LLM JSON 응답 파싱.

    - ```json … ``` 코드펜스 제거
    - strict=False : 문자열 안의 raw newline 허용
    - {…} 부분만 잘라서 재시도
    """
    text = _strip_code_fence(raw)
    for candidate in (text, _extract_braced(text)):
        if candidate is None:
            continue
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            continue
    raise ValueError("JSON 파싱 실패")


def _extract_braced(text: str) -> str | None:
    """문자열에서 첫 '{' 부터 마지막 '}' """
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1 or e <= s:
        return None
    return text[s : e + 1]


_TITLE_RE = re.compile(r'"title"\s*:\s*"([^"\n]+)"')
_BODY_RE = re.compile(r'"body"\s*:\s*"(.+?)"\s*\}\s*$', re.DOTALL)


def _parse_story(raw: str) -> tuple[str, str]:
    """write 노드 응답에서 title/body를 추출. JSON 깨져도 정규식으로 복구."""
    try:
        d = _parse_json(raw)
        return d["title"], d["body"]
    except Exception:
        pass
    text = _strip_code_fence(raw)
    title_m = _TITLE_RE.search(text)
    body_m = _BODY_RE.search(text)
    if title_m and body_m:
        body = body_m.group(1).replace("\\n", "\n")
        return title_m.group(1), body
    return "오늘의 동화", text


def _format_person(p: PersonDict) -> str:
    line = f"- {p.get('name', '')} ({p.get('relation', '')})"
    bits = []
    if p.get("closeness") is not None:
        bits.append(f"친밀도: {p['closeness']}/5")
    if p.get("role_today"):
        bits.append(f"오늘의 역할: {p['role_today']}")
    if p.get("traits"):
        bits.append("특징: " + ", ".join(p["traits"]))
    if p.get("note"):
        bits.append(f"메모: {p['note']}")
    if bits:
        line += "\n    · " + "\n    · ".join(bits)
    return line


def _format_people(people: list[PersonDict]) -> str:
    if not people:
        return "(없음)"
    grouped: dict[str, list[PersonDict]] = defaultdict(list)
    for p in people:
        grouped[p.get("kind", "기타")].append(p)
    order = ["가족", "친구", "선생님", "이웃", "기타"]
    sections = []
    for kind in order:
        if kind in grouped:
            sections.append(
                f"〔{kind}〕\n" + "\n".join(_format_person(p) for p in grouped[kind])
            )
    return "\n\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# 1) PLAN — 동화 outline 짜기
# ─────────────────────────────────────────────────────────────────────────────

PLAN_SYS = """너는 5~7세 유아 동화의 기획자다.
일기와 인물 정보를 받아 동화의 뼈대를 JSON으로 설계한다.

[필수 슬롯]
- setting          : 동화 세계 배경 (예: "별빛이 흐르는 숲속 마을")
- protagonist      : 일기 주인공이 변신한 동화 캐릭터 (예: "호기심 많은 토끼 빛나")
- companions       : 인물 → 동화 캐릭터 매핑 배열 [{from, to, role}]
                     · 가족 → 따뜻한 보호자 (요정/곰 할머니/사슴 아빠 등)
                     · 친구 → 갈등 또는 협력 상대 (토끼/다람쥐/여우 등)
                     · 선생님 → 지혜로운 안내자 (부엉이/별 마법사 등)
- magical_element  : 일기 속 사물·사건이 변신한 마법 장치
                     (예: "소원을 들어주는 별빛 돌", "노래하는 무지개 다리")
- conflict         : 동화 속 사건의 갈등
- resolution       : 마법적 도움 또는 깨달음으로 풀리는 결말

[출력]
JSON만 출력 (다른 말, 코드펜스 금지)."""


def plan(state: GraphState) -> dict:
    user = f"""[일기]
{state.get('diary', '')}

[주변 인물 — 카테고리별]
{_format_people(state.get('people', []))}

위를 동화 outline JSON으로 만들어줘."""

    raw = _safe_invoke(
        get_chat_model(),
        [SystemMessage(content=PLAN_SYS), HumanMessage(content=user)],
        stage="plan",
    )
    # 파싱 실패해도 다음 단계가 텍스트 그대로 받을 수 있도록 raw를 저장한다.
    try:
        outline_obj = _parse_json(raw)
        outline = json.dumps(outline_obj, ensure_ascii=False, indent=2)
    except Exception:
        outline = _strip_code_fence(raw)
    return {"outline": outline, "revision_count": 0}


# ─────────────────────────────────────────────────────────────────────────────
# 2) WRITE — outline → 동화 본문
#   (재호출 시에는 critique 피드백을 보고 고쳐 쓴다)
# ─────────────────────────────────────────────────────────────────────────────

WRITE_SYS = """너는 5~7세 유아를 위한 동화 작가다.
주어진 outline 을 따라 한 편의 완성된 동화를 만든다.

[작성 규칙]
- "옛날 옛적", "어느 별빛 흐르는 밤에" 같은 동화 특유의 시작
- 일기 속 현실 사물·장소를 outline 의 마법 장치·세계로 변환해서 사용
- 의인화된 동물·요정·자연물, 의성어/의태어, 운율감 있는 표현
- 분량 6~10 문장, 5~7세 어휘
- 폭력/공포/혐오/직접 훈계 금지
- 교훈은 별도로 적지 말고 결말 분위기로 자연스럽게 느껴지게

[출력 형식]
JSON만 출력 (다른 말, 코드펜스 금지). body 안에 큰따옴표가 들어가면 반드시 \\" 로 이스케이프할 것:
{"title": "동화 제목", "body": "동화 본문"}"""


def write(state: GraphState) -> dict:
    rev = state.get("revision_count", 0)
    critique = state.get("critique") if rev > 0 else None

    user_parts = [
        f"[일기]\n{state.get('diary', '')}",
        f"[인물]\n{_format_people(state.get('people', []))}",
        f"[동화 outline]\n{state.get('outline', '')}",
    ]
    if critique:
        user_parts.append(
            "[이전 원고에 대한 비평가의 지적 — 반드시 반영해서 다시 쓸 것]\n"
            f"점수: {critique.get('scores')}\n"
            f"개선 코멘트: {critique.get('comment', '')}"
        )
    user_parts.append("위를 바탕으로 동화 한 편을 JSON으로 작성해줘.")
    user = "\n\n".join(user_parts)

    raw = _safe_invoke(
        get_chat_model(),
        [SystemMessage(content=WRITE_SYS), HumanMessage(content=user)],
        stage="write",
    )
    title, body = _parse_story(raw)
    return {
        "draft_title": title,
        "draft_body": body,
        "revision_count": rev + 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3) CRITIQUE — 동화를 4개 기준으로 채점
# ─────────────────────────────────────────────────────────────────────────────

CRITIQUE_SYS = """너는 유아 동화 편집자이자 아동 콘텐츠 검수자다.
주어진 동화를 다음 4개 기준으로 1~5점으로 채점하고, 어떻게 더 좋아질 수 있는지 한 단락의 구체적 코멘트를 작성한다.

[채점 기준]
1) fairy_tale       : 동화적 분위기 (옛날옛적 톤, 마법 장치, 의인화, 의성어/의태어)
2) age_vocab        : 5~7세 어휘 적절성 (너무 어렵거나 추상적이지 않은가)
3) character_mapping: 입력 인물의 카테고리/역할이 동화 캐릭터에 잘 녹아들었는가
4) safety           : 공포·폭력·직접 훈계·차별 표현이 없는가

[출력 형식]
JSON만 출력 (다른 말, 코드펜스 금지):
{
  "scores": {"fairy_tale": 1~5, "age_vocab": 1~5, "character_mapping": 1~5, "safety": 1~5},
  "comment": "어디를 어떻게 고치면 좋을지 한 단락. 안 고쳐도 되면 칭찬."
}"""


def critique(state: GraphState) -> dict:
    user = f"""[원본 일기]
{state.get('diary', '')}

[입력 인물]
{_format_people(state.get('people', []))}

[검수할 동화]
제목: {state.get('draft_title', '')}

본문:
{state.get('draft_body', '')}

위 동화를 채점해줘."""

    raw = _safe_invoke(
        get_chat_model(),
        [SystemMessage(content=CRITIQUE_SYS), HumanMessage(content=user)],
        stage="critique",
    )

    try:
        data = _parse_json(raw)
        raw_scores = data.get("scores", {})
        scores = {k: _clamp_score(v) for k, v in raw_scores.items()}
        comment = str(data.get("comment", "")).strip()
        parsing_failed = False
    except Exception:
        # critique 파싱 자체가 깨졌으면 안전하지 않은 콘텐츠가 통과될 위험이 있으므로
        # safety 0점으로 강제하여 finalize 분기는 막되, MAX_REVISIONS 도달 시 강제 종료에 의존한다.
        scores = {}
        comment = "(critique 파싱 실패)"
        parsing_failed = True

    # 누락된 채점 항목 채우기:
    #  · safety 가 누락되거나 파싱 실패 시 0점 → 절대 통과 못하게
    #  · 그 외 항목은 보수적으로 3점
    for key in CRITIQUE_KEYS:
        if key not in scores:
            scores[key] = 0 if (key == "safety" or parsing_failed) else 3

    average = sum(scores.values()) / len(CRITIQUE_KEYS)
    passed = average >= PASS_THRESHOLD and not parsing_failed

    return {
        "critique": Critique(
            scores=scores, average=round(average, 2),
            comment=comment, passed=passed,
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4) FINALIZE — draft → story 로 확정
# ─────────────────────────────────────────────────────────────────────────────

def finalize(state: GraphState) -> dict:
    return {
        "story": StoryOut(
            title=state.get("draft_title", "오늘의 동화"),
            body=state.get("draft_body", ""),
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 라우팅: critique 이후 통과면 끝, 아니면 write 로 되돌림 (단, MAX_REVISIONS 한도)
# ─────────────────────────────────────────────────────────────────────────────

def route_after_critique(state: GraphState) -> str:
    crit = state.get("critique") or {}
    rev = state.get("revision_count", 0)
    if crit.get("passed") or rev > MAX_REVISIONS:
        return "finalize"
    return "write"
