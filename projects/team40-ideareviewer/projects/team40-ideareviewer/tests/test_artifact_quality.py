import unittest

from schemas import PointFeedback, ReactionPoint, ServicePlanInput, TargetUserPersonaCard
from services.artifact_quality import assess_feedback, assess_reaction_point


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농가는 사진과 음성 설명으로 상품을 등록하고 소비자는 산지 배송으로 주문한다.",
        title="산지 직거래",
        description="농가와 소비자를 직접 연결한다.",
        target="농촌 생산자, 도시 소비자",
        key_features=["사진·음성 상품 등록", "소비자 주문", "산지 배송"],
        concerns="배송 책임",
    )


def _persona() -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id="persona_a",
        source_uuid="source",
        display_name="테스트",
        age_group="50s",
        sex="여자",
        occupation="온라인 판매원",
        region="경남",
        one_line_summary="온라인 판매를 한다.",
        life_context="상품 사진을 자주 올린다.",
        user_goals=["상품 등록 시간을 줄이기"],
        pain_points=["등록 과정이 번거로움"],
        speaking_style="차분한 말투",
    )


class ArtifactQualityTests(unittest.TestCase):
    def test_assess_reaction_point_passes_grounded_point(self) -> None:
        point = ReactionPoint(
            point_id="a_pos_01",
            title="사진 등록이 쉬움",
            detail="나는 상품 사진을 자주 올리기 때문에 사진과 음성으로 등록하는 흐름이 짧으면 좋다.",
        )

        level, flags = assess_reaction_point(point, _brief(), _persona())

        self.assertEqual(level, "pass")
        self.assertEqual(flags, [])

    def test_assess_reaction_point_fails_unsupported_solution(self) -> None:
        point = ReactionPoint(
            point_id="a_pos_01",
            title="정산 자동화",
            detail="나는 실시간 정산 자동화 대시보드가 있으면 좋겠다.",
        )

        level, flags = assess_reaction_point(point, _brief(), _persona())

        self.assertEqual(level, "fail")
        self.assertEqual(flags[0].code, "unsupported_solution")

    def test_assess_reaction_point_fails_unsupported_numeric_claim(self) -> None:
        point = ReactionPoint(
            point_id="a_pos_01",
            title="Higher sale price",
            detail="Photo registration helped me sell the product for a 20% higher price.",
        )

        level, flags = assess_reaction_point(point, _brief(), _persona())

        self.assertEqual(level, "fail")
        self.assertTrue(any(flag.code == "unsupported_numeric_claim" for flag in flags))

    def test_assess_reaction_point_fails_unsupported_domain_workflow(self) -> None:
        point = ReactionPoint(
            point_id="a_pos_01",
            title="[사진·가격 등록] 등급 판단 지원",
            detail="사진과 가격 등록 기능이 농산물 등급 판단에 도움이 된다.",
        )

        level, flags = assess_reaction_point(point, _brief(), _persona())

        self.assertEqual(level, "fail")
        self.assertTrue(any(flag.code == "unsupported_solution" for flag in flags))

    def test_assess_feedback_fails_unsupported_solution(self) -> None:
        feedback = PointFeedback(
            target_point_id="b_pos_01",
            agreement="agree",
            comment="품질 인증 알고리즘과 실시간 모니터링을 추가하면 좋겠다.",
        )

        level, flags = assess_feedback(feedback, _brief())

        self.assertEqual(level, "fail")
        self.assertEqual(flags[0].code, "unsupported_solution")


if __name__ == "__main__":
    unittest.main()
