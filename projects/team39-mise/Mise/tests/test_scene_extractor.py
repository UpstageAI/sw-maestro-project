import os
import pytest
from unittest.mock import patch, MagicMock

# MUST set before importing mise modules (config.py validates on import)
os.environ["GOOGLE_API_KEY"] = "test"

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


def _setup_mock_llm(side_effects):
    """LangGraph 파이프라인에서 사용할 mock LLM을 설정한다.

    각 노드에서 template | llm.with_structured_output(Model) 형태로 체인이 구성되고,
    체인이 invoke되면 side_effects 순서대로 결과를 반환한다.
    """
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.side_effect = side_effects
    mock_llm.with_structured_output.return_value = mock_chain
    return mock_llm


class TestExtractSceneGenerate:
    @patch("mise.chains.scene_extractor._create_llm")
    def test_generate_mode_returns_scene_schema(self, mock_create_llm):
        # 모든 요소가 채워진 경우: extract(1) + prompt(1) = 2회 LLM 호출
        mock_create_llm.side_effect = [
            _setup_mock_llm([_make_mock_extraction_result()]),
            _setup_mock_llm([_make_mock_prompt_result()]),
        ]

        result = extract_scene(NOVEL_SAMPLE_1)

        assert isinstance(result, SceneSchema)
        assert isinstance(result.elements, SceneElements)
        assert isinstance(result.prompt, PromptResult)
        assert result.elements.character == "검은 갑옷을 입은 기사"
        assert "cinematic" in result.prompt.positive_prompt


class TestExtractSceneRegenerate:
    @patch("mise.chains.scene_extractor._create_llm")
    def test_regenerate_skips_extract(self, mock_create_llm):
        # regenerate: extract_node는 prev_scene 사용 (LLM 호출 없음)
        # prompt_node만 LLM 호출 = 1회
        mock_create_llm.side_effect = [
            _setup_mock_llm([_make_mock_prompt_result()]),
        ]

        prev_scene = {
            "elements": _make_mock_elements().model_dump(),
        }

        result = extract_scene(NOVEL_SAMPLE_1, mode="regenerate", prev_scene=prev_scene)

        assert isinstance(result, SceneSchema)
        assert mock_create_llm.call_count == 1


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
        with patch("mise.chains.scene_extractor._create_llm") as mock_create_llm:
            mock_create_llm.side_effect = [
                _setup_mock_llm([_make_mock_extraction_result()]),
                _setup_mock_llm([_make_mock_prompt_result()]),
            ]
            result = extract_scene(text)
            assert isinstance(result, SceneSchema)

    def test_regenerate_without_prev_scene_raises_error(self):
        with pytest.raises(ValueError, match="prev_scene"):
            extract_scene("텍스트", mode="regenerate", prev_scene=None)

    def test_invalid_mode_raises_error(self):
        with pytest.raises(ValueError, match="mode"):
            extract_scene("텍스트", mode="invalid")
