"""P0-1 Mock LLM provider — 회귀 테스트.

검증 포인트:
- mock classifier 가 CLASSIFIER_SCHEMA 와 호환되는 JSON 반환
- mock drafter 가 비어있지 않은 50자 이상 텍스트 반환
- 환경 분기: UPSTAGE_API_KEY 없으면 mock, 있으면 real path 시도
- _MockChatLLM 의 bind_tools / invoke 2회 호출 시 tool_calls→content 흐름
"""

from __future__ import annotations

import importlib

import pytest


# --- helpers ------------------------------------------------------------------


def _reset_env_for_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    monkeypatch.setenv("REVIEW_OPS_LLM", "mock")


def _reset_env_for_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTAGE_API_KEY", "dummy-key-for-testing")
    monkeypatch.delenv("REVIEW_OPS_LLM", raising=False)


# --- classifier schema 호환 ---------------------------------------------------


def test_mock_classifier_returns_valid_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env_for_mock(monkeypatch)
    from src.graph.nodes.classifier import CLASSIFIER_SCHEMA, classify

    result, meta = classify("주말 대기가 너무 길어요 위생도 별로")
    assert result["sentiment"] in {"positive", "negative", "neutral"}
    assert isinstance(result["categories"], list)
    for cat in result["categories"]:
        assert "category" in cat and "confidence" in cat
        assert 0.0 <= cat["confidence"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["risk_flag"], bool)

    # meta 필수 키
    for key in ("model", "duration_ms", "input_tokens", "output_tokens"):
        assert key in meta

    # negative 키워드 매칭 → sentiment=negative
    assert result["sentiment"] == "negative"
    # CLASSIFIER_SCHEMA 의 required 필드가 모두 있는지
    for req in CLASSIFIER_SCHEMA["required"]:
        assert req in result


def test_mock_classifier_positive_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env_for_mock(monkeypatch)
    from src.graph.nodes.classifier import classify

    result, _ = classify("정말 맛있고 친절한 최고의 카페예요")
    assert result["sentiment"] == "positive"
    assert result["confidence"] >= 0.8


def test_mock_classifier_lowconf_when_mixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """양쪽 키워드 공존 시 confidence<0.7 → apology_lowconf 분기 유도."""
    _reset_env_for_mock(monkeypatch)
    from src.graph.nodes.classifier import classify

    result, _ = classify("맛있긴 한데 줄이 너무 길고 비싸요")
    assert result["sentiment"] == "negative"
    assert result["confidence"] < 0.7


def test_mock_classifier_risk_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env_for_mock(monkeypatch)
    from src.graph.nodes.classifier import classify

    result, _ = classify("씨발 진짜 별로네 고소할까")
    assert result["risk_flag"] is True
    assert result["risk_reason"] is not None


# --- drafter 텍스트 응답 ------------------------------------------------------


def test_mock_drafter_returns_nonempty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env_for_mock(monkeypatch)
    from src.llm.upstage import complete_text_with_meta

    drafter_system = (
        "You write a Korean reply to a customer review.\n\n"
        "[지시]\n"
        "다음 부정 리뷰에 사과 답글을 작성하세요. 다음 3단 구조 강제:\n"
        "1) 사실 인정 (리뷰의 구체적 포인트 한 번 언급)\n"
        "2) 사과\n"
        "3) 개선 방향이나 대안 제시"
    )
    text, meta = complete_text_with_meta(
        prompt="리뷰 원문: 대기가 너무 길어요",
        system=drafter_system,
    )
    assert text.startswith("[MOCK")
    assert len(text) >= 50
    assert meta["input_tokens"] == 0


# --- 환경 분기 ----------------------------------------------------------------


def test_routing_uses_mock_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    monkeypatch.delenv("REVIEW_OPS_LLM", raising=False)
    from src.llm.upstage import complete_text_with_meta

    text, _ = complete_text_with_meta(prompt="안녕", system="generic system")
    assert text.startswith("[MOCK")


def test_routing_uses_real_when_api_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """API_KEY 가 있으면 real path 시도 → 우리가 _do_call 을 가로채 raise."""
    _reset_env_for_real(monkeypatch)
    # _client 캐시 초기화 (다른 테스트 영향 제거)
    from src.llm import upstage as upstage_mod
    monkeypatch.setattr(upstage_mod, "_client", None)

    real_path_called = {"flag": False}

    def fake_do_call(**kwargs):
        real_path_called["flag"] = True
        raise upstage_mod.UpstageError("real path attempted (test stub)")

    monkeypatch.setattr(upstage_mod, "_do_call", fake_do_call)

    with pytest.raises(upstage_mod.UpstageError):
        upstage_mod.complete_text_with_meta(prompt="안녕", system="generic system")

    assert real_path_called["flag"] is True


# --- _MockChatLLM bind_tools / invoke 흐름 -----------------------------------


def test_mock_chat_llm_bind_tools_invoke_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env_for_mock(monkeypatch)
    # upstage_chat 모듈을 재import — env 분기를 새로 평가
    import src.llm.upstage_chat as chat_mod
    importlib.reload(chat_mod)

    from langchain_core.messages import HumanMessage, SystemMessage

    llm = chat_mod.get_chat_llm(model="solar-pro2", tools=[lambda x: x])
    assert isinstance(llm, chat_mod._MockChatLLM)

    msgs = [
        SystemMessage(content="aggregator system"),
        HumanMessage(content="매장 'PLACE_DEMO_001' 의 최근 4주 부정 카테고리 TOP 3"),
    ]
    first = llm.invoke(msgs)
    assert first.tool_calls and first.tool_calls[0]["name"] == "query_review_stats"
    assert first.tool_calls[0]["args"]["place_id"] == "PLACE_DEMO_001"
    assert first.tool_calls[0]["args"]["group_by"] == "category"
    assert first.content == ""

    second = llm.invoke(msgs)
    assert second.content.startswith("[MOCK]")
    assert second.tool_calls == []
    assert "1." in second.content  # 자연어 TOP 3 포맷
