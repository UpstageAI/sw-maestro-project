import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# MUST set before importing mise modules (config.py validates on import)
os.environ["GOOGLE_API_KEY"] = "test"

from mise.generators.image_generator import generate_image


class TestGenerateImage:
    @patch("mise.generators.image_generator.genai.Client")
    def test_generate_image_returns_pil_image(self, mock_client_cls):
        expected = Image.new("RGB", (8, 8), color="red")
        part = SimpleNamespace(
            inline_data=object(),
            text=None,
            as_image=lambda: expected,
        )
        response = SimpleNamespace(parts=[part])

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = response
        mock_client_cls.return_value = mock_client

        result = generate_image(
            positive="cinematic, a knight in black armor, ruined castle wall",
            negative="blurry, low quality",
            style="cinematic",
        )

        assert result is expected
        mock_client.models.generate_content.assert_called_once()

    def test_generate_image_rejects_empty_positive_prompt(self):
        with pytest.raises(ValueError, match="positive_prompt"):
            generate_image("", "blurry", "cinematic")

    @patch("mise.generators.image_generator.genai.Client")
    def test_generate_image_raises_when_no_image_part_exists(self, mock_client_cls):
        response = SimpleNamespace(parts=[SimpleNamespace(inline_data=None, text="text only response")])

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = response
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="이미지 생성 응답에 이미지 데이터가 없습니다."):
            generate_image(
                positive="cinematic, a mage above ruined walls",
                negative="blurry",
                style="cinematic",
            )
