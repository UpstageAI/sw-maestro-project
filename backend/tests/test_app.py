"""FastAPI 앱 통합 테스트 (TestClient)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.llm import (
    FallbackProvider,
    LLMProvider,
    OfflineProvider,
    _coerce_response,
    _parse_llm_json,
)
from backend.schemas import AnalyzeRequest


client = TestClient(app)


SAMPLE_AGENDA = "1. Q3 마케팅 전략\n2. 신규 기능 로드맵"
SAMPLE_TRANSCRIPT = (
    "[10:00] 김철수: Q3 마케팅 예산안은 이영희 님이 5월 10일까지 정리해 주세요.\n"
    "[10:05] 이영희: 신규 기능 요구사항 문서는 박민준 님이 5월 7일까지 작성하기로 하시죠.\n"
    "[10:10] 박민준: 협업 방식은 다음 회의에서 이어서 논의하면 좋겠습니다."
)


# ---------------------------------------------------------------------------
# 기본 엔드포인트
# ---------------------------------------------------------------------------


def test_healthz_ok():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "provider" in body


def test_root_metadata():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body
    assert "/analyze" in body["endpoints"]


# ---------------------------------------------------------------------------
# /analyze - 정상 케이스
# ---------------------------------------------------------------------------


def test_analyze_success_returns_full_schema():
    resp = client.post(
        "/analyze",
        json={"agenda": SAMPLE_AGENDA, "transcript": SAMPLE_TRANSCRIPT},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 필수 필드 존재
    for key in ("summary", "missed_agenda", "next_agenda", "action_items"):
        assert key in body
    assert isinstance(body["action_items"], list)


def test_analyze_extracts_action_items_from_transcript():
    resp = client.post(
        "/analyze",
        json={"agenda": SAMPLE_AGENDA, "transcript": SAMPLE_TRANSCRIPT},
    )
    body = resp.json()
    assert len(body["action_items"]) >= 1
    item = body["action_items"][0]
    assert set(item.keys()) >= {"who", "when", "what"}
    assert "sub_items" in item
    assert isinstance(item["sub_items"], list)


# ---------------------------------------------------------------------------
# /analyze - 검증 실패
# ---------------------------------------------------------------------------


def test_analyze_rejects_empty_agenda():
    resp = client.post("/analyze", json={"agenda": "", "transcript": "abc"})
    assert resp.status_code == 422


def test_analyze_rejects_empty_transcript():
    resp = client.post("/analyze", json={"agenda": "안건", "transcript": "  "})
    assert resp.status_code == 422


def test_analyze_rejects_missing_field():
    resp = client.post("/analyze", json={"agenda": "안건"})
    assert resp.status_code == 422


def test_analyze_rejects_oversized_transcript():
    huge = "가" * 200_001
    resp = client.post("/analyze", json={"agenda": "x", "transcript": huge})
    assert resp.status_code == 422


def test_schema_allows_chunkable_transcript_length():
    req = AnalyzeRequest(agenda="안건", transcript="가" * 100_001)
    assert len(req.transcript) == 100_001


# ---------------------------------------------------------------------------
# 응답 정규화 / JSON 파싱 헬퍼
# ---------------------------------------------------------------------------


def test_coerce_response_handles_none_and_strings():
    out = _coerce_response(None)
    assert out["action_items"] == []
    assert out["summary"] == ""

    out = _coerce_response(
        {"summary": ["a", "b"], "action_items": [{"who": None, "when": None, "what": "x"}]}
    )
    assert "a" in out["summary"]
    assert out["action_items"][0]["what"] == "x"
    assert out["action_items"][0]["who"] == ""
    assert out["action_items"][0]["sub_items"] == []


def test_coerce_response_preserves_sub_action_items():
    out = _coerce_response(
        {
            "summary": "회의에서 작업을 나눴습니다.",
            "action_items": [
                {
                    "title": "요구사항 문서 준비",
                    "who": "박민준",
                    "when": "2026-05-07",
                    "what": "신규 기능 요구사항 문서를 준비한다.",
                    "sub_items": [
                        {
                            "who": "박민준",
                            "when": "2026-05-06",
                            "what": "인증 개편 요구사항을 정리한다.",
                        },
                        "초안을 팀에 공유한다.",
                    ],
                }
            ],
        }
    )

    item = out["action_items"][0]
    assert item["title"] == "요구사항 문서 준비"
    assert len(item["sub_items"]) == 2
    assert item["sub_items"][0]["what"] == "인증 개편 요구사항을 정리한다."
    assert item["sub_items"][1]["what"] == "초안을 팀에 공유한다."


def test_parse_llm_json_with_code_fence():
    text = "여기 결과입니다.\n```json\n{\"summary\": \"hi\"}\n```\n끝."
    parsed = _parse_llm_json(text)
    assert parsed and parsed["summary"] == "hi"


def test_parse_llm_json_with_trailing_comma():
    text = '{"summary": "hi", "action_items": [],}'
    parsed = _parse_llm_json(text)
    assert parsed and parsed["summary"] == "hi"


def test_parse_llm_json_returns_none_for_garbage():
    assert _parse_llm_json("hello") is None


# ---------------------------------------------------------------------------
# Fallback 동작
# ---------------------------------------------------------------------------


class _BoomProvider(LLMProvider):
    name = "boom"

    def analyze(self, agenda, transcript):
        raise RuntimeError("simulated failure")


def test_fallback_provider_falls_back_to_offline():
    fp = FallbackProvider(_BoomProvider())
    out = fp.analyze(SAMPLE_AGENDA, SAMPLE_TRANSCRIPT)
    assert out.get("_fallback") is True
    assert isinstance(out["action_items"], list)


def test_offline_provider_alone_works():
    out = OfflineProvider().analyze(SAMPLE_AGENDA, SAMPLE_TRANSCRIPT)
    assert "action_items" in out
    assert any("이영희" == it["who"] or "박민준" == it["who"] for it in out["action_items"])
    assert all("sub_items" in it for it in out["action_items"])


# ---------------------------------------------------------------------------
# 잘못된 Content-Type / JSON
# ---------------------------------------------------------------------------


def test_analyze_rejects_invalid_json_body():
    resp = client.post(
        "/analyze",
        data="not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 422)
