# persona-reviewer

서비스 기획안을 입력하면 적합한 페르소나 2명을 선정하고, 각 페르소나의 1차 반응과 교차 리뷰를 거쳐 최종 리포트를 생성하는 LangGraph 기반 리뷰 파이프라인입니다.

Streamlit UI로 데모를 실행할 수 있고, LangSmith tracing을 켜면 각 노드의 실행 흐름을 추적할 수 있습니다.

## 주요 기능

- 자유 형식 기획안을 `ServicePlanInput`으로 구조화
- 선별된 100개 페르소나 카드에서 검색 기반 후보 랭킹 후 2명 선정
- 페르소나별 긍정/우려 포인트와 사용 의향 생성
- 상대 페르소나의 의견을 포인트 단위로 교차 리뷰
- f2/f3 산출물에 deterministic 품질 리포트 부착
- 품질 실패 산출물은 다음 노드와 UI 표시에서 제외
- 최종 판단 토큰은 품질 플래그 기준으로 deterministic 결정
- 기획안에 없는 추론은 최종 리포트의 `추가 검증 가설` 섹션으로 분리
- Streamlit UI에서 품질 기준, 선택된 패널, 실행 로그, 페르소나 선택 애니메이션 제공

## 파이프라인

```text
raw_input
  -> f0_parse
  -> select_personas
  -> generate_opinion x 2
  -> collect_opinions
  -> generate_review x N
  -> collect_reviews
  -> supervisor_finalize
  -> final_review_text
```

각 단계의 역할은 다음과 같습니다.

| 단계 | 역할 |
| --- | --- |
| `f0_parse` | 자유 입력 기획안을 구조화하고 부족한 필드를 원문 기반으로 보수적으로 보강 |
| `select_personas` | 페르소나 풀을 검색 랭킹한 뒤 서로 보완적인 2명 선정 |
| `generate_opinion` | 각 페르소나가 기획안에 대해 1차 긍정/우려 반응 작성 |
| `generate_review` | 실패한 1차 포인트는 제외하고, 상대 의견을 포인트 단위로 리뷰 |
| `supervisor_finalize` | 검증된 산출물만 종합해 최종 리포트 작성 |

## 품질 관리

중간 산출물은 `services/artifact_quality.py`와 `services/brief_evidence.py`에서 검사합니다.

- 기획안 핵심 기능/우려사항과 직접 연결되지 않은 포인트 감지
- 기획안에 없는 기능, 운영 방식, 자동화, 정산, 추천 등 unsupported solution 감지
- 근거 없는 숫자/비율 주장 감지
- 페르소나 맥락 연결이 약한 산출물은 weak로 표시
- fail 산출물은 UI와 다음 노드 입력에서 제외

최종 리포트는 품질 상태에 따라 `[통과]`, `[보류]`, `[재검토]` 중 하나로 시작합니다.

## 요구사항

- Python 3.11 이상
- Upstage API key
- Windows PowerShell 기준 실행 스크립트 제공

## 설치

권장 방식은 `uv`입니다.

```powershell
uv venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
```

`pip`로도 설치할 수 있습니다.

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

Streamlit UI를 tracing 없이 실행합니다.

```powershell
.\scripts\run_demo_streamlit.ps1 -NoTrace
```

기본 포트는 `8501`입니다.

```text
http://localhost:8501
```

직접 실행할 수도 있습니다.

```powershell
streamlit run app.py
```

LangSmith tracing을 켜려면 `.env`에 `LANGSMITH_API_KEY`를 설정한 뒤 `-NoTrace` 없이 실행합니다.

```powershell
.\scripts\run_demo_streamlit.ps1
```

## 테스트와 수동 확인

전체 테스트:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

노드별 품질 산출물 확인:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_node_quality.py farm_direct
```

샘플 brief 전체 파이프라인 실행:

```powershell
.\scripts\run_demo_trace.ps1 -NoTrace
```

LangSmith tracing까지 확인하려면 `LANGSMITH_API_KEY`를 설정하고 `-NoTrace` 없이 실행합니다.

```powershell
.\scripts\run_demo_trace.ps1
```

## 주요 파일 구조

```text
persona-reviewer/
├── app.py                         # Streamlit UI
├── graph.py                       # LangGraph 노드 연결
├── schemas.py                     # Pydantic 데이터 모델
├── state.py                       # LangGraph ProjectState
├── nodes/
│   ├── f0_parse.py                # 기획안 파싱
│   ├── f1_select.py               # 페르소나 선정
│   ├── f2_opinion.py              # 1차 의견 생성
│   ├── f3_review.py               # 교차 리뷰 생성
│   └── f4_supervisor.py           # 최종 리포트 생성
├── services/
│   ├── artifact_quality.py        # 산출물 품질 검사
│   ├── brief_evidence.py          # 기획안 근거 추출/검증
│   ├── persona_repository.py      # 페르소나 카드 로드
│   ├── persona_retrieval.py       # 임베딩 캐시 기반 페르소나 랭킹
│   └── pipeline_runner.py         # UI용 파이프라인 실행 헬퍼
├── data/
│   ├── personas/                  # 선별 페르소나 풀과 임베딩 캐시
│   └── service_plans/             # 샘플 서비스 기획안
├── scripts/                       # 데이터 생성, 데모, 품질 확인 스크립트
├── tests/                         # unittest 기반 테스트
└── docs/                          # 설계/실행 참고 문서
```

## 데이터와 스크립트

- `data/personas/persona_cards.selected.json`: 런타임에서 사용하는 100개 페르소나 카드
- `data/personas/persona_cards.selected.embeddings.json`: 검색 랭킹용 임베딩 캐시
- `scripts/sample_hf_personas.py`: HuggingFace 원천 데이터 샘플링
- `scripts/generate_user_cards.py`: raw persona를 runtime card로 변환
- `scripts/build_persona_embedding_cache.py`: 페르소나 카드 임베딩 캐시 생성
- `scripts/evaluate_node_quality.py`: 샘플 입력의 노드별 품질 리포트 출력

## 참고 문서

- `docs/setup.md`: 개발환경 세팅 상세 가이드
- `docs/structure.md`: 초기 파일 구조와 팀 개발 메모
- `docs/schema_example.md`: 데이터 모델과 파이프라인 예시
- `docs/test-briefs.md`: 페르소나 선택 수동 평가용 샘플 brief
