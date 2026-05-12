from typing import Literal
from pydantic import BaseModel, Field, field_validator


# Area is validated at runtime against the curation seed so adding a new
# area only requires editing data/seoul_seed.json.
Area = str
Category = Literal["food", "place", "experience"]
Language = Literal["ko", "en"]


class Mission(BaseModel):
    id: str
    title: str = Field(..., min_length=2, max_length=60)
    hook: str = Field(..., min_length=4, max_length=160)
    place_id: str
    place_name: str
    route_hint: str = Field(..., max_length=200)
    proof_method: str = Field(..., max_length=160)
    estimated_minutes: int = Field(..., ge=5, le=240)
    category: Category


class MissionBundle(BaseModel):
    missions: list[Mission]

    @field_validator("missions")
    @classmethod
    def reasonable_count(cls, v: list[Mission]) -> list[Mission]:
        # The agent's whitelist filter + deterministic fallback in
        # generate_missions() guarantees exactly 5 missions are returned to
        # the caller. Here we just sanity-check the shape so downstream code
        # has at least 1 mission to work with and at most 10 to dedupe.
        if len(v) < 1:
            raise ValueError("expected at least 1 mission")
        if len(v) > 10:
            raise ValueError(f"too many missions: {len(v)}")
        return v


class Verdict(BaseModel):
    ok: bool
    reason: str = Field(..., max_length=200)
    comment: str = Field(..., max_length=200)


class Context(BaseModel):
    area: Area
    group: str
    time_budget: str = ""
    mood: str
    avoid: str
    language: Language

    @field_validator("area")
    @classmethod
    def _area_known(cls, v: str) -> str:
        # Lazy import to avoid circular import (seed → schemas → seed).
        from seed import known_area_ids

        valid = known_area_ids()
        if v not in valid:
            raise ValueError(
                f"unknown area: {v!r} (valid: {sorted(valid)})"
            )
        return v
