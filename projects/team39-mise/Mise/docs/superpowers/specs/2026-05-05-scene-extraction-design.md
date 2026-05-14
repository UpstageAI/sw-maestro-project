# Scene Extraction Design

## 개요

소설 텍스트에서 12개 장면 요소를 추출하고, 이를 이미지 생성용 영문 프롬프트로 변환하는 LangChain 파이프라인. Gemini API 2회 호출 방식.

## 아키텍처 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 호출 방식 | 2-call | 요소 카드 UI 확인/수정 후 프롬프트 생성이 기획서 워크플로우와 자연스럽게 연결 |
| JSON 강제 | `with_structured_output()` | Gemini에서 가장 안정적, LangChain 표준, 자동 재시도 |
| focus 파라미터 | MVP 제외 | 균형형으로 고정 |
| 모델 | gemini-2.0-flash | 무료, 빠름, 구조화 출력 지원 |

## 데이터 흐름

```
extract_scene(novel_text, mode, prev_scene)
    |
    +-- mode="generate"
    |   Call 1: novel_text -> Gemini -> SceneElements (12 elements)
    |   Call 2: SceneElements -> Gemini -> PromptResult (positive/negative)
    |   -> SceneSchema 반환
    |
    +-- mode="regenerate"
        prev_scene elements를 수정된 값으로 사용
        Call 2만: 수정된 SceneElements -> Gemini -> PromptResult
        -> SceneSchema 반환
```

## Pydantic 스키마

```python
class SceneElements(BaseModel):
    character: str       # 인물 외형, 복장, 자세
    background: str      # 배경 환경, 공간 구조
    time: str            # 시간대 (새벽/오전/오후/저녁/밤)
    place: str           # 구체적 장소
    objects: list[str]   # 주요 사물/오브젝트
    action: str          # 인물의 행동/동작
    emotion: str         # 감정 상태
    mood: str            # 전체적 분위기
    color: str           # 색감/색조
    lighting: str        # 조명 상태
    camera_view: str     # 시점/카메라 앵글
    composition: str     # 구도/프레이밍

class ExtractionResult(BaseModel):
    """Call 1 출력: 12개 요소 + 각 요소의 출처 구분"""
    elements: SceneElements
    source_type: dict[str, str]  # {"character": "original", "lighting": "inferred"}

class PromptResult(BaseModel):
    """Call 2 출력: 이미지 생성용 프롬프트"""
    positive_prompt: str   # 이미지에 포함할 요소 (영문)
    negative_prompt: str   # 이미지에서 제외할 요소 (영문)
    style: str = "cinematic"
    missing_info: list[str] = []  # 원문에서 부족한 정보

class SceneSchema(BaseModel):
    """최종 반환: 요소 + 출처 + 프롬프트"""
    elements: SceneElements
    source_type: dict[str, str]
    prompt: PromptResult
```

## 공개 인터페이스

```python
# scene_extractor.py

def extract_scene(
    novel_text: str,
    mode: str = "generate",          # "generate" | "regenerate"
    prev_scene: dict | None = None,  # regenerate 시 이전 결과
) -> SceneSchema:
```

- `mode="generate"`: Call 1 (요소 추출) + Call 2 (프롬프트 생성)
- `mode="regenerate"`: `prev_scene["elements"]`를 기반으로 Call 2만 실행
- 반환: `SceneSchema` Pydantic 객체

## Call 1: 장면 요소 추출

**입력:** 한국어 소설 텍스트 (최대 1000자)

**시스템 프롬프트 핵심 지시:**
- 역할: 소설 장면을 12개 시각 요소로 분해하는 장면 해석 전문가
- 각 요소값은 한국어로 작성 (UI 카드 표시용)
- 원문에 명시된 정보는 해당 요소에 반영
- 명시되지 않은 요소는 장면 맥락에서 합리적으로 추론
- source_type에 각 요소별 "original" 또는 "inferred" 표시
- 단일 장면만 추출 (MVP 제약)
- 과도한 잔혹/선정/혐오 묘사는 완화

**출력:** `ExtractionResult` (elements + source_type)

## Call 2: 프롬프트 생성

**입력:** `SceneElements` (한국어 값)

**시스템 프롬프트 핵심 지시:**
- 역할: 장면 분석 데이터를 이미지 생성용 영문 프롬프트로 변환
- 한국어 요소값을 영문 시각 키워드로 변환
- Positive 프롬프트 구조: `{style}, {character}, {action}, {background}, {objects}, {mood}, {lighting}, {color}, {composition}, high quality, detailed`
- Negative 프롬프트 필수 포함: `excessive gore, explicit content, hate symbols, blurry, low quality, deformed, text, watermark, signature, out of frame`
- 원문에서 부족한 정보를 missing_info에 명시

**출력:** `PromptResult`

## 파일 구조

```
mise/
├── chains/
│   └── scene_extractor.py    # extract_scene() 함수
├── models/
│   └── scene_schema.py       # SceneElements, ExtractionResult, PromptResult, SceneSchema
├── prompts/
│   ├── extraction_prompt.py  # Call 1 시스템 프롬프트 템플릿
│   └── prompt_generator.py   # Call 2 시스템 프롬프트 템플릿
└── config.py                 # GOOGLE_API_KEY 등 환경 변수
```

## 에러 처리

| 상황 | 처리 |
|------|------|
| Gemini API 타임아웃 | 25초 타임아웃 설정, 실패 시 구조화된 에러 메시지 |
| JSON 파싱 실패 | `with_structured_output()` 자동 재시도 (최대 2회) |
| 입력 1000자 초과 | 함수 진입 전 사전 차단 |
| 빈 입력 | 함수 진입 전 사전 차단 |
| API 키 미설정 | config.py에서 감지, ValueError 발생 |

## 테스트 계획

- 한국어 소설 구절 5~10개로 정확도 측정
- 측정 항목: 12요소 누락률, JSON 파싱 실패율, 프롬프트 품질 (원문 충실도)
- 목표: 누락률 10% 미만, 파싱 실패율 5% 미만
