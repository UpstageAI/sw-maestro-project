"""PoC #1 — Gemini structured output (intake 노드용).

목적:
    intake_node가 자연어를 구조화 dict로 파싱할 때 사용할
    `google-genai` SDK의 structured output 호출 형태와 응답 attribute 경로를 검증.

사용:
    cd autocoin-ai
    source .venv/bin/activate
    cp .env.example .env  &&  vim .env   # GEMINI_API_KEY 채우기
    python poc/poc_structured.py

검증 포인트:
    1) `response_mime_type="application/json"` + `response_schema`가 동작하는가
    2) 응답 객체에서 파싱된 dict를 어떤 attribute로 꺼내는가
       (resp.text? resp.parsed? candidates[0]....?)
    3) 한국어 자연어를 영어 enum 값으로 매핑하는가
       ("공격적으로" → "AGGRESSIVE")

이 스크립트가 통과하면 → llm.py의 gemini_generate() 시그니처 확정.
실패하면 → 응답 attribute가 다른 위치에 있을 가능성. dir()/repr() 출력으로 추적.
"""
from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv


INTAKE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symbol": {"type": "STRING", "description": "예: BTCUSDT"},
        "side": {"type": "STRING", "enum": ["BUY", "SELL"]},
        "type": {"type": "STRING", "enum": ["MARKET", "LIMIT"]},
        "size_usd": {"type": "STRING", "description": "USDT 환산 금액 문자열"},
        "inferred_persona": {
            "type": "STRING",
            "enum": ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"],
        },
        "persona_override_reason": {
            "type": "STRING",
            "description": "발화에 명시 단어 있을 때만 사유, 없으면 빈 문자열",
        },
        "ambiguity_score": {
            "type": "NUMBER",
            "description": "0=명확, 1=모호. 0.5 초과 시 HOLD 처리 예정",
        },
    },
    "required": [
        "symbol", "side", "type", "size_usd",
        "inferred_persona", "persona_override_reason", "ambiguity_score",
    ],
}


SYSTEM_INSTRUCTION = (
    "당신은 코인 거래 의도 파서입니다. 사용자의 한국어 발화를 받아 "
    "구조화된 매매 의도로 변환합니다. Binance Spot Testnet의 BTCUSDT/ETHUSDT "
    "심볼만 우선 처리합니다. 모호한 입력에는 ambiguity_score를 높게 매기세요."
)


TEST_INPUTS = [
    "BTC 5만원치 사줘 공격적으로",
    "비트코인 좀 사봐",                # 모호 — ambiguity_score 높아야
    "이더리움 10만원 시장가 매수",
]


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경변수가 비어있음. .env 확인.", file=sys.stderr)
        return 1

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    for index, text in enumerate(TEST_INPUTS, start=1):
        print("=" * 70)
        print(f"[입력 {index}] {text}")
        print("-" * 70)

        try:
            resp = client.models.generate_content(
                model=model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=INTAKE_SCHEMA,
                    temperature=0,
                ),
            )
        except Exception as exc:
            print(f"[CALL FAILED] {type(exc).__name__}: {exc}")
            continue

        print("\n[응답 객체 type]", type(resp).__name__)
        print("\n[응답 attribute 후보]")
        for attr in ("text", "parsed", "candidates"):
            value = getattr(resp, attr, "<not present>")
            print(f"  resp.{attr} = {repr(value)[:200]}")

        print("\n[resp.text 시도]")
        try:
            parsed = json.loads(resp.text)
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except Exception as exc:
            print(f"  JSON 파싱 실패: {exc}")

        print("\n[resp.parsed 시도]")
        parsed_attr = getattr(resp, "parsed", None)
        print(f"  type: {type(parsed_attr).__name__}")
        print(f"  value: {parsed_attr}")

    print("\n" + "=" * 70)
    print("[다음 액션] 위 출력에서 ✅ 동작한 attribute 경로 기록 → llm.py에 매핑")
    return 0


if __name__ == "__main__":
    sys.exit(main())
