"""persona_cards.seed.json 로드 — 런타임 페르소나 풀."""

import json
from pathlib import Path

from schemas import TargetUserPersonaCard

_SEED_PATH = Path(__file__).parent.parent / "data" / "personas" / "persona_cards.seed.json"


def load_personas() -> list[TargetUserPersonaCard]:
    raw = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return [TargetUserPersonaCard(**item) for item in raw]
