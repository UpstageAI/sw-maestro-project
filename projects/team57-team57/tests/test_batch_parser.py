"""일괄 톤 샘플 입력 파서 테스트 (블록 / TSV / CSV / auto-detect).

검증 포인트:
- 블록: '리뷰:/답글:' 멀티라인 본문, 빈 줄 블록 구분, '리뷰 :' whitespace 허용
- TSV: TAB 구분, 헤더 행 스킵
- CSV: 첫 쉼표만 split → 답글에 쉼표 포함 OK
- auto-detect 우선순위: 블록 > TSV > CSV
- 빈/너무 짧은/한 쪽 비어있는 pair 는 제외됨
"""

from __future__ import annotations

import os

# mock 강제 (LLM 호출 없음, parser unit test)
os.environ["REVIEW_OPS_LLM"] = "mock"
os.environ.pop("UPSTAGE_API_KEY", None)

from src.ui.components import (  # noqa: E402
    _parse_block,
    _parse_tabular,
    _parse_tone_sample_batch,
)


def test_parse_block_basic():
    text = (
        "리뷰: 음식이 정말 맛있었어요\n"
        "답글: 감사합니다 또 들러주세요!\n"
        "\n"
        "리뷰: 너무 짰어요\n"
        "답글: 죄송합니다 간을 점검하겠습니다"
    )
    pairs = _parse_block(text)
    assert len(pairs) == 2
    assert pairs[0] == ("음식이 정말 맛있었어요", "감사합니다 또 들러주세요!")
    assert pairs[1] == ("너무 짰어요", "죄송합니다 간을 점검하겠습니다")


def test_parse_block_multiline_review():
    text = (
        "리뷰: 음식은 맛있었는데\n"
        "주차장이 너무 좁아요\n"
        "답글: 불편을 드려 죄송합니다"
    )
    pairs = _parse_block(text)
    assert len(pairs) == 1
    review, reply = pairs[0]
    assert "음식은 맛있었는데" in review
    assert "주차장이 너무 좁아요" in review
    assert reply == "불편을 드려 죄송합니다"


def test_parse_block_extra_whitespace():
    text = (
        "  리뷰 :   친절했어요\n"
        "답글 : 감사합니다 좋은 하루 되세요"
    )
    pairs = _parse_block(text)
    assert len(pairs) == 1
    assert pairs[0][0] == "친절했어요"
    assert pairs[0][1] == "감사합니다 좋은 하루 되세요"


def test_parse_tabular_tsv():
    text = (
        "맛있었어요\t감사합니다 또 오세요\n"
        "별로였어요\t죄송합니다 개선하겠습니다\n"
        "친절해요\t방문 감사드립니다"
    )
    pairs = _parse_tabular(text, "\t")
    assert len(pairs) == 3
    assert pairs[0] == ("맛있었어요", "감사합니다 또 오세요")
    assert pairs[2] == ("친절해요", "방문 감사드립니다")


def test_parse_tabular_csv_first_comma_only():
    text = "정말 맛있어요,맛있어요,또 올게요"
    pairs = _parse_tabular(text, ",")
    assert len(pairs) == 1
    review, reply = pairs[0]
    assert review == "정말 맛있어요"
    # 답글에 쉼표 포함 — 첫 쉼표만 split 되어 뒤는 전부 reply
    assert reply == "맛있어요,또 올게요"


def test_parse_tabular_skips_header_row():
    text = (
        "리뷰,답글\n"
        "맛있어요,감사합니다 또 오세요"
    )
    pairs = _parse_tabular(text, ",")
    assert len(pairs) == 1
    assert pairs[0] == ("맛있어요", "감사합니다 또 오세요")


def test_parse_auto_detects_block():
    text = (
        "리뷰: 너무 좋아요\n"
        "답글: 감사드립니다 또 들러주세요"
    )
    pairs = _parse_tone_sample_batch(text, "자동 감지")
    assert len(pairs) == 1
    assert pairs[0][0] == "너무 좋아요"


def test_parse_auto_detects_tsv():
    text = "맛있어요\t감사합니다 또 들러주세요"
    pairs = _parse_tone_sample_batch(text, "자동 감지")
    assert len(pairs) == 1
    assert pairs[0] == ("맛있어요", "감사합니다 또 들러주세요")


def test_parse_auto_falls_back_csv():
    text = "맛있어요,감사합니다 또 들러주세요"
    pairs = _parse_tone_sample_batch(text, "자동 감지")
    assert len(pairs) == 1
    assert pairs[0] == ("맛있어요", "감사합니다 또 들러주세요")


def test_parse_empty_text_returns_empty_list():
    assert _parse_tone_sample_batch("", "자동 감지") == []
    assert _parse_tone_sample_batch("   \n  \n", "자동 감지") == []
    assert _parse_tone_sample_batch(None, "자동 감지") == []  # type: ignore[arg-type]


def test_parse_skips_short_pairs():
    # review 가 너무 짧음 (< 3 chars) → 제외
    text = "ok,감사합니다 또 들러주세요"
    pairs = _parse_tone_sample_batch(text, "CSV")
    assert pairs == []


def test_parse_skips_blank_reply():
    # 답글이 비어있으면 _parse_tabular 단계에서 이미 drop
    text = "맛있어요,"
    pairs = _parse_tone_sample_batch(text, "CSV")
    assert pairs == []

    # 블록 포맷도 동일
    text2 = "리뷰: 맛있어요\n답글:    "
    pairs2 = _parse_tone_sample_batch(text2, "블록")
    assert pairs2 == []
