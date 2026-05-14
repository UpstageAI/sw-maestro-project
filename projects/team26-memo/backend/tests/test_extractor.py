"""extractor 단위 테스트."""

from __future__ import annotations

from datetime import date

import pytest

from backend.extractor import (
    extract_action_items,
    extract_persons,
    extract_summary,
    find_missed_agenda,
    is_action_sentence,
    parse_date,
    split_agenda_items,
    suggest_next_agenda,
)


SAMPLE_TRANSCRIPT = (
    "[10:00] 김철수: 안녕하세요, 오늘 회의 시작하겠습니다. Q3 마케팅 전략부터 보시죠.\n"
    "[10:02] 이영희: 지난 분기 대비 디지털 광고 비중을 30%로 늘리는 안을 제안합니다.\n"
    "[10:05] 박민준: 좋습니다. 다만 예산이 한정되어 있어 콘텐츠 마케팅 비중을 조정해야 할 것 같아요.\n"
    "[10:10] 김철수: Q3 마케팅 예산안은 김철수 님이 5월 10일까지 정리해 공유해 주세요.\n"
    "[10:15] 이영희: 신규 기능 로드맵 관련, 사용자 인증 개편이 우선순위가 되어야 할 것 같습니다.\n"
    "[10:20] 박민준: 신규 기능 요구사항 문서는 이영희 님이 5월 7일까지 작성하기로 하시죠.\n"
    "[10:25] 김철수: 경쟁사 분석 보고서는 박민준 님이 5월 12일까지 마무리 부탁드립니다.\n"
    "[10:30] 이영희: 협업 방식 개선은 다음 회의에서 이어서 논의하면 좋겠습니다.\n"
    "[10:32] 김철수: 네, 그럼 오늘 회의 마치겠습니다."
)

SAMPLE_AGENDA = (
    "1. Q3 마케팅 전략 검토\n"
    "2. 신규 기능 로드맵 논의\n"
    "3. 예산 배분 확정\n"
    "4. 고객 피드백 리뷰\n"
    "5. 경쟁사 분석 결과 공유"
)


# ---------------------------------------------------------------------------
# 인명 / 날짜 / 액션 키워드
# ---------------------------------------------------------------------------


def test_extract_persons_finds_korean_names():
    persons = extract_persons("김철수가 이영희에게 박민준을 소개했다.")
    assert "김철수" in persons
    assert "이영희" in persons
    assert "박민준" in persons


def test_extract_persons_dedup_order():
    persons = extract_persons("김철수 김철수 이영희")
    assert persons == ["김철수", "이영희"]


def test_parse_date_iso():
    assert parse_date("마감은 2026-05-10 입니다") == "2026-05-10"


def test_parse_date_korean_full():
    assert parse_date("2026년 5월 10일까지") == "2026-05-10"


def test_parse_date_korean_short_uses_base_year():
    base = date(2026, 5, 1)
    assert parse_date("5월 10일까지", base=base) == "2026-05-10"


def test_parse_date_relative_tomorrow():
    base = date(2026, 5, 1)
    assert parse_date("내일까지 부탁드립니다", base=base) == "2026-05-02"


def test_parse_date_none_for_no_date():
    assert parse_date("기한은 추후 결정") is None


def test_is_action_sentence_positive():
    assert is_action_sentence("내일까지 정리해 주세요")
    assert is_action_sentence("문서 작성을 부탁드립니다")
    assert is_action_sentence("이영희 님이 마무리하기로 했습니다")


def test_is_action_sentence_negative():
    assert not is_action_sentence("오늘 날씨가 좋네요")
    assert not is_action_sentence("안녕하세요")


# ---------------------------------------------------------------------------
# 안건 분리 / 누락 안건
# ---------------------------------------------------------------------------


def test_split_agenda_items_handles_numbering():
    items = split_agenda_items("1. 첫번째\n2) 두번째\n- 세번째")
    assert items == ["첫번째", "두번째", "세번째"]


def test_find_missed_agenda_detects_missing():
    missed = find_missed_agenda(SAMPLE_AGENDA, SAMPLE_TRANSCRIPT)
    # '고객 피드백' 은 녹취록에 없음 → 누락
    assert any("고객 피드백" in m for m in missed)


def test_find_missed_agenda_does_not_flag_discussed():
    missed = find_missed_agenda(SAMPLE_AGENDA, SAMPLE_TRANSCRIPT)
    # 'Q3 마케팅 전략' 은 충분히 논의됨
    assert not any("Q3 마케팅 전략" in m for m in missed)


# ---------------------------------------------------------------------------
# 액션 아이템
# ---------------------------------------------------------------------------


def test_extract_action_items_basic():
    items = extract_action_items(SAMPLE_TRANSCRIPT)
    assert len(items) >= 3

    whats = [it.what for it in items]
    assert any("예산안" in w for w in whats)
    assert any("요구사항" in w for w in whats)
    assert any("경쟁사" in w for w in whats)


def test_extract_action_items_owner_assignment():
    items = extract_action_items(SAMPLE_TRANSCRIPT)
    # 본문에 다른 이름이 명시된 경우 그 사람을 우선
    by_what = {it.what: it for it in items}
    found = [it for w, it in by_what.items() if "요구사항" in w]
    assert found and found[0].who == "이영희"


def test_extract_action_items_when_parsed():
    items = extract_action_items(SAMPLE_TRANSCRIPT)
    dates = [it.when for it in items if it.when]
    assert any(d.endswith("-05-10") for d in dates)
    assert any(d.endswith("-05-07") for d in dates)


def test_extract_action_items_empty_transcript():
    assert extract_action_items("") == []


def test_extract_action_items_no_actions():
    assert extract_action_items("그냥 잡담을 했습니다. 날씨 좋네요.") == []


# ---------------------------------------------------------------------------
# 요약 / 다음 회의 안건
# ---------------------------------------------------------------------------


def test_extract_summary_non_empty():
    summary = extract_summary(SAMPLE_TRANSCRIPT)
    assert summary
    # 인사말은 포함되지 않아야 함
    assert "안녕하세요" not in summary


def test_extract_summary_empty():
    assert extract_summary("") == ""


def test_suggest_next_agenda_includes_missed_and_explicit():
    actions = extract_action_items(SAMPLE_TRANSCRIPT)
    missed = find_missed_agenda(SAMPLE_AGENDA, SAMPLE_TRANSCRIPT)
    nxt = suggest_next_agenda(SAMPLE_AGENDA, SAMPLE_TRANSCRIPT, missed, actions)
    assert nxt
    # '협업 방식' 은 다음 회의에서 다루기로 명시됨
    assert any("협업" in n for n in nxt) or any("이월" in n for n in nxt)
