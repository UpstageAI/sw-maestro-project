# persona-reviewer

LangGraph 기반 서비스 기획 리뷰 데모입니다. 사용자가 서비스 기획안을 입력하면 가상 사용자 페르소나 2명을 선정하고, 각 페르소나의 1차 반응과 상호 리뷰를 거쳐 최종 종합 리뷰를 생성합니다.

Streamlit UI로 실행할 수 있으며, 필요하면 LangSmith tracing으로 각 노드 실행 흐름을 확인할 수 있습니다.

## 주요 기능

- 서비스 기획안 자유 입력을 구조화된 `ServicePlanInput`으로 파싱
- seed 페르소나 카드에서 리뷰에 적합한 사용자 2명 선정
- 페르소나별 긍정/부정 반응 포인트 생성
- 두 페르소나가 서로의 의견을 읽고 교차 리뷰
- 슈퍼바이저 노드가 최종 리뷰 리포트 생성
- Streamlit 데모 UI와 선택적 LangSmith tracing 지원

## 파이프라인 흐름

```text
raw_input
  -> f0_parse
  -> select_personas
  -> generate_opinion
  -> generate_review
  -> supervisor_finalize
  -> final_review_text
```

주요 연결은 `graph.py`에 있고, 각 처리 단계는 `nodes/` 아래에 나뉘어 있습니다.

## 요구사항

- Python 3.11 이상
- Upstage API key
- Windows PowerShell 스크립트 기준 실행 가이드 제공

## 설치

권장 방식은 `uv`입니다.

```powershell
uv venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
```

`uv`를 쓰기 어렵다면 `pip`로 설치해도 됩니다.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일을 만들고 API 키를 설정합니다.

```env
UPSTAGE_API_KEY=your_upstage_api_key
```

LangSmith tracing을 사용할 때만 아래 값을 추가합니다.

```env
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## 실행

Streamlit 데모는 아래 스크립트로 실행합니다. tracing 없이 빠르게 확인하려면 `-NoTrace`를 붙입니다.

```powershell
.\scripts\run_demo_streamlit.ps1 -NoTrace
```

기본 포트는 `8501`입니다. 실행 후 브라우저에서 `http://localhost:8501`로 접속합니다.

직접 실행할 수도 있습니다.

```powershell
streamlit run app.py
```

LangSmith tracing을 켜고 실행하려면 `.env`에 `LANGSMITH_API_KEY`를 설정한 뒤 `-NoTrace` 없이 실행합니다.

```powershell
.\scripts\run_demo_streamlit.ps1
```

## 테스트와 데모 확인

단위 테스트:

```powershell
python -m unittest discover -s tests
```

파이프라인 데모 실행:

```powershell
.\scripts\run_demo_trace.ps1 -NoTrace
```

LangSmith 연결까지 확인하려면 `LANGSMITH_API_KEY`를 설정하고 `-NoTrace` 없이 실행합니다.

```powershell
.\scripts\run_demo_trace.ps1
```

## 주요 파일 구조

```text
persona-reviewer/
├── app.py                         # Streamlit UI 진입점
├── graph.py                       # LangGraph 노드 연결
├── schemas.py                     # Pydantic 데이터 모델
├── state.py                       # LangGraph ProjectState
├── nodes/                         # f0~f4 파이프라인 노드
├── services/                      # UI/런타임 보조 로직
├── data/
│   ├── personas/                  # raw/persona seed JSON
│   └── service_plans/             # 샘플 서비스 기획안
├── scripts/                       # 데모 실행 및 데이터 생성 스크립트
└── docs/                          # 세팅, 구조, 설계 문서
```

## 참고 문서

- `docs/setup.md`: 개발환경 세팅 상세 가이드
- `docs/structure.md`: 프로젝트 파일 구조와 초기 설계 메모
- `docs/schema_example.md`: 데이터 모델과 파이프라인 예시
