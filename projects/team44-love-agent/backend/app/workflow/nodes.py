from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.errors import to_public_error
from app.schemas.consultation import (
    AGENT_NAMES,
    ROUND_1_AGENT_ORDER,
    SEQUENTIAL_AGENT_ORDER,
    AgentFinalPosition,
    AgentId,
    AgentOpinion,
    AgentRebuttal,
    ConsultationState,
    ConsultationStatus,
    ErrorCode,
    ErrorEvent,
    Termination,
    TerminationReason,
    SupervisorNote,
    TargetReference,
    AgreementType,
    utc_now_iso,
)
from app.services.event_broker import EventBroker
from app.services.llm_client import LLMClient, LLMOutputError
from app.store.memory import MemoryStore
from app.workflow.classification import normalize_classify_payload
from app.workflow.state import build_consultation_response
from pydantic import ValidationError


logger = logging.getLogger(__name__)


class WorkflowNodes:
    def __init__(self, store: MemoryStore, broker: EventBroker, llm: LLMClient) -> None:
        self.store = store
        self.broker = broker
        self.llm = llm

    async def analyze_question(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ANALYZING)
        current = await self._require_state(consultation_id)
        analysis = await self.llm.analyze_question(consultation_id, current.user_question)

        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "analysis", analysis))
        await self.broker.publish(
            consultation_id,
            "analysis_completed",
            {"analysis": analysis.model_dump(mode="json")},
        )
        return {"analysis": analysis.model_dump(mode="json")}

    async def run_round_1(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ROUND_1_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None:
            raise RuntimeError("analysis is required before round_1")

        drafts = await asyncio.gather(
            *[
                self.llm.create_agent_opinion(agent_id, current.user_question, current.analysis)
                for agent_id in ROUND_1_AGENT_ORDER
            ]
        )
        opinions = [
            AgentOpinion(
                consultation_id=consultation_id,
                agent_id=agent_id,
                agent_name=AGENT_NAMES[agent_id],
                **draft.model_dump(),
            )
            for agent_id, draft in zip(ROUND_1_AGENT_ORDER, drafts, strict=True)
        ]

        async def mutate(stored: ConsultationState) -> None:
            stored.round_1_opinions.extend(opinions)

        await self.store.mutate(consultation_id, mutate)
        for opinion in opinions:
            await self.broker.publish(
                consultation_id,
                "agent_message_added",
                {"round": "round_1", "message": opinion.model_dump(mode="json")},
            )
        return {"round_1_opinions": [opinion.model_dump(mode="json") for opinion in opinions]}

    async def summarize_round_1(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.SUMMARY_1_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None:
            raise RuntimeError("analysis is required before summary_1")
        payload = await self.llm.summarize_round_1(
            current.user_question,
            current.analysis,
            current.round_1_opinions,
        )
        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="summary_1",
            payload=payload.model_dump(mode="json"),
        )
        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "summary_1", note))
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        return {"summary_1": note.model_dump(mode="json")}

    async def run_round_2(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ROUND_2_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None or current.summary_1 is None:
            raise RuntimeError("analysis and summary_1 are required before round_2")
        rebuttals: list[AgentRebuttal] = []

        for index, agent_id in enumerate(SEQUENTIAL_AGENT_ORDER):
            # 자기 자신의 1라운드 의견을 타겟으로 잡지 않도록 다른 에이전트 의견에서 선택.
            others = [o for o in current.round_1_opinions if o.agent_id != agent_id]
            if others:
                target_opinion = others[index % len(others)]
            else:
                target_opinion = current.round_1_opinions[index % len(current.round_1_opinions)]
            target = TargetReference(
                target_message_id=target_opinion.id,
                target_agent_id=target_opinion.agent_id,
                agreement=AgreementType.DISAGREE,
            )
            draft = await self.llm.create_agent_rebuttal(
                agent_id,
                current.user_question,
                current.analysis,
                current.summary_1,
                target_opinion,
                target,
                rebuttals,
            )
            rebuttal = AgentRebuttal(
                consultation_id=consultation_id,
                agent_id=agent_id,
                agent_name=AGENT_NAMES[agent_id],
                **draft.model_dump(),
            )
            self._validate_rebuttal_targets(rebuttal, current.round_1_opinions)
            rebuttals.append(rebuttal)

            async def mutate(stored: ConsultationState, item: AgentRebuttal = rebuttal) -> None:
                stored.round_2_rebuttals.append(item)

            await self.store.mutate(consultation_id, mutate)
            await self.broker.publish(
                consultation_id,
                "agent_message_added",
                {"round": "round_2", "message": rebuttal.model_dump(mode="json")},
            )

        return {"round_2_rebuttals": [item.model_dump(mode="json") for item in rebuttals]}

    async def classify_round_2(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.CLASSIFY_2_RUNNING)
        current = await self._require_state(consultation_id)
        if current.summary_1 is None:
            raise RuntimeError("summary_1 is required before classify_2")
        payload = await self.llm.classify_round_2(current.summary_1, current.round_2_rebuttals)
        payload = normalize_classify_payload(
            payload,
            valid_message_ids={
                item.id for item in [*current.round_1_opinions, *current.round_2_rebuttals]
            },
        )
        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="classify_2",
            payload=payload.model_dump(mode="json"),
        )
        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "classify_2", note))
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        return {"classify_2": note.model_dump(mode="json")}

    async def mark_consensus_reached(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        termination = Termination(
            reason=TerminationReason.CONSENSUS_REACHED,
            occurred_at=utc_now_iso(),
            notes="classify_2.payload.next_action == skip_to_final",
        )
        await self.store.mutate(
            consultation_id,
            lambda stored: setattr(stored, "termination", termination),
        )
        return {"termination": termination.model_dump(mode="json")}

    async def run_round_3(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.ROUND_3_RUNNING)
        current = await self._require_state(consultation_id)
        if current.analysis is None or current.summary_1 is None or current.classify_2 is None:
            raise RuntimeError("analysis, summary_1, and classify_2 are required before round_3")
        positions: list[AgentFinalPosition] = []

        for agent_id in SEQUENTIAL_AGENT_ORDER:
            draft = await self.llm.create_agent_final_position(
                agent_id,
                current.user_question,
                current.analysis,
                current.summary_1,
                current.classify_2,
                self._find_opinion(current.round_1_opinions, agent_id),
                self._find_rebuttal(current.round_2_rebuttals, agent_id),
                positions,
            )
            position = AgentFinalPosition(
                consultation_id=consultation_id,
                agent_id=agent_id,
                agent_name=AGENT_NAMES[agent_id],
                **draft.model_dump(),
            )
            positions.append(position)

            async def mutate(stored: ConsultationState, item: AgentFinalPosition = position) -> None:
                stored.round_3_positions.append(item)

            await self.store.mutate(consultation_id, mutate)
            await self.broker.publish(
                consultation_id,
                "agent_message_added",
                {"round": "round_3", "message": position.model_dump(mode="json")},
            )

        return {"round_3_positions": [item.model_dump(mode="json") for item in positions]}

    async def finalize(self, state: dict[str, Any]) -> dict[str, Any]:
        consultation_id = state["consultation_id"]
        await self._set_status(consultation_id, ConsultationStatus.SUMMARIZING)
        current = await self._require_state(consultation_id)
        payload = await self.llm.create_final_summary(
            current.user_question,
            current.analysis,
            current.summary_1,
            current.classify_2,
            current.round_3_positions,
            current.round_2_rebuttals,
        )
        note = SupervisorNote(
            consultation_id=consultation_id,
            mode="final",
            payload=payload.model_dump(mode="json"),
        )

        async def mutate(stored: ConsultationState) -> None:
            stored.final_summary = note
            stored.status = (
                ConsultationStatus.TERMINATED
                if stored.termination is not None
                else ConsultationStatus.COMPLETED
            )
            stored.completed_at = stored.updated_at

        updated, _ = await self.store.mutate(consultation_id, mutate)
        await self.broker.publish(
            consultation_id,
            "supervisor_note_added",
            {"note": note.model_dump(mode="json")},
        )
        await self.broker.publish(
            consultation_id,
            "status_changed",
            {"status": updated.status.value},
        )
        await self.broker.publish(
            consultation_id,
            "completed",
            {"response": build_consultation_response(updated).model_dump(mode="json")},
        )
        return {
            "final_summary": note.model_dump(mode="json"),
            "status": updated.status.value,
            "completed_at": updated.completed_at,
        }

    async def handle_failure(self, consultation_id: str, exc: Exception) -> None:
        error = _error_event_from_exception(exc)
        logger.error(
            "consultation workflow failed",
            extra={
                "consultation_id": consultation_id,
                "error_code": error.code.value,
                "where": error.where,
                "retry_count": error.retry_count,
            },
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        async def mutate(stored: ConsultationState) -> None:
            stored.errors.append(error)
            stored.status = ConsultationStatus.FAILED
            stored.completed_at = stored.updated_at

        await self.store.mutate(consultation_id, mutate)
        await self.broker.publish(
            consultation_id,
            "error_occurred",
            {"error": to_public_error(error).model_dump(mode="json")},
        )
        await self.broker.publish(
            consultation_id,
            "status_changed",
            {"status": ConsultationStatus.FAILED.value},
        )

    async def _set_status(self, consultation_id: str, status: ConsultationStatus) -> None:
        await self.store.mutate(consultation_id, lambda stored: setattr(stored, "status", status))
        await self.broker.publish(consultation_id, "status_changed", {"status": status.value})

    async def _require_state(self, consultation_id: str) -> ConsultationState:
        state = await self.store.get(consultation_id)
        if state is None:
            raise RuntimeError(f"consultation not found: {consultation_id}")
        return state

    @staticmethod
    def _validate_rebuttal_targets(
        rebuttal: AgentRebuttal,
        round_1_opinions: list[AgentOpinion],
    ) -> None:
        opinions_by_id = {opinion.id: opinion for opinion in round_1_opinions}
        for target in rebuttal.targets:
            opinion = opinions_by_id.get(target.target_message_id)
            if opinion is None:
                raise ValueError(f"unknown target_message_id: {target.target_message_id}")
            if opinion.agent_id != target.target_agent_id:
                raise ValueError(
                    "target_agent_id does not match target_message_id: "
                    f"{target.target_agent_id} != {opinion.agent_id}"
                )
            # 자기 자신을 반박 대상으로 삼지 않도록 거절 (자기 1라운드 의견 대상 금지).
            if opinion.agent_id == rebuttal.agent_id:
                raise ValueError(
                    f"agent {rebuttal.agent_id} cannot target its own round_1 opinion"
                )

    @staticmethod
    def _find_opinion(opinions: list[AgentOpinion], agent_id: AgentId) -> AgentOpinion | None:
        return next((opinion for opinion in opinions if opinion.agent_id == agent_id), None)

    @staticmethod
    def _find_rebuttal(rebuttals: list[AgentRebuttal], agent_id: AgentId) -> AgentRebuttal | None:
        return next((rebuttal for rebuttal in rebuttals if rebuttal.agent_id == agent_id), None)


def _error_event_from_exception(exc: Exception) -> ErrorEvent:
    if isinstance(exc, LLMOutputError):
        return ErrorEvent(
            code=exc.code,
            where=f"llm:{exc.task}",
            detail=exc.detail,
            retry_count=exc.retry_count,
            fatal=True,
        )

    if isinstance(exc, ValidationError):
        return ErrorEvent(
            code=ErrorCode.SCHEMA_VIOLATION,
            where="workflow:schema_validation",
            detail=str(exc),
            fatal=True,
        )

    detail = str(exc)
    if _is_schema_boundary_error(detail):
        return ErrorEvent(
            code=ErrorCode.SCHEMA_VIOLATION,
            where=_infer_schema_error_where(detail),
            detail=detail,
            fatal=True,
        )

    return ErrorEvent(
        code=ErrorCode.UNKNOWN,
        where="workflow",
        detail=detail,
        fatal=True,
    )


def _is_schema_boundary_error(detail: str) -> bool:
    schema_error_markers = (
        "unknown target_message_id",
        "target_agent_id does not match target_message_id",
        "supporting_message_ids",
        "validation error",
    )
    return any(marker in detail for marker in schema_error_markers)


def _infer_schema_error_where(detail: str) -> str:
    if "target_message_id" in detail or "target_agent_id" in detail:
        return "workflow:round_2_target_reference"
    if "supporting_message_ids" in detail:
        return "workflow:classify_2_supporting_ids"
    return "workflow:schema_validation"
