# apps/ai-gateway — 냥멍일기 AI Gateway

FastAPI + LangGraph + OpenAI GPT-4o-mini Vision (ADR-0003, ADR-0005, ADR-0011).

- Python 3.12 + uv
- 사진 + 키워드 → 1인칭 일기 생성
- 호스팅: Railway us-east4
- 보안 경계: `X-Internal-Secret` + Bearer JWT (ADR-0006)
