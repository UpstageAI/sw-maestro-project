# [schemas] 데이터 모델 정의

## 배경
다른 팀원분들이 먼저 올려주신 스키마 초안을 검토한 뒤, 우리 팀 구현 방향에 맞게 취합하여 정리했습니다.

**참고한 문서**
- `Persona` 클래스 구조 (LifeConditions / Identity / Lifestyle / Values / SkillsAndHobbies 분리)
- `RawNemotronPersona` → `TargetUserPersonaCard` 분리 설계, `point_id` 기반 교차 피드백, LangGraph State 입출력 구조

**설계 방향**
- 두 분 문서를 참고하되, 데모(5/10) 일정과 팀 학습 목표를 고려해 구현 가능한 범위로 조정했습니다
- flat State 구조를 베이스로 유지하되, `TargetUserPersonaCard` / `guardrails` / `point_id` 개념을 흡수했습니다
- `AdoptionIntent`, `FinalUserFeedbackSynthesis`, `RunMetadata` 등 복잡도 높은 항목은 고도화로 미뤘습니다

---

## 클래스 구조 한눈에 보기

```
RawNemotronPersona          # HuggingFace 원본 (런타임에 직접 사용 안 함)
  ↓ 사전 변환 (script)
TargetUserPersonaCard       # 런타임에서 실제 사용하는 페르소나 카드

ServicePlanInput            # 사용자 입력 구조화 결과
Opinion                     # 각 페르소나의 1차 의견 (point_id 포함)
Review                      # 상호 리뷰 (point_id 기반 교차 반응)
```

---

## ProjectState — LangGraph 공유 상태

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

| 필드 | 타입 | 쓰는 노드 | 설명 |
|------|------|-----------|------|
| `raw_input` | `str` | 외부 입력 | Streamlit 사용자 자유 텍스트 |
| `brief` | `ServicePlanInput` | `f0_parse` | 구조화된 기획안 |
| `persona_a` | `TargetUserPersonaCard` | `f1_select` | 선택된 페르소나 A |
| `persona_b` | `TargetUserPersonaCard` | `f1_select` | 선택된 페르소나 B |
| `opinion_a` | `Opinion` | `f2_opinion_a` | A의 1차 의견 |
| `opinion_b` | `Opinion` | `f2_opinion_b` | B의 1차 의견 |
| `review_a` | `Review` | `f3_review_a` | A가 B 의견을 리뷰 |
| `review_b` | `Review` | `f3_review_b` | B가 A 의견을 리뷰 |

---

## 전체 파이프라인 흐름

```
[사용자 입력 (raw_input)]
        │
        ▼
   f0_parse ──────────────────▶ brief
        │
        ▼
   f1_select ─────────────────▶ persona_a, persona_b
        │
   ┌────┴────┐  (병렬)
   ▼         ▼
f2_opinion_a  f2_opinion_b ───▶ opinion_a, opinion_b
        │
   ┌────┴────┐  (병렬)
   ▼         ▼
f3_review_a  f3_review_b ─────▶ review_a, review_b
        │
        ▼
   Streamlit 출력
```

---

## 스키마 정의

### 1. RawNemotronPersona

> 런타임에 직접 사용하지 않는다. `scripts/sample_hf_personas.py` 에서만 사용한다.

```python
from pydantic import BaseModel, Field

class RawNemotronPersona(BaseModel):
    uuid: str

    persona: str | None = None
    professional_persona: str | None = None
    cultural_background: str | None = None
    sports_persona: str | None = None
    arts_persona: str | None = None
    travel_persona: str | None = None
    culinary_persona: str | None = None
    family_persona: str | None = None

    skills_and_expertise_list: list[str] = Field(default_factory=list)
    hobbies_and_interests_list: list[str] = Field(default_factory=list)
    career_goals_and_ambitions: str | None = None

    sex: str | None = None
    age: int | None = None
    occupation: str | None = None
    province: str | None = None
    district: str | None = None
    education_level: str | None = None
    marital_status: str | None = None
    military_status: str | None = None
    housing_type: str | None = None
    family_type: str | None = None
    bachelors_field: str | None = None
    country: str | None = None
```

---

### 2. TargetUserPersonaCard

> 런타임 프롬프트에서 실제로 사용하는 카드.
> 원본 데이터를 그대로 쓰지 않고, 이 서비스를 어떻게 받아들일지 판단하는 데 필요한 필드로 재구성한다.
> 사람이 생각해서 나와야 될 법한 결과물 컬럼은 모두 LLM 사용 의도

```python
class TargetUserPersonaCard(BaseModel):
    card_id: str
    source_uuid: str
    display_name: str

    // age: int | None = None
    age_group: str | None = None   # 20s / 30s / 40s / 50s / 60s / 70plus
    sex: str | None = None
    occupation: str | None = None
    region: str | None = None // province 만 넣기 (고도화 단계에서 district 고려 논의)

    one_line_summary: str // LLM 가공 의도 (script? 어떤 방법이든 형식만 JSON 고정)
    life_context: str // LLM 가공 의도

    user_goals: list[str] = Field(default_factory=list) 
    pain_points: list[str] = Field(default_factory=list)
    positive_triggers: list[str] = Field(default_factory=list)
    negative_triggers: list[str] = Field(default_factory=list)

    speaking_style: str
    guardrails: list[str] = Field(default_factory=list)
```

**guardrails 기본값 (공통 적용)**
```
- 전문가처럼 평가하지 말고 실제 사용자 입장에서 반응한다
- 성별, 나이, 지역, 학력만으로 성향을 단정하지 않는다
- 원본 페르소나에 없는 경험을 만들어내지 않는다
- 서비스 기획에 없는 기능을 있다고 가정하지 않는다
```

---

### 3. ServicePlanInput

```python
class ServicePlanInput(BaseModel):
    raw_text: str
    title: str | None = None
    description: str | None = None
    target: str | None = None
    key_features: list[str] = Field(default_factory=list)
    concerns: str | None = None
```

---

### 4. Opinion + ReactionPoint

> `point_id`를 도입해 Review 단계에서 특정 포인트를 참조할 수 있도록 한다.

**point_id 네이밍 규칙**: `{페르소나}_{긍부정}_{번호}` (예: `a_pos_01`, `b_neg_02`)

```python
class ReactionPoint(BaseModel):
    point_id: str     # 예: "a_pos_01", "a_neg_01"
    title: str
    detail: str

class Opinion(BaseModel):
    persona_id: str
    first_impression: str // 제거, would_use, would_use_description 에서 반영 가능
    positive_points: list[ReactionPoint] = Field(default_factory=list)
    negative_points: list[ReactionPoint] = Field(default_factory=list)
    overall_score: int = Field(ge=0, le=100) // 제거, MVP 단계 점수 제거
    would_use: bool
    would_use_description : str | None = None // would_use 결과의 부가 설명 제공
```

---

### 5. Review + PointFeedback

> 상대 페르소나의 `point_id`를 기반으로 특정 포인트에 반응한다.

```python
from typing import Literal

AgreementLevel = Literal["agree", "partially_agree", "disagree"] // MVP 단계 둘중 하나로만

class PointFeedback(BaseModel):
    target_point_id: str       # 상대 ReactionPoint의 point_id 참조
    agreement: AgreementLevel
    comment: str

class Review(BaseModel):
    reviewer_id: str
    target_id: str
    point_feedbacks: list[PointFeedback] = Field(default_factory=list)
    overall_comment: str
    revised_would_use: bool // 리뷰를 듣고 의향이 바뀌었는지 확인
```

---

## 노드 시그니처 요약

```python
def f0_parse(state: ProjectState) -> dict:
    return {"brief": ServicePlanInput(...)}

def f1_select(state: ProjectState) -> dict:
    return {
        "persona_a": TargetUserPersonaCard(...),
        "persona_b": TargetUserPersonaCard(...)
    }

def f2_opinion_a(state: ProjectState) -> dict:
    return {"opinion_a": Opinion(
        persona_id=state["persona_a"].card_id,
        positive_points=[ReactionPoint(point_id="a_pos_01", ...)],
        negative_points=[ReactionPoint(point_id="a_neg_01", ...)],
        ...
    )}

def f2_opinion_b(state: ProjectState) -> dict:
    return {"opinion_b": Opinion(
        persona_id=state["persona_b"].card_id,
        positive_points=[ReactionPoint(point_id="b_pos_01", ...)],
        negative_points=[ReactionPoint(point_id="b_neg_01", ...)],
        ...
    )}

def f3_review_a(state: ProjectState) -> dict:
    # persona_a가 opinion_b의 point_id를 참조해서 리뷰
    return {"review_a": Review(
        reviewer_id=state["persona_a"].card_id,
        target_id=state["persona_b"].card_id,
        point_feedbacks=[
            PointFeedback(target_point_id="b_pos_01", agreement="agree", comment=...),
            PointFeedback(target_point_id="b_neg_01", agreement="disagree", comment=...),
        ],
        ...
    )}

def f3_review_b(state: ProjectState) -> dict:
    # persona_b가 opinion_a의 point_id를 참조해서 리뷰
    return {"review_b": Review(
        reviewer_id=state["persona_b"].card_id,
        target_id=state["persona_a"].card_id,
        point_feedbacks=[
            PointFeedback(target_point_id="a_pos_01", ...),
            PointFeedback(target_point_id="a_neg_01", ...),
        ],
        ...
    )}
```

---

## 데이터 준비 전략

```
HuggingFace nvidia/Nemotron-Personas-Korea (1M rows)
        │
        ▼ scripts/sample_hf_personas.py
        │  occupation 기준 클러스터링 → 대표 샘플 추출
        ▼
data/personas/raw_personas.seed.json
        │
        ▼ scripts/generate_user_cards.py
        │  RawNemotronPersona → TargetUserPersonaCard 변환
        ▼
data/personas/persona_cards.seed.json  ← 런타임에서 로드
```

---

## MVP 범위

| 항목 | 포함 여부 | 비고 |
|------|:---:|------|
| `RawNemotronPersona` | ✅ | 스크립트에서만 사용 |
| `TargetUserPersonaCard` | ✅ | seed JSON으로 로드 |
| `ServicePlanInput` | ✅ | LLM structured output |
| `Opinion` + `ReactionPoint` + `point_id` | ✅ | |
| `Review` + `PointFeedback` | ✅ | |
| `AdoptionIntent` | ❌ | 고도화 시 추가 |
| `FinalUserFeedbackSynthesis` | ❌ | 고도화 시 추가 |
| `RunMetadata` / `NodeTrace` | ❌ | 고도화 시 추가 |
| pgvector DB | ❌ | seed JSON으로 대체 |
| FastAPI | ❌ | Streamlit 직접 연결 |

---

## 논의 필요한 사항

- [x] `TargetUserPersonaCard` 필드 중 추가/제거할 것 있는지
- [x] `ReactionPoint` 개수 제한 설정 여부 > 긍정/부정 3개로 고정
- [x] `guardrails` 기본값 문구 최종 확정 > 변수로 빼서 각자 알아서 조정 (잘 만들어오기)
- [x] `point_id` 네이밍 규칙 (`a_pos_01` 형식) 확정
- [x] 데모용 seed 카드 몇 개 준비할지 > 이후 고도화 단계에서 카드 생성 스크립트 자동화 처리 가능

---

### 사전 작업 

도메인, 페르소나 선정 후 그 페르소나에 맞춰 기획안 만들어달라고 해서 그걸 인풋으로 넣기
