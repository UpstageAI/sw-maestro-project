import unittest

from schemas import OpinionQualityReport, QualityFlag, ReviewQualityReport
from state import ProjectState


class QualityContractTests(unittest.TestCase):
    def test_quality_flag_contract(self) -> None:
        flag = QualityFlag(
            code="unsupported_feature",
            severity="fail",
            message="서비스 기획안에 없는 기능을 언급했습니다.",
            point_id="abc_pos_01",
        )

        self.assertEqual(flag.code, "unsupported_feature")
        self.assertEqual(flag.severity, "fail")
        self.assertEqual(flag.point_id, "abc_pos_01")

    def test_opinion_quality_report_defaults(self) -> None:
        report = OpinionQualityReport(persona_id="persona_a")

        self.assertEqual(report.pass_point_ids, [])
        self.assertEqual(report.weak_point_ids, [])
        self.assertEqual(report.fail_point_ids, [])
        self.assertEqual(report.flags, [])

    def test_review_quality_report_defaults(self) -> None:
        report = ReviewQualityReport(reviewer_id="persona_a", target_id="persona_b")

        self.assertEqual(report.pass_feedback_ids, [])
        self.assertEqual(report.weak_feedback_ids, [])
        self.assertEqual(report.fail_feedback_ids, [])
        self.assertEqual(report.flags, [])

    def test_project_state_declares_quality_fields(self) -> None:
        annotations = ProjectState.__annotations__

        self.assertIn("opinion_quality_a", annotations)
        self.assertIn("opinion_quality_b", annotations)
        self.assertIn("review_quality_a", annotations)
        self.assertIn("review_quality_b", annotations)


if __name__ == "__main__":
    unittest.main()
