# LLM Integration Test Results

**Date:** 2026-05-10  
**Model:** gemini-2.5-pro  
**Run time:** 19.62s total (5 tests)

## Test Summary

| Test | Node | Result | Notes |
|------|------|--------|-------|
| `test_intake_nl_parse_buy` | intake | ✅ PASS | "비트코인 100달러치 시장가로 매수하고 싶어" → BTCUSDT BUY |
| `test_intake_nl_parse_ambiguous` | intake | ✅ PASS | "그냥 좀 사줘" → LIFECYCLE_HOLD (ambiguity_score > 0.5) |
| `test_strategy_generates_proposal` | strategy | ✅ PASS | Returns action ∈ {BUY, SELL, HOLD}, conviction float, rationale |
| `test_evaluator_generates_report` | evaluator | ✅ PASS | user_message + reason_codes present, no EVALUATOR_LLM_FALLBACK |
| `test_risk_agent_react_loop` | risk_agent | ✅ PASS | ReAct loop made ≥ 1 tool call (get_balance / get_volatility) |

## Run Command

```
pytest tests/test_llm_live.py -v -m live --tb=short
```

## Key Observations

- **intake NL parsing**: Gemini correctly parsed Korean natural language into structured intent. Symbol, side, and size were extracted accurately.
- **intake ambiguity detection**: Vague input ("그냥 좀 사줘") correctly scored ambiguity_score > 0.5 → LIFECYCLE_HOLD.
- **strategy**: LLM produced a structured proposal with valid action, float conviction, and rationale text.
- **evaluator**: Produced a non-fallback response with `user_message`, `summary`, and `reason_codes` populated.
- **risk_agent ReAct**: Function-calling loop triggered at least one real tool call (balance/volatility check) before stopping.

## Skip Behavior

Tests are decorated with `pytest.mark.live` and `skipif(not GEMINI_API_KEY)`.  
CI without a key skips all 5 tests cleanly — no failures.

## Regression Suite

After all refactoring, the full mock test suite also passed:

```
pytest tests/ -q --tb=short --ignore=tests/test_http_api.py
49 passed, 458 warnings in 102.98s
```
