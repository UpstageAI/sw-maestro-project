# Mise 백엔드 파이프라인 아키텍처

## 개요

소설 텍스트를 입력하면 12개 장면 요소를 추출하고, 누락된 요소를 AI가 자동 보완한 뒤, 이미지 생성용 영문 프롬프트를 생성하는 LangGraph 기반 5단계 파이프라인.

## 전체 흐름도

```
                    START
                      │
                      ▼
              ┌───────────────┐
              │   extract     │  소설 텍스트 → 12개 장면 요소 추출
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ check_missing │  빈 필드 목록 확인 (API 호출 없음)
              └───────┬───────┘
                      │
            ┌─────────┴───────── conditional edge ───────┐
            │                                            │
       누락 있음                                         누락 없음
            │                                            │
            ▼                                            │
    ┌───────────────┐                                    │
    │     fill      │  AI가 빈 요소를 문맥에 맞게 추론          │
    └───────┬───────┘                                    │
            │                                            │
            ▼                                            │
    ┌───────────────┐                                    │
    │    verify     │  보완 값이 원문 분위기와 충돌하는지 검증     │
    └───────┬───────┘                                    │
            │                                            │
            └──────────────┬─────────────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │    prompt     │  12개 요소 → 영문 이미지 프롬프트 생성
                   └───────┬───────┘
                           │
                           ▼
                          END
```

## 프로젝트 구조

```
mise/
├── chains/
│   └── scene_extractor.py    # LangGraph StateGraph — 5개 노드 + 조건부 엣지
├── models/
│   └── scene_schema.py       # Pydantic 데이터 모델 6개
├── prompts/
│   ├── extraction_prompt.py  # Node 1: 장면 추출용 시스템 프롬프트
│   ├── fill_prompt.py        # Node 3: 누락 보완용 시스템 프롬프트
│   ├── verify_prompt.py      # Node 4: 일관성 검증용 시스템 프롬프트
│   └── prompt_generator.py   # Node 5: 프롬프트 생성용 시스템 프롬프트
└── config.py                 # 환경 변수, 상수 설정
```

## 데이터 모델 (`models/scene_schema.py`)

```
SceneElements        12개 장면 요소 (character, background, time, place, objects,
                     action, emotion, mood, color, lighting, camera_view, composition)

ExtractionResult     Node 1 출력  → elements + source_type
FillResult           Node 3 출력  → elements + fill_reason
VerifyResult         Node 4 출력  → elements + corrections
PromptResult         Node 5 출력  → positive_prompt + negative_prompt + style + missing_info
SceneSchema          최종 반환값  → elements + source_type + prompt
```

## 각 노드 상세

### Node 1: extract — 장면 추출

| 항목     | 내용                                              |
| -------- | ------------------------------------------------- |
| 입력     | `novel_text`, `mode`                              |
| 출력     | `elements`, `source_type`, `style`                |
| LLM 호출 | generate 모드만. regenerate는 prev_scene에서 복원 |

**generate 모드:** 소설 텍스트를 Gemini에 보내 12개 요소를 JSON으로 추출. `source_type`은 각 요소별로 `"original"`(원문에 있음), `"inferred"`(추론), `"missing"`(알 수 없음)으로 구분.

**regenerate 모드:** 이전 결과(`prev_scene`)에서 요소를 복원. LLM 호출 없음.

### Node 2: check_missing — 누락 검사

| 항목     | 내용               |
| -------- | ------------------ |
| 입력     | `elements`         |
| 출력     | `missing_fields`   |
| LLM 호출 | 없음 (순수 Python) |

`SceneElements`의 각 필드를 순회하며 `""`인 필드명을 리스트로 수집. `objects`는 기본값이 빈 리스트이므로 검사 제외.

### Node 3: fill — 보완 생성

| 항목     | 내용                                                      |
| -------- | --------------------------------------------------------- |
| 입력     | `novel_text`, `elements`, `missing_fields`, `source_type` |
| 출력     | `elements` (보완됨), `source_type` (업데이트됨)           |
| LLM 호출 | 있음                                                      |

**실행 조건:** conditional edge에서 `missing_fields`가 비어있지 않을 때만 진입.

빈 요소를 Gemini가 원문 문맥을 보고 추론해 채움. 보완된 요소의 `source_type`은 `"inferred"`로 표시.

### Node 4: verify — 일관성 검증

| 항목     | 내용                                       |
| -------- | ------------------------------------------ |
| 입력     | `novel_text`, `elements`, `missing_fields` |
| 출력     | `elements` (검증/수정됨)                   |
| LLM 호출 | 있음                                       |

**실행 조건:** Node 3을 거친 경우에만 실행 (fill → verify 순차).

보완된 값이 원문의 시대적 배경, 분위기, 논리와 충돌하면 AI가 수정.

### Node 5: prompt — 프롬프트 생성

| 항목     | 내용                |
| -------- | ------------------- |
| 입력     | `elements`, `style` |
| 출력     | `prompt_result`     |
| LLM 호출 | 있음                |

12개 한국어 요소를 이미지 생성 AI용 영문 키워드 프롬프트로 변환.
positive_prompt는 쉼표로 구분된 키워드 형태 (`cinematic, knight, moonlight, ...`).

## API 호출 횟수

| 상황                   | extract | fill | verify | prompt | 합계    |
| ---------------------- | ------- | ---- | ------ | ------ | ------- |
| generate + 누락 없음   | 1       | -    | -      | 1      | **2회** |
| generate + 누락 있음   | 1       | 1    | 1      | 1      | **4회** |
| regenerate + 누락 없음 | -       | -    | -      | 1      | **1회** |
| regenerate + 누락 있음 | -       | 1    | 1      | 1      | **3회** |

## 공개 API

```python
from mise.chains.scene_extractor import extract_scene

result = extract_scene(
    novel_text="소설 텍스트",    # 최대 1000자
    mode="generate",             # "generate" 또는 "regenerate"
    prev_scene=None,             # regenerate 모드에서 필요
)
# 반환: SceneSchema
#   result.elements          → SceneElements (12개 장면 요소)
#   result.source_type       → dict[str, str] (각 요소의 출처)
#   result.prompt            → PromptResult (positive/negative 프롬프트)
```

## 기술 스택

| 기술             | 용도                                             |
| ---------------- | ------------------------------------------------ |
| LangGraph        | StateGraph 기반 파이프라인 오케스트레이션        |
| LangChain        | 프롬프트 템플릿 + LLM 체인 구성                  |
| Gemini 2.5 Flash | 텍스트 분석, 요소 추출, 프롬프트 생성            |
| Pydantic v2      | 데이터 모델 검증 및 직렬화                       |
| pytest           | 단위 테스트 + 통합 테스트 (38개 단위 + 5개 통합) |

## 테스트 실행

```bash
# 전체 단위 테스트 (API 호출 없음, mock 사용)
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py

# 통합 테스트 (실제 Gemini API 호출)
RUN_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py -v -s
```

## 환경 변수

```bash
# .env
GOOGLE_API_KEY=your_gemini_api_key
```
