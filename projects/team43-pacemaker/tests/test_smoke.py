"""스모크 테스트: 인터페이스가 import 가능한지, 진입점이 호출되는지만 확인."""
from agent.graph import run_agent
from schemas import (
    AgentResponse,
    CalendarEvent,
    HealthSnapshot,
    MuscleFatigueState,
    ScheduleProposal,
    WorkoutRecord,
    WorkoutSlot,
)


def test_schemas_importable():
    assert all(
        cls is not None
        for cls in [
            CalendarEvent,
            HealthSnapshot,
            WorkoutRecord,
            WorkoutSlot,
            MuscleFatigueState,
            ScheduleProposal,
            AgentResponse,
        ]
    )


def test_run_agent_returns_response():
    response = run_agent("안녕", session_state={})
    assert isinstance(response, AgentResponse)
    assert response.message
