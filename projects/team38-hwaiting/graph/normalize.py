"""부록 A.1 — 사용자 표현 → Canonical 값 정규화 (Node B 책임).

LLM 이 자유 형식으로 답해도 결정론적 매핑이 우선 적용되어 Node D 의 SQL 변환을
단순하게 유지한다.
"""
from __future__ import annotations

import re
from typing import Any

# A.1.1 해상도 ----------------------------------------------------------------

_RES_KEYWORD_MAP: dict[str, str] = {
    "fhd": "1920x1080",
    "풀hd": "1920x1080",
    "1080p": "1920x1080",
    "wuxga": "1920x1200",
    "hd+": "1600x900",
    "qhd": "2560x1440",
    "2k": "2560x1440",
    "1440p": "2560x1440",
    "wqxga": "2560x1600",
    "uhd": "3840x2160",
    "4k": "3840x2160",
    "2160p": "3840x2160",
}
_RES_PATTERN = re.compile(r"(\d{3,4})\s*[x×*]\s*(\d{3,4})", re.IGNORECASE)


def normalize_resolution(s: str | None) -> str | None:
    if not s:
        return None
    text = s.strip().lower()
    if text in _RES_KEYWORD_MAP:
        return _RES_KEYWORD_MAP[text]
    for k, v in _RES_KEYWORD_MAP.items():
        if k in text:
            return v
    m = _RES_PATTERN.search(s)
    if m:
        return f"{int(m.group(1))}x{int(m.group(2))}"
    return None


# A.1.2 OS --------------------------------------------------------------------

_OS_KEYWORDS: list[tuple[str, str]] = [
    ("windows", "Windows"),
    ("윈도우", "Windows"),
    ("윈11", "Windows"),
    ("윈10", "Windows"),
    ("win11", "Windows"),
    ("win10", "Windows"),
    ("macos", "macOS"),
    ("mac os", "macOS"),
    ("osx", "macOS"),
    ("맥os", "macOS"),
    ("맥북", "macOS"),
    ("맥", "macOS"),
    ("freedos", "FreeDOS"),
    ("프리도스", "FreeDOS"),
    ("도스", "FreeDOS"),
    ("ubuntu", "Linux"),
    ("우분투", "Linux"),
    ("linux", "Linux"),
    ("리눅스", "Linux"),
]


def normalize_os(s: str | None) -> str | None:
    if not s:
        return None
    text = s.strip().lower()
    for k, v in _OS_KEYWORDS:
        if k in text:
            return v
    return None


# A.1.3 CPU 키워드 추출 --------------------------------------------------------

_CPU_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"Apple\s+M[1-4](?:\s+(?:Pro|Max|Ultra))?", re.IGNORECASE),
    re.compile(
        r"Intel\s+Core\s+(?:Ultra\s+)?(?:i[3579]|Ultra\s+[579])-?\s*\d{3,5}[A-Z]?",
        re.IGNORECASE,
    ),
    re.compile(r"Ryzen\s+[3579]\s+\d{4,5}[A-Z]?", re.IGNORECASE),
]

# 한글/혼합 표현용 매핑 — 영문 매칭이 실패한 입력에 한해 적용한다.
# 출력은 DB cpu 컬럼의 substring 이 되도록 짧은 영문 키워드.
_CPU_KR_APPLE = re.compile(
    r"(?:애플\s*|맥\s*|apple\s*|mac\s*)?M\s*([1-4])"
    r"(?:\s*(Pro|Max|Ultra|프로|맥스|울트라))?",
    re.IGNORECASE,
)
_CPU_KR_INTEL_ULTRA = re.compile(
    r"(?:인텔\s*코어\s*울트라|코어\s*울트라|intel\s*core\s*ultra|ultra)\s*([579])",
    re.IGNORECASE,
)
_CPU_KR_INTEL_I = re.compile(
    r"(?:인텔\s*코어\s*|인텔\s*|intel\s*core\s*|intel\s*|코어\s*)?"
    r"i\s*([3579])"
    r"(?:\s*[-]?\s*(\d{3,5}[A-Za-z]?))?",
    re.IGNORECASE,
)
_CPU_KR_RYZEN = re.compile(
    r"(?:AMD\s*)?(?:라이젠|ryzen)\s*([3579])"
    r"(?:\s+(\d{4,5}[A-Za-z]+))?",
    re.IGNORECASE,
)
_CPU_TIER_MAP = {"프로": "Pro", "맥스": "Max", "울트라": "Ultra"}


def extract_cpu_keyword(s: str | None) -> str | None:
    if not s:
        return None

    # 1) 영문 정규식 — 풀 canonical 키워드 추출 (회귀 방지)
    for pat in _CPU_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(0).strip()

    # 2) 한글/혼합 매핑 — DB substring 으로 변환
    m = _CPU_KR_APPLE.search(s)
    if m:
        digit = m.group(1)
        tier_raw = (m.group(2) or "").strip()
        tier = _CPU_TIER_MAP.get(tier_raw, tier_raw).title() if tier_raw else ""
        return f"Apple M{digit}" + (f" {tier}" if tier else "")

    m = _CPU_KR_INTEL_ULTRA.search(s)
    if m:
        return f"Intel Core Ultra {m.group(1)}"

    m = _CPU_KR_INTEL_I.search(s)
    if m:
        digit = m.group(1)
        model = m.group(2)
        return f"i{digit}-{model}" if model else f"i{digit}"

    m = _CPU_KR_RYZEN.search(s)
    if m:
        digit = m.group(1)
        model = m.group(2)
        return f"Ryzen {digit} {model}" if model else f"Ryzen {digit}"

    # 3) 입력 원문 폴백 (기존 동작)
    return s.strip() or None


# A.1.4 단위 -------------------------------------------------------------------

def parse_weight_kg(s: Any) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    text = str(s).lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|키로|킬로)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(g|그램)", text)
    if m:
        return float(m.group(1)) / 1000.0
    m = re.search(r"\d+(?:\.\d+)?", text)
    if m:
        return float(m.group(0))
    return None


def parse_screen_inch(s: Any) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    text = str(s).lower()
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:인치|"|in\b)', text)
    if m:
        return float(m.group(1))
    m = re.search(r"\d+(?:\.\d+)?", text)
    if m:
        return float(m.group(0))
    return None


def parse_ram_gb(s: Any) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        return int(s)
    text = str(s).lower().replace(",", "")
    m = re.search(r"(\d+)\s*(gb|기가|g\b)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+", text)
    if m:
        return int(m.group(0))
    return None


def parse_storage_gb(s: Any) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        return int(s)
    text = str(s).lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(tb|테라)", text)
    if m:
        return int(float(m.group(1)) * 1024)
    m = re.search(r"(\d+)\s*(gb|기가|g\b)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+", text)
    if m:
        return int(m.group(0))
    return None


def parse_price_krw(s: Any) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        return int(s)
    text = str(s).lower().replace(",", "").replace(" ", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*억", text)
    if m:
        return int(float(m.group(1)) * 100_000_000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*만", text)
    if m:
        return int(float(m.group(1)) * 10_000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*천", text)
    if m:
        return int(float(m.group(1)) * 1_000)
    m = re.search(r"\d+", text)
    if m:
        return int(m.group(0))
    return None


def parse_brightness_nits(s: Any) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        return int(s)
    text = str(s).lower().replace(",", "")
    m = re.search(r"(\d+)\s*(nit|니트)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+", text)
    if m:
        return int(m.group(0))
    return None


# 통합 후처리 -----------------------------------------------------------------

_PARSERS: dict[str, Any] = {
    "weight_kg": parse_weight_kg,
    "screen_inch": parse_screen_inch,
    "ram_gb": parse_ram_gb,
    "storage_gb": parse_storage_gb,
    "price_krw": parse_price_krw,
    "brightness_nits": parse_brightness_nits,
    "resolution": normalize_resolution,
    "os": normalize_os,
}


def apply_canonical(slots: dict[str, Any]) -> dict[str, Any]:
    """LLM 이 추출한 슬롯 값을 부록 A.1 룰로 후처리.

    `cpu` 는 Node D 의 LIKE 매칭 시점에 키워드 추출하므로 여기서는 원문 유지.
    실패 시 None 으로 클리어 (잘못된 값을 그대로 두는 것보다 미수집 처리가 안전).
    """
    cleaned: dict[str, Any] = dict(slots)
    for k, parser in _PARSERS.items():
        v = cleaned.get(k)
        if v is None or v == "":
            cleaned[k] = None
            continue
        try:
            cleaned[k] = parser(v)
        except Exception:  # noqa: BLE001
            cleaned[k] = None
    return cleaned
