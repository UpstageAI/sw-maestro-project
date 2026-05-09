from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ResumeCommandPayload(_CamelModel):
    run_id: str
    resume_reason: str
    patch_fields: dict[str, Any] = {}
