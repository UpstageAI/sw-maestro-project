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
