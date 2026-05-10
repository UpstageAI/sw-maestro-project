"""PoC #2 — Gemini function calling (risk_agent 노드용).

목적:
    risk_agent_node가 ReAct 루프로 도구를 호출할 때 사용할
    `google-genai` SDK의 function calling 응답 attribute 경로를 검증.

사용:
    cd autocoin-ai
    source .venv/bin/activate
    python poc/poc_function_calling.py

검증 포인트:
    1) tools=[Tool(function_declarations=[...])] 설정이 동작하는가
    2) LLM이 도구를 호출하기로 결정했을 때 응답 어디에 함수명/인자가 있는가
       (resp.candidates[0].content.parts[*].function_call?)
    3) 도구 결과를 다시 LLM에 넘겨 다음 turn으로 이어가는 메시지 형식
    4) "더 부를 도구 없음 → 최종 답" 종료 조건 감지 방법

이 스크립트가 통과하면 → risk_agent의 ReAct 루프 시그니처 확정.
실패하면 → SDK 버전이 다르거나 응답 shape이 다름. dir()/repr() 추적.
"""
from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv


# ── 가짜 도구 핸들러 ────────────────────────────────────────────────
def fake_get_balance(asset: str) -> dict:
    fake = {
        "USDT": {"free": "5000.0", "locked": "0", "total": "5000.0"},
        "BTC":  {"free": "0.05",   "locked": "0", "total": "0.05"},
    }
    return fake.get(asset, {"error": f"unknown asset: {asset}"})


def fake_get_volatility(symbol: str, days: int) -> dict:
    fake = {
        "BTCUSDT": {"atr_pct": 0.045, "stdev_pct": 0.038},
        "ETHUSDT": {"atr_pct": 0.061, "stdev_pct": 0.054},
    }
    base = fake.get(symbol, {"error": f"unknown symbol: {symbol}"})
    return {**base, "window_days": days} if "error" not in base else base


HANDLERS = {
    "get_balance": fake_get_balance,
    "get_volatility": fake_get_volatility,
}


SYSTEM_INSTRUCTION = (
    "당신은 코인 거래 리스크 오피서입니다. 매매 제안의 안전성을 검토하기 위해 "
    "도구를 사용해 관련 데이터를 조회한 뒤 최종 verdict를 내립니다. "
    "각 도구 호출 전에 왜 그 도구가 필요한지 짧게 설명하세요. "
    "최종 답을 낼 때는 ALLOW / HOLD / REJECT 중 하나의 verdict를 명시하세요."
)


TEST_PROMPT = (
    "다음 매매 제안을 검토해주세요: BUY BTCUSDT, $200 USDT 시장가. "
    "잔고와 변동성을 조회한 뒤 verdict를 알려주세요."
)


def build_tools(types_module):
    return [
        types_module.Tool(function_declarations=[
            types_module.FunctionDeclaration(
                name="get_balance",
                description="사용자의 보유 자산 잔고를 조회합니다.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "asset": {"type": "STRING", "description": "자산 심볼 (예: USDT, BTC)"},
                    },
                    "required": ["asset"],
                },
            ),
            types_module.FunctionDeclaration(
                name="get_volatility",
                description="특정 심볼의 최근 N일 ATR 및 표준편차 변동성.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "symbol": {"type": "STRING", "description": "예: BTCUSDT"},
                        "days": {"type": "INTEGER", "description": "조회 윈도우 (일)"},
                    },
                    "required": ["symbol", "days"],
                },
            ),
        ]),
    ]


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경변수가 비어있음.", file=sys.stderr)
        return 1

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    tools = build_tools(types)

    contents: list = [
        types.Content(role="user", parts=[types.Part(text=TEST_PROMPT)]),
    ]

    print("=" * 70)
    print(f"[프롬프트] {TEST_PROMPT}")
    print("=" * 70)

    MAX_TURNS = 6
    for turn in range(1, MAX_TURNS + 1):
        print(f"\n--- Turn {turn} ---")
        try:
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=tools,
                    temperature=0,
                ),
            )
        except Exception as exc:
            print(f"[CALL FAILED] {type(exc).__name__}: {exc}")
            return 2

        candidate = resp.candidates[0]
        parts = candidate.content.parts or []

        function_calls: list = []
        text_parts: list[str] = []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                function_calls.append(fc)
            if getattr(part, "text", None):
                text_parts.append(part.text)

        if text_parts:
            print(f"[모델 텍스트]\n{''.join(text_parts)}")

        if not function_calls:
            print("[종료] 도구 호출 없음 → 최종 답")
            print(f"[finish_reason] {getattr(candidate, 'finish_reason', '?')}")
            print(f"[응답 attribute 후보]")
            for attr in ("text", "candidates"):
                print(f"  resp.{attr} = {repr(getattr(resp, attr, None))[:200]}")
            break

        # 도구 호출 → 핸들러 dispatch → tool 응답 메시지 추가 후 다음 턴
        contents.append(candidate.content)
        for fc in function_calls:
            print(f"[호출 요청] name={fc.name} args={dict(fc.args)}")
            handler = HANDLERS.get(fc.name)
            result = handler(**fc.args) if handler else {"error": f"unknown tool: {fc.name}"}
            print(f"[핸들러 결과] {json.dumps(result, ensure_ascii=False)}")

            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_function_response(name=fc.name, response={"result": result})],
            ))
    else:
        print("\n[WARN] MAX_TURNS 도달. 무한 루프 가능성. risk_agent에서는 4~8회로 제한 권장.")

    print("\n" + "=" * 70)
    print("[다음 액션] 위 출력에서 ✅ part.function_call 접근 패턴 + 종료 조건 기록")
    return 0


if __name__ == "__main__":
    sys.exit(main())
