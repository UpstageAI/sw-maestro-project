import unittest
from unittest.mock import patch

from nodes.f3_review import _reviewable_points, generate_review
from schemas import (
    Opinion,
    OpinionQualityReport,
    PointFeedback,
    ReactionPoint,
    ServicePlanInput,
    TargetUserPersonaCard,
)


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
        card_id="persona_reviewer",
        source_uuid="source",
        display_name="리뷰어",
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


def _opinion() -> Opinion:
    return Opinion(
        persona_id="persona_target",
        positive_points=[
            ReactionPoint(point_id="target_pos_01", title="사진 등록", detail="사진과 음성 등록이 쉽다."),
            ReactionPoint(point_id="target_pos_02", title="정산 자동화", detail="정산 자동화가 있으면 좋다."),
        ],
        negative_points=[],
        would_use=True,
        would_use_description="써볼 수 있다.",
    )


class ReviewQualityTests(unittest.TestCase):
    def test_reviewable_points_excludes_failed_opinion_points(self) -> None:
        quality = OpinionQualityReport(
            persona_id="persona_target",
            pass_point_ids=["target_pos_01"],
            fail_point_ids=["target_pos_02"],
        )

        points = _reviewable_points(_opinion(), quality)

        self.assertEqual([point.point_id for point in points], ["target_pos_01"])

    def test_generate_review_calls_llm_once_per_reviewable_point(self) -> None:
        quality = OpinionQualityReport(
            persona_id="persona_target",
            pass_point_ids=["target_pos_01"],
            fail_point_ids=["target_pos_02"],
        )
        feedback = PointFeedback(
            target_point_id="target_pos_01",
            agreement="agree",
            comment="사진 등록이 짧아지면 실제 판매 준비 시간이 줄어들어 공감된다.",
        )

        with patch("nodes.f3_review._generate_point_feedback", return_value=feedback) as call:
            update = generate_review({
                "reviewer": _persona(),
                "target_opinion": _opinion(),
                "target_opinion_quality": quality,
                "brief": _brief(),
                "slot": "a",
            })

        call.assert_called_once()
        review = update["review_a"]
        report = update["review_quality_a"]
        self.assertEqual([item.target_point_id for item in review.point_feedbacks], ["target_pos_01"])
        self.assertIn("target_pos_01", report.pass_feedback_ids)
        self.assertTrue(any(flag.code == "skipped_failed_opinion_point" for flag in report.flags))


if __name__ == "__main__":
    unittest.main()
