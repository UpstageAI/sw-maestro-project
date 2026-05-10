"""리마인더 생성 규칙"""

from datetime import datetime, timedelta


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _at_time(base: datetime, hour: int, minute: int = 0) -> datetime:
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _is_future(remind_at: datetime, now: datetime) -> bool:
    if remind_at.tzinfo and now.tzinfo is None:
        now = now.astimezone(remind_at.tzinfo)
    elif remind_at.tzinfo is None and now.tzinfo:
        now = now.replace(tzinfo=None)
    return remind_at > now


def _message(title: str, label: str) -> str:
    return f"{label} '{title}' 일정이 있습니다."


def generate_reminders(event: dict) -> list[dict]:
    """카테고리에 따라 리마인더 목록 생성

    입력:
    {
        "id": "uid123",
        "title": "A기업 면접",
        "start_time": "2025-05-15T14:00:00",
        "category": "면접"
    }

    반환:
    [
        {
            "event_id": "uid123",
            "remind_at": "2025-05-13T09:00:00",
            "message": "2일 뒤 A기업 면접이 있습니다",
            "is_sent": 0,
            "created_by": "ai"
        },
        ...
    ]

    규칙:
        면접 → 2일 전 오전 9시, 전날 오후 8시, 당일 오전 8시
        시험 → 3일 전, 전날 저녁, 당일 오전
        약속 → 2시간 전
        마감 → 전날 오전, 당일 오전
        기타 → 1시간 전
    """
    start = _parse_datetime(event["start_time"])
    now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
    title = event["title"]
    category = event.get("category") or "기타"

    rules = {
        "면접": [
            (_at_time(start - timedelta(days=2), 9), "2일 뒤"),
            (_at_time(start - timedelta(days=1), 20), "내일"),
            (_at_time(start, 8), "오늘"),
        ],
        "시험": [
            (_at_time(start - timedelta(days=3), 9), "3일 뒤"),
            (_at_time(start - timedelta(days=1), 20), "내일"),
            (_at_time(start, 8), "오늘"),
        ],
        "약속": [
            (start - timedelta(hours=2), "2시간 뒤"),
        ],
        "마감": [
            (_at_time(start - timedelta(days=1), 9), "내일"),
            (_at_time(start, 9), "오늘"),
        ],
        "기타": [
            (start - timedelta(hours=1), "1시간 뒤"),
        ],
    }

    reminders = []
    for remind_at, label in rules.get(category, rules["기타"]):
        if not _is_future(remind_at, now):
            continue

        reminders.append({
            "event_id": event["id"],
            "remind_at": remind_at.isoformat(),
            "message": _message(title, label),
            "is_sent": 0,
            "created_by": "ai",
        })

    return reminders
