# [structure] 프로젝트 파일 구조

## 배경

스키마(`schemas.py`) · State(`state.py`) · 노드 시그니처 논의를 바탕으로
프로젝트 파일 구조를 정리했습니다.

**진행 순서**
1. 5/4(월) 사전합의 — 스키마 · State 확정 → main 직접 커밋
2. 5/4(월)부터 개인 브랜치 생성 → 노드 개발 시작

> ⭐ `schemas.py` · `state.py` 는 전원 공유 파일입니다.
> 확정 이후 개인 임의 수정 금지 — 변경 필요 시 이슈로 논의 후 반영합니다.

---

## 파일 구조

```
persona-reviewer/
│
├── .env                              # API 키 (Git 업로드 금지)
├── .env.example                      # API 키 형식 예시 (Git 업로드)
├── .gitignore
├── requirements.txt
├── README.md
│
├── schemas.py                        # ⭐ Pydantic 스키마 전체 (전원 공유, 수정 금지)
├── state.py                          # ⭐ LangGraph ProjectState 정의 (전원 공유, 수정 금지)
│
├── app.py                            # Streamlit 진입점
├── graph.py                          # LangGraph 노드 연결 및 빌드
│
├── nodes/
│   ├── f0_parse.py                   # 입력 파싱 노드
│   ├── f1_select.py                  # 페르소나 선정 노드
│   ├── f2_opinion.py                 # 의견 생성 노드 (a/b 공통)
│   └── f3_review.py                  # 상호 리뷰 노드 (a/b 공통)
│
├── services/
│   └── persona_repository.py         # persona_cards.seed.json 로드
│
├── data/
│   └── personas/
│       ├── raw_personas.seed.json    # RawNemotronPersona 샘플
│       └── persona_cards.seed.json   # TargetUserPersonaCard 샘플 (런타임 로드)
│
└── scripts/
    ├── sample_hf_personas.py         # HuggingFace → raw_personas.seed.json 추출
    └── generate_user_cards.py        # RawNemotronPersona → TargetUserPersonaCard 변환
```

---

## 주요 파일 설명

### ⭐ schemas.py — 전원 공유

모든 Pydantic 스키마를 한 파일에 정의합니다.

```python
# 포함 클래스 목록
RawNemotronPersona
TargetUserPersonaCard
ServicePlanInput
ReactionPoint
Opinion
PointFeedback
Review
```

> 스키마 상세 내용은 #5 이슈 참고

---

### ⭐ state.py — 전원 공유

LangGraph `ProjectState` TypedDict를 정의합니다.

```python
from typing import TypedDict

class ProjectState(TypedDict, total=False):
    raw_input: str
    brief: ServicePlanInput
    persona_a: TargetUserPersonaCard
    persona_b: TargetUserPersonaCard
    opinion_a: Opinion
    opinion_b: Opinion
    review_a: Review
    review_b: Review
```

---

### nodes/ — 노드별 구현

각 노드는 별도 파일로 분리합니다.
`f2_opinion.py` 안에 `f2_opinion_a` / `f2_opinion_b` 함수를 함께 정의합니다.
`f3_review.py` 도 동일하게 `f3_review_a` / `f3_review_b` 를 함께 정의합니다.

```python
# nodes/f2_opinion.py
def f2_opinion_a(state: ProjectState) -> dict: ...
def f2_opinion_b(state: ProjectState) -> dict: ...

# nodes/f3_review.py
def f3_review_a(state: ProjectState) -> dict: ...
def f3_review_b(state: ProjectState) -> dict: ...
```

---

### graph.py — 노드 연결

> 5/8(목) 통합 날에 전원 함께 작성합니다.

```python
from langgraph.graph import StateGraph, START, END
from nodes.f0_parse import f0_parse
from nodes.f1_select import f1_select
from nodes.f2_opinion import f2_opinion_a, f2_opinion_b
from nodes.f3_review import f3_review_a, f3_review_b

def build_graph():
    builder = StateGraph(ProjectState)

    builder.add_node("f0_parse", f0_parse)
    builder.add_node("f1_select", f1_select)
    builder.add_node("f2_opinion_a", f2_opinion_a)
    builder.add_node("f2_opinion_b", f2_opinion_b)
    builder.add_node("f3_review_a", f3_review_a)
    builder.add_node("f3_review_b", f3_review_b)

    builder.add_edge(START, "f0_parse")
    builder.add_edge("f0_parse", "f1_select")

    # 병렬 의견 생성
    builder.add_edge("f1_select", "f2_opinion_a")
    builder.add_edge("f1_select", "f2_opinion_b")

    # 병렬 상호 리뷰
    builder.add_edge(["f2_opinion_a", "f2_opinion_b"], "f3_review_a")
    builder.add_edge(["f2_opinion_a", "f2_opinion_b"], "f3_review_b")

    builder.add_edge(["f3_review_a", "f3_review_b"], END)

    return builder.compile()
```

---

### data/ — 페르소나 데이터

```
raw_personas.seed.json      # scripts/sample_hf_personas.py 로 생성
persona_cards.seed.json     # scripts/generate_user_cards.py 로 생성
```

데모까지는 수동으로 작성한 카드 6개를 seed로 사용합니다.

```json
[
  { "card_id": "card_20s_jobseeker_001", ... },
  { "card_id": "card_30s_worker_001", ... },
  { "card_id": "card_40s_selfemployed_001", ... },
  { "card_id": "card_50s_housewife_001", ... },
  { "card_id": "card_60s_laborer_001", ... },
  { "card_id": "card_80s_elder_001", ... }
]
```

---

### .env.example

```
UPSTAGE_API_KEY=your_api_key_here
```

---

## 브랜치 전략

```
main
├── feature/schema-definition     # schemas.py · state.py (5/4 main 직접 커밋 후 삭제)
├── feature/data-preparation      # seed JSON · scripts
├── feature/parse                 # 입력 파싱 노드
├── feature/select                # 페르소나 선정 노드
├── feature/f1-opinion            # 의견 생성 노드 (johnhuh619 #13)
├── feature/f2-review             # 상호 리뷰 노드 (johnhuh619 #14)
└── feature/streamlit             # Streamlit UI 연결

# 개인 브랜치 (PR 올리는 곳)
# 1: 김운경 · 2: 김지환 · 3: 오세인 · 4: 이현정 · 5: 허재원
1/feature/parse
2/feature/parse
3/feature/parse
4/feature/parse
5/feature/parse

1/feature/select
2/feature/select
3/feature/select
4/feature/select
5/feature/select

1/feature/f1-opinion
2/feature/f1-opinion
3/feature/f1-opinion
4/feature/f1-opinion
5/feature/f1-opinion

1/feature/f2-review
2/feature/f2-review
3/feature/f2-review
4/feature/f2-review
5/feature/f2-review
```

---

## 개발 시작 순서

```
1. main pull → schemas.py · state.py 확인
2. 개인 브랜치 생성 ({각자 번호}/feature/f1-select 등)
3. parse, select, f1-opinion, f2-review 구현
4. f1, f2 기준으로 PR 올리기 → 전원 코드 리뷰 (24시간 내) → feature 브랜치 머지
5. 다음 기능으로
```
