#!/usr/bin/env python3
"""KPI 시나리오 씨딩 스크립트.

사용법:
    python data/seed_scenario.py <시나리오 번호>

예시:
    python data/seed_scenario.py 1   # KPI 3 테스트 (빈 시간 없는 주)
    python data/seed_scenario.py 3   # KPI 1+2 테스트 (충돌 0회 + 하체 회피)

동작:
    1. calendar_events / health_snapshots / workout_records 테이블 전체 삭제
    2. 해당 시나리오 JSON 데이터를 현재 주 날짜로 조정 후 Supabase에 삽입
    3. 채팅 UI에서 '이번 주 운동 추천해줘'를 입력하면 KPI 검증 가능

사전 요건:
    - .env에 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 설정
    - pip install supabase python-dotenv (requirements.txt에 포함됨)

KPI 시나리오 목록:
    1 → KPI 3  : 꽉 찬 일주일 (01_full_week)
                 검증: 모든 슬롯이 10분 이하 대체 루틴인지 확인
    2 → KPI 2a : 수면 부족 (02_sleep_deprived)
                 검증: 추천 강도가 모두 ≤2인지 확인
    3 → KPI 1+2b: 하체 연속 운동 (03_consecutive_muscle)
                 검증: 일정 충돌 없는지 + 하체가 target_muscles에 없는지 확인
    4 → KPI 4  : 멀티턴 재조정 (04_multiturn)
                 검증: 1턴 추천 후 '화요일은 피곤할 것 같아' 입력 → 화요일 슬롯만 변경
    5 → KPI 5  : 고피로 부위 (05_free)
                 검증: 가슴·삼두 미포함 + FE 레이더 차트 색상 변화 확인
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
_SCENARIO_WEEK_START = date(2026, 5, 4)  # 시나리오 JSON 기준 월요일

SCENARIO_MAP = {
    1: ("01_full_week.json",          "KPI 3  — 꽉 찬 일주일 → 10분 대체 루틴"),
    2: ("02_sleep_deprived.json",     "KPI 2a — 수면 부족 → 추천 강도 ≤2"),
    3: ("03_consecutive_muscle.json", "KPI 1+2b — 일정 충돌 0회 + 하체 회피"),
    4: ("04_multiturn.json",          "KPI 4  — 멀티턴 재조정 (화요일만 변경)"),
    5: ("05_free.json",               "KPI 5  — 고피로 부위 추천 0회 + 레이더"),
}

VERIFY_HINTS = {
    1: [
        "채팅: '이번 주 운동 추천해줘'",
        "모든 슬롯이 10분 이하 대체 루틴(홈트)인지 확인",
        "강도 1 이하인지 확인",
    ],
    2: [
        "채팅: '이번 주 운동 추천해줘'",
        "모든 슬롯의 강도(intensity)가 2 이하인지 확인",
    ],
    3: [
        "채팅: '이번 주 운동 추천해줘'",
        "평일 09:00~18:00 busy 일정과 겹치는 슬롯 없는지 확인",
        "어떤 슬롯에도 '하체'가 target_muscles에 없는지 확인",
    ],
    4: [
        "채팅 1턴: '이번 주 운동 일정 짜줘'  → 7일 스케줄 확인",
        "채팅 2턴: '화요일은 피곤할 것 같아'  → 화요일 슬롯만 변경되는지 확인",
        "나머지 6일 슬롯은 1턴과 동일한지 확인",
    ],
    5: [
        "채팅: '이번 주 운동 추천해줘'",
        "가슴, 삼두가 target_muscles에 포함된 슬롯 없는지 확인",
        "FE 레이더 차트에서 가슴·삼두 부위 색상이 높은 피로도로 표시되는지 확인",
    ],
}


def _shift_to_current_week(scenario: dict) -> dict:
    """시나리오 날짜를 현재 주 월요일 기준으로 조정."""
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    delta = (current_week_start - _SCENARIO_WEEK_START).days

    sc = json.loads(json.dumps(scenario))

    for ev in sc.get("calendar", []):
        ev["start_at"] = (datetime.fromisoformat(ev["start_at"]) + timedelta(days=delta)).isoformat()
        ev["end_at"] = (datetime.fromisoformat(ev["end_at"]) + timedelta(days=delta)).isoformat()
    for h in sc.get("health", []):
        h["date"] = (date.fromisoformat(h["date"]) + timedelta(days=delta)).isoformat()
    for w in sc.get("workouts", []):
        w["date"] = (date.fromisoformat(w["date"]) + timedelta(days=delta)).isoformat()

    return sc


def _shift_workouts_to_recent(sc: dict) -> dict:
    """workout 날짜를 오늘 기준 최근으로 추가 조정.

    프롬프트의 '최근 N일' 규칙이 동작하려면 workout이 오늘과 가까워야 한다.
    시나리오의 가장 마지막 workout이 어제(today-1)에 오도록 delta를 계산.
    calendar/health 날짜는 그대로 유지.
    """
    if not sc.get("workouts"):
        return sc

    sc = json.loads(json.dumps(sc))
    last_date = max(date.fromisoformat(w["date"]) for w in sc["workouts"])
    delta = (date.today() - timedelta(days=1) - last_date).days

    if delta == 0:
        return sc

    for w in sc["workouts"]:
        w["date"] = (date.fromisoformat(w["date"]) + timedelta(days=delta)).isoformat()

    return sc


def _get_client():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("❌ .env에 SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")
        print("   .env.example을 참고해 .env 파일을 설정하세요.")
        sys.exit(1)
    return create_client(url, key)


def _print_usage() -> None:
    print("사용법: python data/seed_scenario.py <1~5>")
    print()
    for n, (_, desc) in SCENARIO_MAP.items():
        print(f"  {n}: {desc}")


def seed(scenario_num: int) -> None:
    if scenario_num not in SCENARIO_MAP:
        print(f"❌ 시나리오 번호는 1~5 중 하나여야 합니다. (입력: {scenario_num})")
        _print_usage()
        sys.exit(1)

    filename, description = SCENARIO_MAP[scenario_num]
    raw = json.loads((SCENARIOS_DIR / filename).read_text(encoding="utf-8"))
    sc = _shift_workouts_to_recent(_shift_to_current_week(raw))
    client = _get_client()

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    print(f"\n{'=' * 60}")
    print(f"  시나리오 {scenario_num}: {description}")
    print(f"  대상 주: {week_start} ~ {week_end}")
    print(f"{'=' * 60}")

    # 1. 기존 데이터 삭제
    print("\n[1/2] 기존 데이터 삭제 중...")
    tables = ["calendar_events", "health_snapshots", "workout_records"]
    for table in tables:
        client.table(table).delete().gte("id", 1).execute()
        print(f"      🗑️  {table} 삭제 완료")

    # 2. 시나리오 데이터 삽입
    print("\n[2/2] 시나리오 데이터 삽입 중...")

    if sc.get("calendar"):
        client.table("calendar_events").insert(sc["calendar"]).execute()
        print(f"      📅 calendar_events : {len(sc['calendar'])}건")

    if sc.get("health"):
        client.table("health_snapshots").insert(sc["health"]).execute()
        print(f"      ❤️  health_snapshots: {len(sc['health'])}건")

    if sc.get("workouts"):
        client.table("workout_records").insert(sc["workouts"]).execute()
        print(f"      🏋️  workout_records  : {len(sc['workouts'])}건")

    # 3. 검증 안내
    print(f"\n{'=' * 60}")
    print("  ✅ 씨딩 완료! 아래 순서로 KPI를 검증하세요:")
    print()
    for i, hint in enumerate(VERIFY_HINTS[scenario_num], 1):
        print(f"  {i}. {hint}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        _print_usage()
        sys.exit(0)

    try:
        num = int(sys.argv[1])
    except ValueError:
        print(f"❌ 숫자를 입력하세요. (입력: {sys.argv[1]})")
        _print_usage()
        sys.exit(1)

    seed(num)
