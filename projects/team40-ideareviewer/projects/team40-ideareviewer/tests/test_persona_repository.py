import unittest

from services.persona_repository import _SEED_PATH, load_personas


class PersonaRepositoryTests(unittest.TestCase):
    def test_seed_path_points_to_selected_pool(self) -> None:
        self.assertEqual(_SEED_PATH.name, "persona_cards.selected.json")

    def test_load_personas_returns_one_hundred_cards(self) -> None:
        cards = load_personas()

        self.assertEqual(len(cards), 100)
        self.assertTrue(all(card.card_id.startswith("persona_") for card in cards))


if __name__ == "__main__":
    unittest.main()
