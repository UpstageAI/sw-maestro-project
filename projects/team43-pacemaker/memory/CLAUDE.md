# memory/ — LangGraph 체크포인터

> **담당**: C(이유준). agent/와 함께.

## 역할

멀티턴 대화에서 이전 제안과 사용자 피드백 컨텍스트를 유지. `agent/graph.py`가 그래프를 컴파일할 때 `checkpointer=` 인자로 주입한다.

## 구현 가이드

### 1차 — InMemorySaver (5/4~5/7)

```python
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()
```

- 프로세스 메모리에만 저장. FastAPI 재시작 시 초기화.
- 개발/데모엔 충분.

### 2차 — SqliteSaver (시간 남으면)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("memory.sqlite")
```

- 파일 기반. 재시작해도 대화 유지.
- `.gitignore`에 `*.sqlite` 등록되어 있음.

## thread_id

FE(B의 채팅 위젯)가 세션마다 고유한 `thread_id`를 만들어 `POST /agent/chat`에 매번 같이 보냄. backend/api/chat.py가 `run_agent_stream(user_input, thread_id)`로 그대로 위임.

## 작업 시 주의

- 체크포인터 객체는 **모듈 레벨에서 1회만 생성** (그래프 컴파일 시점에 재사용)
- 프로덕션 시크릿/PII 저장 금지 — 우리는 가상 데이터지만 습관 차원
