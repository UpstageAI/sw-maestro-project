"""E 슬라이스 — 시나리오 5종 end-to-end 검증 (mock 데이터 주입).

OPENAI_API_KEY 필요 (LLM 호출 포함). 없으면 skip.
Supabase 불필요 — agent.tools의 _get_* 함수를 mock해서 시나리오 JSON 데이터 주입.

5/9 test_kpi.py 정식화 전 단계 검증.
"""
import asyncio
import json
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from schemas.models import (
    CalendarEvent,
    HealthSnapshot,
    ScheduleProposal,
    WorkoutRecord,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for LLM-based e2e tests",
)

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios"


def _load_scenario(name: str) -> dict:
    return json.loads((SCENARIOS_DIR / name).read_text())


def _to_calendar(raw: list[dict]) -> list[CalendarEvent]:
    return [CalendarEvent.model_validate(r) for r in raw]


def _to_health(raw: list[dict]) -> list[HealthSnapshot]:
    return [HealthSnapshot.model_validate(r) for r in raw]


def _to_workouts(raw: list[dict]) -> list[WorkoutRecord]:
    return [WorkoutRecord.model_validate(r) for r in raw]


def _run_with_mock(
    scenario: dict, user_input: str, thread_id: str
) -> dict | None:
    """시나리오 데이터를 mock으로 주입해 agent 실행, proposal dict 반환."""
    from agent.graph import run_agent_stream

    cal = _to_calendar(scenario.get("calendar", []))
    hlth = _to_health(scenario.get("health", []))
    wkt = _to_workouts(scenario.get("workouts", []))

    async def _run() -> dict | None:
        proposal = None
        async for chunk in run_agent_stream(user_input, thread_id=thread_id):
            if chunk.type == "proposal":
                proposal = chunk.payload
            elif chunk.type == "error":
                pytest.fail(f"agent error: {chunk.payload.get('message')}")
        return proposal

    with (
        patch("agent.tools._get_calendar", return_value=cal),
        patch("agent.tools._get_health", return_value=hlth),
        patch("agent.tools._get_workouts", return_value=wkt),
    ):
        return asyncio.run(_run())


# ── 01: 꽉 찬 일주일 → 10분 대체 루틴 (KPI 3) ──

def test_01_full_week_short_routine():
    sc = _load_scenario("01_full_week.json")
    proposal = _run_with_mock(sc, "이번 주 운동 일정 짜줘", "e2e-01")
    assert proposal, "proposal이 생성되어야 함"

    p = ScheduleProposal.model_validate(proposal)
    for slot in p.slots:
        duration = int((slot.end - slot.start).total_seconds() / 60)
        assert duration <= 10, f"{slot.start.date()}: {duration}분 — 10분 이하여야 함"
        assert slot.intensity <= 1, f"{slot.start.date()}: 강도 {slot.intensity} — 1 이하여야 함"


# ── 02: 수면 부족 → 강도 하향 (KPI 2) ──

def test_02_sleep_deprived_low_intensity():
    sc = _load_scenario("02_sleep_deprived.json")
    proposal = _run_with_mock(sc, "이번 주 운동 일정 짜줘", "e2e-02")
    assert proposal, "proposal이 생성되어야 함"

    p = ScheduleProposal.model_validate(proposal)
    for slot in p.slots:
        assert slot.intensity <= 2, f"{slot.start.date()}: 강도 {slot.intensity} — 수면 부족 시 2 이하"


# ── 03: 같은 부위 3일 연속 → 회피 (KPI 2) ──

def test_03_consecutive_muscle_avoidance():
    sc = _load_scenario("03_consecutive_muscle.json")
    proposal = _run_with_mock(sc, "이번 주 운동 일정 짜줘", "e2e-03")
    assert proposal, "proposal이 생성되어야 함"

    p = ScheduleProposal.model_validate(proposal)
    must_not = set(sc["expected"]["must_not_target"])
    for slot in p.slots:
        targeted = set(slot.target_muscles)
        assert not (targeted & must_not), (
            f"{slot.start.date()}: {targeted & must_not} 부위가 추천됨 — 피로도 높아 회피해야 함"
        )


# ── 04: 멀티턴 재조정 (KPI 4) ──

def test_04_multiturn_tuesday_change():
    sc = _load_scenario("04_multiturn.json")
    turns = sc.get("turns", [])
    assert len(turns) >= 2, "시나리오에 2턴 이상 필요"

    tid = "e2e-04-multiturn"
    proposal1 = _run_with_mock(sc, turns[0]["content"], tid)
    assert proposal1, "1턴 proposal이 생성되어야 함"

    proposal2 = _run_with_mock(sc, turns[1]["content"], tid)
    assert proposal2, "2턴 proposal이 생성되어야 함"

    p1 = ScheduleProposal.model_validate(proposal1)
    p2 = ScheduleProposal.model_validate(proposal2)

    changed_dates = {date.fromisoformat(d) for d in sc["expected"]["changed_dates"]}
    slots1 = {s.start.date(): s for s in p1.slots}
    slots2 = {s.start.date(): s for s in p2.slots}

    for d in slots1:
        if d in changed_dates:
            continue
        if d in slots2:
            assert slots1[d].target_muscles == slots2[d].target_muscles, (
                f"{d}: 변경 안 된 날의 부위가 바뀜 — 유지되어야 함"
            )


# ── 05: 추천 부위 ↔ 레이더 일치 (KPI 5) ──

def test_05_fatigue_radar_consistency():
    sc = _load_scenario("05_free.json")
    proposal = _run_with_mock(sc, "이번 주 운동 일정 짜줘", "e2e-05")
    assert proposal, "proposal이 생성되어야 함"

    p = ScheduleProposal.model_validate(proposal)
    must_not = set(sc["expected"]["proposal_must_not_target"])
    for slot in p.slots:
        targeted = set(slot.target_muscles)
        assert not (targeted & must_not), (
            f"{slot.start.date()}: {targeted & must_not} — 고피로 부위 추천됨"
        )

    assert len(p.fatigue_timeline) == 7, "fatigue_timeline 7일치 필요"
