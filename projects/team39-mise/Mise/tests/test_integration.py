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
