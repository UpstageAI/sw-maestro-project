# AI 모듈 API 레퍼런스

> `app.service.generate_story()` 의 입력/출력/예외 명세
> 마지막 수정: 2026-05-09

---

## 한눈에 보기

```python
from app.service import generate_story
from app.models.schemas import StoryRequest, Story

story: Story = generate_story(req)   # req: StoryRequest
# → Story(title: str, body: str)
```

| 항목 | 값 |
|---|---|
| Import | `from app.service import generate_story` |
| 시그니처 | `generate_story(req: StoryRequest) -> Story` |
| 호출 방식 | 동기 (필요 시 threadpool로 감싸기) |
| 평균 응답 시간 | 5~12초 (LLM 응답 시간 의존) |
| LLM 호출 횟수 | 3회 (통과 시) / 4회 (1회 재집필 시) |

---

## 1. 입력 — `StoryRequest`

```python
class StoryRequest(BaseModel):
    diary_date: date              # 필수
    diary: str                    # 필수
    people: list[Person] = []     # 선택
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `diary_date` | `date` (YYYY-MM-DD) | ✅ | — | 일기 날짜 |
| `diary` | `str` | ✅ | — | 일기 본문 (자유 문장) |
| `people` | `list[Person]` | ❌ | `[]` | 등장 인물 목록. 비어 있어도 호출 가능 |

### `Person`

```python
class Person(BaseModel):
    name: str                          # 필수
    relation: str                      # 필수
    kind: PersonKind = "기타"
    closeness: int | None = None       # 1~5
    role_today: str | None = None
    traits: list[str] = []
    note: str | None = None
```

| 필드 | 타입 | 필수 | 기본값 | 제약 / 예시 |
|---|---|---|---|---|
| `name` | `str` | ✅ | — | "민준", "엄마" |
| `relation` | `str` | ✅ | — | 자유 표현. "엄마", "짝꿍", "담임선생님" |
| `kind` | `PersonKind` enum | ❌ | `"기타"` | 5택 (아래 참고) |
| `closeness` | `int \| None` | ❌ | `None` | 1~5 (`ge=1, le=5`). `None`이면 LLM이 일기 톤으로 추론 |
| `role_today` | `str \| None` | ❌ | `None` | 오늘 일기 속 역할. "위로해줌", "갈등 상대" |
| `traits` | `list[str]` | ❌ | `[]` | 성격/특징 키워드 |
| `note` | `str \| None` | ❌ | `None` | 추가 메모 |

### `PersonKind` (str enum)

```python
"가족" | "친구" | "선생님" | "이웃" | "기타"
```

### 입력 검증 규칙 요약

| 필드 | 제약 | 위반 시 |
|---|---|---|
| `diary_date` | `date` 파싱 가능 | `pydantic.ValidationError` → FastAPI 422 |
| `diary` | 문자열 | `pydantic.ValidationError` → 422 |
| `Person.closeness` | 1 ≤ x ≤ 5 | 422 |
| `Person.kind` | 5택 외 값 | 422 |

### JSON 입력 예시

```json
{
  "diary_date": "2026-05-08",
  "diary": "오늘 민준이랑 블록 때문에 다퉜다. 선생님이 같이 만들자고 했다.",
  "people": [
    {
      "name": "민준",
      "relation": "짝꿍",
      "kind": "친구",
      "closeness": 4,
      "role_today": "블록 갈등 상대",
      "traits": ["장난기 많음", "활발함"]
    }
  ]
}
```

---

## 2. 출력 — `Story`

```python
class Story(BaseModel):
    title: str
    body: str
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `title` | `str` | 동화 제목 |
| `body` | `str` | 동화 본문 (5~7세용 동화풍, 6~10문장) |

### 반환 보장 사항

- 두 필드 모두 `.strip()` 처리되어 **앞뒤 공백 없음**
- `title`이 빈 문자열일 경우 `"오늘의 동화"`로 폴백
- `body`가 비어있으면 반환하지 않고 `StoryParsingError`를 발생시킴
  → **반환된 `Story.body`는 항상 비어있지 않음이 보장됨**

### 응답 래퍼 — `StoryResponse`

FastAPI에서 응답으로 내보낼 땐 한 번 감싸서 보내는 것을 권장합니다.

```python
class StoryResponse(BaseModel):
    story: Story
```

JSON 출력:
```json
{
  "story": {
    "title": "블록 성을 함께 쌓은 두 친구",
    "body": "옛날 옛적, 별빛이 흐르는 마을에 ..."
  }
}
```

---

## 3. 예외

`generate_story()`는 다음 예외를 발생시킬 수 있습니다. 모두 `app.exceptions`에서 import.

| 예외 | 의미 | 권장 HTTP 상태 |
|---|---|---|
| `pydantic.ValidationError` | 입력 스키마 위반 | FastAPI 자동 **422** |
| `LLMUnavailableError` | 업스트림 LLM 호출 실패 (timeout / 401 / 429 / 5xx). `e.stage`로 어느 단계(plan/write/critique)인지 식별 가능 | **503** |
| `StoryParsingError` | LLM 응답은 받았으나 본문 추출 실패 | **502** |
| `StoryGenerationError` | 위 두 예외의 베이스 + 그 외 예기치 못한 오류 | **422** |

> `StoryGenerationError` 하나만 잡아도 `LLMUnavailableError`, `StoryParsingError`까지 전부 잡힙니다 (베이스 클래스). 다만 HTTP 상태를 다르게 매핑하려면 개별로 잡으세요.

---

## 4. 사용 예

### 4-1. Python에서 직접 호출

```python
from datetime import date
from app.service import generate_story
from app.models.schemas import StoryRequest, Person

req = StoryRequest(
    diary_date=date(2026, 5, 8),
    diary="오늘 민준이랑 블록 때문에 다퉜다. 선생님이 같이 만들자고 했다.",
    people=[
        Person(
            name="민준", relation="짝꿍", kind="친구",
            closeness=4, role_today="블록 갈등 상대",
            traits=["장난기 많음", "활발함"],
        ),
    ],
)

story = generate_story(req)
print(story.title)
print(story.body)
```

### 4-2. FastAPI 라우트로 감싸기 (권장 패턴)

```python
from fastapi import APIRouter, HTTPException
from app.service import generate_story
from app.models.schemas import StoryRequest, StoryResponse
from app.exceptions import (
    LLMUnavailableError,
    StoryParsingError,
    StoryGenerationError,
)

router = APIRouter(prefix="/api", tags=["stories"])


@router.post("/stories", response_model=StoryResponse)
def create_story(req: StoryRequest) -> StoryResponse:
    try:
        story = generate_story(req)
    except LLMUnavailableError as e:
        raise HTTPException(503, detail=str(e))
    except StoryParsingError as e:
        raise HTTPException(502, detail=str(e))
    except StoryGenerationError as e:
        raise HTTPException(422, detail=str(e))
    return StoryResponse(story=story)
```

> `StoryRequest`는 pydantic 모델이므로 FastAPI가 입력 검증(422)을 자동 처리합니다.
> `generate_story()`는 동기 함수이므로 `def` 핸들러로 두면 FastAPI가 threadpool에서 실행합니다. (`async def`로 두면 이벤트 루프를 막으니 주의)

---

## 5. 관련 문서

- 모듈 전체 명세 (그래프 흐름, 노드 동작, .env 등): [`docs/AI_MODULE_SPEC.md`](./AI_MODULE_SPEC.md)
