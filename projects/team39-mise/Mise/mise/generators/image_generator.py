from google import genai
from google.genai.errors import ClientError
from PIL import Image

from mise.config import GOOGLE_API_KEY, IMAGE_MODEL_NAME


def _build_image_prompt(positive: str, negative: str, style: str) -> str:
    style_text = style.strip() if style else "cinematic"
    negative_text = negative.strip() if negative else "none"

    return (
        f"Generate a single high-quality {style_text} image.\n"
        f"Follow this visual prompt closely: {positive.strip()}\n"
        f"Avoid these elements: {negative_text}\n"
        "Return the generated image."
    )


def generate_image(positive: str, negative: str, style: str) -> Image.Image:
    if not positive or not positive.strip():
        raise ValueError("positive_prompt가 비어있습니다.")

    client = genai.Client(api_key=GOOGLE_API_KEY)

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL_NAME,
            contents=[_build_image_prompt(positive, negative, style)],
        )
    except ClientError as exc:
        message = str(exc)
        if "RESOURCE_EXHAUSTED" in message or "429" in message:
            raise RuntimeError(
                "이미지 생성 quota를 초과했습니다. 잠시 후 다시 시도하거나 프로젝트 billing/모델 사용 가능 여부를 확인해주세요."
            ) from exc
        raise RuntimeError(f"이미지 생성 API 호출에 실패했습니다: {exc}") from exc

    for part in response.parts:
        if part.inline_data is not None:
            return part.as_image()

    raise RuntimeError("이미지 생성 응답에 이미지 데이터가 없습니다.")
