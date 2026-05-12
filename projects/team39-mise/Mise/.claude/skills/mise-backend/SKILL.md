---
name: mise-backend
description: "Mise 백엔드 구현 스킬. LangChain 체인 설계, Gemini API 프롬프트 템플릿, Gemini 이미지 생성 API 연동, Pydantic 데이터 모델, 장면 요소 추출 로직 구현. 백엔드 코드 작성, API 연동, 프롬프트 엔지니어링, 체인 구성 요청 시 반드시 이 스킬을 사용."
---

# Mise Backend — 백엔드 구현 가이드

소설 텍스트 → 12개 장면 요소 추출 → 이미지 프롬프트 생성 → 이미지 생성 API 호출의 전체 백엔드 파이프라인을 구현하는 방법을 안내한다.

## 프로젝트 구조

```
mise/
├── app.py                    # Streamlit 메인 (프론트엔드 담당)
├── chains/
│   ├── __init__.py
│   ├── scene_extractor.py    # LangChain 체인: 텍스트 → 12개 요소 JSON
│   ├── prompt_generator.py   # 장면 요소 → Positive/Negative 프롬프트
│   └── pipeline.py           # 전체 파이프라인 오케스트레이션
├── models/
│   ├── __init__.py
│   ├── scene_elements.py     # Pydantic: SceneElements 모델
│   └── image_result.py       # Pydantic: ImageResult 모델
├── api/
│   ├── __init__.py
│   └── image_generator.py    # Gemini 이미지 생성 API 클라이언트
├── prompts/
│   ├── extraction_prompt.py  # 장면 요소 추출용 시스템 프롬프트
│   └── image_prompt.py       # 이미지 프롬프트 생성용 시스템 프롬프트
├── config.py                 # 환경 변수, 설정
├── requirements.txt
└── .env                      # API 키 (gitignore 필수)
```

## 데이터 모델

PRD에 정의된 12개 장면 요소를 Pydantic 모델로 정의한다:

```python
# models/scene_elements.py
from pydantic import BaseModel, Field
from typing import List, Optional

class SceneElements(BaseModel):
    character: str = Field(description="인물 외형, 복장, 자세")
    background: str = Field(description="배경 환경, 공간 구조")
    time: str = Field(description="시간대 (새벽/오전/오후/저녁/밤)")
    place: str = Field(description="구체적 장소")
    objects: List[str] = Field(default_factory=list, description="주요 사물/오브젝트")
    action: str = Field(description="인물의 행동/동작")
    emotion: str = Field(description="감정 상태")
    mood: str = Field(description="전체적 분위기")
    color: str = Field(description="색감/색조")
    lighting: str = Field(description="조명 상태")
    camera_view: str = Field(description="시점/카메라 앵글")
    composition: str = Field(description="구도/프레이밍")

class SceneAnalysisResult(BaseModel):
    elements: SceneElements
    source_type: dict = Field(description="각 요소별 'original' 또는 'inferred' 구분")
    positive_prompt: str
    negative_prompt: str
    style: str = Field(default="cinematic")
    missing_info: List[str] = Field(default_factory=list, description="원문에서 부족한 정보")
```

## LangChain 체인 구현 핵심

### 1. 장면 요소 추출 체인

Gemini 모델을 사용하여 소설 텍스트에서 12개 요소를 추출한다. LangChain의 `ChatPromptTemplate`과 `with_structured_output`을 활용한다.

```python
# chains/scene_extractor.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from models.scene_elements import SceneAnalysisResult
import json

def create_extraction_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.3,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACTION_SYSTEM_PROMPT),
        ("human", "{novel_text}"),
    ])

    chain = prompt | llm
    return chain
```

### 2. 프롬프트 생성 체인

추출된 장면 요소를 이미지 생성 AI가 이해하기 쉬운 영문 프롬프트로 변환한다.

**Positive 프롬프트 구조:**
`{스타일 키워드}, {인물 묘사}, {행동}, {배경}, {오브젝트}, {분위기}, {조명}, {색감}, {구도}, {화질 키워드}`

**Negative 프롬프트 필수 포함:**
`excessive gore, explicit content, hate symbols, blurry, low quality, deformed, text, watermark, signature, out of frame`

### 3. Gemini 이미지 생성 API 연동

Gemini의 이미지 생성 기능(gemini-2.0-flash)을 사용하여 프롬프트 기반 이미지를 생성한다. `langchain-google-genai`의 동일 클라이언트를 활용하므로 별도 API 키가 필요 없다.

```python
# api/image_generator.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
import base64

class ImageGenerator:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7,
        )

    def generate(self, positive_prompt: str, negative_prompt: str, style: str = "cinematic") -> bytes:
        # Gemini 이미지 생성 호출
        # positive_prompt + negative_prompt를 조합하여 이미지 생성 요청
        # 타임아웃 25초 설정 (30초 목표 달성을 위한 안전 마진)
        pass
```

## 프롬프트 템플릿 설계 원칙

시스템 프롬프트는 LLM에게 다음을 명확히 지시한다:
1. **역할:** "소설 장면을 이미지 생성용 프롬프트로 변환하는 장면 해석 agent"
2. **입력:** 소설 문단 텍스트
3. **출력:** JSON (12개 요소 + 프롬프트)
4. **제약:**
   - 원문에 없는 핵심 설정을 임의로 창작하지 않음
   - 부족한 정보는 missing_info에 명시
   - 과도한 잔혹/선정/혐오 묘사는 완화하거나 제외
   - 단일 장면만 추출 (MVP 제약)

## 환경 변수

```bash
# .env
GOOGLE_API_KEY=your_gemini_api_key
```

## 에러 처리 체크리스트

- [ ] Gemini API 타임아웃 (25초) → 에러 메시지 반환
- [ ] JSON 파싱 실패 → 구조화된 에러 응답
- [ ] Gemini API 한도 초과 → 프롬프트만 반환
- [ ] 입력 1000자 초과 → 사전 차단
- [ ] 빈 입력 → 안내 메시지
- [ ] API 키 미설정 → 시작 시 경고
