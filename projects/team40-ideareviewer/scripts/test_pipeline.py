"""전체 파이프라인 터미널 테스트 스크립트.

사용법:
    python scripts/test_pipeline.py            # persona_cards 캐시 사용
    python scripts/test_pipeline.py --regen    # persona_cards LLM 재생성
"""

import asyncio
import json
import sys
from pathlib import Path

# persona/ 및 persona/scripts/ 디렉토리를 모듈 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from generate_user_cards import generate_cards

from graph import graph
from schemas import Opinion, RawNemotronPersona, Review, TargetUserPersonaCard

RAW_PATH   = Path(__file__).parent.parent / "data" / "personas" / "raw_personas.seed.json"
CARDS_PATH = Path(__file__).parent.parent / "data" / "personas" / "persona_cards.seed.json"
BRIEF_PATH = Path(__file__).parent.parent / "data" / "service_plans" / "sample_brief.seed.json"

W = 62

_NODE_LABEL = {
    "f0_parse": "f0  기획안 파싱",
    "select_personas": "f1  페르소나 선택",
    "generate_opinion": "f2  의견 생성",
    "collect_opinions": "    의견 fan-in",
    "generate_review": "f3  교차 리뷰 생성",
    "collect_reviews": "    리뷰 fan-in",
    "supervisor_finalize": "f4  최종 리뷰 생성",
}


def banner(title: str) -> None:
    print(f"\n{'━' * W}\n  {title}\n{'━' * W}")


def section(title: str) -> None:
    print(f"\n  {'─' * (W - 4)}\n  {title}\n  {'─' * (W - 4)}")


# ── STEP 0: raw_personas 현황 ─────────────────────────────────────────────────

def step0_show_raw() -> list[RawNemotronPersona]:
    banner("STEP 0  raw_personas 로드")
    raw_list = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    raws = [RawNemotronPersona(**r) for r in raw_list]
    print(f"\n  총 {len(raws)}개 원본 페르소나\n")
    for r in raws:
        age_str = f"{r.age}세" if r.age else "나이불명"
        print(f"  ┌ {r.uuid[:8]}  {age_str} / {r.sex or '-'} / {r.occupation or '-'} / {r.province or '-'}")
        if r.persona:
            print(f"  │ 인물: {r.persona[:80]}{'...' if len(r.persona or '') > 80 else ''}")
        if r.professional_persona:
            print(f"  │ 직업: {r.professional_persona[:80]}{'...' if len(r.professional_persona or '') > 80 else ''}")
        if r.hobbies_and_interests:
            print(f"  │ 취미: {r.hobbies_and_interests[:80]}{'...' if len(r.hobbies_and_interests or '') > 80 else ''}")
        if r.career_goals_and_ambitions:
            print(f"  │ 목표: {r.career_goals_and_ambitions[:80]}{'...' if len(r.career_goals_and_ambitions or '') > 80 else ''}")
        print(f"  └ 학력: {r.education_level or '-'}  /  거주: {r.housing_type or '-'}  /  결혼: {r.marital_status or '-'}\n")
    return raws


# ── STEP 1: persona_cards 로드 또는 생성 ──────────────────────────────────────

async def _regen_cards(raws: list[RawNemotronPersona]) -> None:
    await generate_cards(raws, CARDS_PATH)


def step1_load_cards(raws: list[RawNemotronPersona], regen: bool) -> list[TargetUserPersonaCard]:
    banner("STEP 1  persona_cards 준비")
    if regen or not CARDS_PATH.exists():
        print("\n  → LLM으로 페르소나 카드 생성 중...")
        asyncio.run(_regen_cards(raws))
    else:
        print(f"\n  → 캐시 사용: {CARDS_PATH.name}  (재생성: --regen)\n")

    raw_cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    cards = [TargetUserPersonaCard(**c) for c in raw_cards]
    for c in cards:
        print(f"  ┌ [{c.card_id}]  {c.display_name}  |  {c.age_group} / {c.sex or '-'} / {c.occupation or '-'} / {c.region or '-'}")
        print(f"  │ {c.one_line_summary}")
        print(f"  │ 맥락: {c.life_context[:100]}{'...' if len(c.life_context) > 100 else ''}")
        print(f"  │ 목표: {' / '.join(c.user_goals)}")
        print(f"  │ 불편: {' / '.join(c.pain_points)}")
        print(f"  └ 말투: {c.speaking_style}\n")
    return cards


# ── STEP 2: 파이프라인 실행 (노드별 스트리밍) ────────────────────────────────

def step2_run(raw_input: str) -> dict:
    banner("STEP 2  파이프라인 실행")
    print()

    result: dict = {}
    for chunk in graph.stream({"raw_input": raw_input}, stream_mode="updates"):
        for node_name, update in chunk.items():
            label = _NODE_LABEL.get(node_name, node_name)
            keys = [k for k, v in update.items() if v is not None] if update else []
            suffix = f"  → {', '.join(keys)}" if keys else ""
            print(f"  ✓ {label}{suffix}")
            if update:
                result.update(update)

    return result


# ── 결과 출력 ─────────────────────────────────────────────────────────────────

def _print_opinion(persona: TargetUserPersonaCard, opinion: Opinion) -> None:
    section(f"{persona.display_name}  ({persona.card_id})")
    print("\n  [긍정]")
    for pt in opinion.positive_points:
        print(f"  + {pt.title}")
        print(f"    {pt.detail}\n")
    print("  [부정]")
    for pt in opinion.negative_points:
        print(f"  - {pt.title}")
        print(f"    {pt.detail}\n")
    use_str = "사용할 것" if opinion.would_use else "사용 안 할 것"
    print(f"  [사용 의향] {use_str}")
    print(f"    {opinion.would_use_description}")


def _print_review(reviewer: TargetUserPersonaCard, review: Review) -> None:
    section(f"{reviewer.display_name} → 상대 의견 리뷰")
    for fb in review.point_feedbacks:
        mark = "✓" if fb.agreement == "agree" else "✗"
        print(f"  {mark} [{fb.target_point_id}]")
        print(f"    {fb.comment}\n")
    revised_str = "사용할 것" if review.revised_would_use else "사용 안 할 것"
    print("  [종합 소감]")
    print(f"    {review.overall_comment}")
    print(f"\n  [최종 사용 의향] {revised_str}")


def print_results(result: dict) -> None:
    brief = result["brief"]
    pa: TargetUserPersonaCard = result["persona_a"]
    pb: TargetUserPersonaCard = result["persona_b"]

    banner("기획안 요약")
    print(f"\n  제목  : {brief.title}")
    print(f"  타겟  : {brief.target}")
    print("  기능  :")
    for f in brief.key_features:
        print(f"    · {f}")
    if brief.concerns:
        print(f"  우려  : {brief.concerns}")

    banner("선택된 페르소나")
    print(f"\n  [A] {pa.display_name}  |  {pa.age_group} / {pa.occupation or '-'} / {pa.region or '-'}")
    print(f"      {pa.one_line_summary}")
    print(f"\n  [B] {pb.display_name}  |  {pb.age_group} / {pb.occupation or '-'} / {pb.region or '-'}")
    print(f"      {pb.one_line_summary}")

    banner("페르소나 의견")
    _print_opinion(pa, result["opinion_a"])
    _print_opinion(pb, result["opinion_b"])

    if result.get("review_a") and result.get("review_b"):
        banner("교차 리뷰")
        _print_review(pa, result["review_a"])
        _print_review(pb, result["review_b"])

    if result.get("final_review_text"):
        banner("최종 리뷰")
        print(f"\n{result['final_review_text']}")

    print(f"\n{'━' * W}\n  파이프라인 완료\n{'━' * W}\n")


# ── 엔트리포인트 ──────────────────────────────────────────────────────────────

def main() -> None:
    regen = "--regen" in sys.argv

    raws = step0_show_raw()
    step1_load_cards(raws, regen)

    raw_input: str = json.loads(BRIEF_PATH.read_text(encoding="utf-8"))["raw_text"]
    result = step2_run(raw_input)
    print_results(result)


if __name__ == "__main__":
    main()
