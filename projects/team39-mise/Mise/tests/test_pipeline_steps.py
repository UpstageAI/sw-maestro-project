import os
import json
import pytest
from unittest.mock import patch, MagicMock

os.environ["GOOGLE_API_KEY"] = "test"

from mise.models.scene_schema import (
    SceneElements, ExtractionResult, FillResult, VerifyResult, PromptResult, SceneSchema,
)
from mise.chains.scene_extractor import (
    extract_node, check_missing_node, fill_node, verify_node, prompt_node, extract_scene,
)


def _make_elements_with_blanks():
    return SceneElements(
        character="검은 갑옷을 입은 기사",
        background="폐허가 된 성벽",
        time="저녁",
        place="",
        objects=[],
        action="",
        emotion="",
        mood="장엄한 분위기",
        color="붉은색",
        lighting="",
        camera_view="",
        composition="",
    )


def _make_filled_elements():
    return SceneElements(
        character="검은 갑옷을 입은 기사",
        background="폐허가 된 성벽",
        time="저녁",
        place="무너진 성벽 위",
        objects=[],
        action="하늘을 올려다보고 있다",
        emotion="경외",
        mood="장엄한 분위기",
        color="붉은색",
        lighting="노을빛",
        camera_view="성벽 너머 와이드샷",
        composition="배경 중심 구도",
    )


def _setup_mock_llm(side_effects):
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.side_effect = side_effects
    mock_llm.with_structured_output.return_value = mock_chain
    return mock_llm


# ── Node 2: check_missing_node 단위 테스트 ──────────────────────────

class TestCheckMissingNode:
    def test_finds_empty_fields(self):
        state = {"elements": _make_elements_with_blanks()}
        result = check_missing_node(state)
        assert "place" in result["missing_fields"]
        assert "action" in result["missing_fields"]
        assert "emotion" in result["missing_fields"]
        assert "lighting" in result["missing_fields"]
        assert "camera_view" in result["missing_fields"]
        assert "composition" in result["missing_fields"]

    def test_ignores_filled_fields(self):
        state = {"elements": _make_elements_with_blanks()}
        result = check_missing_node(state)
        assert "character" not in result["missing_fields"]
        assert "background" not in result["missing_fields"]
        assert "time" not in result["missing_fields"]
        assert "mood" not in result["missing_fields"]

    def test_skips_objects_field(self):
        state = {"elements": _make_elements_with_blanks()}
        result = check_missing_node(state)
        assert "objects" not in result["missing_fields"]

    def test_returns_empty_when_all_filled(self):
        elements = SceneElements(
            character="기사", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        result = check_missing_node({"elements": elements})
        assert result["missing_fields"] == []

    def test_all_fields_empty(self):
        elements = SceneElements(
            character="", background="", time="", place="",
            action="", emotion="", mood="", color="",
            lighting="", camera_view="", composition="",
        )
        result = check_missing_node({"elements": elements})
        assert len(result["missing_fields"]) == 11

    def test_whitespace_only_not_treated_as_missing(self):
        elements = SceneElements(
            character="  ", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        result = check_missing_node({"elements": elements})
        assert "character" not in result["missing_fields"]


# ── Node 3: fill_node 단위 테스트 ────────────────────────────────────

class TestFillNode:
    @patch("mise.chains.scene_extractor._create_llm")
    def test_fills_missing_and_updates_source_type(self, mock_create_llm):
        filled = _make_filled_elements()
        mock_create_llm.return_value = _setup_mock_llm([
            FillResult(elements=filled, fill_reason={"place": "문맥상 성벽 위"}),
        ])

        state = {
            "novel_text": "기사가 서 있었다.",
            "elements": _make_elements_with_blanks(),
            "missing_fields": ["place", "action", "emotion", "lighting", "camera_view", "composition"],
            "source_type": {"character": "original"},
        }
        result = fill_node(state)

        assert result["elements"] == filled
        assert result["source_type"]["place"] == "inferred"
        assert result["source_type"]["character"] == "original"


# ── Node 4: verify_node 단위 테스트 ──────────────────────────────────

class TestVerifyNode:
    @patch("mise.chains.scene_extractor._create_llm")
    def test_verifies_elements(self, mock_create_llm):
        verified = _make_filled_elements()
        mock_create_llm.return_value = _setup_mock_llm([
            VerifyResult(elements=verified, corrections=[]),
        ])

        state = {
            "novel_text": "기사가 서 있었다.",
            "elements": _make_filled_elements(),
            "missing_fields": ["place"],
        }
        result = verify_node(state)
        assert result["elements"] == verified


# ── 프롬프트 템플릿 존재 확인 ─────────────────────────────────────────

class TestPromptTemplates:
    def test_fill_prompt_template_exists(self):
        from mise.prompts.fill_prompt import FILL_SYSTEM_PROMPT, create_fill_messages
        assert "추론" in FILL_SYSTEM_PROMPT
        messages = create_fill_messages("소설 텍스트", '{"character": ""}')
        assert len(messages) == 2

    def test_verify_prompt_template_exists(self):
        from mise.prompts.verify_prompt import VERIFY_SYSTEM_PROMPT, create_verify_messages
        assert "일관성" in VERIFY_SYSTEM_PROMPT
        assert "검증" in VERIFY_SYSTEM_PROMPT
        messages = create_verify_messages("소설 텍스트", '{"character": "기사"}')
        assert len(messages) == 2


# ── Pydantic 모델 테스트 ──────────────────────────────────────────────

class TestNewModels:
    def test_fill_result_model(self):
        result = FillResult(
            elements=_make_filled_elements(),
            fill_reason={"place": "문맥상 성벽 위로 추론"},
        )
        assert result.fill_reason["place"] == "문맥상 성벽 위로 추론"

    def test_fill_result_default_empty_reason(self):
        result = FillResult(elements=_make_filled_elements())
        assert result.fill_reason == {}

    def test_verify_result_model(self):
        result = VerifyResult(elements=_make_filled_elements(), corrections=["시간 수정"])
        assert len(result.corrections) == 1

    def test_verify_result_default_empty_corrections(self):
        result = VerifyResult(elements=_make_filled_elements())
        assert result.corrections == []


# ── 통합: 전체 그래프 실행 테스트 ─────────────────────────────────────

class TestGraphNoMissing:
    """누락이 없을 때: extract(1) + prompt(1) = 2회 LLM 호출"""

    @patch("mise.chains.scene_extractor._create_llm")
    def test_full_pipeline_no_missing(self, mock_create_llm):
        all_filled = SceneElements(
            character="기사", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        # 각 노드가 _create_llm()을 개별 호출하므로 side_effect로 순서 제공
        mock_create_llm.side_effect = [
            _setup_mock_llm([ExtractionResult(
                elements=all_filled,
                source_type={"character": "original"},
            )]),
            _setup_mock_llm([PromptResult(
                positive_prompt="cinematic, knight",
                negative_prompt="blurry",
            )]),
        ]

        result = extract_scene("기사가 성벽 위에 서 있었다.")

        assert isinstance(result, SceneSchema)
        assert result.elements.character == "기사"
        assert "cinematic" in result.prompt.positive_prompt


class TestGraphWithMissing:
    """누락이 있을 때: extract(1) + fill(1) + verify(1) + prompt(1) = 4회 LLM 호출"""

    @patch("mise.chains.scene_extractor._create_llm")
    def test_full_pipeline_with_missing(self, mock_create_llm):
        partial = SceneElements(
            character="기사", background="", time="저녁", place="",
            action="", emotion="", mood="장엄", color="붉은",
            lighting="", camera_view="", composition="",
        )
        filled = SceneElements(
            character="기사", background="성벽", time="저녁", place="성벽 위",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        mock_create_llm.side_effect = [
            # extract_node
            _setup_mock_llm([ExtractionResult(
                elements=partial,
                source_type={"character": "original", "time": "original", "mood": "original"},
            )]),
            # fill_node
            _setup_mock_llm([FillResult(
                elements=filled,
                fill_reason={"place": "문맥상 유추"},
            )]),
            # verify_node
            _setup_mock_llm([VerifyResult(elements=filled, corrections=[])]),
            # prompt_node
            _setup_mock_llm([PromptResult(
                positive_prompt="cinematic, knight, castle",
                negative_prompt="blurry",
            )]),
        ]

        result = extract_scene("기사가 서 있었다.")

        assert isinstance(result, SceneSchema)
        assert result.source_type.get("place") == "inferred"
        assert result.source_type.get("background") == "inferred"
        assert result.source_type.get("character") == "original"
        assert mock_create_llm.call_count == 4


class TestGraphRegenerate:
    """regenerate 모드: extract_node는 prev_scene 사용, prompt_node만 LLM 호출"""

    @patch("mise.chains.scene_extractor._create_llm")
    def test_regenerate_no_missing(self, mock_create_llm):
        all_filled = SceneElements(
            character="기사", background="성", time="저녁", place="성벽",
            action="바라본다", emotion="경외", mood="장엄", color="붉은",
            lighting="노을빛", camera_view="와이드", composition="배경 중심",
        )
        mock_create_llm.side_effect = [
            _setup_mock_llm([PromptResult(
                positive_prompt="cinematic, knight",
                negative_prompt="blurry",
            )]),
        ]

        prev_scene = {
            "elements": all_filled.model_dump(),
            "source_type": {"character": "original"},
        }

        result = extract_scene("기사가 서 있었다.", mode="regenerate", prev_scene=prev_scene)

        assert isinstance(result, SceneSchema)
        assert mock_create_llm.call_count == 1  # prompt_node만 호출
