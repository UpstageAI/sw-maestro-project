from dataclasses import dataclass, field
from typing import Callable, Optional

from .repo import RepoContext
from .story import StoryDraft


@dataclass
class NotionTemplate:
    id: str
    name: str
    description: str
    render: Callable[[StoryDraft, RepoContext], list[dict]]
    preview_md: Optional[Callable[[StoryDraft, RepoContext], str]] = None
