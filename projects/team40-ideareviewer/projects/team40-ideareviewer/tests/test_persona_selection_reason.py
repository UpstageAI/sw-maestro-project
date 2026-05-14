import unittest

from schemas import PersonaSelectionReason


class PersonaSelectionReasonTests(unittest.TestCase):
    def test_minimum_required_fields(self) -> None:
        reason = PersonaSelectionReason(
            selected_card_ids=["persona_a", "persona_b"],
            pair_reason="핵심 타겟과 리스크 관점을 함께 본다",
        )

        self.assertEqual(reason.selected_card_ids, ["persona_a", "persona_b"])
        self.assertEqual(reason.pair_reason, "핵심 타겟과 리스크 관점을 함께 본다")
        self.assertEqual(reason.per_persona_reasons, {})
        self.assertEqual(reason.expected_review_angles, [])

    def test_all_fields_present(self) -> None:
        reason = PersonaSelectionReason(
            selected_card_ids=["persona_a", "persona_b"],
            per_persona_reasons={
                "persona_a": "핵심 타겟 적합",
                "persona_b": "디지털 접근성 리스크 검증",
            },
            pair_reason="생산자와 접근성 약자의 관점을 동시에 본다",
            expected_review_angles=["등록 난이도", "신뢰", "가격"],
        )

        self.assertEqual(reason.per_persona_reasons["persona_b"], "디지털 접근성 리스크 검증")
        self.assertEqual(len(reason.expected_review_angles), 3)

    def test_fields_carry_descriptions_for_llm_schema(self) -> None:
        # Field descriptions propagate into the JSON schema sent to with_structured_output.
        # Empty/missing descriptions degrade LLM compliance.
        schema = PersonaSelectionReason.model_json_schema()
        props = schema["properties"]

        self.assertIn("description", props["selected_card_ids"])
        self.assertIn("description", props["per_persona_reasons"])
        self.assertIn("description", props["pair_reason"])
        self.assertIn("description", props["expected_review_angles"])

        # The description for selected_card_ids must enforce the "정확히 2개" invariant in prose.
        self.assertIn("2", props["selected_card_ids"]["description"])

    def test_reason_descriptions_require_candidate_fact_grounding(self) -> None:
        schema = PersonaSelectionReason.model_json_schema()
        props = schema["properties"]

        self.assertIn("후보 목록의 사실", props["per_persona_reasons"]["description"])
        self.assertIn("공유 연결고리", props["pair_reason"]["description"])
        self.assertIn("서로 다른 검증 관점", props["pair_reason"]["description"])
        self.assertIn("후보 목록의 사실", props["pair_reason"]["description"])


if __name__ == "__main__":
    unittest.main()
