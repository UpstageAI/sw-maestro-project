"""Deterministic Bazi (사주팔자) calculator — Python port of
``server/saju/baziCalculator.ts``.

Given a birth date (YYYY-MM-DD) + Korean two-hour branch, returns the four
pillars (year/month/day/hour) with their heavenly stems / earthly branches
plus an aggregated 오행 balance. This is the simplified astronomical model
used in the TypeScript original — accurate enough that different birthdays
produce different charts.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, TypedDict

Element = str  # '목' | '화' | '토' | '금' | '수'

HEAVENLY_STEMS: List[str] = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
EARTHLY_BRANCHES: List[str] = [
    "자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해",
]

STEM_ELEMENTS: Dict[str, Element] = {
    "갑": "목", "을": "목",
    "병": "화", "정": "화",
    "무": "토", "기": "토",
    "경": "금", "신": "금",
    "임": "수", "계": "수",
}

BRANCH_ELEMENTS: Dict[str, Element] = {
    "자": "수", "해": "수",
    "축": "토", "진": "토", "미": "토", "술": "토",
    "인": "목", "묘": "목",
    "사": "화", "오": "화",
    "신": "금", "유": "금",
}

# BirthHour string → earthly branch index (0=자, 11=해). None for '모름'.
HOUR_BRANCH_INDEX: Dict[str, Optional[int]] = {
    "모름": None,
    "자시(23-01)": 0,
    "축시(01-03)": 1,
    "인시(03-05)": 2,
    "묘시(05-07)": 3,
    "진시(07-09)": 4,
    "사시(09-11)": 5,
    "오시(11-13)": 6,
    "미시(13-15)": 7,
    "신시(15-17)": 8,
    "유시(17-19)": 9,
    "술시(19-21)": 10,
    "해시(21-23)": 11,
}

ALL_ELEMENTS: List[Element] = ["목", "화", "토", "금", "수"]


class BaziPillar(TypedDict):
    stem: str
    branch: str
    stemElement: Element
    branchElement: Element


class DayMaster(TypedDict):
    stem: str
    element: Element


class BaziChart(TypedDict):
    year: BaziPillar
    month: BaziPillar
    day: BaziPillar
    hour: Optional[BaziPillar]
    dayMaster: DayMaster


class ElementBalance(TypedDict):
    scores: Dict[Element, float]
    dominant: Element
    weakest: Element
    strong: List[Element]
    weak: List[Element]


def _build_pillar(stem_idx: int, branch_idx: int) -> BaziPillar:
    stem = HEAVENLY_STEMS[((stem_idx % 10) + 10) % 10]
    branch = EARTHLY_BRANCHES[((branch_idx % 12) + 12) % 12]
    return {
        "stem": stem,
        "branch": branch,
        "stemElement": STEM_ELEMENTS[stem],
        "branchElement": BRANCH_ELEMENTS[branch],
    }


def _day_pillar_index(d: date) -> int:
    # 1900-01-31 = 갑진 (jiazi index 40). Mod 60.
    ref = date(1900, 1, 31)
    diff = (d - ref).days
    return ((diff + 40) % 60 + 60) % 60


def _year_pillar(d: date) -> BaziPillar:
    # Lunar new year approximation: Feb 4 cutoff.
    yr = d.year - 1 if (d.month == 1 or (d.month == 2 and d.day < 4)) else d.year
    idx = ((yr - 1984) % 60 + 60) % 60
    return _build_pillar(idx % 10, idx % 12)


def _month_pillar(d: date, year_stem: str) -> BaziPillar:
    m = d.month
    # Feb=2→인(2), Mar=3→묘(3), ..., Dec=12→자(0), Jan=1→축(1).
    corrected_branch = m % 12  # Jan(1)→1, Feb(2)→2, ..., Nov(11)→11, Dec(12)→0
    # 五虎遁: 갑/기 year → 인월 stem 병(2); 을/경 → 무(4); 병/신 → 경(6);
    # 정/임 → 임(8); 무/계 → 갑(0).
    stem_seed: Dict[str, int] = {
        "갑": 2, "기": 2,
        "을": 4, "경": 4,
        "병": 6, "신": 6,
        "정": 8, "임": 8,
        "무": 0, "계": 0,
    }
    branch_offset = ((corrected_branch - 2) + 12) % 12  # 인월=0
    stem_idx = (stem_seed[year_stem] + branch_offset) % 10
    return _build_pillar(stem_idx, corrected_branch)


def _day_pillar(d: date) -> BaziPillar:
    idx = _day_pillar_index(d)
    return _build_pillar(idx % 10, idx % 12)


def _hour_pillar(day_stem: str, branch_idx: int) -> BaziPillar:
    # 五鼠遁: stem_idx = (day_stem_idx * 2 + hour_branch_idx) mod 10.
    day_stem_idx = HEAVENLY_STEMS.index(day_stem)
    stem_idx = (day_stem_idx * 2 + branch_idx) % 10
    return _build_pillar(stem_idx, branch_idx)


def compute_bazi(birth_date: str, birth_hour: str) -> BaziChart:
    try:
        d = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError as err:
        raise ValueError(f"Invalid birthDate: {birth_date}") from err

    year = _year_pillar(d)
    month = _month_pillar(d, year["stem"])
    day = _day_pillar(d)
    hour_branch_idx = HOUR_BRANCH_INDEX.get(birth_hour)
    hour = _hour_pillar(day["stem"], hour_branch_idx) if hour_branch_idx is not None else None

    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "dayMaster": {"stem": day["stem"], "element": day["stemElement"]},
    }


def compute_element_balance(chart: BaziChart) -> ElementBalance:
    scores: Dict[Element, float] = {"목": 0.0, "화": 0.0, "토": 0.0, "금": 0.0, "수": 0.0}

    pillars: List[BaziPillar] = [chart["year"], chart["month"], chart["day"]]
    if chart["hour"] is not None:
        pillars.append(chart["hour"])  # type: ignore[arg-type]

    for p in pillars:
        scores[p["stemElement"]] += 1.0
        scores[p["branchElement"]] += 0.8

    # Day master gets a slight extra weight — represents the self.
    scores[chart["dayMaster"]["element"]] += 0.5

    sorted_elems = sorted(ALL_ELEMENTS, key=lambda e: scores[e], reverse=True)
    dominant = sorted_elems[0]
    weakest = sorted_elems[-1]

    total = sum(scores.values())
    avg = total / 5
    strong = [e for e in ALL_ELEMENTS if scores[e] >= avg * 1.25]
    weak = [e for e in ALL_ELEMENTS if scores[e] <= avg * 0.6]

    return {
        "scores": scores,
        "dominant": dominant,
        "weakest": weakest,
        "strong": strong,
        "weak": weak,
    }


# Each element maps to travel-environment affinities used by ranking.
ELEMENT_TRAVEL_AFFINITY: Dict[Element, Dict[str, List[str]]] = {
    "목": {
        "environments": ["숲", "산", "한옥/사찰"],
        "keywords": ["성장", "확장", "아침의 결"],
    },
    "화": {
        "environments": ["핫플", "야경", "액티비티"],
        "keywords": ["활동성", "개방감", "밝은 빛"],
    },
    "토": {
        "environments": ["전원", "한옥", "시골 한적"],
        "keywords": ["안정", "머무름", "품에 안기는"],
    },
    "금": {
        "environments": ["전시/예술", "도시 미식", "깔끔한 공간"],
        "keywords": ["정돈", "날카로운 영감", "단정함"],
    },
    "수": {
        "environments": ["바다", "호수", "온천", "강가"],
        "keywords": ["흐름", "회복", "깊은 고요"],
    },
}
