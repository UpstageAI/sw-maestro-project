import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    try:
        import streamlit as st
        GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        pass

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY가 설정되지 않았습니다. "
        "환경 변수(.env) 또는 Streamlit Secrets에 추가하세요."
    )

MODEL_NAME = "gemini-2.5-flash"
IMAGE_MODEL_NAME = "gemini-2.5-flash-image"
MAX_INPUT_LENGTH = 1000
API_TIMEOUT = 25
