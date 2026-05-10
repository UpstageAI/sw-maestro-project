import unittest

from nodes.f4_supervisor import _build_supervisor_prompt_vars
from schemas import (
    Opinion,
    PointFeedback,
    ReactionPoint,
    Review,
    ServicePlanInput,
    TargetUserPersonaCard,
)


def _persona(card_id: str, name: str) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=name,
        age_group="60s",
        sex="남자",
        occupation="테스트 직업",
        region="서울",
        one_line_summary=f"{name} 한 줄 요약",
        life_context=f"{name} 생활 맥락",
        user_goals=["목표 1"],
        pain_points=["불편 1"],
        positive_triggers=["긍정 1"],
        negative_triggers=["부정 1"],
        speaking_style="차분한 말투",
    )


def _opinion(persona_id: str, prefix: str) -> Opinion:
    return Opinion(
        persona_id=persona_id,
        positive_points=[
            ReactionPoint(
                point_id=f"{prefix}_pos_01",
                title="긍정 제목",
                detail="긍정 상세",
            )
        ],
        negative_points=[
            ReactionPoint(
                point_id=f"{prefix}_neg_01",
                title="부정 제목",
                detail="부정 상세",
            )
        ],
        would_use=True,
        would_use_description="사용 의향 설명",
    )


def _review(reviewer_id: str, target_id: str, point_id: str) -> Review:
    return Review(
        reviewer_id=reviewer_id,
        target_id=target_id,
        point_feedbacks=[
            PointFeedback(
                target_point_id=point_id,
                agreement="agree",
                comment="교차 리뷰 코멘트",
            )
        ],
        overall_comment="종합 소감",
        revised_would_use=True,
    )


class SupervisorFormattingTests(unittest.TestCase):
    def test_build_supervisor_prompt_vars_contains_all_artifacts(self) -> None:
        state = {
            "brief": ServicePlanInput(
                raw_text="원문",
                title="테스트 서비스",
                description="서비스 설명",
                target="테스트 타겟",
                key_features=["핵심 기능"],
                concerns="우려사항",
            ),
            "persona_a": _persona("persona_a", "페르소나 A"),
            "persona_b": _persona("persona_b", "페르소나 B"),
            "opinion_a": _opinion("persona_a", "a"),
            "opinion_b": _opinion("persona_b", "b"),
            "review_a": _review("persona_a", "persona_b", "b_pos_01"),
            "review_b": _review("persona_b", "persona_a", "a_pos_01"),
        }

        prompt_vars = _build_supervisor_prompt_vars(state)

        self.assertIn("테스트 서비스", prompt_vars["brief"])
        self.assertIn("페르소나 A", prompt_vars["persona_a"])
        self.assertIn("페르소나 B", prompt_vars["persona_b"])
        self.assertIn("a_pos_01", prompt_vars["opinion_a"])
        self.assertIn("b_pos_01", prompt_vars["opinion_b"])
        self.assertIn("b_pos_01", prompt_vars["review_a"])
        self.assertIn("a_pos_01", prompt_vars["review_b"])


if __name__ == "__main__":
    unittest.main()
