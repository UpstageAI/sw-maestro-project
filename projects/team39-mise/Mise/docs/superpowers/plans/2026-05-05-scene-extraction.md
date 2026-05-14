# Scene Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 소설 텍스트에서 12개 장면 요소를 추출하고 이미지 생성용 영문 프롬프트로 변환하는 2-call LangChain 파이프라인 구현

**Architecture:** Gemini API 2회 호출 방식. Call 1에서 한국어 소설 텍스트를 12개 시각 요소로 분해하고, Call 2에서 추출된 요소를 영문 이미지 생성 프롬프트로 변환. `with_structured_output()`로 JSON 강제.

**Tech Stack:** Python 3.11+, LangChain, langchain-google-genai, Pydantic, pytest

**Spec:** `docs/superpowers/specs/2026-05-05-scene-extraction-design.md`

---

## File Structure

```
mise/
├── __init__.py
├── config.py                     # 환경 변수 로딩
├── models/
│   ├── __init__.py
│   └── scene_schema.py           # SceneElements, ExtractionResult, PromptResult, SceneSchema
├── prompts/
│   ├── __init__.py
│   ├── extraction_prompt.py      # Call 1: 소설 → 12개 요소
│   └── prompt_generator.py       # Call 2: 요소 → 영문 프롬프트
├── chains/
│   ├── __init__.py
│   └── scene_extractor.py        # extract_scene() 메인 함수
├── .env.example                  # API 키 템플릿
└── requirements.txt
tests/
├── __init__.py
├── test_scene_schema.py          # Pydantic 모델 테스트
├── test_extraction_prompt.py     # Call 1 프롬프트 테스트
├── test_prompt_generator.py      # Call 2 프롬프트 테스트
├── test_scene_extractor.py       # extract_scene() 단위 테스트 (mock)
└── samples.py                    # 테스트용 소설 샘플 데이터
```

---

### Task 1: Project scaffold + config

**Files:**
- Create: `mise/__init__.py`
- Create: `mise/config.py`
- Create: `mise/.env.example`
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
langchain>=0.3.0
langchain-google-genai>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages installed successfully

- [ ] **Step 3: Create mise/__init__.py**

```python
```

(빈 파일)

- [ ] **Step 4: Create mise/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

MODEL_NAME = "gemini-2.0-flash"
MAX_INPUT_LENGTH = 1000
API_TIMEOUT = 25
```

- [ ] **Step 5: Create mise/.env.example**

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

- [ ] **Step 6: Create mise/.env from template**

`.env.example`을 복사하여 `mise/.env` 생성 후 실제 API 키 입력.

- [ ] **Step 7: Create tests/__init__.py**

```python
```

(빈 파일)

- [ ] **Step 8: Verify config loads**

Run: `cd mise && python -c "from config import GOOGLE_API_KEY; print('Config OK')"`
Expected: `Config OK` (API 키가 설정된 경우) 또는 ValueError (미설정 시)

- [ ] **Step 9: Commit**

```bash
git add mise/__init__.py mise/config.py mise/.env.example mise/.env requirements.txt tests/__init__.py
git commit -m "feat: project scaffold with config and dependencies"
```

---

### Task 2: Pydantic models + tests

**Files:**
- Create: `mise/models/__init__.py`
- Create: `mise/models/scene_schema.py`
- Create: `tests/test_scene_schema.py`

- [ ] **Step 1: Create mise/models/__init__.py**

```python
```

(빈 파일)

- [ ] **Step 2: Write failing test for SceneElements**

Create `tests/test_scene_schema.py`:

```python
import pytest
from mise.models.scene_schema import SceneElements, ExtractionResult, PromptResult, SceneSchema


class TestSceneElements:
    def test_create_with_all_fields(self):
        elements = SceneElements(
            character="검은 갑옷을 입은 기사",
            background="폐허가 된 성",
            time="저녁",
            place="무너진 성벽",
            objects=["거대한 마법진", "검"],
            action="마법진을 바라보고 있다",
            emotion="경외",
            mood="장엄하고 불길함",
            color="붉은색과 주황색",
            lighting="노을빛",
            camera_view="성벽 너머를 바라보는 와이드샷",
            composition="배경 중심 구도",
        )
        assert elements.character == "검은 갑옷을 입은 기사"
        assert len(elements.objects) == 2

    def test_objects_default_empty_list(self):
        elements = SceneElements(
            character="", background="", time="", place="",
            action="", emotion="", mood="", color="",
            lighting="", camera_view="", composition="",
        )
        assert elements.objects == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_scene_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mise'`

- [ ] **Step 4: Create mise/models/scene_schema.py**

```python
from pydantic import BaseModel


class SceneElements(BaseModel):
    character: str
    background: str
    time: str
    place: str
    objects: list[str] = []
    action: str
    emotion: str
    mood: str
    color: str
    lighting: str
    camera_view: str
    composition: str


class ExtractionResult(BaseModel):
    """Call 1 출력: 12개 요소 + 각 요소의 출처 구분"""
    elements: SceneElements
    source_type: dict[str, str]


class PromptResult(BaseModel):
    """Call 2 출력: 이미지 생성용 프롬프트"""
    positive_prompt: str
    negative_prompt: str
    style: str = "cinematic"
    missing_info: list[str] = []


class SceneSchema(BaseModel):
    """최종 반환: 요소 + 출처 + 프롬프트"""
    elements: SceneElements
    source_type: dict[str, str]
    prompt: PromptResult
```

- [ ] **Step 5: Add more tests for ExtractionResult, PromptResult, SceneSchema**

Append to `tests/test_scene_schema.py`:

```python
    def test_extraction_result_combines_elements_and_source(self):
        elements = SceneElements(
            character="기사", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        result = ExtractionResult(
            elements=elements,
            source_type={"character": "original", "lighting": "inferred"},
        )
        assert result.source_type["character"] == "original"
        assert result.source_type["lighting"] == "inferred"


class TestPromptResult:
    def test_defaults(self):
        result = PromptResult(
            positive_prompt="cinematic scene, a knight",
            negative_prompt="blurry, low quality",
        )
        assert result.style == "cinematic"
        assert result.missing_info == []

    def test_custom_style_and_missing_info(self):
        result = PromptResult(
            positive_prompt="watercolor painting, a castle",
            negative_prompt="blurry",
            style="watercolor",
            missing_info=["인물 외형 불명확", "시간대 추론"],
        )
        assert result.style == "watercolor"
        assert len(result.missing_info) == 2


class TestSceneSchema:
    def test_assemble_from_parts(self):
        elements = SceneElements(
            character="기사", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        prompt = PromptResult(
            positive_prompt="cinematic, knight, castle",
            negative_prompt="blurry",
        )
        schema = SceneSchema(
            elements=elements,
            source_type={"character": "original"},
            prompt=prompt,
        )
        assert schema.elements.character == "기사"
        assert schema.prompt.positive_prompt == "cinematic, knight, castle"

    def test_dict_roundtrip(self):
        """JSON 직렬화/역직렬화가 정상 동작하는지 확인"""
        elements = SceneElements(
            character="기사", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        prompt = PromptResult(
            positive_prompt="cinematic, knight",
            negative_prompt="blurry",
        )
        schema = SceneSchema(
            elements=elements,
            source_type={"character": "original"},
            prompt=prompt,
        )
        data = schema.model_dump()
        restored = SceneSchema.model_validate(data)
        assert restored == schema
```

- [ ] **Step 6: Run all schema tests**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_scene_schema.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add mise/models/ tests/test_scene_schema.py
git commit -m "feat: Pydantic schema models for scene extraction"
```

---

### Task 3: Call 1 prompt template + tests

**Files:**
- Create: `mise/prompts/__init__.py`
- Create: `mise/prompts/extraction_prompt.py`
- Create: `tests/test_extraction_prompt.py`

- [ ] **Step 1: Create mise/prompts/__init__.py**

```python
```

(빈 파일)

- [ ] **Step 2: Write failing test**

Create `tests/test_extraction_prompt.py`:

```python
from mise.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT, create_extraction_messages


class TestExtractionPrompt:
    def test_system_prompt_contains_key_instructions(self):
        assert "12" in EXTRACTION_SYSTEM_PROMPT
        assert "시각 요소" in EXTRACTION_SYSTEM_PROMPT
        assert "original" in EXTRACTION_SYSTEM_PROMPT
        assert "inferred" in EXTRACTION_SYSTEM_PROMPT

    def test_create_messages_returns_system_and_human(self):
        messages = create_extraction_messages("붉은 노을 아래 무너진 성벽")
        assert len(messages) == 2
        assert messages[0][0] == "system"
        assert messages[1][0] == "human"
        assert "붉은 노을" in messages[1][1]

    def test_create_messages_passes_novel_text_as_human(self):
        novel_text = "검은 기사가 폐허 위에 서 있었다."
        messages = create_extraction_messages(novel_text)
        assert messages[1][1] == novel_text
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_extraction_prompt.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Create mise/prompts/extraction_prompt.py**

```python
from langchain_core.prompts import ChatPromptTemplate

EXTRACTION_SYSTEM_PROMPT = """당신은 소설 장면을 12개 시각 요소로 분해하는 장면 해석 전문가입니다.

사용자가 입력한 소설 문단에서 다음 12개 요소를 추출하세요:
1. character (인물): 인물의 외형, 복장, 자세
2. background (배경): 배경 환경, 공간 구조
3. time (시간대): 새벽, 오전, 오후, 저녁, 밤 등
4. place (장소): 구체적 장소
5. objects (사물): 주요 사물이나 오브젝트 목록
6. action (행동): 인물의 행동이나 동작
7. emotion (감정): 감정 상태
8. mood (분위기): 전체적인 분위기
9. color (색감): 색감이나 색조
10. lighting (조명): 조명 상태
11. camera_view (시점): 카메라 앵글이나 시점
12. composition (구도): 화면 구도나 프레이밍

규칙:
- 각 요소값은 한국어로 작성하세요.
- 원문에 명시된 정보는 그대로 반영하고, source_type에 "original"로 표시하세요.
- 원문에 명시되지 않았지만 장면 맥락에서 합리적으로 추론한 정보는 source_type에 "inferred"로 표시하세요.
- 추론이 불가능한 요소는 빈 문자열로 남두되고, source_type에 "missing"으로 표시하세요.
- 여러 장면이 있더라도 가장 시각적으로 뚜렷한 단일 장면만 추출하세요.
- 과도한 잔혹, 선정, 혐오 묘사는 순화하여 표현하세요."""

_prompt_template = ChatPromptTemplate.from_messages([
    ("system", EXTRACTION_SYSTEM_PROMPT),
    ("human", "{novel_text}"),
])


def create_extraction_messages(novel_text: str) -> list[tuple[str, str]]:
    """Call 1용 메시지 튜플 리스트를 반환한다."""
    messages = _prompt_template.format_messages(novel_text=novel_text)
    return [(msg.type, msg.content) for msg in messages]
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_extraction_prompt.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add mise/prompts/__init__.py mise/prompts/extraction_prompt.py tests/test_extraction_prompt.py
git commit -m "feat: Call 1 extraction prompt template"
```

---

### Task 4: Call 2 prompt template + tests

**Files:**
- Create: `mise/prompts/prompt_generator.py`
- Create: `tests/test_prompt_generator.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_prompt_generator.py`:

```python
from mise.prompts.prompt_generator import PROMPT_GENERATOR_SYSTEM_PROMPT, create_prompt_messages


class TestPromptGenerator:
    def test_system_prompt_contains_key_instructions(self):
        assert "영문" in PROMPT_GENERATOR_SYSTEM_PROMPT or "영어" in PROMPT_GENERATOR_SYSTEM_PROMPT
        assert "positive" in PROMPT_GENERATOR_SYSTEM_PROMPT.lower()
        assert "negative" in PROMPT_GENERATOR_SYSTEM_PROMPT.lower()

    def test_create_messages_contains_all_elements(self):
        elements = {
            "character": "검은 갑옷의 기사",
            "background": "폐허가 된 성",
            "time": "저녁",
            "place": "성벽",
            "objects": ["마법진", "검"],
            "action": "바라보고 있다",
            "emotion": "경외",
            "mood": "장엄함",
            "color": "붉은색",
            "lighting": "노을빛",
            "camera_view": "와이드샷",
            "composition": "배경 중심",
        }
        messages = create_prompt_messages(elements, style="cinematic")
        assert len(messages) == 2
        human_content = messages[1][1]
        assert "검은 갑옷의 기사" in human_content
        assert "cinematic" in human_content

    def test_create_messages_with_default_style(self):
        messages = create_prompt_messages(
            {"character": "기사", "background": "성", "time": "밤",
             "place": "탑", "objects": [], "action": "서 있다", "emotion": "결의",
             "mood": "긴장감", "color": "어두운 파랑", "lighting": "달빛",
             "camera_view": "로우앵글", "composition": "인물 중심"}
        )
        assert "cinematic" in messages[1][1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_prompt_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create mise/prompts/prompt_generator.py**

```python
import json
from langchain_core.prompts import ChatPromptTemplate

PROMPT_GENERATOR_SYSTEM_PROMPT = """당신은 장면 분석 데이터를 이미지 생성용 영문 프롬프트로 변환하는 전문가입니다.

입력으로 한국어 장면 요소가 제공됩니다. 이를 이미지 생성 AI가 이해할 수 있는 영문 프롬프트로 변환하세요.

positive_prompt 작성 규칙:
- 모든 설명은 영어로 작성하세요.
- 쉼표로 구분된 키워드 형태로 작성하세요.
- 순서: {스타일}, {인물 묘사}, {행동}, {배경}, {주요 사물}, {분위기}, {조명}, {색감}, {구도}, high quality, detailed
- 구체적이고 시각적인 표현을 사용하세요.

negative_prompt 작성 규칙:
- 반드시 다음 기본 항목을 포함하세요: excessive gore, explicit content, hate symbols, blurry, low quality, deformed, text, watermark, signature, out of frame
- 장면과 어울리지 않는 요소를 추가로 제외하세요.

missing_info:
- 입력 요소 중 빈 문자열이거나 추론이 불가능한 항목의 한국어 설명을 나열하세요.
- 모든 정보가 충분하면 빈 리스트를 반환하세요."""

_prompt_template = ChatPromptTemplate.from_messages([
    ("system", PROMPT_GENERATOR_SYSTEM_PROMPT),
    ("human", "장면 요소:\n{elements_json}\n\n이미지 스타일: {style}"),
])


def create_prompt_messages(elements: dict, style: str = "cinematic") -> list[tuple[str, str]]:
    """Call 2용 메시지 튜플 리스트를 반환한다."""
    elements_json = json.dumps(elements, ensure_ascii=False, indent=2)
    messages = _prompt_template.format_messages(elements_json=elements_json, style=style)
    return [(msg.type, msg.content) for msg in messages]
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_prompt_generator.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add mise/prompts/prompt_generator.py tests/test_prompt_generator.py
git commit -m "feat: Call 2 prompt generator template"
```

---

### Task 5: Scene extractor (main function) + unit tests

**Files:**
- Create: `mise/chains/__init__.py`
- Create: `mise/chains/scene_extractor.py`
- Create: `tests/test_scene_extractor.py`
- Create: `tests/samples.py`

- [ ] **Step 1: Create test samples data**

Create `tests/samples.py`:

```python
NOVEL_SAMPLE_1 = "붉은 노을 아래 무너진 성벽 너머로 거대한 마법진이 떠오르고 있었다. 검은 갑옷을 입은 기사가 폐허 위에 홀로 서서 하늘을 올려다보았다. 바람이 그의 망토를 흔들었다."

NOVEL_SAMPLE_2 = "달빛이 은백색으로 물든 탑 꼭대기에서, 소녀는 별을 향해 손을 뻗었다. 그녀의 주변으로 푸른 빛의 입자들이 흩날렸고, 먼 바다에서는 고래의 노래가 들려왔다."

NOVEL_SAMPLE_3 = "지하 감옥의 차가운 돌바닥에 웅크린 채, 노인은 떨리는 손으로 벽에 글자를 새기고 있었다. 촛불 하나가 깜빡였고, 멀리서 발소리가 가까워졌다."
```

- [ ] **Step 2: Write failing test for extract_scene generate mode**

Create `tests/test_scene_extractor.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from mise.models.scene_schema import SceneElements, ExtractionResult, PromptResult, SceneSchema
from mise.chains.scene_extractor import extract_scene
from tests.samples import NOVEL_SAMPLE_1


def _make_mock_elements():
    return SceneElements(
        character="검은 갑옷을 입은 기사",
        background="폐허가 된 성벽, 무너진 돌무더기",
        time="저녁",
        place="무너진 성벽 위",
        objects=["거대한 마법진", "검은 갑옷", "망토"],
        action="하늘을 올려다보고 있다",
        emotion="경외",
        mood="장엄하고 불길한 분위기",
        color="붉은색과 주황색 노을",
        lighting="노을빛",
        camera_view="성벽 너머를 바라보는 와이드샷",
        composition="배경 중심 구도, 인물은 작게",
    )


def _make_mock_extraction_result():
    return ExtractionResult(
        elements=_make_mock_elements(),
        source_type={
            "character": "original",
            "background": "original",
            "time": "original",
            "place": "inferred",
            "objects": "original",
            "action": "original",
            "emotion": "inferred",
            "mood": "inferred",
            "color": "original",
            "lighting": "inferred",
            "camera_view": "inferred",
            "composition": "inferred",
        },
    )


def _make_mock_prompt_result():
    return PromptResult(
        positive_prompt="cinematic, a knight in black armor standing on ruined castle walls, looking up at the sky, massive magic circle floating above, dramatic sunset, red and orange sky, cape blowing in the wind, ominous fantasy scene, wide shot, high quality, detailed",
        negative_prompt="excessive gore, explicit content, hate symbols, blurry, low quality, deformed, text, watermark, signature, out of frame, modern buildings, technology",
        style="cinematic",
        missing_info=["기사의 얼굴 묘사 불명확"],
    )


class TestExtractSceneGenerate:
    @patch("mise.chains.scene_extractor.ChatGoogleGenerativeAI")
    def test_generate_mode_returns_scene_schema(self, MockLLM):
        mock_llm = MagicMock()
        MockLLM.return_value = mock_llm

        mock_structured = MagicMock()
        mock_llm.with_structured_output.side_effect = [mock_structured, mock_structured]

        mock_structured.invoke.side_effect = [
            _make_mock_extraction_result(),
            _make_mock_prompt_result(),
        ]

        result = extract_scene(NOVEL_SAMPLE_1)

        assert isinstance(result, SceneSchema)
        assert isinstance(result.elements, SceneElements)
        assert isinstance(result.prompt, PromptResult)
        assert result.elements.character == "검은 갑옷을 입은 기사"
        assert "cinematic" in result.prompt.positive_prompt

    @patch("mise.chains.scene_extractor.ChatGoogleGenerativeAI")
    def test_generate_calls_gemini_twice(self, MockLLM):
        mock_llm = MagicMock()
        MockLLM.return_value = mock_llm
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.invoke.side_effect = [
            _make_mock_extraction_result(),
            _make_mock_prompt_result(),
        ]

        extract_scene(NOVEL_SAMPLE_1)

        assert mock_structured.invoke.call_count == 2


class TestExtractSceneRegenerate:
    @patch("mise.chains.scene_extractor.ChatGoogleGenerativeAI")
    def test_regenerate_skips_call1(self, MockLLM):
        mock_llm = MagicMock()
        MockLLM.return_value = mock_llm
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.invoke.return_value = _make_mock_prompt_result()

        prev_scene = {
            "elements": _make_mock_elements().model_dump(),
        }

        result = extract_scene(NOVEL_SAMPLE_1, mode="regenerate", prev_scene=prev_scene)

        assert isinstance(result, SceneSchema)
        assert mock_structured.invoke.call_count == 1  # Call 2만


class TestExtractSceneValidation:
    def test_empty_input_raises_error(self):
        with pytest.raises(ValueError, match="입력 텍스트가 비어있습니다"):
            extract_scene("")

    def test_whitespace_only_input_raises_error(self):
        with pytest.raises(ValueError, match="입력 텍스트가 비어있습니다"):
            extract_scene("   \n\t  ")

    def test_over_1000_chars_raises_error(self):
        long_text = "가" * 1001
        with pytest.raises(ValueError, match="1000자"):
            extract_scene(long_text)

    def test_exactly_1000_chars_passes(self):
        text = "가" * 1000
        with patch("mise.chains.scene_extractor.ChatGoogleGenerativeAI"):
            with patch("mise.chains.scene_extractor._create_llm") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm
                mock_structured = MagicMock()
                mock_llm.with_structured_output.return_value = mock_structured
                mock_structured.invoke.side_effect = [
                    _make_mock_extraction_result(),
                    _make_mock_prompt_result(),
                ]
                result = extract_scene(text)
                assert isinstance(result, SceneSchema)

    def test_regenerate_without_prev_scene_raises_error(self):
        with pytest.raises(ValueError, match="prev_scene"):
            extract_scene("텍스트", mode="regenerate", prev_scene=None)

    def test_invalid_mode_raises_error(self):
        with pytest.raises(ValueError, match="mode"):
            extract_scene("텍스트", mode="invalid")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_scene_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Create mise/chains/__init__.py**

```python
```

(빈 파일)

- [ ] **Step 5: Create mise/chains/scene_extractor.py**

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_google_genai import ChatGoogleGenerativeAI
from mise.config import GOOGLE_API_KEY, MODEL_NAME, MAX_INPUT_LENGTH, API_TIMEOUT
from mise.models.scene_schema import ExtractionResult, PromptResult, SceneSchema, SceneElements
from mise.prompts.extraction_prompt import _prompt_template as extraction_template
from mise.prompts.prompt_generator import _prompt_template as prompt_template


def _create_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3,
        request_timeout=API_TIMEOUT,
    )


def _validate_input(novel_text: str, mode: str, prev_scene: dict | None) -> None:
    if not novel_text or not novel_text.strip():
        raise ValueError("입력 텍스트가 비어있습니다.")
    if len(novel_text) > MAX_INPUT_LENGTH:
        raise ValueError(f"입력 텍스트가 {MAX_INPUT_LENGTH}자를 초과합니다. (현재: {len(novel_text)}자)")
    if mode not in ("generate", "regenerate"):
        raise ValueError(f"잘못된 mode: '{mode}'. 'generate' 또는 'regenerate'만 허용됩니다.")
    if mode == "regenerate" and prev_scene is None:
        raise ValueError("regenerate 모드에서는 prev_scene이 필요합니다.")


def _call_extract(novel_text: str, llm: ChatGoogleGenerativeAI) -> ExtractionResult:
    chain = extraction_template | llm.with_structured_output(ExtractionResult)
    return chain.invoke({"novel_text": novel_text})


def _call_prompt(elements: SceneElements, style: str, llm: ChatGoogleGenerativeAI) -> PromptResult:
    elements_dict = elements.model_dump()
    chain = prompt_template | llm.with_structured_output(PromptResult)
    return chain.invoke({
        "elements_json": __import__("json").dumps(elements_dict, ensure_ascii=False),
        "style": style,
    })


def extract_scene(
    novel_text: str,
    mode: str = "generate",
    prev_scene: dict | None = None,
) -> SceneSchema:
    _validate_input(novel_text, mode, prev_scene)
    llm = _create_llm()

    if mode == "generate":
        extraction = _call_extract(novel_text, llm)
        elements = extraction.elements
        source_type = extraction.source_type
        style = "cinematic"
    else:
        elements = SceneElements.model_validate(prev_scene["elements"])
        source_type = prev_scene.get("source_type", {})
        style = prev_scene.get("prompt", {}).get("style", "cinematic")

    prompt_result = _call_prompt(elements, style, llm)

    return SceneSchema(
        elements=elements,
        source_type=source_type,
        prompt=prompt_result,
    )
```

- [ ] **Step 6: Run tests and fix issues**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/test_scene_extractor.py -v`

테스트가 실패하면 구현을 수정하여 통과시킨다. 주요 확인:
- `_create_llm`이 mock에 의해 올바르게 대체되는지
- `_call_prompt`에 전달되는 `elements_json` 포맷이 올바른지

- [ ] **Step 7: Commit**

```bash
git add mise/chains/ tests/test_scene_extractor.py tests/samples.py
git commit -m "feat: scene extractor with generate/regenerate modes"
```

---

### Task 6: Integration test with real Gemini API

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test (skipped by default)**

Create `tests/test_integration.py`:

```python
import os
import pytest

# 실제 API 키가 있고 RUN_INTEGRATION=1일 때만 실행
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION"),
    reason="RUN_INTEGRATION 환경 변수가 설정되지 않음. 실제 API 호출 테스트 생략.",
)

from mise.chains.scene_extractor import extract_scene
from mise.models.scene_schema import SceneSchema
from tests.samples import NOVEL_SAMPLE_1, NOVEL_SAMPLE_2, NOVEL_SAMPLE_3


class TestIntegration:
    def test_generate_sample1(self):
        result = extract_scene(NOVEL_SAMPLE_1)
        assert isinstance(result, SceneSchema)
        assert result.elements.character != ""
        assert result.prompt.positive_prompt != ""
        assert "blurry" in result.prompt.negative_prompt

    def test_generate_sample2(self):
        result = extract_scene(NOVEL_SAMPLE_2)
        assert isinstance(result, SceneSchema)
        assert result.elements.place != ""

    def test_generate_sample3(self):
        result = extract_scene(NOVEL_SAMPLE_3)
        assert isinstance(result, SceneSchema)
        assert len(result.elements.objects) >= 0

    def test_regenerate_from_previous(self):
        first = extract_scene(NOVEL_SAMPLE_1)
        prev = {"elements": first.elements.model_dump(), "source_type": first.source_type}
        regenerated = extract_scene(NOVEL_SAMPLE_1, mode="regenerate", prev_scene=prev)
        assert isinstance(regenerated, SceneSchema)
        assert regenerated.elements.character == first.elements.character
        assert regenerated.prompt.positive_prompt != ""

    def test_all_elements_populated(self):
        """12개 요소가 모두 비어있지 않은지 확인 (누락률 측정)"""
        result = extract_scene(NOVEL_SAMPLE_1)
        empty_count = sum(
            1 for field_name, value in result.elements.model_dump().items()
            if field_name != "objects" and (value == "" or value == [])
        )
        assert empty_count <= 1, f"{empty_count}개 요소가 비어있음"
```

- [ ] **Step 2: Run unit tests (should all pass without API key)**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: 모든 단위 테스트 통과

- [ ] **Step 3: Run integration test (requires API key)**

Run: `cd /Users/simjonghan/source_code/asm-39-mise && RUN_INTEGRATION=1 python -m pytest tests/test_integration.py -v`
Expected: 5 passed (실제 Gemini API 호출)

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests for scene extraction with real Gemini API"
```
