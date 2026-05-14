import unittest

from services.persona_repository import load_personas


class PersonaRepositoryTests(unittest.TestCase):
    def test_seed_persona_cards_match_runtime_schema(self) -> None:
        personas = load_personas()

        self.assertGreaterEqual(len(personas), 2)
        for persona in personas:
            for field_name in (
                "user_goals",
                "pain_points",
                "positive_triggers",
                "negative_triggers",
            ):
                values = getattr(persona, field_name)
                self.assertIsInstance(values, list)
                self.assertTrue(
                    all(isinstance(item, str) for item in values),
                    f"{persona.card_id}.{field_name} must be list[str]",
                )


if __name__ == "__main__":
    unittest.main()
