# 노트북 추천 챗봇 — LangGraph 코어

PRD `tasks/prd.md` 의 LangGraph 그래프 (Node B/C/D/E/F) + Streamlit UI 구현.
크롤러(US-001~005), 단위 테스트, 페르소나 시뮬레이션은 별도 PR 에서 진행.

> 브랜치: `feat/langgraph-core`

## 요구사항

- Python 3.11+
- SQLite3 CLI (DB 초기화에 사용)
- Upstage Solar API Key (https://console.upstage.ai)

## 빠른 시작

```powershell
# 1) 가상 환경
python -m venv .venv
.venv\Scripts\activate

# 2) 의존성
pip install -r requirements.txt

# 3) DB 초기화 (시드 더미 10건)
sqlite3 db/laptops.db ".read db/schema.sql"
sqlite3 db/laptops.db ".read db/seed_dummy.sql"

# 4) 환경 변수
copy .env.example .env
#   .env 의 UPSTAGE_API_KEY 를 채우세요.

# 5) 실행
streamlit run app/main.py
```

## 구조

```
graph/
  state.py        # LaptopChatState (TypedDict + add_messages reducer)
  llm.py          # make_llm() — langchain-upstage 우선, langchain-openai 폴백
  prompts.py      # Node B/C/F 시스템 프롬프트
  normalize.py    # 부록 A.1: 해상도 / OS / CPU / 단위 매핑
  nodes.py        # Node B/C/D/E/F 구현
  edges.py        # route_after_b — is_complete + turn_count>20 안전장치
  build.py        # build_graph() — StateGraph 컴파일

app/
  main.py         # Streamlit 엔트리 (Node A 입력)
  ui_components.py# 사이드바·카드 그리드·비교표
  static/         # no_image.png 직접 배치 (선택)

db/
  schema.sql      # laptops 테이블
  seed_dummy.sql  # 더미 10건
  laptops.db      # 위 명령으로 생성 (gitignore)
```

## 그래프 흐름 (PRD §7.7)

```
ENTRY → B ┬─[is_complete]      → D → E → F → END
          └─[!is_complete]     → C → END
```

- 매 사용자 발화당 `graph.invoke(state)` 1회 호출
- State 는 `st.session_state["chat_state"]` 가 보관 (체크포인터 역할)
- `turn_count > 20` 시 강제 D 진입 (부분 슬롯 모드, FR-16)

## 트러블슈팅

- **`langchain-upstage` import 에러**: `pip install langchain-upstage` 실패 시 자동으로 `langchain-openai` 의 `ChatOpenAI(base_url=...)` 로 폴백됩니다 (`graph/llm.py`).
- **JSON 모드 미지원 (OQ-9)**: 현재 시스템 프롬프트로 JSON 강제 + Pydantic 검증을 함께 사용하므로 양쪽 SDK 모두 동작합니다.
- **`no_image.png`**: 적당한 PNG 파일을 `app/static/no_image.png` 로 배치하면 썸네일이 없는 후보에서 사용됩니다. 없으면 이모지 폴백.
- **DB 파일 부재**: `streamlit run` 전 `sqlite3` 명령 두 줄로 `db/laptops.db` 를 만들었는지 확인하세요.

## Out of Scope

- crawler/ 모듈 (다나와 크롤링)
- 단위 / 통합 테스트
- 페르소나 시뮬레이션 (US-020)
- LangGraph `MemorySaver` 영속화
