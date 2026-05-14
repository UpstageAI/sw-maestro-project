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
