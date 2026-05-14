from fastapi import APIRouter

from app.data.mentors import get_all_mentors
from app.modules.mentor_candidate.schemas import Mentor

router = APIRouter(prefix="/api/mentors", tags=["mentor"])


@router.get("", response_model=list[Mentor])
async def list_mentors() -> list[Mentor]:
    return get_all_mentors()
