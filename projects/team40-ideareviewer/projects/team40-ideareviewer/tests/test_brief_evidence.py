import unittest

from schemas import ServicePlanInput
from services.brief_evidence import (
    brief_terms,
    has_brief_feature_overlap,
    introduces_unsupported_solution,
    text_terms,
)


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농가는 사진과 음성 설명으로 농산물을 등록하고 소비자는 산지 배송으로 주문한다.",
        title="산지 직거래",
        description="농가와 소비자를 직접 연결한다.",
        target="농촌 생산자, 도시 소비자",
        key_features=["사진·음성 상품 등록", "소비자 주문", "산지 배송"],
        concerns="배송 책임",
    )


class BriefEvidenceTests(unittest.TestCase):
    def test_text_terms_extracts_korean_terms(self) -> None:
        terms = text_terms("사진과 음성으로 상품을 등록하고 배송을 확인한다.")

        self.assertIn("사진", terms)
        self.assertIn("음성", terms)
        self.assertIn("등록", terms)
        self.assertIn("배송", terms)

    def test_brief_terms_include_features_and_concerns(self) -> None:
        terms = brief_terms(_brief())

        self.assertIn("사진", terms)
        self.assertIn("배송", terms)
        self.assertIn("책임", terms)

    def test_has_brief_feature_overlap_requires_feature_term(self) -> None:
        brief = _brief()

        self.assertTrue(has_brief_feature_overlap("사진으로 상품 등록이 쉬운지 본다.", brief))
        self.assertFalse(has_brief_feature_overlap("정산 자동화 대시보드가 필요하다.", brief))

    def test_introduces_unsupported_solution_detects_new_feature(self) -> None:
        brief = _brief()

        self.assertFalse(introduces_unsupported_solution("배송 책임을 확인하고 싶다.", brief))
        self.assertTrue(introduces_unsupported_solution("정산 자동화와 실시간 모니터링이 필요하다.", brief))


if __name__ == "__main__":
    unittest.main()
