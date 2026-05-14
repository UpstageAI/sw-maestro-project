from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.consultation import (
    ConsultationResponse,
    ConsultationStartResponse,
    FinalPayload,
    PunchlinePayload,
    UserConsultationRequest,
)
from app.workflow.state import build_consultation_response, build_initial_state

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("", response_model=ConsultationStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_consultation(
    payload: UserConsultationRequest,
    request: Request,
) -> ConsultationStartResponse:
    store = request.app.state.store
    broker = request.app.state.broker
    runner = request.app.state.workflow_runner

    existing = await store.get(payload.consultation_id)
    if existing is not None:
        return ConsultationStartResponse(
            consultation_id=existing.consultation_id,
            status=existing.status,
        )

    state = build_initial_state(payload)
    await store.create(state)
    await broker.publish(
        state.consultation_id,
        "status_changed",
        {"status": state.status.value},
    )

    task = asyncio.create_task(
        runner.run(state.consultation_id, state.model_dump(mode="json")),
        name=f"consultation-{state.consultation_id}",
    )
    request.app.state.running_tasks.add(task)
    task.add_done_callback(request.app.state.running_tasks.discard)

    return ConsultationStartResponse(
        consultation_id=state.consultation_id,
        status=state.status,
    )


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(consultation_id: str, request: Request) -> ConsultationResponse:
    state = await request.app.state.store.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="consultation not found")
    return build_consultation_response(state)


@router.post("/{consultation_id}/punchline", response_model=PunchlinePayload)
async def create_punchline(consultation_id: str, request: Request) -> PunchlinePayload:
    """오케스트라(슈퍼바이저)가 최종 보고서를 보고 4명 중 한 명의 톤으로 한 줄 조언을 던진다.

    멱등: 이미 생성됐으면 동일한 결과를 반환.
    """
    store = request.app.state.store
    llm = request.app.state.llm_client

    state = await store.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="consultation not found")

    if state.punchline is not None:
        return state.punchline

    if state.final_summary is None:
        raise HTTPException(
            status_code=409,
            detail="final summary not ready; wait for workflow to complete",
        )

    # final_summary.payload는 dict로 저장돼 있으니 FinalPayload로 변환.
    final_payload = FinalPayload.model_validate(state.final_summary.payload)
    punchline = await llm.create_punchline(state.user_question, final_payload)

    async def mutate(stored):
        stored.punchline = punchline

    await store.mutate(consultation_id, mutate)
    return punchline
