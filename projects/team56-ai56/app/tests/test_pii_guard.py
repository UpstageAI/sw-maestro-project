from app.services.pii_guard import PIIGuard


def test_pii_guard_masks_email_phone_rrn_and_labeled_name() -> None:
    guard = PIIGuard()
    source = """
이름: 홍길동
연락처: 010-1234-5678
이메일: gildong@example.com
주민번호: 900101-1234567
"""
    result = guard.mask(source)

    assert result.safe_for_llm is True
    assert "[NAME_001]" in result.masked_text
    assert "[PHONE_001]" in result.masked_text
    assert "[EMAIL_001]" in result.masked_text
    assert "[RRN_001]" in result.masked_text
    assert len(result.tokens) == 4

