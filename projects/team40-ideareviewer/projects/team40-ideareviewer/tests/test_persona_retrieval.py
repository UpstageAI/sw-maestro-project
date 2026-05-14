import json
import tempfile
import unittest
from pathlib import Path

from schemas import ServicePlanInput, TargetUserPersonaCard
from services.persona_retrieval import (
    brief_selection_text,
    cosine_similarity,
    persona_selection_text,
    persona_text_hash,
    rank_personas_for_brief,
)


def _card(card_id: str, summary: str) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=f"name-{card_id}",
        age_group="60s",
        sex="남",
        occupation="테스트 직업",
        region="서울",
        one_line_summary=summary,
        life_context="생활 맥락",
        user_goals=["목표"],
        pain_points=["불편"],
        positive_triggers=[],
        negative_triggers=[],
        speaking_style="간결함",
    )


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농산물 산지 직거래",
        title="산지 직거래",
        target="고령 생산자",
        description="사진과 음성으로 상품 등록",
        key_features=["산지 배송"],
        concerns="등록 난이도",
    )


class PersonaRetrievalTests(unittest.TestCase):
    def test_selection_texts_include_core_fields(self) -> None:
        card = _card("persona_a", "농산물 판매자")

        self.assertIn("고령 생산자", brief_selection_text(_brief()))
        self.assertIn("농산물 판매자", persona_selection_text(card))
        self.assertNotIn("name-persona_a", persona_selection_text(card))

    def test_cosine_similarity_orders_vectors(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_missing_cache_keeps_original_order(self) -> None:
        cards = [_card("persona_a", "A"), _card("persona_b", "B")]

        ranked = rank_personas_for_brief(_brief(), cards, cache_path=Path("missing.json"))

        self.assertEqual([c.card_id for c in ranked], ["persona_a", "persona_b"])

    def test_unmatched_cache_keeps_order_without_query_embedding(self) -> None:
        cards = [_card("persona_a", "A"), _card("persona_b", "B")]

        def _unexpected_embed(_text: str) -> list[float]:
            raise AssertionError("query embedding should not run")

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "embeddings.json"
            cache_path.write_text(
                json.dumps({"items": [{"card_id": "persona_other", "text_hash": "x", "embedding": [1.0]}]}),
                encoding="utf-8",
            )

            ranked = rank_personas_for_brief(
                _brief(),
                cards,
                cache_path=cache_path,
                embed_query=_unexpected_embed,
            )

        self.assertEqual([c.card_id for c in ranked], ["persona_a", "persona_b"])

    def test_rank_uses_cached_embeddings_and_fake_query_embedding(self) -> None:
        farm = _card("persona_farm", "농산물 생산자")
        unrelated = _card("persona_other", "게임 이용자")

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "embeddings.json"
            cache_path.write_text(
                json.dumps({
                    "model": "test-model",
                    "items": [
                        {
                            "card_id": farm.card_id,
                            "text_hash": persona_text_hash(persona_selection_text(farm)),
                            "embedding": [1.0, 0.0],
                        },
                        {
                            "card_id": unrelated.card_id,
                            "text_hash": persona_text_hash(persona_selection_text(unrelated)),
                            "embedding": [0.0, 1.0],
                        },
                    ],
                }),
                encoding="utf-8",
            )

            ranked = rank_personas_for_brief(
                _brief(),
                [unrelated, farm],
                cache_path=cache_path,
                embed_query=lambda _text: [1.0, 0.0],
            )

        self.assertEqual([c.card_id for c in ranked], ["persona_farm", "persona_other"])


if __name__ == "__main__":
    unittest.main()
