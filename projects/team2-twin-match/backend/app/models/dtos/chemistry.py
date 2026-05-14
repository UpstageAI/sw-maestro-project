from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ChemistryDTO:
    score: int
    oneliner: str
    summary: str
    good_points: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    metrics: Dict[str, int] = field(default_factory=dict)
    final_comment: str = ""
