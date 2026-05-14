"""Interview — 압축 컨텍스트를 보고 부족한 정보 0-3개 질문 생성.
질문 0개도 정상. 너무 일반적인 질문은 피하도록 프롬프트에서 지시."""
import json
import logging
import re

from src.agents.base import invoke
from src.models.repo import RepoContext

log = logging.getLogger(__name__)

PROMPT = """\
다음은 GitHub 레포 메타와 압축된 README/커밋 요약입니다.
포트폴리오의 4섹션 (문제 인식 / 현황 파악 / 원인 분석 및 해결책 / 결과 정리 및 성능 향상)을
*근거 있게* 작성하기 위해 사용자에게 직접 물어봐야 할 *결정적으로 부족한 정보*를 0-3개 질문으로 정의하세요.

질문 기준:
- 레포에서 추론/관찰 불가능한 정보만 (예: 프로젝트 동기, 측정 수치, 회고, 향후 계획, 사용자 피드백)
- manifest나 트리에서 추론 가능한 건 묻지 말 것 (예: 기술 스택 X)
- 너무 일반적인 질문 금지 — 이 프로젝트만의 구체성이 있어야 함
- 정보가 충분하면 빈 배열 반환

JSON으로만 응답:
{{"questions": ["...", "...", "..."]}}

== 메타 ==
{meta}

== 압축 요약 ==
{summary}

== 사용자가 미리 첨부한 정보 ==
{attached}
"""


def _extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text)
    raw = m.group(1) if m else text
    s = raw.find("{")
    e = raw.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("JSON 못 찾음")
    return json.loads(raw[s : e + 1])


def run(ctx: RepoContext) -> list[str]:
    meta = (
        f"- 레포: {ctx.full_name}\n"
        f"- 설명: {ctx.description or '(없음)'}\n"
        f"- 토픽: {', '.join(ctx.topics) or '(없음)'}\n"
        f"- 주 언어: {ctx.primary_language or '(없음)'}\n"
        f"- 스타/포크: {ctx.stars}/{ctx.forks}\n"
        f"- 총 커밋: {len(ctx.commits)}"
    )
    raw = invoke(
        PROMPT.format(
            meta=meta,
            summary=ctx.commit_summary or "(없음)",
            attached=ctx.user_attached_info or "(없음)",
        ),
        deep=False,
    )
    try:
        data = _extract_json(raw)
        qs = [q for q in data.get("questions", []) if isinstance(q, str) and q.strip()]
        return qs[:3]
    except (ValueError, json.JSONDecodeError) as e:
        log.warning("interview JSON 파싱 실패: %s — 질문 0개로 진행", e)
        return []
