"""KPI 시나리오 테스트 — D(박영준): KPI 1·3 / E(신승민): KPI 2·4·5.

compose_schedule_node / refine_node 직접 호출. OPENAI_API_KEY 필요 (없으면 skip).
pytest -m kpi 로만 실행 (통합·데모 시점).
"""
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from agent.nodes import compose_schedule_node, refine_node
from schemas.models import ScheduleProposal

_NEEDS_OPENAI = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY 없으면 skip"
)

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios"
_SCENARIO_WEEK_START = date(2026, 5, 4)  # 시나리오 JSON 기준 월요일


def _load_scenario(name: str) -> dict:
    return json.loads((SCENARIOS_DIR / name).read_text())


def _shift_to_current_week(scenario: dict) -> dict:
    """시나리오 날짜를 현재 주 월요일 기준으로 조정."""
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    delta_days = (current_week_start - _SCENARIO_WEEK_START).days

    sc = json.loads(json.dumps(scenario))  # deep copy

    def shift_dt(s: str) -> str:
        return (datetime.fromisoformat(s) + timedelta(days=delta_days)).isoformat()

    def shift_d(s: str) -> str:
        return (date.fromisoformat(s) + timedelta(days=delta_days)).isoformat()

    for ev in sc.get("calendar", []):
        ev["start_at"] = shift_dt(ev["start_at"])
        ev["end_at"] = shift_dt(ev["end_at"])
    for h in sc.get("health", []):
        h["date"] = shift_d(h["date"])
    for w in sc.get("workouts", []):
        w["date"] = shift_d(w["date"])

    return sc


def _has_conflict(proposal: ScheduleProposal, calendar: list[dict]) -> list[str]:
    """busy 일정과 겹치는 슬롯 목록 반환. 빈 리스트면 충돌 없음."""
    conflicts = []
    for slot in proposal.slots:
        for ev in calendar:
            if not ev.get("is_busy", True):
                continue
            ev_start = datetime.fromisoformat(ev["start_at"])
            ev_end = datetime.fromisoformat(ev["end_at"])
            if ev_start.date() != slot.start.date():
                continue
            if slot.start < ev_end and slot.end > ev_start:
                conflicts.append(
                    f"{slot.start.date()} {slot.start.strftime('%H:%M')}~"
                    f"{slot.end.strftime('%H:%M')} ↔ {ev_start.strftime('%H:%M')}~{ev_end.strftime('%H:%M')}"
                )
    return conflicts


# ── D(박영준) 담당: KPI 1·3 ──────────────────────────────────────────────


@pytest.mark.kpi
@pytest.mark.asyncio
@_NEEDS_OPENAI
async def test_kpi1_no_schedule_conflict():
    """KPI 1: 10회 생성 시 is_busy 일정과 충돌 0회.

    03_consecutive_muscle 시나리오: 평일 09:00~18:00 busy → 자유 시간 06:00~09:00.
    """
    sc = _shift_to_current_week(_load_scenario("03_consecutive_muscle.json"))
    state = {
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }

    for i in range(10):
        result = await compose_schedule_node(state)
        proposal = ScheduleProposal.model_validate(result["proposal"])
        conflicts = _has_conflict(proposal, sc["calendar"])
        assert not conflicts, f"[{i+1}/10] 충돌 발생:\n" + "\n".join(conflicts)


@pytest.mark.kpi
@pytest.mark.asyncio
@_NEEDS_OPENAI
async def test_kpi3_full_week_short_routine():
    """KPI 3: 빈 시간 없는 주에 10분 대체 루틴 제안.

    01_full_week 시나리오: 매일 06:00~22:00 busy → 자유 시간 0.
    모든 슬롯이 10분 이하 대체 루틴이어야 함.
    """
    sc = _shift_to_current_week(_load_scenario("01_full_week.json"))
    state = {
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }

    result = await compose_schedule_node(state)
    proposal = ScheduleProposal.model_validate(result["proposal"])

    assert len(proposal.slots) == 7, "7일치 슬롯이 모두 있어야 함"
    for slot in proposal.slots:
        duration = int((slot.end - slot.start).total_seconds() / 60)
        assert duration <= 10, (
            f"{slot.start.date()}: {duration}분 슬롯 — 빈 시간 없을 때 10분 이하여야 함"
        )
        assert slot.intensity <= 1, (
            f"{slot.start.date()}: 강도 {slot.intensity} — 대체 루틴은 강도 1 이하여야 함"
        )


# ── E(신승민) 담당: KPI 2·4·5 ──────────────────────────────────────────────


@pytest.mark.kpi
@pytest.mark.asyncio
@_NEEDS_OPENAI
async def test_kpi2_sleep_deprived_low_intensity():
    """KPI 2: 수면 부족(평균 4.1h) → 추천 강도 ≤2.

    02_sleep_deprived 시나리오: 최근 4일 sleep_hours 4.0~4.5h.
    _assess_condition에서 fatigue_flag=True → base_intensity=2.
    """
    sc = _shift_to_current_week(_load_scenario("02_sleep_deprived.json"))
    state = {
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }
    result = await compose_schedule_node(state)
    proposal = ScheduleProposal.model_validate(result["proposal"])

    for slot in proposal.slots:
        assert slot.intensity <= 2, (
            f"{slot.start.date()}: 강도 {slot.intensity} — 수면 부족 시 2 이하"
        )


@pytest.mark.kpi
@pytest.mark.asyncio
@_NEEDS_OPENAI
async def test_kpi2_consecutive_muscle_avoidance():
    """KPI 2: 하체 3일 연속(intensity 3~4) → 하체 추천 0회.

    03_consecutive_muscle 시나리오: 하체 피로도 ≥4.0.
    _select_workout에서 eligible 부위에서 제외.
    """
    sc = _shift_to_current_week(_load_scenario("03_consecutive_muscle.json"))
    original = _load_scenario("03_consecutive_muscle.json")
    must_not = set(original["expected"]["must_not_target"])

    state = {
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }
    result = await compose_schedule_node(state)
    proposal = ScheduleProposal.model_validate(result["proposal"])

    for slot in proposal.slots:
        overlap = set(slot.target_muscles) & must_not
        assert not overlap, (
            f"{slot.start.date()}: {overlap} — 피로도 높아 회피해야 함"
        )


@pytest.mark.kpi
@pytest.mark.asyncio
@_NEEDS_OPENAI
async def test_kpi4_multiturn_only_target_changed():
    """KPI 4: '화요일은 피곤할 것 같아' → 화요일만 변경, 나머지 유지.

    04_multiturn 시나리오: compose → refine 순서.
    refine_node가 화요일 슬롯만 교체하고 나머지 6일은 보존.
    """
    sc = _shift_to_current_week(_load_scenario("04_multiturn.json"))
    state1 = {
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }
    result1 = await compose_schedule_node(state1)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    tuesday = week_start + timedelta(days=1)

    state2 = {
        "user_input": "화요일은 피곤할 것 같아",
        "proposal": result1["proposal"],
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }
    result2 = await refine_node(state2)

    p1 = ScheduleProposal.model_validate(result1["proposal"])
    p2 = ScheduleProposal.model_validate(result2["proposal"])

    slots1 = {s.start.date(): s for s in p1.slots}
    slots2 = {s.start.date(): s for s in p2.slots}

    for d in slots1:
        if d == tuesday:
            continue
        if d in slots2:
            assert slots1[d].target_muscles == slots2[d].target_muscles, (
                f"{d}: 변경 안 된 날 부위가 바뀜 — 유지되어야 함"
            )


@pytest.mark.kpi
@pytest.mark.asyncio
@_NEEDS_OPENAI
async def test_kpi5_fatigue_radar_consistency():
    """KPI 5: 고피로 부위(가슴·삼두) 추천 0회 + fatigue_timeline 7일·7종 부위.

    05_free 시나리오: 가슴·삼두 최근 고강도 운동 → 피로도 ≥4.0.
    proposal에서 해당 부위 미포함 + fatigue_timeline이 레이더 차트 데이터와 일치.
    """
    sc = _shift_to_current_week(_load_scenario("05_free.json"))
    original = _load_scenario("05_free.json")
    must_not = set(original["expected"]["proposal_must_not_target"])

    state = {
        "calendar_data": sc["calendar"],
        "health_data": sc["health"],
        "workouts_data": sc["workouts"],
    }
    result = await compose_schedule_node(state)
    proposal = ScheduleProposal.model_validate(result["proposal"])

    for slot in proposal.slots:
        overlap = set(slot.target_muscles) & must_not
        assert not overlap, (
            f"{slot.start.date()}: {overlap} — 고피로 부위 추천됨"
        )

    assert len(proposal.fatigue_timeline) == 7, "fatigue_timeline 7일치 필요"
    for ft in proposal.fatigue_timeline:
        assert len(ft.fatigue) >= 7, f"{ft.date}: 부위 7종 미만"
