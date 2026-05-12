import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

MODEL_NAME = "gemini-2.5-flash"
IMAGE_MODEL_NAME = "gemini-2.5-flash-image"
MAX_INPUT_LENGTH = 1000
API_TIMEOUT = 25
