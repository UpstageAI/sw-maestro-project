from mise.prompts.focused_prompt_generator import (
    FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT,
    create_focused_prompt_messages,
)


class TestFocusedPromptGenerator:
    def test_system_prompt_contains_emphasis_rules(self):
        assert "강조" in FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT
        assert "변경된 요소" in FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT
        assert "positive" in FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT.lower()
        assert "negative" in FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT.lower()

    def test_create_messages_contains_changed_values(self):
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
        changed = {"character": "검은 갑옷의 기사", "lighting": "노을빛"}
        messages = create_focused_prompt_messages(elements, changed, style="cinematic")

        assert len(messages) == 2
        human_content = messages[1][1]
        assert "검은 갑옷의 기사" in human_content
        assert "노을빛" in human_content
        assert "변경된 요소" in human_content
        assert "cinematic" in human_content

    def test_create_messages_with_default_style(self):
        elements = {
            "character": "기사", "background": "성", "time": "밤",
            "place": "탑", "objects": [], "action": "서 있다", "emotion": "결의",
            "mood": "긴장감", "color": "어두운 파랑", "lighting": "달빛",
            "camera_view": "로우앵글", "composition": "인물 중심",
        }
        messages = create_focused_prompt_messages(elements, {"emotion": "결의"})
        assert "cinematic" in messages[1][1]

    def test_create_messages_with_empty_changed_values(self):
        elements = {
            "character": "기사", "background": "성", "time": "밤",
            "place": "탑", "objects": [], "action": "서 있다", "emotion": "결의",
            "mood": "긴장감", "color": "어두운 파랑", "lighting": "달빛",
            "camera_view": "로우앵글", "composition": "인물 중심",
        }
        messages = create_focused_prompt_messages(elements, {})
        assert len(messages) == 2
