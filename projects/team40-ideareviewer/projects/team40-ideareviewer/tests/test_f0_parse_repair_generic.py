import unittest

from nodes.f0_parse import _repair_brief
from schemas import ServicePlanInput


class GenericParseRepairTests(unittest.TestCase):
    def test_repair_brief_uses_raw_sentences_without_domain_keywords(self) -> None:
        raw = (
            "Writers upload early drafts to a shared workspace. "
            "Editors leave paragraph-level comments before the weekly review. "
            "Readers can preview paid samples through a private link."
        )
        parsed = ServicePlanInput(
            raw_text=raw,
            title="Editorial workspace",
            description=None,
            target=None,
            key_features=[],
            concerns=None,
        )

        repaired = _repair_brief(parsed, raw)

        self.assertGreaterEqual(len(repaired.key_features), 3)
        self.assertTrue(any("early drafts" in feature for feature in repaired.key_features))
        self.assertTrue(any("paragraph-level comments" in feature for feature in repaired.key_features))
        self.assertTrue(any("private link" in feature for feature in repaired.key_features))


if __name__ == "__main__":
    unittest.main()
