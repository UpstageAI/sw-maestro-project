from __future__ import annotations

import logging

from app.core.config import settings
from app.modules.mentor_candidate.schemas import CandidateResult, TeamProfile
from app.modules.mentor_candidate.retriever import filter_mentors
from app.modules.mentor_candidate.llm_selector import select_candidates
from app.data.mentors import get_all_mentors

logger = logging.getLogger(__name__)

async def get_mentor_candidates(
    team_profile: TeamProfile,
    top_k: int = 5,
    prefilter_top_n: int | None = None,
) -> list[CandidateResult]:
    """
    중앙에서 절차적으로 호출하는 멘토 후보 추천 메인 함수.
    2단계 프로세스를 거칩니다:
    1. 전체 멘토(예: 220명) 중 임베딩 기반 유사도 검색으로 상위 N명(기본 30명) 필터링
    2. 필터링된 후보를 Solar LLM 컨텍스트에 주입하여 최종 K명 선정 및 이유 도출
    """
    logger.info("🚀 [mentor_candidate] 멘토 후보 추천 파이프라인 시작")
    
    mentors = get_all_mentors()
    logger.info(f"   - 가용 멘토 데이터 로드 완료: 총 {len(mentors)}명")

    # 1단계: 임베딩 기반 사전 필터링 (컨텍스트 오버플로우 방지)
    filter_limit = prefilter_top_n or settings.prefilter_top_n
    logger.info(f"🔍 [Stage 1] 임베딩 기반 사전 필터링 시작 (목표: 상위 {filter_limit}명)")
    prefiltered_mentors = await filter_mentors(
        team_profile=team_profile,
        mentors=mentors,
        top_n=filter_limit,
    )
    logger.info(f"✅ [Stage 1] 사전 필터링 완료: {len(prefiltered_mentors)}명 추출됨")

    # 2단계: LLM을 통한 최종 후보 선정 및 이유 작성
    logger.info(f"🧠 [Stage 2] LLM 기반 최종 후보 선정 시작 (목표: Top {top_k}명)")
    candidates = await select_candidates(
        team_profile=team_profile,
        mentors=prefiltered_mentors,
        top_k=top_k
    )
    logger.info(f"✅ [Stage 2] LLM 최종 선정 완료: {len(candidates)}명 확정")
    
    logger.info("🎉 [mentor_candidate] 멘토 후보 추천 파이프라인 정상 종료")
    return candidates
