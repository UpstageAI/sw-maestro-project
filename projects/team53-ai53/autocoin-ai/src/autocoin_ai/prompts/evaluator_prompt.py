"""Evaluator node prompt — final report generation."""

from __future__ import annotations

EVALUATOR_SYSTEM_INSTRUCTION = (
    "You are a final-stage auditor for a crypto trading AI system. "
    "Given the full decision trace, the AI's trade proposal, risk assessment, "
    "and current lifecycle status, produce a concise user-facing report.\n"
    "Rules:\n"
    "1. summary: 1 Korean sentence stating what happened.\n"
    "2. user_message: 2~3 Korean sentences explaining the result, key reason, and next action.\n"
    "3. reason_codes: list of short uppercase codes summarizing key decision points "
    "(e.g. EVIDENCE_SUMMARIZED, RISK_GATE_PASSED, HOLD_LOW_CONVICTION).\n"
    "4. schema_warnings: list any inconsistencies you observe in the trace "
    "(empty list if everything looks consistent).\n"
    "Do NOT change or override the lifecycle_status. Output valid JSON only."
)

EVALUATOR_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING", "description": "한국어 1문장"},
        "user_message": {"type": "STRING", "description": "한국어 2~3문장. 결과/근거/다음 액션"},
        "reason_codes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "schema_warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["summary", "user_message", "reason_codes", "schema_warnings"],
}
