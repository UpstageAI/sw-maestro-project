import unittest
from unittest.mock import patch

from nodes.f1_select import (
    _PROMPT,
    _RETRIEVAL_POOL_LIMIT,
    _format_persona_list,
    _resolve_selection,
    select_personas,
)
from schemas import PersonaSelectionReason, ServicePlanInput, TargetUserPersonaCard


def _make_card(card_id: str = "persona_test1") -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid="source-test",
        display_name="김영수",
        age_group="60s",
        sex="남",
        occupation="농업",
        region="충청남",
        one_line_summary="농산물을 직접 판매하는 60대",
        life_context="가족 농장을 30년째 운영 중.",
        user_goals=["판매 채널 확대", "직거래"],
        pain_points=["복잡한 앱", "작은 글씨"],
        positive_triggers=["간단한 등록"],
        negative_triggers=["배송 책임"],
        speaking_style="현실적이고 직설적",
    )


def _make_custom_card(
    card_id: str,
    *,
    age_group: str = "30s",
    occupation: str = "무직",
    summary: str = "일반적인 생활 맥락을 가진 사용자",
    goals: list[str] | None = None,
    pains: list[str] | None = None,
) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=f"사용자-{card_id}",
        age_group=age_group,
        sex="남",
        occupation=occupation,
        region="충청남",
        one_line_summary=summary,
        life_context="테스트용 생활 맥락",
        user_goals=goals or [],
        pain_points=pains or [],
        positive_triggers=[],
        negative_triggers=[],
        speaking_style="간결함",
    )


class FormatPersonaListTests(unittest.TestCase):
    def test_includes_required_fields(self) -> None:
        text = _format_persona_list([_make_card("persona_abc")])

        self.assertIn("persona_abc", text)
        self.assertIn("김영수", text)
        self.assertIn("60s", text)
        self.assertIn("농업", text)
        self.assertIn("농산물을 직접 판매하는 60대", text)
        self.assertIn("가족 농장을 30년째 운영 중.", text)
        self.assertIn("판매 채널 확대", text)
        self.assertIn("작은 글씨", text)
        self.assertIn("간단한 등록", text)
        self.assertIn("배송 책임", text)

    def test_excludes_omitted_fields(self) -> None:
        text = _format_persona_list([_make_card()])

        self.assertNotIn("현실적이고 직설적", text)
        self.assertNotIn("source-test", text)

    def test_separates_multiple_cards_with_blank_line(self) -> None:
        text = _format_persona_list([_make_card("persona_a"), _make_card("persona_b")])

        self.assertIn("persona_a", text)
        self.assertIn("persona_b", text)
        self.assertIn("\n\n", text)


class ResolveSelectionTests(unittest.TestCase):
    def test_keeps_valid_ids_in_order(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection(["persona_b", "persona_a"], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_b", "persona_a"])

    def test_drops_invalid_ids_and_fills_from_pool_head(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection(["missing_x", "persona_c"], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_c", "persona_a"])

    def test_pads_when_llm_returns_fewer_than_two(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection([], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_a", "persona_b"])

    def test_dedupes_duplicates_then_fills(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection(["persona_a", "persona_a"], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_a", "persona_b"])


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농산물 직거래",
        title="직거래 앱",
        target="고령 생산자",
        description="농촌과 도시를 연결",
        key_features=["사진 등록", "산지 배송"],
        concerns="등록 난이도",
    )


def _pool(*card_ids: str) -> list[TargetUserPersonaCard]:
    return [_make_card(cid) for cid in card_ids]


class SelectPersonasTests(unittest.TestCase):
    def test_happy_path_returns_two_cards_and_reason(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c", "persona_d")
        canned = PersonaSelectionReason(
            selected_card_ids=["persona_c", "persona_a"],
            per_persona_reasons={"persona_c": "관점 A", "persona_a": "관점 B"},
            pair_reason="두 관점을 함께 본다",
            expected_review_angles=["등록", "신뢰"],
        )

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", return_value=canned):
            result = select_personas({"brief": _brief()})

        self.assertEqual(result["persona_a"].card_id, "persona_c")
        self.assertEqual(result["persona_b"].card_id, "persona_a")
        reason = result["persona_selection_reason"]
        self.assertEqual(reason.selected_card_ids, ["persona_c", "persona_a"])
        self.assertEqual(reason.pair_reason, "두 관점을 함께 본다")

    def test_invalid_llm_ids_fall_back_and_reason_is_normalized(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c")
        canned = PersonaSelectionReason(
            selected_card_ids=["missing_x", "missing_y"],
            pair_reason="invalid id 케이스",
        )

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", return_value=canned):
            result = select_personas({"brief": _brief()})

        self.assertEqual(result["persona_a"].card_id, "persona_a")
        self.assertEqual(result["persona_b"].card_id, "persona_b")
        self.assertEqual(
            result["persona_selection_reason"].selected_card_ids,
            ["persona_a", "persona_b"],
        )

    def test_reason_per_persona_keys_are_normalized_to_selected_cards(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c")
        canned = PersonaSelectionReason(
            selected_card_ids=["persona_a", "persona_b"],
            per_persona_reasons={
                "persona_a": "핵심 타겟",
                "persona_c": "선택되지 않은 후보",
            },
            pair_reason="서로 다른 관점",
        )

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", return_value=canned):
            result = select_personas({"brief": _brief()})

        reason = result["persona_selection_reason"]
        self.assertEqual(reason.selected_card_ids, ["persona_a", "persona_b"])
        self.assertEqual(set(reason.per_persona_reasons), {"persona_a", "persona_b"})
        self.assertEqual(reason.per_persona_reasons["persona_a"], "핵심 타겟")
        self.assertTrue(reason.per_persona_reasons["persona_b"])

    def test_llm_exception_falls_back_to_pool_head(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c")

        def _boom(*_args, **_kwargs):
            raise RuntimeError("upstream timeout")

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", side_effect=_boom):
            result = select_personas({"brief": _brief()})

        self.assertEqual(result["persona_a"].card_id, "persona_a")
        self.assertEqual(result["persona_b"].card_id, "persona_b")
        reason = result["persona_selection_reason"]
        self.assertEqual(reason.selected_card_ids, ["persona_a", "persona_b"])
        self.assertIn("LLM", reason.pair_reason)

    def test_llm_exception_logs_to_stderr_before_fallback(self) -> None:
        import io
        import sys

        pool = _pool("persona_a", "persona_b", "persona_c")

        def _boom(*_args, **_kwargs):
            raise RuntimeError("upstream timeout")

        buf = io.StringIO()
        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", side_effect=_boom), \
             patch.object(sys, "stderr", buf):
            select_personas({"brief": _brief()})

        log = buf.getvalue()
        self.assertIn("f1_select", log)
        self.assertIn("RuntimeError", log)
        self.assertIn("upstream timeout", log)

    def test_small_pool_skips_llm_and_returns_all(self) -> None:
        pool = _pool("persona_a", "persona_b")

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select") as llm_mock:
            result = select_personas({"brief": _brief()})

        llm_mock.assert_not_called()
        self.assertEqual(result["persona_a"].card_id, "persona_a")
        self.assertEqual(result["persona_b"].card_id, "persona_b")

    def test_select_personas_passes_ranked_pool_to_llm(self) -> None:
        unrelated = _make_custom_card(
            "persona_unrelated",
            occupation="육군 부사관",
            summary="부대 행정과 가족 시간을 중시하는 사용자",
        )
        farm = _make_custom_card(
            "persona_farm",
            age_group="70plus",
            occupation="농업 단순 종사원",
            summary="농촌에서 농산물 생산과 산지 배송 부담을 겪는 고령 생산자",
            goals=["농산물 판매 채널 확대"],
            pains=["복잡한 상품 등록", "배송 책임 분쟁"],
        )
        other = _make_custom_card(
            "persona_other",
            occupation="도서관 사서",
            summary="지역 도서관 운영과 독서 모임을 중시하는 사용자",
        )
        brief = _brief()
        original_pool = [unrelated, farm, other]
        ranked_pool = [farm, unrelated, other]
        seen_pool: list[TargetUserPersonaCard] = []

        def _select_from_seen_pool(_brief_arg, pool_arg):
            seen_pool.extend(pool_arg)
            return PersonaSelectionReason(
                selected_card_ids=["persona_farm", "persona_unrelated"],
                per_persona_reasons={
                    "persona_farm": "농산물 직거래 타겟",
                    "persona_unrelated": "비교 관점",
                },
                pair_reason="등록 난이도와 신뢰 형성을 함께 검토",
                expected_review_angles=["등록", "신뢰", "배송"],
            )

        with patch("nodes.f1_select.load_personas", return_value=original_pool), \
             patch("nodes.f1_select.rank_personas_for_brief", return_value=ranked_pool) as rank_mock, \
             patch("nodes.f1_select._llm_select", side_effect=_select_from_seen_pool):
            select_personas({"brief": brief})

        rank_mock.assert_called_once_with(brief, original_pool)
        self.assertEqual(
            [card.card_id for card in seen_pool],
            ["persona_farm", "persona_unrelated", "persona_other"],
        )

    def test_select_personas_limits_ranked_pool_before_llm(self) -> None:
        ranked_pool = _pool(*(f"persona_{i}" for i in range(_RETRIEVAL_POOL_LIMIT + 5)))
        seen_pool: list[TargetUserPersonaCard] = []

        def _select_from_seen_pool(_brief_arg, pool_arg):
            seen_pool.extend(pool_arg)
            return PersonaSelectionReason(
                selected_card_ids=[pool_arg[0].card_id, pool_arg[1].card_id],
                pair_reason="상위 후보 검토",
            )

        with patch("nodes.f1_select.load_personas", return_value=ranked_pool), \
             patch("nodes.f1_select.rank_personas_for_brief", return_value=ranked_pool), \
             patch("nodes.f1_select._llm_select", side_effect=_select_from_seen_pool):
            select_personas({"brief": _brief()})

        self.assertEqual(len(seen_pool), _RETRIEVAL_POOL_LIMIT)
        self.assertEqual(seen_pool[-1].card_id, f"persona_{_RETRIEVAL_POOL_LIMIT - 1}")

    def test_system_prompt_emphasises_demographic_fit(self) -> None:
        system_text = _PROMPT.messages[0].prompt.template

        self.assertIn("타겟", system_text)
        self.assertIn("demographic", system_text.lower())

    def test_system_prompt_explains_ranked_candidates(self) -> None:
        system_text = _PROMPT.messages[0].prompt.template

        self.assertIn("semantic relevance", system_text)
        self.assertIn("상위 후보", system_text)
        self.assertIn("추측하지 마세요", system_text)

    def test_system_prompt_defines_anchor_and_complement_contract(self) -> None:
        system_text = _PROMPT.messages[0].prompt.template

        self.assertIn("Anchor", system_text)
        self.assertIn("Complement", system_text)
        self.assertIn("내부 선택 역할", system_text)
        self.assertIn("같은 서비스 문제 공간", system_text)
        self.assertIn("단순히 산업/키워드", system_text)

    def test_pair_reason_requires_grounded_connection_and_difference(self) -> None:
        system_text = _PROMPT.messages[0].prompt.template

        self.assertIn("공유 연결고리", system_text)
        self.assertIn("서로 다른 검증 관점", system_text)
        self.assertIn("후보 목록의 사실", system_text)
        self.assertIn("Anchor/Complement", system_text)
        self.assertIn("그대로 쓰지 마세요", system_text)

    def test_system_prompt_forbids_names_in_pair_reason(self) -> None:
        system_text = _PROMPT.messages[0].prompt.template

        self.assertIn("pair_reason", system_text)
        self.assertIn("이름", system_text)


if __name__ == "__main__":
    unittest.main()
