"""Chat agent tools — 5개 read+write 도구. place_id 가 closure 로 주입됨.

각 tool 은 사장님이 자연어로 요청한 작업을 실행하고 결과를 한국어 평문으로 반환.
LLM 이 요약·재구성해서 응답하므로 tool return 은 *데이터 풍부*하게.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from langchain_core.tools import tool

from src.store import memory
from src.store import sqlite as db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_chat_tools(place_id: str) -> list:
    """매장 1개에 closure 로 묶인 tool 5개 반환. agent factory 가 호출."""

    @tool
    def analyze_new_reviews(n: int = 5) -> str:
        """매장의 미처리 리뷰 N건을 LangGraph main graph 로 분석해 분류·답글 초안을 만듭니다.

        Args:
            n: 처리할 리뷰 개수 (기본 5, 최대 20)

        Returns:
            처리 결과 요약 — 긍/부/중립 카운트, 카테고리 분포, 답글 미리보기.
            결과는 Inbox 화면에서 자세히 확인 가능하다는 안내 포함.
        """
        from src.graph.build import graph

        n = max(1, min(int(n), 20))
        unprocessed = db.get_unprocessed_reviews(place_id, limit=n)
        if not unprocessed:
            return "처리할 새 리뷰가 없습니다. 모든 mock 리뷰가 이미 처리됐어요."

        processed = []
        for review in unprocessed:
            final_state: dict = {}
            try:
                for chunk in graph.stream(
                    {
                        "place_id": place_id,
                        "review_id": review["review_id"],
                        "raw_text": review["raw_text"],
                        "review_created_at": review["created_at"],
                    },
                    stream_mode="updates",
                ):
                    for _node, delta in chunk.items():
                        if delta:
                            final_state.update(
                                {k: v for k, v in delta.items() if k != "node_log"}
                            )
            except Exception as e:  # noqa: BLE001
                processed.append({"review_id": review["review_id"], "error": str(e)})
                continue
            processed.append(
                {
                    "review_id": review["review_id"],
                    "sentiment": final_state.get("sentiment"),
                    "categories": [
                        c.get("category") for c in final_state.get("categories", [])
                    ],
                    "drafter": final_state.get("drafter_used"),
                    "reply_preview": (final_state.get("reply_draft") or "")[:120],
                }
            )

        # 통계 집계
        from collections import Counter
        sentiments = Counter(p.get("sentiment") for p in processed if p.get("sentiment"))
        cats = Counter()
        for p in processed:
            for c in p.get("categories") or []:
                cats[c] += 1

        lines = [
            f"{len(processed)}건 처리 완료.",
            f"감정 분포: {dict(sentiments)}",
        ]
        if cats:
            lines.append(f"카테고리 분포: {dict(cats)}")
        if processed:
            lines.append("답글 미리보기:")
            for p in processed[:3]:
                if p.get("reply_preview"):
                    lines.append(f"- [{p['sentiment']}] {p['reply_preview']}…")
        lines.append("자세한 분류·답글은 Inbox 화면 카드에서 확인하세요.")
        return "\n".join(lines)

    @tool
    def get_top_complaints() -> str:
        """최근 4주 부정 리뷰 카테고리 TOP 3 와 점검 체크리스트를 생성합니다.

        Returns:
            TOP 3 카테고리·빈도 + 매장 메뉴를 반영한 점검 To-Do 3~5개.
        """
        from src.graph.build_batch import batch_graph

        result_state: dict = {}
        try:
            for chunk in batch_graph.stream({"place_id": place_id}, stream_mode="updates"):
                for _node, delta in chunk.items():
                    if delta:
                        result_state.update(
                            {k: v for k, v in delta.items() if k != "node_log"}
                        )
        except Exception as e:  # noqa: BLE001
            return f"batch 분석 실패: {e}"

        top3 = result_state.get("top3_data", [])
        summary = result_state.get("top3_summary", "")
        checklist = result_state.get("checklist", [])

        if not top3:
            return "최근 4주간 분류된 부정 리뷰가 부족합니다. 먼저 새 리뷰를 분석해주세요."

        out = ["[TOP 3 반복 불만 (최근 4주)]"]
        for i, t in enumerate(top3, 1):
            out.append(f"  {i}. {t.get('category')} — {t.get('freq')}회")
        out.append("")
        out.append("[이번 주 점검 체크리스트]")
        for item in checklist[:5]:
            out.append(f"  - {item}")
        return "\n".join(out)

    @tool
    def query_reviews(
        sentiment: Literal["positive", "negative", "neutral", "all"] = "all",
        limit: int = 5,
    ) -> str:
        """매장에 저장된 리뷰를 감정별로 조회합니다.

        Args:
            sentiment: 'positive' | 'negative' | 'neutral' | 'all'
            limit: 최대 조회 개수 (기본 5, 최대 20)
        """
        limit = max(1, min(int(limit), 20))
        rows = db.list_reviews(place_id, limit=200)
        if sentiment != "all":
            rows = [r for r in rows if r["sentiment"] == sentiment]
        rows = rows[:limit]
        if not rows:
            return f"조건에 맞는 리뷰가 없습니다 (sentiment={sentiment})."

        out = [f"[{sentiment} 리뷰 {len(rows)}건]"]
        for r in rows:
            sent = r["sentiment"] or "?"
            cats = r["categories"] or "—"
            text = (r["raw_text"] or "")[:80]
            out.append(f"- [{sent}/{cats}] {text}…")
        return "\n".join(out)

    @tool
    def get_store_info() -> str:
        """현재 매장의 메뉴·가격대·답글 톤·톤 샘플 개수·최근 리뷰 통계를 알려드립니다."""
        meta = memory.get_metadata(place_id)
        samples = memory.get_tone_samples(place_id, limit=100)
        feedback = memory.get_feedback_hints(place_id, limit=10)

        # 최근 4주 리뷰 통계
        with db.connect() as conn:
            row = conn.execute(
                """SELECT sentiment, COUNT(*) AS c
                   FROM reviews
                   WHERE place_id = ?
                     AND sentiment IS NOT NULL
                     AND created_at >= datetime('now', '-28 days')
                   GROUP BY sentiment""",
                (place_id,),
            ).fetchall()
        sent_counts = {r["sentiment"]: r["c"] for r in row}

        menus = meta.get("menus") or []
        menu_str = (
            ", ".join(f"{m.get('name')}({m.get('price', '?')}원)" for m in menus[:8])
            or "(미입력)"
        )

        out = [
            f"**{meta.get('display_name', place_id)}** ({meta.get('category', '?')})",
            f"- 가격대: {meta.get('price_range', '?')}",
            f"- 답글 톤: {meta.get('tone_preference', '?')}",
            f"- 메뉴 {len(menus)}개: {menu_str}",
            f"- 톤 샘플: {len(samples)}건",
            f"- 톤 hint: {len(feedback)}건",
            f"- 최근 4주 리뷰: {sent_counts}",
        ]
        return "\n".join(out)

    @tool
    def add_owner_reply(
        review_text: str,
        owner_reply: str,
        drafter_kind: Literal["thanks", "apology", "neutral"] = "neutral",
    ) -> str:
        """사장님이 과거 작성하셨던 리뷰-답글 쌍을 톤 샘플로 추가합니다.
        다음 답글 생성 시 Drafter prompt 의 few-shot 으로 자동 주입됩니다.

        Args:
            review_text: 원본 리뷰 (10~500자)
            owner_reply: 사장님이 작성한 답글 (10~300자)
            drafter_kind: 'thanks' | 'apology' | 'neutral' (기본 'neutral')
        """
        review_text = (review_text or "").strip()
        owner_reply = (owner_reply or "").strip()
        if len(review_text) < 5 or len(owner_reply) < 5:
            return "리뷰와 답글 모두 5자 이상 입력해주세요."
        sample_id = memory.append_tone_sample(
            place_id,
            {
                "review_text": review_text,
                "ai_draft": "",
                "owner_final": owner_reply,
                "drafter_used": drafter_kind,
                "categories": [],
                "created_at": _now_iso(),
                "source": "manual_via_chat",
            },
        )
        # UX-2: 사장 직접 추가도 audit trail 에 기록 (manual_add 이벤트)
        try:
            db.insert_feedback_event(
                place_id=place_id,
                review_id=None,
                reply_id=None,
                event_type="manual_add",
                before_text=None,
                after_text=owner_reply,
            )
        except Exception:  # noqa: BLE001
            # audit 기록 실패가 tool 자체를 실패로 끌고 가면 안 됨
            pass
        total = len(memory.get_tone_samples(place_id, limit=100))
        return (
            f"톤 샘플 추가됨 (id={sample_id}, source=manual_via_chat). "
            f"이 매장의 누적 톤 샘플은 이제 {total}건이고, 다음 답글 prompt 의 "
            f"few-shot 으로 자동 주입됩니다."
        )

    return [
        analyze_new_reviews,
        get_top_complaints,
        query_reviews,
        get_store_info,
        add_owner_reply,
    ]
