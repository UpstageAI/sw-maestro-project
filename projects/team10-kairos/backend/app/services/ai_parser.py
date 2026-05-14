from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from app.schemas import ScheduleAnalysisContext


class ParsedSchedule(BaseModel):
    title: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    location: Optional[str] = None
    reminder_minutes: Optional[int] = None
    schedule_type: Optional[str] = None


def parse_schedule_text(
    text: str,
    timezone: str,
    analysis_context: Optional[ScheduleAnalysisContext] = None,
) -> ParsedSchedule:
    api_key = os.getenv("UPSTAGE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_upstage_api_key_here":
        raise RuntimeError("UPSTAGE_API_KEY is not set")

    model = os.getenv("UPSTAGE_MODEL") or os.getenv("OPENAI_MODEL", "solar-pro3")
    base_url = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")
    reasoning_effort = os.getenv("UPSTAGE_REASONING_EFFORT", "high")
    now = datetime.now().astimezone().isoformat()
    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract one calendar event from Korean natural language. "
                        "If previous schedule context is provided, treat the user text as a follow-up answer or correction. "
                        "Merge the new user text into the previous schedule and preserve previous values unless the user clearly changes them. "
                        "Prioritize filling previous missing_fields. "
                        "Return only valid JSON with these exact keys: "
                        "title, start_at, end_at, location, reminder_minutes, schedule_type. "
                        "Use ISO 8601 datetimes with timezone offsets. "
                        "Do not invent missing information. "
                        "If a field is missing, set it to null. "
                        "If title is unclear, create a short Korean noun phrase. "
                        "If reminder is missing, set reminder_minutes to null. "
                        "If end time is missing, set end_at to null. "
                        "For schedule_type, use a short category such as meeting, deadline, appointment, exercise, study, or personal."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current datetime: {now}\n"
                        f"User timezone: {timezone}\n"
                        f"Previous schedule context: {_dump_context(analysis_context)}\n"
                        f"Text: {text}"
                    ),
                },
            ],
            reasoning_effort=reasoning_effort,
            stream=False,
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("AI returned no schedule content")
        return ParsedSchedule.model_validate(_load_json(content))
    except (json.JSONDecodeError, OpenAIError, ValidationError) as exc:
        raise RuntimeError("AI schedule parsing failed") from exc


def _load_json(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def _dump_context(analysis_context: Optional[ScheduleAnalysisContext]) -> str:
    if analysis_context is None:
        return "null"
    return analysis_context.model_dump_json()
