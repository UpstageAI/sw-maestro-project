import unittest

from app import (
    _build_persona_visual_html,
    _compose_raw_review_input,
    _filter_feedbacks_for_display,
    _filter_points_for_display,
    _public_result_state,
    _quality_counts,
    _result_tab_labels,
)
from schemas import (
    OpinionQualityReport,
    PointFeedback,
    ReactionPoint,
    ReviewQualityReport,
)


class AppVisibilityTests(unittest.TestCase):
    def test_result_tabs_do_not_expose_selection_reason_tab(self) -> None:
        labels = _result_tab_labels()

        self.assertNotIn("근거 보기", labels)
        self.assertIn("실행 로그", labels)

    def test_app_review_input_does_not_include_focus_area_hint(self) -> None:
        raw_input = _compose_raw_review_input(
            service_name="테스트 서비스",
            stage="아이디어",
            description="사진 등록과 배송을 검토하는 서비스입니다.",
        )

        self.assertIn("서비스 이름: 테스트 서비스", raw_input)
        self.assertIn("현재 단계: 아이디어", raw_input)
        self.assertNotIn("중점 검토 항목", raw_input)

    def test_public_result_state_hides_selection_reason(self) -> None:
        state = {
            "brief": {"title": "테스트"},
            "persona_selection_reason": {"pair_reason": "숨겨야 함"},
            "persona_a": {"card_id": "persona_a"},
        }

        public_state = _public_result_state(state)

        self.assertNotIn("persona_selection_reason", public_state)
        self.assertEqual(public_state["brief"], {"title": "테스트"})
        self.assertEqual(public_state["persona_a"], {"card_id": "persona_a"})

    def test_public_result_state_hides_quality_reports(self) -> None:
        state = {
            "final_review_text": "done",
            "opinion_quality_a": OpinionQualityReport(persona_id="persona_a"),
            "review_quality_b": ReviewQualityReport(reviewer_id="persona_b", target_id="persona_a"),
        }

        public_state = _public_result_state(state)

        self.assertEqual(public_state, {"final_review_text": "done"})

    def test_filter_points_for_display_excludes_failed_points(self) -> None:
        points = [
            ReactionPoint(point_id="p1", title="shown", detail="shown detail"),
            ReactionPoint(point_id="p2", title="hidden", detail="hidden detail"),
        ]
        quality = OpinionQualityReport(
            persona_id="persona_a",
            pass_point_ids=["p1"],
            fail_point_ids=["p2"],
        )

        visible = _filter_points_for_display(points, quality)

        self.assertEqual([point.point_id for point in visible], ["p1"])

    def test_filter_feedbacks_for_display_excludes_failed_feedback(self) -> None:
        feedbacks = [
            PointFeedback(target_point_id="p1", agreement="agree", comment="shown"),
            PointFeedback(target_point_id="p2", agreement="agree", comment="hidden"),
        ]
        quality = ReviewQualityReport(
            reviewer_id="persona_a",
            target_id="persona_b",
            pass_feedback_ids=["p1"],
            fail_feedback_ids=["p2"],
        )

        visible = _filter_feedbacks_for_display(feedbacks, quality)

        self.assertEqual([feedback.target_point_id for feedback in visible], ["p1"])

    def test_quality_counts_handles_opinion_and_review_reports(self) -> None:
        opinion_quality = OpinionQualityReport(
            persona_id="persona_a",
            pass_point_ids=["p1"],
            weak_point_ids=["p2"],
            fail_point_ids=["p3"],
        )
        review_quality = ReviewQualityReport(
            reviewer_id="persona_a",
            target_id="persona_b",
            pass_feedback_ids=["r1"],
            weak_feedback_ids=["r2"],
            fail_feedback_ids=["r3", "r4"],
        )

        self.assertEqual(_quality_counts(opinion_quality), (1, 1, 1))
        self.assertEqual(_quality_counts(review_quality), (1, 1, 2))

    def test_persona_visualizer_shows_anonymous_scanning_before_selection(self) -> None:
        html = _build_persona_visual_html(
            state={},
            events=[],
            running_node="select_personas",
        )

        self.assertIn("persona-scan-track", html)
        self.assertIn("익명 후보", html)
        self.assertIn("persona-slot is-loading", html)
        self.assertNotIn("김테스트", html)

    def test_persona_visualizer_locks_selected_two_personas(self) -> None:
        state = {
            "persona_a": {
                "display_name": "김테스트",
                "age_group": "40대",
                "occupation": "농업",
                "region": "경북",
                "one_line_summary": "소규모 농가",
            },
            "persona_b": {
                "display_name": "이테스트",
                "age_group": "30대",
                "occupation": "회사원",
                "region": "서울",
                "one_line_summary": "신선식품 구매자",
            },
        }

        html = _build_persona_visual_html(
            state=state,
            events=[],
            running_node=None,
        )

        self.assertIn("persona-card-selected", html)
        self.assertIn("김테스트", html)
        self.assertIn("이테스트", html)
        self.assertIn("선정 완료", html)
        self.assertNotIn("persona-scan-track", html)


if __name__ == "__main__":
    unittest.main()
