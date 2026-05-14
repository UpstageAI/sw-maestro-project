import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas import RawNemotronPersona, TargetUserPersonaCard
from scripts.generate_user_cards import (
    configure_langsmith_tracing,
    configure_openai_client_platform,
    generate_cards,
    generate_cards_from_paths,
)


def _raw(uuid: str) -> dict:
    return {
        "uuid": uuid,
        "persona": "김테스트 씨는 동네 생활과 가족 돌봄을 중요하게 여기는 사용자입니다.",
        "professional_persona": "작은 가게에서 손님 응대를 오래 해 온 사람입니다.",
        "cultural_background": "지역 커뮤니티 안에서 실용적인 선택을 선호합니다.",
        "hobbies_and_interests": "스마트폰으로 유튜브를 보고 동네 산책을 즐깁니다.",
        "family_persona": "가족과 자주 연락하며 생활 정보를 나눕니다.",
        "career_goals_and_ambitions": "건강을 유지하며 안정적인 일상을 이어가고 싶어 합니다.",
        "sex": "여자",
        "age": 42,
        "occupation": "상점 판매 종사자",
        "province": "서울",
    }


class GenerateUserCardsTests(unittest.IsolatedAsyncioTestCase):
    def test_configure_langsmith_tracing_disables_batch_tracing_by_default(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_TRACING": "true",
                "LANGCHAIN_TRACING_V2": "true",
            },
            clear=False,
        ):
            configure_langsmith_tracing(False)

            self.assertEqual(os.environ["LANGSMITH_TRACING"], "false")
            self.assertEqual(os.environ["LANGCHAIN_TRACING_V2"], "false")

    def test_configure_langsmith_tracing_preserves_explicit_trace_mode(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            configure_langsmith_tracing(True)

            self.assertEqual(os.environ["LANGSMITH_TRACING"], "true")
            self.assertEqual(os.environ["LANGCHAIN_TRACING_V2"], "true")

    def test_configure_openai_client_platform_skips_platform_detection(self) -> None:
        class FakeRootClient:
            def __init__(self) -> None:
                self._platform = None
                self._version = "1.0"

        class FakeResource:
            def __init__(self) -> None:
                self._client = FakeRootClient()

        class FakeChatModel:
            def __init__(self) -> None:
                self.client = FakeResource()
                self.async_client = FakeResource()

        model = FakeChatModel()

        configure_openai_client_platform(model)

        self.assertEqual(model.client._client._platform, "Windows")
        self.assertEqual(model.async_client._client._platform, "Windows")
        self.assertEqual(
            model.client._client.platform_headers(),
            {
                "X-Stainless-Lang": "python",
                "X-Stainless-Package-Version": "1.0",
                "X-Stainless-OS": "Windows",
                "X-Stainless-Arch": "unknown",
                "X-Stainless-Runtime": "CPython",
                "X-Stainless-Runtime-Version": "unknown",
            },
        )

    async def test_generate_cards_checkpoints_after_each_completed_card(self) -> None:
        raws = [RawNemotronPersona(**_raw("aaa123456789ffff")), RawNemotronPersona(**_raw("bbb123456789ffff"))]
        writes = []

        async def fake_converter(raw_persona):
            return TargetUserPersonaCard(
                card_id=f"persona_{raw_persona.uuid[:12]}",
                source_uuid=raw_persona.uuid,
                display_name="김테스트",
                age_group="40s",
                sex=raw_persona.sex,
                occupation=raw_persona.occupation,
                region=raw_persona.province,
                one_line_summary="동네 생활과 가족 돌봄을 중요하게 여기는 40대 사용자입니다.",
                life_context="서울에서 상점 판매 일을 하며 가족과 자주 연락합니다.",
                user_goals=["건강 유지"],
                pain_points=["복잡한 가입 절차"],
                positive_triggers=["간단한 사용법"],
                negative_triggers=["추가 비용"],
                speaking_style="현실적인 불편을 차분하게 말합니다.",
            )

        await generate_cards(
            raws,
            Path("unused.json"),
            converter=fake_converter,
            concurrency=1,
            writer=lambda _path, cards: writes.append([card.card_id for card in cards]),
        )

        self.assertEqual(
            writes,
            [
                ["persona_aaa123456789"],
                ["persona_aaa123456789", "persona_bbb123456789"],
                ["persona_aaa123456789", "persona_bbb123456789"],
            ],
        )

    async def test_generate_cards_times_out_stuck_converter(self) -> None:
        raws = [RawNemotronPersona(**_raw("timeout12345678"))]
        writes = []

        async def stuck_converter(_raw_persona):
            await asyncio.sleep(1)
            return None

        cards = await generate_cards(
            raws,
            Path("unused.json"),
            converter=stuck_converter,
            concurrency=1,
            converter_timeout_seconds=0.01,
            writer=lambda _path, cards: writes.append([card.card_id for card in cards]),
        )

        self.assertEqual(cards, [])
        self.assertEqual(writes, [[]])

    async def test_generate_cards_from_paths_uses_injected_converter_and_writes_schema_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_path = Path(temp_dir) / "raw.json"
            out_path = Path(temp_dir) / "cards.json"
            raw_path.write_text(
                json.dumps([_raw("abc123456789ffff")], ensure_ascii=False),
                encoding="utf-8",
            )

            async def fake_converter(raw):
                return TargetUserPersonaCard(
                    card_id=f"persona_{raw.uuid[:12]}",
                    source_uuid=raw.uuid,
                    display_name="김테스트",
                    age_group="40s",
                    sex=raw.sex,
                    occupation=raw.occupation,
                    region=raw.province,
                    one_line_summary="동네 생활과 가족 돌봄을 중요하게 여기는 40대 사용자입니다.",
                    life_context="서울에서 상점 판매 일을 하며 가족과 자주 연락합니다.",
                    user_goals=["건강 유지", "가족과 소통", "생활비 절약"],
                    pain_points=["복잡한 가입 절차", "불명확한 가격", "느린 고객지원"],
                    positive_triggers=["간단한 사용법", "명확한 안내", "가족에게 공유 가능"],
                    negative_triggers=["추가 비용", "개인정보 요구", "복잡한 인증"],
                    speaking_style="현실적인 불편을 차분하게 말합니다.",
                )

            cards = await generate_cards_from_paths(
                raw_path=raw_path,
                out_path=out_path,
                converter=fake_converter,
                concurrency=1,
            )

            saved = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(len(cards), 1)
            self.assertEqual(saved[0]["card_id"], "persona_abc123456789")
            self.assertEqual(saved[0]["source_uuid"], "abc123456789ffff")
            TargetUserPersonaCard(**saved[0])

    async def test_generate_cards_from_paths_can_limit_raw_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_path = Path(temp_dir) / "raw.json"
            out_path = Path(temp_dir) / "cards.json"
            raw_path.write_text(
                json.dumps(
                    [_raw("first12345678"), _raw("second1234567")],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            converted = []

            async def fake_converter(raw):
                converted.append(raw.uuid)
                return TargetUserPersonaCard(
                    card_id=f"persona_{raw.uuid[:12]}",
                    source_uuid=raw.uuid,
                    display_name="김테스트",
                    age_group="40s",
                    sex=raw.sex,
                    occupation=raw.occupation,
                    region=raw.province,
                    one_line_summary="동네 생활과 가족 돌봄을 중요하게 여기는 40대 사용자입니다.",
                    life_context="서울에서 상점 판매 일을 하며 가족과 자주 연락합니다.",
                    user_goals=["건강 유지"],
                    pain_points=["복잡한 가입 절차"],
                    positive_triggers=["간단한 사용법"],
                    negative_triggers=["추가 비용"],
                    speaking_style="현실적인 불편을 차분하게 말합니다.",
                )

            cards = await generate_cards_from_paths(
                raw_path=raw_path,
                out_path=out_path,
                converter=fake_converter,
                concurrency=1,
                limit=1,
            )

            self.assertEqual(converted, ["first12345678"])
            self.assertEqual(len(cards), 1)


    async def test_generate_cards_from_paths_accepts_stringified_source_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw = _raw("def123456789ffff")
            raw["skills_and_expertise_list"] = "['고객 응대', '재고 관리']"
            raw["hobbies_and_interests_list"] = "['산책', '유튜브 시청']"
            raw_path = Path(temp_dir) / "raw.json"
            out_path = Path(temp_dir) / "cards.json"
            raw_path.write_text(json.dumps([raw], ensure_ascii=False), encoding="utf-8")

            async def fake_converter(raw_persona):
                self.assertEqual(raw_persona.skills_and_expertise_list, ["고객 응대", "재고 관리"])
                self.assertEqual(raw_persona.hobbies_and_interests_list, ["산책", "유튜브 시청"])
                return TargetUserPersonaCard(
                    card_id=f"persona_{raw_persona.uuid[:12]}",
                    source_uuid=raw_persona.uuid,
                    display_name="김테스트",
                    age_group="40s",
                    sex=raw_persona.sex,
                    occupation=raw_persona.occupation,
                    region=raw_persona.province,
                    one_line_summary="동네 생활과 가족 돌봄을 중요하게 여기는 40대 사용자입니다.",
                    life_context="서울에서 상점 판매 일을 하며 가족과 자주 연락합니다.",
                    user_goals=["건강 유지"],
                    pain_points=["복잡한 가입 절차"],
                    positive_triggers=["간단한 사용법"],
                    negative_triggers=["추가 비용"],
                    speaking_style="현실적인 불편을 차분하게 말합니다.",
                )

            cards = await generate_cards_from_paths(
                raw_path=raw_path,
                out_path=out_path,
                converter=fake_converter,
                concurrency=1,
            )

            self.assertEqual(len(cards), 1)


if __name__ == "__main__":
    unittest.main()
