"""에이전트 파이프라인 실제 동작 확인용 스크립트."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.graph import run_agent_stream


async def run(user_input: str, thread_id: str) -> None:
    print(f"\n{'='*60}")
    print(f"[입력] {user_input!r}  (thread: {thread_id})")
    print("="*60)

    async for chunk in run_agent_stream(user_input, thread_id=thread_id):
        t = chunk.type
        p = chunk.payload

        if t == "tool_call":
            print(f"  [tool_call]  {p['name']}")
        elif t == "text":
            print(p["delta"], end="", flush=True)
        elif t == "proposal":
            slots = p.get("slots", [])
            fatigue = p.get("fatigue_timeline", [])
            print(f"\n\n  [proposal]  슬롯 {len(slots)}개 / 피로도 타임라인 {len(fatigue)}일")
            for s in slots:
                date = s["start"][:10]
                time = f"{s['start'][11:16]}~{s['end'][11:16]}"
                muscles = ", ".join(s.get("target_muscles", []))
                print(f"    {date} {time}  {s['type']}  [{muscles}]  강도:{s['intensity']}  — {s['rationale']}")
        elif t == "done":
            print(f"\n  [done]  thread_id={p.get('thread_id')}")
        elif t == "error":
            print(f"\n  [error]  {p.get('message')}")

    print()


async def collect_proposal(user_input: str, thread_id: str) -> dict | None:
    """proposal 청크만 수집해서 반환."""
    print(f"\n{'='*60}")
    print(f"[입력] {user_input!r}  (thread: {thread_id})")
    print("="*60)
    proposal = None
    async for chunk in run_agent_stream(user_input, thread_id=thread_id):
        t = chunk.type
        p = chunk.payload
        if t == "tool_call":
            print(f"  [tool_call]  {p['name']}")
        elif t == "text":
            print(p["delta"], end="", flush=True)
        elif t == "proposal":
            proposal = p
        elif t == "done":
            print(f"\n  [done]  thread_id={p.get('thread_id')}")
        elif t == "error":
            print(f"\n  [error]  {p.get('message')}")
    return proposal


def print_slots(label: str, slots: list[dict]) -> None:
    print(f"\n--- {label} ---")
    for s in slots:
        date = s["start"][:10]
        time = f"{s['start'][11:16]}~{s['end'][11:16]}"
        muscles = ", ".join(s.get("target_muscles", []))
        print(f"  {date} ({time})  {s['type']}  [{muscles}]  강도:{s['intensity']}")


def compare_proposals(before: dict, after: dict) -> None:
    before_slots = {s["start"][:10]: s for s in before.get("slots", [])}
    after_slots  = {s["start"][:10]: s for s in after.get("slots",  [])}

    print("\n\n[비교] 변경 전 → 변경 후")
    print("-" * 60)
    for date in sorted(before_slots):
        b = before_slots[date]
        a = after_slots.get(date)
        b_muscles = ", ".join(b.get("target_muscles", []))
        if a is None:
            print(f"  {date}  MISSING in after")
            continue
        a_muscles = ", ".join(a.get("target_muscles", []))
        changed = (b_muscles != a_muscles or b["intensity"] != a["intensity"] or b["type"] != a["type"])
        marker = "⬅ 변경됨" if changed else "  (동일)"
        print(f"  {date}  [{b_muscles}] 강도:{b['intensity']}  →  [{a_muscles}] 강도:{a['intensity']}  {marker}")


async def main() -> None:
    tid = "demo-thread-002"

    before = await collect_proposal("이번 주 운동 스케줄 짜줘", tid)
    after  = await collect_proposal("화요일은 너무 피곤할 것 같아서 바꿔줘", tid)

    if before and after:
        print_slots("1차 원본", before["slots"])
        print_slots("2차 재조정", after["slots"])
        compare_proposals(before, after)


asyncio.run(main())
