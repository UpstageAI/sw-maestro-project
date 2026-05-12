# tests/ — 스모크/단위 테스트

> **담당**: 전원이 자기 슬라이스 테스트 추가

## 실행

```bash
pytest                       # 전체
pytest tests/test_smoke.py   # 스모크만
pytest -k calendar           # 키워드 매칭
```

5/4 EOD부터 매 PR이 `pytest` 통과해야 머지.

## 작성 규칙

- 파일명: `test_<slice>.py` — 슬라이스 명은 A~E.
  - 예: `test_a_frontend_contract.py` (A), `test_b_chat_protocol.py` (B), `test_c_agent.py` (C), `test_d_tools_calendar.py` (D), `test_e_tools_health.py` (E)
- 한 테스트 = 한 가지 검증. assert 메시지 한국어 OK.
- 외부 LLM 호출이 필요한 테스트는 `@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), ...)` 로 보호
- FE(Flutter) 단위 테스트는 `frontend/test/` 안에서 `flutter test`로. pytest 범위는 Python (BE/Agent/Tools)만.

## 슬라이스별 최소 테스트 (5/5 EOD까지 1개씩)

- **A** (FE): BE 응답 모델 JSON 라운드트립 (Python에서 `model_dump → model_validate` 통과). FE Dart 모델은 `frontend/test/`에서 별도.
- **B** (Chat 프로토콜): `ChatChunk` type별 payload 키가 schemas/CLAUDE.md 표와 일치
- **C** (Agent): 시스템 프롬프트에 ReAct 3단계 키워드 포함 + `run_agent_stream` async iterator 동작
- **D** (Tools 분담분): `get_/create_/update_/delete_calendar_event` 시그니처와 빈 입력 케이스
- **E** (Tools 분담분): D와 동일하되 자기 도메인 (예: health)

## KPI 시나리오 테스트 (5/9까지)

`tests/test_kpi.py`에 시나리오 5개. 실제 입력 데이터는 `data/scenarios/*.json`에서 로드 (D/E가 적재). LLM 호출 포함되므로 `@pytest.mark.kpi` 마커로 묶어 평소엔 스킵, 통합 시점에만 실행:

```bash
pytest -m kpi   # 통합/데모 시점에만
```

## Backend 통합 테스트

FastAPI는 `httpx.AsyncClient`로 라우터 직접 호출 (`uvicorn` 띄울 필요 X):

```python
from httpx import AsyncClient
from backend.main import app

async def test_health_ping():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
```
