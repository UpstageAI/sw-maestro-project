from __future__ import annotations

from enum import Enum

from app.modules.mentor_candidate.schemas import TeamProfile


class MentoringDomain(str, Enum):
    TECH_DEPTH = "기술_깊이"
    ARCHITECTURE = "아키텍처_설계"
    STARTUP_BM = "창업_BM"
    CAREER = "취업_커리어"
    CERTIFICATION = "인증_발표"
    COLLAB_PLANNING = "협업_기획"


__all__ = ["MentoringDomain", "TeamProfile"]
