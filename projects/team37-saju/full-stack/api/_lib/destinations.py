"""Server-side destination catalog mirroring ``src/mocks/destinations.ts``
augmented with element affinity from ``server/data/destinations.ts``.
"""

from __future__ import annotations

from typing import Dict, List, TypedDict

DepartureRegion = str  # '서울'|'경기'|'부산'|'대구'|'광주'|'대전'|'기타'


class CandidateDestination(TypedDict):
    id: str
    name: str
    region: str
    tags: List[str]
    styles: List[str]
    emoji: str
    description: str
    activities: List[str]
    travelTime: Dict[DepartureRegion, float]
    elementAffinity: List[str]


def _tt(
    seoul: float,
    gyeonggi: float,
    busan: float,
    daegu: float,
    gwangju: float,
    daejeon: float,
    etc: float,
) -> Dict[DepartureRegion, float]:
    return {
        "서울": seoul,
        "경기": gyeonggi,
        "부산": busan,
        "대구": daegu,
        "광주": gwangju,
        "대전": daejeon,
        "기타": etc,
    }


SERVER_DESTINATIONS: List[CandidateDestination] = [
    {
        "id": "gangneung",
        "name": "강릉",
        "region": "강원도",
        "emoji": "🌊",
        "description": "동해의 푸른 결이 마음을 천천히 정리해주는 도시.",
        "tags": ["바다", "카페", "조용한 곳"],
        "styles": ["EMOTIONAL_RECOVERY", "SELF_REFLECTION"],
        "activities": ["경포 해변 산책", "안목해변 카페 투어", "정동진 일출 보기"],
        "travelTime": _tt(2.5, 2.3, 4.5, 3.5, 5.0, 3.5, 4.0),
        "elementAffinity": ["수", "목"],
    },
    {
        "id": "yangyang",
        "name": "양양",
        "region": "강원도",
        "emoji": "🏄",
        "description": "파도 위에서 흐트러진 에너지를 끌어올리는 서핑 마을.",
        "tags": ["바다", "액티비티", "핫플"],
        "styles": ["ENERGY_CHARGE", "ACTIVITY"],
        "activities": ["죽도 해변 서핑", "서피비치 라운지", "하조대 일출"],
        "travelTime": _tt(2.5, 2.5, 5.0, 4.0, 5.5, 4.0, 4.5),
        "elementAffinity": ["수", "화"],
    },
    {
        "id": "gapyeong",
        "name": "가평",
        "region": "경기도",
        "emoji": "🌲",
        "description": "서울에서 가장 가까운 숲, 짧게 다녀오는 회복 코스.",
        "tags": ["숲", "조용한 곳", "카페"],
        "styles": ["SELF_REFLECTION", "EMOTIONAL_RECOVERY"],
        "activities": ["아침고요수목원 걷기", "쁘띠프랑스 산책", "북한강 카페"],
        "travelTime": _tt(1.0, 0.8, 4.5, 3.5, 5.0, 2.5, 3.0),
        "elementAffinity": ["목", "토"],
    },
    {
        "id": "gyeongju",
        "name": "경주",
        "region": "경상북도",
        "emoji": "🏯",
        "description": "천년의 시간이 천천히 흐르는 한국의 야외 박물관.",
        "tags": ["사찰/한옥", "전시/예술", "야경"],
        "styles": ["CULTURE", "SELF_REFLECTION"],
        "activities": ["불국사 산책", "동궁과 월지 야경", "황리단길 거닐기"],
        "travelTime": _tt(4.0, 4.0, 1.5, 1.5, 3.5, 3.0, 3.5),
        "elementAffinity": ["토", "금"],
    },
    {
        "id": "jeonju",
        "name": "전주",
        "region": "전라북도",
        "emoji": "🍜",
        "description": "한옥과 음식, 사람의 온기로 마음이 데워지는 도시.",
        "tags": ["사찰/한옥", "맛집", "카페"],
        "styles": ["CULTURE", "RELATIONSHIP_REFRESH"],
        "activities": ["한옥마을 한복 산책", "비빔밥 한 그릇", "경기전 둘러보기"],
        "travelTime": _tt(2.5, 2.5, 3.5, 3.0, 1.5, 1.5, 2.5),
        "elementAffinity": ["토", "화"],
    },
    {
        "id": "busan",
        "name": "부산",
        "region": "경상남도",
        "emoji": "🌆",
        "description": "바다와 도시, 야경이 한 번에 펼쳐지는 활기의 도시.",
        "tags": ["바다", "핫플", "야경", "맛집"],
        "styles": ["ENERGY_CHARGE", "RELATIONSHIP_REFRESH"],
        "activities": ["해운대 야경 보기", "광안리 회 한상", "감천문화마을 산책"],
        "travelTime": _tt(4.5, 4.5, 0.3, 1.5, 3.0, 3.5, 3.5),
        "elementAffinity": ["수", "화"],
    },
    {
        "id": "jeju",
        "name": "제주",
        "region": "제주도",
        "emoji": "🌴",
        "description": "숲과 바다, 오름까지 모든 결을 품은 섬.",
        "tags": ["바다", "숲", "카페", "조용한 곳"],
        "styles": ["EMOTIONAL_RECOVERY", "SELF_REFLECTION"],
        "activities": ["올레길 한 코스 걷기", "오름 트레킹", "해안도로 드라이브"],
        "travelTime": _tt(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.5),
        "elementAffinity": ["수", "목"],
    },
    {
        "id": "tongyeong",
        "name": "통영",
        "region": "경상남도",
        "emoji": "⛴️",
        "description": "잔잔한 한려수도의 빛이 마음을 천천히 가라앉혀요.",
        "tags": ["바다", "조용한 곳", "맛집"],
        "styles": ["EMOTIONAL_RECOVERY", "CULTURE"],
        "activities": ["미륵산 케이블카", "동피랑 벽화마을", "굴 요리 한 끼"],
        "travelTime": _tt(4.5, 4.5, 1.5, 2.5, 2.5, 3.5, 4.0),
        "elementAffinity": ["수", "금"],
    },
    {
        "id": "andong",
        "name": "안동",
        "region": "경상북도",
        "emoji": "🏮",
        "description": "느린 한옥 골목에서 자기를 다시 만나는 도시.",
        "tags": ["사찰/한옥", "조용한 곳", "전시/예술"],
        "styles": ["CULTURE", "SELF_REFLECTION"],
        "activities": ["하회마을 산책", "월영교 야경", "병산서원 둘러보기"],
        "travelTime": _tt(3.0, 3.0, 2.5, 1.5, 3.5, 2.0, 3.0),
        "elementAffinity": ["토", "금"],
    },
    {
        "id": "sokcho",
        "name": "속초",
        "region": "강원도",
        "emoji": "🏔️",
        "description": "설악과 동해를 동시에 마주하는 회복의 베이스캠프.",
        "tags": ["바다", "산", "맛집"],
        "styles": ["ACTIVITY", "EMOTIONAL_RECOVERY"],
        "activities": ["설악산 케이블카", "속초항 회센터", "영금정 일출"],
        "travelTime": _tt(2.5, 2.5, 5.0, 4.0, 5.5, 4.0, 4.5),
        "elementAffinity": ["수", "목"],
    },
    {
        "id": "yeosu",
        "name": "여수",
        "region": "전라남도",
        "emoji": "🌃",
        "description": "밤바다의 불빛이 흐트러진 마음을 다시 모아주는 도시.",
        "tags": ["바다", "야경", "핫플", "맛집"],
        "styles": ["RELATIONSHIP_REFRESH", "EMOTIONAL_RECOVERY"],
        "activities": ["돌산공원 야경", "오동도 산책", "해상케이블카 타기"],
        "travelTime": _tt(4.5, 4.5, 3.0, 3.0, 1.5, 3.0, 3.5),
        "elementAffinity": ["수", "화"],
    },
    {
        "id": "damyang",
        "name": "담양",
        "region": "전라남도",
        "emoji": "🎋",
        "description": "대숲의 바람 소리가 머릿속을 비워주는 작은 마을.",
        "tags": ["숲", "조용한 곳", "카페"],
        "styles": ["SELF_REFLECTION", "EMOTIONAL_RECOVERY"],
        "activities": ["죽녹원 대숲 산책", "메타세쿼이아길 걷기", "한옥 카페 머무르기"],
        "travelTime": _tt(3.5, 3.5, 3.0, 3.0, 0.8, 2.5, 3.0),
        "elementAffinity": ["목", "수"],
    },
    {
        "id": "boseong",
        "name": "보성",
        "region": "전라남도",
        "emoji": "🍃",
        "description": "초록 차밭의 결을 따라 호흡이 깊어지는 곳.",
        "tags": ["숲", "조용한 곳", "카페"],
        "styles": ["EMOTIONAL_RECOVERY", "SELF_REFLECTION"],
        "activities": ["대한다원 차밭 산책", "율포 해변 거닐기", "녹차 한 잔 마시기"],
        "travelTime": _tt(4.5, 4.5, 3.5, 3.5, 1.5, 3.5, 4.0),
        "elementAffinity": ["목", "토"],
    },
    {
        "id": "danyang",
        "name": "단양",
        "region": "충청북도",
        "emoji": "⛰️",
        "description": "강과 절벽, 패러글라이딩이 어우러진 모험의 도시.",
        "tags": ["산", "액티비티", "조용한 곳"],
        "styles": ["ACTIVITY", "ENERGY_CHARGE"],
        "activities": ["만천하 스카이워크", "도담삼봉 보기", "패러글라이딩 체험"],
        "travelTime": _tt(2.0, 2.0, 3.0, 2.0, 4.0, 1.5, 2.5),
        "elementAffinity": ["목", "토"],
    },
    {
        "id": "samcheok",
        "name": "삼척",
        "region": "강원도",
        "emoji": "🌅",
        "description": "관광객이 적은 동해, 진짜 조용한 시간을 원할 때.",
        "tags": ["바다", "조용한 곳", "산"],
        "styles": ["EMOTIONAL_RECOVERY", "SELF_REFLECTION"],
        "activities": ["장호항 투명카약", "해상케이블카 타기", "환선굴 둘러보기"],
        "travelTime": _tt(3.0, 3.0, 4.0, 3.0, 5.0, 3.5, 4.0),
        "elementAffinity": ["수", "토"],
    },
]
