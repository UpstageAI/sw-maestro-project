"""임시 평가용 — 외부 brief 텍스트로 파이프라인을 한 번 돌리고 결과를 출력."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from test_pipeline import print_results

from graph import graph

BRIEFS = {
    "senior_health": """
혼자 사시는 어르신을 위한 건강관리 앱을 만들고 싶습니다.
혈압과 혈당을 큰 글씨로 기록하고, 매일 정해진 시간에 약 복용 알림을 보냅니다.
스마트폰이 익숙하지 않으셔도 음성으로 결과를 듣고, 가족에게 자동으로 일주일 리포트가 갑니다.
가입 절차는 본인 인증 한 번으로 끝나고, 가족이 보호자 계정으로 연결할 수 있습니다.
""".strip(),
    "farm_direct": """
농촌 생산자와 도시 소비자를 직접 연결하는 산지 직거래 플랫폼입니다.
농가는 사진 한 장과 음성 설명만으로 상품을 등록할 수 있고,
산지에서 바로 포장·배송되어 중간 유통 단계를 없앱니다.
소비자는 농가의 일상 사진과 짧은 영상으로 그 농장이 어떤 곳인지 보고 주문할 수 있고,
배송 후 만족도를 별점과 한 줄로 남기면 다음 시즌 우선 구매권이 생깁니다.
""".strip(),
}


def run(brief_key: str) -> None:
    raw_input = BRIEFS[brief_key]
    print(f"\n{'=' * 70}\n  실행: {brief_key}\n{'=' * 70}\n")
    result: dict = {}
    for chunk in graph.stream({"raw_input": raw_input}, stream_mode="updates"):
        for node_name, update in chunk.items():
            keys = [k for k, v in update.items() if v is not None] if update else []
            suffix = f"  → {', '.join(keys)}" if keys else ""
            print(f"  ✓ {node_name}{suffix}")
            if update:
                result.update(update)

    print_results(result)

    reason = result.get("persona_selection_reason")
    if reason is not None:
        print("\n" + "━" * 62)
        print("  PersonaSelectionReason 원본")
        print("━" * 62)
        print(f"\n  pair_reason: {reason.pair_reason}")
        print("\n  per_persona_reasons:")
        for cid, txt in reason.per_persona_reasons.items():
            print(f"    {cid}: {txt}")
        print("\n  expected_review_angles:")
        for angle in reason.expected_review_angles:
            print(f"    - {angle}")
        print()


def main() -> None:
    args = sys.argv[1:] or list(BRIEFS.keys())
    for key in args:
        if key not in BRIEFS:
            print(f"unknown brief key: {key} (available: {list(BRIEFS.keys())})")
            continue
        run(key)


if __name__ == "__main__":
    main()
