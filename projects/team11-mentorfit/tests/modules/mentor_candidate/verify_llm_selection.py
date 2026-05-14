import asyncio
import os
import logging
from app.modules.mentor_candidate.service import get_mentor_candidates
from app.modules.mentor_candidate.schemas import TeamProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Mock API Key for testing if not set
if not os.environ.get("UPSTAGE_API_KEY"):
    os.environ["UPSTAGE_API_KEY"] = "mock_key"

async def test_selection():
    team = TeamProfile(
        members_rnr="리더(BE), 팀원1(FE)",
        project_plan_tech_goals="AI를 활용한 멘토링 매칭 시스템 개발",
        mentoring_needs="LLM 에이전트 설계 및 RAG 시스템 구축 노하우 전수",
        fit_conditions="AI 엔지니어 출신 멘토 선호",
        maestro_program_goals="소마 인증 및 창업",
        skills="Python, FastAPI, LLM"
    )
    
    print("Searching for candidates...")
    candidates = await get_mentor_candidates(team_profile=team, top_k=5)
    
    for c in candidates:
        print(f"Rank {c.rank}: Mentor ID {c.mentor_id}")
        print(f"Reason: {c.reason}")
        print(f"Weak Point: {c.weak_point}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_selection())
