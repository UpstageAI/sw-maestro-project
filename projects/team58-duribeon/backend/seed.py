import json
from pathlib import Path

SEED_PATH = Path(__file__).parent / "data" / "seoul_seed.json"


def _load_doc() -> dict:
    with SEED_PATH.open(encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict) or "areas" not in doc or "places" not in doc:
        raise RuntimeError(
            f"{SEED_PATH} must be an object with 'areas' and 'places' keys"
        )
    return doc


def load_places() -> list[dict]:
    return _load_doc()["places"]


def load_areas() -> list[dict]:
    return _load_doc()["areas"]


def known_area_ids() -> set[str]:
    return {a["id"] for a in load_areas()}
