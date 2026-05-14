"""FastAPI 응답용 dataclass 직렬화 유틸."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from models.types import EvaluationResult, Question, Report, SessionState


def question_to_dict(question: Question | None) -> dict[str, Any] | None:
    if question is None:
        return None
    return asdict(question)


def evaluation_to_dict(result: EvaluationResult) -> dict[str, Any]:
    data = asdict(result)

    # feedback은 evaluator가 JSON 문자열로 저장한다. 프론트에서 바로 쓰기 쉽도록
    # 파싱 가능한 경우 feedback_json도 함께 제공한다.
    feedback_raw = data.get("feedback")
    if isinstance(feedback_raw, str):
        try:
            data["feedback_json"] = json.loads(feedback_raw)
        except json.JSONDecodeError:
            data["feedback_json"] = None
    return data


def report_to_dict(report: Report | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return asdict(report)


def session_to_summary(
    session_id: str,
    state: SessionState | None,
    current_question: Question | None,
    busy_job_id: str | None,
) -> dict[str, Any]:
    if state is None:
        return {
            "session_id": session_id,
            "status": "initializing",
            "is_active": False,
            "busy_job_id": busy_job_id,
            "current_question": question_to_dict(current_question),
        }

    return {
        "session_id": session_id,
        "status": "active" if state.is_active else "ended",
        "is_active": state.is_active,
        "busy_job_id": busy_job_id,
        "question_count": state.question_count,
        "bundle_count": state.bundle_count,
        "current_followup_depth": state.current_followup_depth,
        "max_followup_depth": state.max_followup_depth,
        "min_bundles_for_report": state.min_bundles_for_report,
        "can_report": state.bundle_count >= state.min_bundles_for_report and len(state.history) > 0,
        "job_family": state.context.job_family,
        "current_question": question_to_dict(current_question),
    }
