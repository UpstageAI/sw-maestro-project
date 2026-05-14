import logging
import re
from dataclasses import dataclass

from json_repair import loads as repair_loads


logger = logging.getLogger(__name__)


@dataclass
class BriefingResult:
    headline: str
    summary: str


class BriefingGenerator:
    def __init__(self, chat_client=None):
        self._client = chat_client

    def generate(self, clusters: list[dict]) -> BriefingResult:
        client = self._client or self._default_client()
        titles = [c.get("title", "") for c in clusters if c.get("title")]
        prompt = (
            "다음 뉴스 제목들을 바탕으로 오늘의 브리핑을 작성하세요.\n"
            "말투는 '~했어요', '~예요', '~이에요' 같은 해요체를 사용하세요. '~했다', '~습니다' 체는 절대 사용하지 마세요.\n"
            "반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:\n"
            '{"headline": "한 줄 제목", "summary": "2~3문장 요약"}\n\n'
            + "\n".join(f"- {t}" for t in titles)
        )
        try:
            response = client.complete([{"role": "user", "content": prompt}])
            parsed = repair_loads(_strip_code_block(response))
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception as exc:
            logger.warning("일일 브리핑 생성 실패: %s", exc)
            parsed = {}
        headline = str(parsed.get("headline", "")).strip() or _fallback_headline(titles)
        summary = str(parsed.get("summary", "")).strip() or _fallback_summary(titles)
        return BriefingResult(
            headline=headline[:40],
            summary=summary[:500],
        )

    def _default_client(self):
        from newspick_ai.solar.chat import SolarChatClient

        return SolarChatClient()


def _strip_code_block(text: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return match.group(1).strip() if match else text.strip()


def _fallback_headline(titles: list[str]) -> str:
    return titles[0][:40] if titles else "오늘의 주요 뉴스"


def _fallback_summary(titles: list[str]) -> str:
    if not titles:
        return "오늘 수집된 주요 기사 흐름을 정리했어요."
    return "오늘 수집된 주요 기사들이 이슈의 흐름을 보여주고 있어요. " + titles[0]
