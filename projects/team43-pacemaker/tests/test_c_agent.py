"""C 슬라이스 (이유준) — Agent 스모크 테스트."""
import datetime
import os

import pytest

from agent.graph import run_agent, run_agent_stream
from agent.nodes import compose_schedule_node, refine_node
from agent.prompts import SYSTEM_PROMPT
from schemas.models import AgentResponse, ChatChunk, MuscleFatigueState, ScheduleProposal

# ── API 키 가드 ───────────────────────────────────────────────────────────────

_requires_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY 없으면 skip",
)

# ── 프롬프트 & 스키마 정적 검사 ───────────────────────────────────────────────

def test_system_prompt_has_react_steps():
    """시스템 프롬프트에 ReAct 3단계 키워드가 모두 포함되어야 한다."""
    assert "get_calendar" in SYSTEM_PROMPT
    assert "get_health" in SYSTEM_PROMPT
    assert "get_workouts" in SYSTEM_PROMPT


# ── 스트림 기본 동작 (5/5 합격 기준) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_agent_stream_yields_chunks():
    """`run_agent_stream`이 ChatChunk를 yield하는 async iterator여야 한다."""
    chunks = []
    async for chunk in run_agent_stream("테스트 입력", thread_id="test-thread"):
        assert isinstance(chunk, ChatChunk)
        chunks.append(chunk)

    assert len(chunks) > 0, "청크가 하나도 없음"
    types = [c.type for c in chunks]
    assert "done" in types, "done 청크가 없음"


@pytest.mark.asyncio
async def test_run_agent_stream_done_has_thread_id():
    """done 청크의 payload에 thread_id가 있어야 한다."""
    thread_id = "my-thread-123"
    async for chunk in run_agent_stream("입력", thread_id=thread_id):
        if chunk.type == "done":
            assert chunk.payload.get("thread_id") == thread_id
            break


@pytest.mark.asyncio
async def test_run_agent_stream_default_thread_id():
    """thread_id를 넘기지 않아도 done 청크에 thread_id가 있어야 한다."""
    async for chunk in run_agent_stream("입력"):
        if chunk.type == "done":
            assert chunk.payload.get("thread_id")
            break


@pytest.mark.asyncio
async def test_react_three_tool_calls_emitted():
    """ReAct 3단계 tool_call 청크가 순서대로 나와야 한다."""
    tool_calls = []
    async for chunk in run_agent_stream("이번 주 운동 짜줘", thread_id="flow-test"):
        if chunk.type == "tool_call":
            tool_calls.append(chunk.payload["name"])

    assert tool_calls == ["get_calendar", "get_health", "get_workouts"], (
        f"예상 순서와 다름: {tool_calls}"
    )


@pytest.mark.asyncio
async def test_proposal_chunk_emitted():
    """스케줄 도출 후 proposal 청크가 나와야 한다."""
    async for chunk in run_agent_stream("이번 주 운동 짜줘", thread_id="proposal-test"):
        if chunk.type == "proposal":
            assert "slots" in chunk.payload, "slots 키 없음"
            return
    pytest.fail("proposal 청크가 emit되지 않았음")


@pytest.mark.asyncio
async def test_full_flow_order():
    """tool_call 3개 → proposal → done 순서로 emit되어야 한다."""
    sequence = []
    async for chunk in run_agent_stream("이번 주 운동 짜줘", thread_id="order-test"):
        sequence.append(chunk.type)

    assert sequence.count("tool_call") == 3, f"tool_call 3개 예상, 실제: {sequence}"
    assert sequence.index("proposal") > sequence.index("tool_call"), "proposal이 tool_call 전에 나옴"
    assert sequence[-1] == "done", "마지막 청크가 done이 아님"


def test_run_agent_returns_agent_response():
    """run_agent(비스트림)가 AgentResponse를 반환해야 한다."""
    response = run_agent("안녕", session_state={})
    assert isinstance(response, AgentResponse)


# ── 5/6 합격 기준: 의미 있는 ScheduleProposal 도출 (LLM 필요) ────────────────

@_requires_key
@pytest.mark.asyncio
async def test_compose_schedule_no_free_time_gives_alternative():
    """빈 시간이 없는 날은 10분 대체 루틴이 포함되어야 한다 (KPI #3)."""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    monday = week_start

    calendar = [{
        "start_at": datetime.datetime(monday.year, monday.month, monday.day, 6, 0).isoformat(),
        "end_at": datetime.datetime(monday.year, monday.month, monday.day, 22, 0).isoformat(),
        "is_busy": True,
    }]
    state = {"calendar_data": calendar, "health_data": [], "workouts_data": [], "user_input": ""}
    result = await compose_schedule_node(state)

    proposal = ScheduleProposal.model_validate(result["proposal"])
    monday_slots = [s for s in proposal.slots if s.start.date() == monday]
    assert len(monday_slots) == 1
    assert monday_slots[0].intensity == 1
    duration = int((monday_slots[0].end - monday_slots[0].start).total_seconds() / 60)
    assert duration <= 10


@_requires_key
@pytest.mark.asyncio
async def test_compose_schedule_proposal_has_all_muscles_in_fatigue():
    """fatigue_timeline의 각 항목이 7개 부위를 모두 가져야 한다 (KPI #5)."""
    state = {"calendar_data": [], "health_data": [], "workouts_data": [], "user_input": ""}
    result = await compose_schedule_node(state)
    proposal = ScheduleProposal.model_validate(result["proposal"])

    assert len(proposal.fatigue_timeline) == 7
    for ft in proposal.fatigue_timeline:
        for muscle in ["가슴", "등", "하체", "어깨", "코어", "이두", "삼두"]:
            assert muscle in ft.fatigue, f"{ft.date}: {muscle} 누락"


@_requires_key
@pytest.mark.asyncio
async def test_compose_schedule_no_conflict_with_busy():
    """추천 슬롯이 is_busy=True 일정과 겹치지 않아야 한다 (KPI #1)."""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    monday = week_start

    calendar = [{
        "start_at": datetime.datetime(monday.year, monday.month, monday.day, 9, 0).isoformat(),
        "end_at": datetime.datetime(monday.year, monday.month, monday.day, 18, 0).isoformat(),
        "is_busy": True,
    }]
    state = {"calendar_data": calendar, "health_data": [], "workouts_data": [], "user_input": ""}
    result = await compose_schedule_node(state)
    proposal = ScheduleProposal.model_validate(result["proposal"])

    busy_start = datetime.datetime(monday.year, monday.month, monday.day, 9, 0)
    busy_end = datetime.datetime(monday.year, monday.month, monday.day, 18, 0)
    for slot in proposal.slots:
        if slot.start.date() == monday:
            no_overlap = slot.end <= busy_start or slot.start >= busy_end
            assert no_overlap, f"충돌 발생: {slot.start}~{slot.end}"


# ── 5/7 합격 기준: 멀티턴 재조정 ─────────────────────────────────────────────

@_requires_key
@pytest.mark.asyncio
async def test_refine_node_replaces_only_target_day():
    """refine_node는 지정 요일 슬롯만 교체해야 한다 (KPI #4)."""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    tuesday = week_start + datetime.timedelta(days=1)

    initial_result = await compose_schedule_node({
        "calendar_data": [], "health_data": [], "workouts_data": [], "user_input": "",
    })
    proposal = ScheduleProposal.model_validate(initial_result["proposal"])
    original_dates = {s.start.date() for s in proposal.slots}

    state = {
        "user_input": "화요일 운동 바꿔줘",
        "proposal": initial_result["proposal"],
        "calendar_data": [],
        "health_data": [],
        "workouts_data": [],
    }
    result = await refine_node(state)
    refined = ScheduleProposal.model_validate(result["proposal"])

    assert len(refined.slots) == 7, "슬롯 수가 7개여야 함"
    refined_by_date = {s.start.date(): s for s in refined.slots}
    original_by_date = {s.start.date(): s for s in proposal.slots}

    for d in original_dates:
        if d == tuesday:
            continue
        assert d in refined_by_date, f"{d} 슬롯이 사라짐"
        # 날짜 기준으로 다른 요일 슬롯이 그대로 유지되는지 확인
        assert refined_by_date[d].start.date() == original_by_date[d].start.date(), (
            f"{d}: 변경되면 안 되는 슬롯 날짜가 바뀜"
        )


# ── 5/8 합격 기준: 실제 GPT 호출 ─────────────────────────────────────────────

@_requires_key
@pytest.mark.asyncio
async def test_multiturn_second_call_is_refine_mode():
    """같은 thread_id 두 번째 호출은 tool_call 없이 proposal만 emit해야 한다."""
    tid = "multiturn-refine-mode-test"
    async for _ in run_agent_stream("이번 주 운동 짜줘", thread_id=tid):
        pass

    chunks = []
    async for chunk in run_agent_stream("화요일은 피곤할 것 같아서 쉬고 싶어", thread_id=tid):
        chunks.append(chunk)

    types = [c.type for c in chunks]
    assert "tool_call" not in types, f"재조정에서 tool_call이 나옴: {types}"
    assert "proposal" in types, "재조정에서 proposal이 없음"
    assert types[-1] == "done"


@_requires_key
@pytest.mark.asyncio
async def test_multiturn_second_proposal_has_seven_slots():
    """재조정 후 proposal도 7개 슬롯을 가져야 한다."""
    tid = "multiturn-seven-slots-test"
    async for _ in run_agent_stream("이번 주 운동 짜줘", thread_id=tid):
        pass

    second_proposal = None
    async for chunk in run_agent_stream("화요일 운동 바꿔줘", thread_id=tid):
        if chunk.type == "proposal":
            second_proposal = chunk.payload

    assert second_proposal is not None
    assert len(second_proposal["slots"]) == 7


@_requires_key
@pytest.mark.asyncio
async def test_llm_think_node_emits_tool_calls_in_order():
    """실제 LLM이 ReAct 3단계를 순서대로 판단해야 한다."""
    tool_calls = []
    async for chunk in run_agent_stream("이번 주 운동 짜줘", thread_id="llm-react-test"):
        if chunk.type == "tool_call":
            tool_calls.append(chunk.payload["name"])

    assert tool_calls == ["get_calendar", "get_health", "get_workouts"], (
        f"LLM ReAct 순서 틀림: {tool_calls}"
    )


@_requires_key
@pytest.mark.asyncio
async def test_llm_response_includes_text_chunk():
    """실제 GPT 응답 텍스트가 text 청크로 도달해야 한다 (5/8 end-to-end 기준)."""
    text_chunks = []
    async for chunk in run_agent_stream("이번 주 운동 짜줘", thread_id="llm-text-test"):
        if chunk.type == "text":
            text_chunks.append(chunk.payload.get("delta", ""))

    assert text_chunks, "text 청크가 없음"
    full_text = "".join(text_chunks)
    assert len(full_text) > 10, f"텍스트가 너무 짧음: {full_text!r}"


@_requires_key
@pytest.mark.asyncio
async def test_llm_full_flow_order():
    """실제 LLM: tool_call(3) → text → proposal → done 순서."""
    sequence = []
    async for chunk in run_agent_stream("이번 주 운동 짜줘", thread_id="llm-order-test"):
        sequence.append(chunk.type)

    assert sequence.count("tool_call") == 3
    assert "text" in sequence
    assert "proposal" in sequence
    assert sequence.index("text") < sequence.index("proposal"), "text가 proposal 앞에 와야 함"
    assert sequence[-1] == "done"
