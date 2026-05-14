"""Travel style catalog mirrored from ``src/mocks/travelStyles.ts``."""

from __future__ import annotations

from typing import Dict, List, TypedDict

StyleKey = str  # one of the keys below
TravelStyle = str  # tag vocabulary, see src/types/index.ts


class TravelStyleDef(TypedDict):
    key: StyleKey
    label: str
    emoji: str
    color: str
    summary: str
    recommendKeywords: List[TravelStyle]


TRAVEL_STYLES: Dict[StyleKey, TravelStyleDef] = {
    "EMOTIONAL_RECOVERY": {
        "key": "EMOTIONAL_RECOVERY",
        "label": "감정 회복형",
        "emoji": "🌊",
        "color": "#60A5FA",
        "summary": "지금은 잠시 멈춰 마음을 다독여 줄 시간이 필요한 시기예요.",
        "recommendKeywords": ["바다", "조용한 곳", "카페"],
    },
    "ENERGY_CHARGE": {
        "key": "ENERGY_CHARGE",
        "label": "에너지 충전형",
        "emoji": "☀️",
        "color": "#F59E0B",
        "summary": "흐트러진 활기를 되찾고 새 기운을 불어넣을 흐름이에요.",
        "recommendKeywords": ["액티비티", "핫플", "맛집"],
    },
    "RELATIONSHIP_REFRESH": {
        "key": "RELATIONSHIP_REFRESH",
        "label": "인간관계 환기형",
        "emoji": "✨",
        "color": "#EC4899",
        "summary": "익숙한 관계의 매듭을 풀고 새로운 결을 맞이하기 좋은 때입니다.",
        "recommendKeywords": ["핫플", "맛집", "야경"],
    },
    "SELF_REFLECTION": {
        "key": "SELF_REFLECTION",
        "label": "자기 성찰형",
        "emoji": "🌲",
        "color": "#10B981",
        "summary": "안을 들여다보고 다음 방향을 차분히 정비할 시기입니다.",
        "recommendKeywords": ["숲", "사찰/한옥", "조용한 곳"],
    },
    "ACTIVITY": {
        "key": "ACTIVITY",
        "label": "액티비티 중심형",
        "emoji": "🏔️",
        "color": "#EF4444",
        "summary": "몸을 움직이며 살아있음을 다시 느낄 시간이 다가왔어요.",
        "recommendKeywords": ["액티비티", "산", "바다"],
    },
    "CULTURE": {
        "key": "CULTURE",
        "label": "문화 탐방형",
        "emoji": "🏯",
        "color": "#7C3AED",
        "summary": "오래된 이야기 속에서 지금의 답을 찾을 흐름이에요.",
        "recommendKeywords": ["사찰/한옥", "전시/예술", "맛집"],
    },
}
