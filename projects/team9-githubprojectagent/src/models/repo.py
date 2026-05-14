from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    sha: str
    message: str
    author: str
    date: datetime
    additions: int = 0
    deletions: int = 0


class RepoContext(BaseModel):
    owner: str
    name: str
    description: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    primary_language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    is_private: bool = False

    readme: Optional[str] = None
    docs_files: dict[str, str] = Field(default_factory=dict)
    core_files: dict[str, str] = Field(default_factory=dict)

    commits: list[CommitInfo] = Field(default_factory=list)
    commit_summary: Optional[str] = None  # context_builder가 LLM 압축 후 채움

    user_attached_info: Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"
