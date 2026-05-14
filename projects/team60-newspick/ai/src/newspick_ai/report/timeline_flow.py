import logging
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from json_repair import loads as repair_loads


SEOUL_TZ = ZoneInfo("Asia/Seoul")
logger = logging.getLogger(__name__)


@dataclass
class TimelineItem:
    articleId: str
    category: str
    timeLabel: str
    title: str
    sourceCount: int
    summary: str | None


@dataclass
class FlowItem:
    category: str
    description: str


@dataclass
class TimelineFlowResult:
    timeline: list[TimelineItem]
    flow: list[FlowItem]


class TimelineFlowGenerator:
    def __init__(self, chat_client=None):
        self._client = chat_client

    def generate(self, articles: list[dict]) -> TimelineFlowResult:
        client = self._client or self._default_client()

        sorted_articles = sorted(articles, key=lambda a: a.get("sourceCount", 1), reverse=True)
        timeline = [
            TimelineItem(
                articleId=a["id"],
                category=a.get("category", ""),
                timeLabel=self._format_time(a.get("publishedAt", "")),
                title=a.get("title", ""),
                sourceCount=a.get("sourceCount", 1),
                summary=_first_summary(a.get("summary")),
            )
            for a in sorted_articles
        ]

        by_category: dict[str, list[str]] = {}
        for a in sorted_articles:
            cat = a.get("category", "기타")
            by_category.setdefault(cat, []).append(a.get("title", ""))

        category_block = "\n".join(
            f"{cat}:\n" + "\n".join(f"  - {t}" for t in titles)
            for cat, titles in by_category.items()
        )
        prompt = (
            "다음 카테고리별 뉴스를 바탕으로 각 카테고리의 핵심 흐름을 한 문장으로 요약하세요.\n"
            "말투는 '~했어요', '~예요', '~이에요' 같은 해요체를 사용하세요. '~했다', '~습니다' 체는 절대 사용하지 마세요.\n"
            "반드시 아래 JSON 배열 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:\n"
            '[{"category": "카테고리명", "description": "..."}, ...]\n\n'
            + category_block
        )
        try:
            response = client.complete([{"role": "user", "content": prompt}])
            flow_data = repair_loads(_strip_code_block(response))
            if not isinstance(flow_data, list):
                flow_data = []
        except Exception as exc:
            logger.warning("일일 흐름 생성 실패: %s", exc)
            flow_data = []
        flow = [
            FlowItem(category=item.get("category", ""), description=item.get("description", ""))
            for item in flow_data
            if isinstance(item, dict)
        ]
        if not flow:
            flow = _fallback_flow(by_category)

        return TimelineFlowResult(timeline=timeline, flow=flow)

    def _default_client(self):
        from newspick_ai.solar.chat import SolarChatClient

        return SolarChatClient()

    @staticmethod
    def _format_time(published_at: str) -> str:
        if not published_at:
            return "00:00"
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.astimezone(SEOUL_TZ).strftime("%H:%M")


def _strip_code_block(text: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return match.group(1).strip() if match else text.strip()


def _first_summary(summary: list[str] | None) -> str | None:
    if not summary:
        return None
    return summary[0] if isinstance(summary, list) else None


def _fallback_flow(by_category: dict[str, list[str]]) -> list[FlowItem]:
    if not by_category:
        return [FlowItem(category="기타", description="오늘 주요 뉴스 흐름을 정리했어요.")]
    return [
        FlowItem(
            category=category,
            description=f"{category} 분야에서 {titles[0]}를 중심으로 관련 소식이 모였어요.",
        )
        for category, titles in by_category.items()
        if titles
    ]
