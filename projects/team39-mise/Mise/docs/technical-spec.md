# Scene Extraction — 기술 스펙 문서

최종 발표 자료 생성 시 참고용.

---

## 1. 담당 모듈 개요

**Scene Extraction** 모듈은 소설 텍스트를 입력받아 12개 시각 요소를 추출하고, 이를 이미지 생성 AI가 이해할 수 있는 영문 프롬프트로 변환하는 LangChain 기반 2-call 파이프라인이다.

## 2. 아키텍처

### 2-1. 2-Call Gemini 파이프라인

```
소설 텍스트 (한국어, 최대 1000자)
        │
        ▼  [Call 1: 장면 요소 추출]
   Gemini 2.5 Flash
        │
        ▼  ExtractionResult
        │   ├── elements: 12개 장면 요소 (한국어)
        │   └── source_type: 각 요소별 original/inferred 구분
        │
        ▼  [Call 2: 프롬프트 변환]
   Gemini 2.5 Flash
        │
        ▼  PromptResult
            ├── positive_prompt: 이미지에 포함할 요소 (영문)
            ├── negative_prompt: 이미지에서 제외할 요소 (영문)
            ├── style: 이미지 스타일
            └── missing_info: 원문에서 부족한 정보
```

**왜 2-call인가:** 기획서의 사용자 워크플로우가 "12개 요소 카드 UI 표시 → 사용자 확인/수정 → 프롬프트 생성"이므로, 요소 추출과 프롬프트 생성을 분리하면 사용자가 중간에 수정 가능.

### 2-2. JSON 강제: `with_structured_output()`

Gemini가 항상 Pydantic 스키마에 맞는 JSON을 반환하도록 LangChain의 `with_structured_output()`을 사용:

```python
chain = prompt_template | llm.with_structured_output(ExtractionResult)
result = chain.invoke({"novel_text": novel_text})
# result는 항상 ExtractionResult Pydantic 객체 (dict가 아님)
```

파싱 실패 시 LangChain이 자동 재시도. 수동 JSON 파싱 불필요.

## 3. 데이터 모델

### SceneElements (12개 장면 요소)

| 필드 | 한국어 | 설명 | 예시 |
|------|--------|------|------|
| character | 인물 | 외형, 복장, 자세 | "검은 갑옷을 입은 기사" |
| background | 배경 | 환경, 공간 구조 | "폐허가 된 성벽" |
| time | 시간대 | 새벽/오전/오후/저녁/밤 | "저녁" |
| place | 장소 | 구체적 장소 | "무너진 성벽 위" |
| objects | 사물 | 주요 사물 목록 | ["거대한 마법진", "검"] |
| action | 행동 | 인물의 동작 | "하늘을 올려다보고 있다" |
| emotion | 감정 | 감정 상태 | "경외" |
| mood | 분위기 | 전체적 분위기 | "장엄하고 불길한 분위기" |
| color | 색감 | 색조 | "붉은색과 주황색 노을" |
| lighting | 조명 | 조명 상태 | "노을빛" |
| camera_view | 시점 | 카메라 앵글 | "성벽 너머를 바라보는 와이드샷" |
| composition | 구도 | 화면 구도 | "배경 중심 구도" |

### ExtractionResult (Call 1 출력)

`SceneElements` + `source_type` (각 요소별 "original"/"inferred"/"missing")

### PromptResult (Call 2 출력)

- `positive_prompt`: 영문 이미지 프롬프트 (쉼표 구분 키워드)
- `negative_prompt`: 제외 요소 (기본 항목 + 장면별 추가)
- `style`: 이미지 스타일 (기본값 "cinematic")
- `missing_info`: 원문에서 부족한 정보 목록

## 4. 핵심 구현 상세

### 4-1. 공개 인터페이스

```python
from mise.chains.scene_extractor import extract_scene

# 최초 생성 모드
result: SceneSchema = extract_scene(
    novel_text="소설 텍스트...",  # 최대 1000자
    mode="generate",              # 기본값
)

# 재생성 모드 (사용자가 요소 수정 후)
result: SceneSchema = extract_scene(
    novel_text="소설 텍스트...",
    mode="regenerate",
    prev_scene={"elements": {...}, "source_type": {...}},
)
```

### 4-2. 입력 검증

| 조건 | 에러 메시지 |
|------|------------|
| 빈 문자열 / 공백만 | "입력 텍스트가 비어있습니다" |
| 1000자 초과 | "입력 텍스트가 1000자를 초과합니다" |
| mode != generate/regenerate | "잘못된 mode: '...'" |
| regenerate인데 prev_scene 없음 | "regenerate 모드에서는 prev_scene이 필요합니다" |
| API 키 미설정 | "GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다" |

### 4-3. Gemini API 설정

| 설정 | 값 |
|------|----|
| 모델 | gemini-2.5-flash |
| temperature | 0.3 |
| request_timeout | 25초 |
| 구조화 출력 | with_structured_output() |

## 5. 프롬프트 설계

### Call 1: 장면 요소 추출

**역할:** 소설 장면을 12개 시각 요소로 분해하는 장면 해석 전문가

**핵심 지시:**
- 요소값은 한국어로 작성 (UI 카드 표시용)
- 원문 명시 정보 → source_type "original"
- 문맥 기반 추론 → source_type "inferred"
- 추론 불가 → 빈 문자열 + source_type "missing"
- 단일 장면만 추출
- 과도한 잔혹/선정/혐오 묘사는 순화

### Call 2: 프롬프트 변환

**역할:** 장면 분석 데이터를 이미지 생성용 영문 프롬프트로 변환

**핵심 지시:**
- 한국어 → 영문 시각 키워드 변환
- Positive 순서: 스타일 → 인물 → 행동 → 배경 → 사물 → 분위기 → 조명 → 색감 → 구도 → 화질 키워드
- Negative 필수: excessive gore, explicit content, hate symbols, blurry, low quality, deformed, text, watermark, signature, out of frame
- 빈 요소는 missing_info에 명시

## 6. 테스트 결과

| 테스트 유형 | 개수 | 결과 |
|------------|------|------|
| Pydantic 모델 | 7 | 전부 통과 |
| Call 1 프롬프트 | 3 | 전부 통과 |
| Call 2 프롬프트 | 3 | 전부 통과 |
| 파이프라인 단위 (mock) | 9 | 전부 통과 |
| 통합 (실제 API) | 5 | 전부 통과 |
| **합계** | **27** | **전부 통과** |

### 통합 테스트 샘플

| 샘플 | 내용 | 특징 |
|------|------|------|
| 1 | "붉은 노을 아래 무너진 성벽..." | 판타지 전투 장면 |
| 2 | "달빛이 은백색으로 물든 탑..." | 로맨스 판타지 |
| 3 | "지하 감옥의 차가운 돌바닥..." | 스릴러/공포 |

## 7. 의존성

```
langchain>=0.3.0
langchain-google-genai>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

## 8. API 비용

- Gemini 2.5 Flash: 무료 등급 사용
- 1회 extract_scene() 호출 = Gemini API 2회 소모
- 무료 한도: 분당 15회, 일일 1,500회
- 1회 호출 소요 시간: 약 10-15초
