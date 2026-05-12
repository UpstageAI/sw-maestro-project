# PoC — Phase 0 시작 전 검증

> Agentic Upgrade 본 작업 전 60~90분 안에 끝내야 하는 SDK 검증.
> 이 두 스크립트가 통과해야 `llm.py`의 시그니처를 확정할 수 있다.

## 1. 준비

```bash
cd autocoin-ai
cp .env.example .env
# .env 열어서 GEMINI_API_KEY=... 채우기

source .venv/bin/activate
```

## 2. 실행

```bash
python poc/poc_structured.py        # intake 노드용
python poc/poc_function_calling.py  # risk_agent 노드용
```

## 3. 통과 기준

### `poc_structured.py`
- [ ] 3개 입력 모두 응답 받음 (CALL FAILED 없음)
- [ ] `resp.text` 또는 `resp.parsed` 중 하나로 JSON dict 추출 가능
- [ ] "공격적으로" 발화가 `inferred_persona: "AGGRESSIVE"` 로 매핑됨
- [ ] "비트코인 좀 사봐" 입력의 `ambiguity_score`가 0.5 이상

→ ✅ 통과 시: `llm.py`의 `gemini_generate(prompt, response_schema)` 시그니처 확정.

### `poc_function_calling.py`
- [ ] 모델이 `get_balance`, `get_volatility` 둘 다 호출함
- [ ] `part.function_call.name`, `dict(part.function_call.args)` 로 인자 접근됨
- [ ] 도구 결과 회신 후 다음 턴에서 추가 호출 또는 최종 텍스트 응답
- [ ] MAX_TURNS 안에 종료됨 (도구 호출 없는 응답으로 빠짐)

→ ✅ 통과 시: `risk_agent_node`의 ReAct 루프 + `llm.py`의 `gemini_generate_with_tools()` 확정.

## 4. 실패 시 폴백

| 실패 양상 | 폴백 |
|---|---|
| `response_schema` 거부됨 | 자유 텍스트 + 수동 JSON 파싱 (정규식) |
| function calling SDK API 다름 | `dir(resp.candidates[0].content.parts[0])`로 attribute 추적 |
| 둘 다 안 되면 | risk_agent ReAct 폐기 → 결정론 risk만으로 MVP 진행 |

## 5. 결과 기록

통과한 attribute 경로를 다음에 옮긴다:
- `src/autocoin_ai/llm.py` — 실제 SDK 호출 함수 시그니처
- `docs/AGENTIC_UPGRADE.md` v2 — 결정 기록(Decision Log)에 한 줄 추가
