"""미리 준비된 예시로 동화 생성을 빠르게 테스트하는 스크립트.

사용법:
    cd backend && source .venv/bin/activate

    python examples.py             # 모든 예시 실행
    python examples.py 1           # 1번 예시만
    python examples.py 2 4         # 2번, 4번 예시만
    python examples.py --list      # 예시 목록
    python examples.py 1 -v        # outline·critique 등 agentic 중간 상태도 출력
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from dataclasses import dataclass

from app.graph.builder import graph
from app.models.api import StoryRequest, Person


@dataclass
class Example:
    label: str
    request: StoryRequest


EXAMPLES: list[Example] = [
    Example(
        label="🧱 친구와 장난감(블록) 갈등",
        request=StoryRequest(
            diary_date=date(2026, 5, 8),
            diary=(
                "오늘 어린이집에서 민준이랑 블록 때문에 다퉜다. "
                "내가 먼저 가지고 놀고 있었는데 민준이가 뺏어가서 속상했다. "
                "선생님이 같이 만들자고 했고 집에 와서 엄마가 안아줬다."
            ),
            people=[
                Person(name="엄마", relation="엄마", kind="가족", closeness=5,
                       role_today="저녁에 위로해줌", traits=["다정함"]),
                Person(name="민준", relation="짝꿍", kind="친구", closeness=4,
                       role_today="블록 갈등 상대", traits=["장난기 많음", "활발함"]),
                Person(name="지수 선생님", relation="담임", kind="선생님", closeness=3,
                       role_today="함께 만들기 제안", traits=["차분함"]),
            ],
        ),
    ),
    Example(
        label="🎤 발표 실수와 부끄러움",
        request=StoryRequest(
            diary_date=date(2026, 5, 8),
            diary=(
                "오늘 유치원에서 노래를 발표하다가 가사를 잊어버렸다. "
                "친구들이 웃는 것 같아서 너무 부끄러웠고 끝나고 울었다."
            ),
            people=[
                Person(name="박선생님", relation="담임선생님", kind="선생님", closeness=4,
                       role_today="끝나고 안아주며 격려", traits=["따뜻함"]),
                Person(name="서연", relation="단짝 친구", kind="친구", closeness=5,
                       role_today="옆에서 박수쳐줌", traits=["다정함"]),
            ],
        ),
    ),
    Example(
        label="👶 동생이 생긴 첫날",
        request=StoryRequest(
            diary_date=date(2026, 5, 8),
            diary=(
                "오늘 동생이 태어났다. 아빠랑 병원에 가서 동생을 처음 봤다. "
                "근데 엄마가 동생만 안아주는 것 같아 살짝 서운했다."
            ),
            people=[
                Person(name="아빠", relation="아빠", kind="가족", closeness=5,
                       role_today="병원에 데려가줌", traits=["든든함"]),
                Person(name="엄마", relation="엄마", kind="가족", closeness=5,
                       role_today="동생을 돌봄", traits=["다정함"]),
                Person(name="아기", relation="동생", kind="가족", closeness=3,
                       role_today="처음 만난 새 가족", traits=["작고 여림"]),
            ],
        ),
    ),
    Example(
        label="🌙 어둠이 무서운 밤",
        request=StoryRequest(
            diary_date=date(2026, 5, 8),
            diary=(
                "오늘 밤에 혼자 자려고 했는데 너무 무서워서 울었다. "
                "방 그림자가 괴물처럼 보였다. 결국 엄마 침대로 갔다."
            ),
            people=[
                Person(name="엄마", relation="엄마", kind="가족", closeness=5,
                       role_today="옆에서 같이 잠들어 줌", traits=["포근함"]),
            ],
        ),
    ),
    Example(
        label="🤝 새로 전학 온 친구",
        request=StoryRequest(
            diary_date=date(2026, 5, 8),
            diary=(
                "오늘 새 친구 하늘이가 전학을 왔다. "
                "혼자 점심을 먹고 있어서 같이 먹자고 했더니 활짝 웃어줬다."
            ),
            people=[
                Person(name="하늘", relation="새 짝꿍", kind="친구", closeness=2,
                       role_today="처음 만난 친구", traits=["수줍음", "조용함"]),
                Person(name="선생님", relation="담임", kind="선생님", closeness=4,
                       role_today="자리를 옆으로 정해줌", traits=["세심함"]),
            ],
        ),
    ),
]


def _print_request(req: StoryRequest) -> None:
    print(f"📅 날짜: {req.diary_date}")
    print(f"📝 일기:")
    for line in req.diary.split(". "):
        if line.strip():
            print(f"   {line.strip()}{'.' if not line.endswith('.') else ''}")
    if req.people:
        print(f"👥 인물:")
        for p in req.people:
            extras = []
            if p.closeness is not None:
                extras.append(f"친밀도 {p.closeness}/5")
            if p.role_today:
                extras.append(f"오늘: {p.role_today}")
            if p.traits:
                extras.append(", ".join(p.traits))
            extra_str = f" — {' · '.join(extras)}" if extras else ""
            print(f"   - {p.name} ({p.kind.value}, {p.relation}){extra_str}")


def run_one(idx: int, ex: Example, verbose: bool = False) -> None:
    print()
    print("=" * 70)
    print(f"[{idx}] {ex.label}")
    print("=" * 70)
    _print_request(ex.request)
    print()
    print("⏳ 생성 중... (plan → write → critique → (필요 시 재집필) → finalize)")
    t = time.time()
    try:
        initial = {
            "diary_date": ex.request.diary_date.isoformat(),
            "diary": ex.request.diary,
            "people": [p.model_dump(mode="json") for p in ex.request.people],
        }
        final = graph.invoke(initial)
    except Exception as e:
        print(f"❌ 실패: {type(e).__name__}: {e}")
        return
    elapsed = time.time() - t

    crit = final.get("critique") or {}
    rev = final.get("revision_count", 0)
    score_str = " ".join(f"{k}:{v}" for k, v in (crit.get("scores") or {}).items())
    flag = "✓ 통과" if crit.get("passed") else "✗ 미통과"
    print(f"✅ 완료 ({elapsed:.1f}s) | write 횟수={rev} | {flag} | avg={crit.get('average')} | {score_str}")

    if verbose:
        print()
        print("--- 🧭 OUTLINE (plan 결과) ---")
        outline = final.get("outline", "")
        try:
            print(json.dumps(json.loads(outline), ensure_ascii=False, indent=2))
        except Exception:
            print(outline)
        print()
        print("--- 🔍 CRITIQUE 코멘트 ---")
        print(crit.get("comment", "(없음)"))

    story = final.get("story") or {}
    print()
    print(f"📖 [제목] {story.get('title', '')}")
    print()
    print("📜 [본문]")
    for line in story.get("body", "").split(". "):
        if line.strip():
            line = line.strip()
            print(f"   {line}{'.' if not line.endswith('.') else ''}")


def main() -> None:
    args = sys.argv[1:]

    if "--list" in args or "-l" in args:
        print("사용 가능한 예시:")
        for i, ex in enumerate(EXAMPLES, 1):
            print(f"  {i}. {ex.label}")
        return

    verbose = False
    nums: list[str] = []
    for a in args:
        if a in ("-v", "--verbose"):
            verbose = True
        else:
            nums.append(a)

    if not nums:
        targets = list(range(1, len(EXAMPLES) + 1))
    else:
        try:
            targets = [int(a) for a in nums]
        except ValueError:
            print("⚠️  사용법: python examples.py [번호...] [-v]   또는  --list")
            sys.exit(1)

    for n in targets:
        if 1 <= n <= len(EXAMPLES):
            run_one(n, EXAMPLES[n - 1], verbose=verbose)
        else:
            print(f"⚠️  {n}번 예시는 없습니다. (1~{len(EXAMPLES)})")


if __name__ == "__main__":
    main()
