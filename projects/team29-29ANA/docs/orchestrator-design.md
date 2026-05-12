# AI 면접 코치 — Orchestrator 설계 문서

작성일: 2026-05-04

---

## 1. 전체 아키텍처

```
UI
 ↓
orchestrator.py          ← 세션 흐름 제어 (지형님)
 ├─ document_loader      ← PDF 파싱 + ChromaDB 인덱싱 (태균님)
 ├─ tavily_search        ← 회사 정보 웹검색 + 캐싱 (태균님)
 ├─ question_generator   ← 질문·꼬리질문 생성 LLM (본인 + 세림님)
 ├─ answer_evaluator     ← 답변 평가 LLM (본인 + 세림님)
 └─ report_generator     ← 종합 리포트 생성 LLM (정훈님)
```

---

## 2. 데이터 계약 (`models/types.py`)

모든 모듈 간 데이터 흐름의 인터페이스. 팀원은 이 타입에 맞춰 모듈을 구현한다.

```python
from dataclasses import dataclass, field
from typing import Literal

Category = Literal["CS", "프로젝트", "문제해결", "인성", "적합성"]


@dataclass
class CompanyProfile:
    name: str
    tech_stack: list[str]
    culture: str
    recent_news: str
    source_urls: list[str]      # Tavily 검색 결과 출처 — LLM 생성값 금지


@dataclass
class SessionContext:
    chroma_collection_name: str          # 태균님이 ChromaDB에 저장한 컬렉션 이름
    company_profile: CompanyProfile | None  # Tavily 실패 시 None
    job_description: str                 # 원본 채용공고 전문


@dataclass
class Question:
    id: str
    text: str
    category: Category
    difficulty: int             # 1~5
    is_followup: bool
    parent_id: str | None       # 꼬리질문이면 부모 질문 id, 아니면 None


@dataclass
class EvaluationResult:
    question: Question
    user_answer: str
    star_score: int             # STAR 구조 점수 1~5
    specificity_score: int      # 구체성 점수 1~5
    relevance_score: int        # 직무 관련성 점수 1~5
    consistency_score: int      # 일관성 점수 1~5
    weakness_tags: list[str]    # 약점 태그 — 꼬리질문 발동 트리거
    feedback: str               # JSON 형식으로 LLM이 반환


@dataclass
class Report:
    overall_score: float
    category_scores: dict[str, float]
    weakness_summary: list[str]
    improvement_suggestions: str


@dataclass
class SessionState:
    context: SessionContext
    history: list[tuple[Question, EvaluationResult]] = field(default_factory=list)
    bundle_count: int = 0           # 완료된 묶음 수 (메인 질문 기준)
    question_count: int = 0         # 전체 질문 수 (꼬리질문 포함)
    current_followup_depth: int = 0 # 현재 묶음에서 발생한 꼬리질문 수
    max_followup_depth: int = 3     # 묶음당 최대 꼬리질문 수
    min_bundles_for_report: int = 3 # 리포트 작성 가능 최소 묶음 수
    max_questions: int = 50         # 세션 전체 질문 한도 (초과 시 강제 종료)
    is_active: bool = True
```

---

## 3. 묶음(Bundle) 개념

한 묶음 = 메인 질문 1개 + 꼬리질문 최대 3개

```
[묶음 1]
  ├─ 메인 질문:  "가장 어려웠던 기술적 결정은?"
  ├─ 꼬리질문 1: "왜 다른 대안이 아니라 그 선택을 했나요?"
  ├─ 꼬리질문 2: "그 결과가 어땠나요?"
  └─ 꼬리질문 3: "지금 다시 결정한다면 바꿀 점이 있나요?"

[묶음 2]  ← bundle_count가 1이 된 후 시작
  └─ ...
```

- `bundle_count >= min_bundles_for_report(3)` 이 되어야 리포트 생성 가능
- 꼬리질문 발동 여부: `weakness_tags`가 있고 `current_followup_depth < max_followup_depth`

---

## 4. 오케스트레이터 기능 흐름

### 4-1. 세션 시작

```
사용자 입력: PDF 경로(자소서·이력서) + 채용공고 텍스트
    ↓
document_loader 호출 → ChromaDB 인덱싱
    ↓
사용자 동의 확인 → tavily_search 호출 → CompanyProfile 생성 (24시간 캐시)
    ↓
SessionContext 생성
    ↓
SessionState 초기화 (question_count=0, bundle_count=0, ...)
    ↓
세션 시작 알림 → 첫 메인 질문 생성
```

### 4-2. 질문 루프 (핵심 분기)

```
[답변 수신]
    ↓
50자 이하 답변? ─── YES → "더 구체적으로 답해 주세요" 재요청 (이하 단계 건너뜀)
    │
    NO
    ↓
answer_evaluator 호출 → EvaluationResult 반환
    ↓
state.history에 (question, result) 추가
state.question_count += 1
    ↓
꼬리질문 가능?
(weakness_tags 있음 AND current_followup_depth < max_followup_depth)
    ├─ YES → question_generator(is_followup=True) 호출
    │         current_followup_depth += 1
    │
    └─ NO  → 묶음 완료
              bundle_count += 1
              current_followup_depth = 0
                  ↓
             강제 종료 조건?
             (question_count >= max_questions)
                  ├─ YES → report_generator 호출 → 세션 종료
                  └─ NO  → 리포트 가능?
                           (bundle_count >= min_bundles_for_report)
                                ├─ YES → 사용자에게 "계속 / 리포트 보기" 선택
                                │        선택에 따라 분기
                                └─ NO  → 다음 메인 질문 생성
                                         question_generator(is_followup=False) 호출
```

### 4-3. 세션 종료

```
report_generator 호출 (state.history 전체 전달)
    ↓
Report 반환
    ↓
state.is_active = False
    ↓
종합 리포트 출력 (점수 + 약점 태그 + 개선 방향)
```

---

## 5. 모듈별 함수 시그니처 (인터페이스 계약)

각 팀원은 아래 시그니처를 반드시 맞춰 구현한다.

```python
# 태균님
def load_documents(pdf_paths: list[str]) -> str:
    """PDF를 ChromaDB에 인덱싱하고 collection_name 반환"""

def search_company(company_name: str) -> CompanyProfile:
    """회사명으로 Tavily 검색 후 CompanyProfile 반환 (24시간 캐시)"""

# 본인 + 세림님
def generate_question(state: SessionState, is_followup: bool) -> Question:
    """SessionState를 받아 다음 질문 반환"""

def evaluate_answer(question: Question, answer: str, context: SessionContext) -> EvaluationResult:
    """질문 + 답변 + 컨텍스트를 받아 평가 결과 반환"""

# 정훈님
def generate_report(history: list[tuple[Question, EvaluationResult]]) -> Report:
    """전체 Q&A 히스토리를 받아 종합 리포트 반환"""
```

---

## 6. 예외 처리 규칙

| 상황 | 처리 방법 |
|---|---|
| 50자 이하 답변 | "더 구체적으로 답해 주세요" 재요청, question_count 증가 없음 |
| 자소서가 아닌 문서 업로드 | document_loader에서 검증 후 차단, 오케스트레이터에 오류 반환 |
| question_count >= 50 | 즉시 report_generator 호출 후 강제 종료 |
| Tavily 검색 실패 | CompanyProfile 없이 진행 (job_description만으로 컨텍스트 구성) |
| LLM 응답이 JSON 형식 아님 | 모듈 내부에서 재시도 1회, 실패 시 오류 반환 |
