"""채점 에이전트 — 4섹션 각각 0-100점 + 약한 섹션 식별."""
import json
import logging
import re

from src import config
from src.agents.base import invoke
from src.models.story import (
    SECTION_ORDER,
    SectionName,
    SectionScore,
    StoryDraft,
    Verdict,
)

log = logging.getLogger(__name__)

RUBRIC = """\
각 섹션은 다음 4가지 항목으로 채점합니다 (각 0-25, 합계 0-100):
1. **사실 정합성** (25): 레포에서 관찰 가능한 근거에서만 끌어왔는가? 추측/환각이 없는가?
2. **목적 부합** (25): 해당 섹션의 목적을 충실히 수행했는가?
3. **흐름/연결** (25): 앞 섹션과 자연스럽게 이어지는가?
4. **구체성** (25): 추상적 일반론 대신 이 프로젝트만의 구체적 디테일이 있는가?

섹션 정의:
- problem = 문제 인식
- status = 현황 파악
- cause = 원인 분석 및 해결책
- result = 결과 정리 및 성능 향상
"""

PROMPT = """\
다음 포트폴리오 초안을 채점합니다.

{rubric}

각 섹션마다:
- score (0-100, 정수)
- rationale (한 줄, 한국어)

JSON으로만 응답하세요. 형식:
{{
  "scores": [
    {{"name": "problem", "score": 92, "rationale": "..."}},
    {{"name": "status", "score": 85, "rationale": "..."}},
    {{"name": "cause", "score": 88, "rationale": "..."}},
    {{"name": "result", "score": 90, "rationale": "..."}}
  ]
}}

== 문제 인식 (problem) ==
{problem}

== 현황 파악 (status) ==
{status}

== 원인 분석 및 해결책 (cause) ==
{cause}

== 결과 정리 및 성능 향상 (result) ==
{result}
"""


def _extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text)
    raw = m.group(1) if m else text
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"JSON 못 찾음: {text[:200]}")
    return json.loads(raw[start : end + 1])


def run(draft: StoryDraft, threshold: int = config.SCORE_THRESHOLD) -> Verdict:
    if not all([draft.problem, draft.status, draft.cause, draft.result]):
        raise ValueError("StoryDraft에 4섹션이 모두 채워져야 합니다.")

    raw = invoke(
        PROMPT.format(
            rubric=RUBRIC,
            problem=draft.problem.content,
            status=draft.status.content,
            cause=draft.cause.content,
            result=draft.result.content,
        ),
        deep=True,
    )

    try:
        parsed = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        log.error("validator JSON 파싱 실패: %s\nraw=%s", e, raw[:500])
        scores = [SectionScore(name=n, score=0, rationale="파싱 실패") for n in SECTION_ORDER]
        return Verdict(scores=scores, weakest="problem", overall_pass=False)

    scores = [SectionScore(**s) for s in parsed["scores"]]

    # 통과 기준: 4섹션 평균 ≥ threshold (기본 80).
    # weakest = 가장 낮은 점수 섹션 (재생성 시 cascade 시작점) — 통과 시에도 None.
    avg = sum(s.score for s in scores) / len(scores) if scores else 0
    overall_pass = avg >= threshold

    weakest: SectionName | None = None
    if not overall_pass:
        # 점수 동률이면 SECTION_ORDER 앞쪽 우선
        order_idx = {n: i for i, n in enumerate(SECTION_ORDER)}
        weakest = min(scores, key=lambda s: (s.score, order_idx[s.name])).name

    log.info("validator: avg=%.1f threshold=%d pass=%s weakest=%s",
             avg, threshold, overall_pass, weakest)

    return Verdict(
        scores=scores,
        weakest=weakest,
        overall_pass=overall_pass,
    )
