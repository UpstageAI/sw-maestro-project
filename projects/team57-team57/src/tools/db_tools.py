from __future__ import annotations

from collections import Counter
from typing import Any

from src.db.repository import ReviewAgentRepository

DEMO_STORE_NAME = "브라운빈 카페"
DEMO_SEED_REVIEWS: list[dict[str, Any]] = [
    {"text": "아메리카노 맛은 좋은데 점심시간 줄이 너무 길어요.", "sentiment": "부정", "categories": ["맛", "대기시간"], "menu_tags": ["아메리카노"]},
    {"text": "바닐라라떼는 맛있었지만 가격이 조금 비싸게 느껴졌어요.", "sentiment": "부정", "categories": ["맛", "가격"], "menu_tags": ["바닐라라떼"]},
    {"text": "소금빵이 정말 맛있고 직원분도 친절했어요.", "sentiment": "긍정", "categories": ["맛", "서비스"], "menu_tags": ["소금빵"]},
    {"text": "테이블 정리가 늦어서 위생이 조금 아쉬웠습니다.", "sentiment": "부정", "categories": ["위생"], "menu_tags": []},
    {"text": "콜드브루는 진하고 좋았는데 주문이 조금 밀렸어요.", "sentiment": "부정", "categories": ["맛", "대기시간"], "menu_tags": ["콜드브루"]},
    {"text": "딸기케이크가 맛있고 사진도 예쁘게 나와요.", "sentiment": "긍정", "categories": ["맛"], "menu_tags": ["딸기케이크"]},
    {"text": "직원 응대가 다소 차갑게 느껴졌어요.", "sentiment": "부정", "categories": ["서비스"], "menu_tags": []},
    {"text": "아메리카노는 무난했지만 자리가 조금 지저분했어요.", "sentiment": "부정", "categories": ["위생"], "menu_tags": ["아메리카노"]},
    {"text": "바닐라라떼가 부드럽고 만족스러웠습니다.", "sentiment": "긍정", "categories": ["맛"], "menu_tags": ["바닐라라떼"]},
    {"text": "피크타임에는 줄 안내가 조금 더 필요해 보여요.", "sentiment": "부정", "categories": ["대기시간"], "menu_tags": []},
    {"text": "소금빵은 맛있는데 가격이 자주 부담돼요.", "sentiment": "부정", "categories": ["맛", "가격"], "menu_tags": ["소금빵"]},
    {"text": "직원분이 친절하게 추천해주셔서 좋았어요.", "sentiment": "긍정", "categories": ["서비스"], "menu_tags": []},
    {"text": "주문 누락이 한 번 있었고 응대가 매끄럽지 않았어요.", "sentiment": "부정", "categories": ["서비스"], "menu_tags": []},
    {"text": "화장실과 매장 바닥 청소 상태가 조금 아쉬웠습니다.", "sentiment": "부정", "categories": ["위생"], "menu_tags": []},
    {"text": "콜드브루 맛은 괜찮았지만 대기 시간이 길었습니다.", "sentiment": "부정", "categories": ["맛", "대기시간"], "menu_tags": ["콜드브루"]},
    {"text": "딸기케이크는 맛있지만 가격대가 높게 느껴졌어요.", "sentiment": "부정", "categories": ["맛", "가격"], "menu_tags": ["딸기케이크"]},
    {"text": "매장이 조용하고 전체적으로 만족스러웠어요.", "sentiment": "긍정", "categories": ["서비스"], "menu_tags": []},
    {"text": "대기 줄은 길었지만 아메리카노 맛은 좋아요.", "sentiment": "중립", "categories": ["맛", "대기시간"], "menu_tags": ["아메리카노"]},
]


def load_store_context_tool(repo: ReviewAgentRepository, store_id: int) -> dict[str, Any]:
    store = repo.get_store(store_id)
    if store is None:
        raise ValueError(f"Store not found: {store_id}")

    return {
        "store_id": store.id,
        "name": store.name,
        "business_type": store.business_type,
        "menu_items": store.menu_items,
        "price_range": store.price_range,
        "reply_tone": store.reply_tone,
        "reply_samples": store.reply_samples,
    }


def load_recent_feedback_tool(
    repo: ReviewAgentRepository,
    store_id: int,
    *,
    limit: int = 5,
) -> list[str]:
    return repo.list_recent_edited_replies(store_id, limit=limit)


def save_reviews_tool(
    repo: ReviewAgentRepository,
    *,
    store_id: int,
    raw_input_text: str,
    classified_reviews: list[dict[str, Any]],
    drafted_replies: list[dict[str, Any]],
) -> tuple[int, list[int]]:
    session_id = repo.create_review_session(store_id=store_id, raw_input_text=raw_input_text)
    saved_review_ids: list[int] = []

    replies_by_index = {item["review_index"]: item for item in drafted_replies}
    for review in classified_reviews:
        drafted = replies_by_index.get(review["review_index"], {})
        review_id = repo.create_review(
            session_id=session_id,
            store_id=store_id,
            original_text=review["original_text"],
            masked_text=review["masked_text"],
            sentiment=review.get("sentiment"),
            sentiment_confidence=review.get("confidence"),
            categories=review.get("categories", []),
            menu_tags=review.get("menu_tags", []),
            generated_replies=drafted.get("replies", []),
            selected_reply=(drafted.get("replies") or [None])[0],
            status=review.get("status", "analyzed"),
        )
        saved_review_ids.append(review_id)

    return session_id, saved_review_ids


def load_negative_review_patterns_tool(
    repo: ReviewAgentRepository,
    store_id: int,
) -> dict[str, Any]:
    reviews = repo.list_reviews_by_store(store_id)
    total_count = len(reviews)
    negative_reviews = [review for review in reviews if review.sentiment == "부정"]

    category_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()

    for review in negative_reviews:
        for category in review.categories:
            category_counter[category] += 1
        for keyword in _extract_keywords(review.masked_text):
            keyword_counter[keyword] += 1

    return {
        "total_review_count": total_count,
        "negative_review_count": len(negative_reviews),
        "category_counts": dict(category_counter),
        "keyword_counts": dict(keyword_counter),
    }


def _extract_keywords(text: str) -> list[str]:
    candidates = [
        "대기",
        "줄",
        "친절",
        "차갑",
        "비싸",
        "청소",
        "위생",
        "누락",
        "응대",
        "테이블",
    ]
    return [keyword for keyword in candidates if keyword in text]


def initialize_demo_store_tool(repo: ReviewAgentRepository) -> dict[str, Any]:
    repo.reset_all_data()
    store_id = repo.upsert_store(
        store_id=None,
        name=DEMO_STORE_NAME,
        business_type="개인 카페",
        menu_items=["아메리카노", "바닐라라떼", "소금빵", "딸기케이크", "콜드브루"],
        price_range="중간",
        reply_tone="정중체",
        reply_samples=[
            "소중한 리뷰 남겨주셔서 감사합니다. 다음 방문에도 만족하실 수 있도록 더 세심하게 준비하겠습니다.",
            "방문해주셔서 감사합니다. 남겨주신 의견은 운영 점검에 반영하겠습니다.",
            "좋은 말씀과 아쉬운 점 모두 감사히 확인했고 더 나은 경험을 드리기 위해 노력하겠습니다.",
        ],
    )
    demo_store = repo.get_store(store_id)

    assert demo_store is not None
    session_id = repo.create_review_session(store_id=demo_store.id, raw_input_text="demo_seed_reviews")

    saved_review_ids: list[int] = []
    for item in DEMO_SEED_REVIEWS:
        replies = [
            "소중한 의견 감사합니다. 말씀해주신 내용을 운영에 반영하겠습니다.",
            "리뷰 남겨주셔서 감사합니다. 더 나은 경험을 드릴 수 있도록 점검하겠습니다.",
        ]
        review_id = repo.create_review(
            session_id=session_id,
            store_id=demo_store.id,
            original_text=item["text"],
            masked_text=item["text"],
            sentiment=item["sentiment"],
            sentiment_confidence=0.84,
            categories=item["categories"],
            menu_tags=item["menu_tags"],
            generated_replies=replies,
            selected_reply=replies[0],
            status="seeded",
        )
        saved_review_ids.append(review_id)

    return {
        "store_id": demo_store.id,
        "store_name": demo_store.name,
        "seeded_review_count": len(saved_review_ids),
        "session_id": session_id,
    }
