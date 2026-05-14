"""Agent 1 — Input Validation.

Pure, synchronous. Validates the user input + API key before any LLM call.
Returns either a normalized ``UserInput`` dict or a list of error strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from _lib.state import UserInput

ALLOWED_HOURS = [
    "모름",
    "자시(23-01)", "축시(01-03)", "인시(03-05)", "묘시(05-07)",
    "진시(07-09)", "사시(09-11)", "오시(11-13)", "미시(13-15)",
    "신시(15-17)", "유시(17-19)", "술시(19-21)", "해시(21-23)",
]

ALLOWED_DEPARTURE = ["서울", "경기", "부산", "대구", "광주", "대전", "기타"]
ALLOWED_RANGE = ["2시간 이내", "4시간 이내", "제한 없음"]
ALLOWED_DURATION = ["당일", "1박 2일", "2박 3일"]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str]
    normalized: Optional[UserInput] = None


def validate_input(api_key: Any, raw_input: Any) -> ValidationResult:
    errors: List[str] = []

    if not isinstance(api_key, str) or len(api_key.strip()) < 8:
        errors.append("Solar API 키가 누락되었거나 형식이 올바르지 않습니다.")

    if not isinstance(raw_input, dict):
        errors.append("사용자 입력이 비어 있습니다.")
        return ValidationResult(ok=False, errors=errors)

    birth_date = raw_input.get("birthDate")
    if not isinstance(birth_date, str) or not _DATE_RE.match(birth_date):
        errors.append("생년월일은 YYYY-MM-DD 형식이어야 합니다.")
    else:
        try:
            parsed = datetime.strptime(birth_date, "%Y-%m-%d")
            if parsed.year < 1900 or parsed.year > 2100:
                errors.append("생년월일이 유효한 날짜가 아닙니다.")
        except ValueError:
            errors.append("생년월일이 유효한 날짜가 아닙니다.")

    birth_hour = raw_input.get("birthHour")
    if not isinstance(birth_hour, str) or birth_hour not in ALLOWED_HOURS:
        errors.append("태어난 시간 값이 유효하지 않습니다.")

    departure = raw_input.get("departure")
    if departure not in ALLOWED_DEPARTURE:
        errors.append("출발지 값이 유효하지 않습니다.")

    travel_range = raw_input.get("travelRange")
    if travel_range not in ALLOWED_RANGE:
        errors.append("이동 범위 값이 유효하지 않습니다.")

    travel_duration = raw_input.get("travelDuration")
    if travel_duration not in ALLOWED_DURATION:
        errors.append("여행 기간 값이 유효하지 않습니다.")

    preferred_styles = raw_input.get("preferredStyles")
    if not isinstance(preferred_styles, list):
        errors.append("선호 스타일은 배열이어야 합니다.")

    if errors:
        return ValidationResult(ok=False, errors=errors)

    normalized: UserInput = {
        "birthDate": birth_date,  # type: ignore[typeddict-item]
        "birthHour": birth_hour,  # type: ignore[typeddict-item]
        "departure": departure,  # type: ignore[typeddict-item]
        "travelRange": travel_range,  # type: ignore[typeddict-item]
        "travelDuration": travel_duration,  # type: ignore[typeddict-item]
        "preferredStyles": list(preferred_styles or []),
    }
    return ValidationResult(ok=True, errors=[], normalized=normalized)
