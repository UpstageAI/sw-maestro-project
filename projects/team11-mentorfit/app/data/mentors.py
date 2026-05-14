import json
from pathlib import Path
from typing import List
from app.core.config import settings
from app.modules.mentor_candidate.schemas import Mentor

_mentors: List[Mentor] | None = None

def get_all_mentors() -> List[Mentor]:
    global _mentors
    if _mentors is None:
        data = json.loads(Path(settings.mentor_data_path).read_text(encoding="utf-8"))
        _mentors = [Mentor(**m) for m in data]
    return _mentors

def reload_mentors():
    """Forces reloading mentors from disk next time get_all_mentors is called."""
    global _mentors
    _mentors = None
