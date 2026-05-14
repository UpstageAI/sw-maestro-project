from typing import Dict, List

from pydantic import BaseModel, Field

from app.models.dtos.chemistry import ChemistryDTO


class ChemistryResp(BaseModel):
    score: int = Field(..., ge=0, le=100)
    oneliner: str
    summary: str
    good_points: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    metrics: Dict[str, int] = Field(default_factory=dict)
    final_comment: str

    @classmethod
    def from_dto(cls, dto: ChemistryDTO) -> "ChemistryResp":
        return cls(
            score=dto.score,
            oneliner=dto.oneliner,
            summary=dto.summary,
            good_points=dto.good_points,
            concerns=dto.concerns,
            metrics=dto.metrics,
            final_comment=dto.final_comment,
        )
