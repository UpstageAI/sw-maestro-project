from typing import TypedDict


class FeedSource(TypedDict):
    url: str
    source: str


class CategoryFeed(TypedDict):
    label: str
    feeds: list[FeedSource]


CATEGORY_FEEDS: dict[str, CategoryFeed] = {
    "tech": {
        "label": "테크",
        "feeds": [
            {"url": "https://www.hankyung.com/feed/it", "source": "한국경제"},
            {"url": "http://rss.etnews.com/03.xml", "source": "전자신문"},
            {"url": "https://nwww.newsis.com/RSS/health.xml", "source": "뉴시스"},
        ],
    },
    "economy": {
        "label": "경제",
        "feeds": [
            {"url": "https://www.hankyung.com/feed/economy", "source": "한국경제"},
            {"url": "https://www.mk.co.kr/rss/30100041/", "source": "매일경제"},
            {"url": "https://nwww.newsis.com/RSS/economy.xml", "source": "뉴시스"},
        ],
    },
    "policy": {
        "label": "정책",
        "feeds": [
            {"url": "https://www.hankyung.com/feed/politics", "source": "한국경제"},
            {"url": "https://www.mk.co.kr/rss/30200030/", "source": "매일경제"},
            {"url": "https://nwww.newsis.com/RSS/politics.xml", "source": "뉴시스"},
        ],
    },
    "issue": {
        "label": "이슈",
        "feeds": [
            {"url": "https://www.hankyung.com/feed/society", "source": "한국경제"},
            {"url": "https://www.mk.co.kr/rss/50400012/", "source": "매일경제"},
            {"url": "https://nwww.newsis.com/RSS/society.xml", "source": "뉴시스"},
        ],
    },
}

RSS_FEEDS: dict[str, list[str]] = {
    feed["label"]: [source["url"] for source in feed["feeds"]]
    for feed in CATEGORY_FEEDS.values()
}


def parse_category_ids(raw_categories: str | None) -> list[str]:
    if raw_categories is None or not raw_categories.strip():
        return []

    category_ids = []
    seen = set()
    for part in raw_categories.split(","):
        category_id = part.strip()
        if category_id and category_id not in seen:
            validate_category_id(category_id)
            category_ids.append(category_id)
            seen.add(category_id)

    return category_ids


def validate_category_id(category_id: str) -> None:
    if category_id not in CATEGORY_FEEDS:
        raise ValueError(f"Unsupported category: {category_id}")
