import re
import unicodedata

MIN_PERSONA_LENGTH = 50
MAX_PERSONA_LENGTH = 5000


def normalize_text(text: str) -> str:
    """Strip, collapse whitespace, and apply Unicode NFC normalization."""
    text = unicodedata.normalize("NFC", text).strip()
    return re.sub(r"\s+", " ", text)
