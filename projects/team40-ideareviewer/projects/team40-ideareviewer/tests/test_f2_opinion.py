import unittest

from nodes.f2_opinion import _PROMPT, _build_opinion_quality_report
from schemas import Opinion, ReactionPoint, ServicePlanInput, TargetUserPersonaCard


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


class OpinionQualityTests(unittest.TestCase):
    def test_prompt_prioritizes_brief_grounding_over_persona_story(self) -> None:
        messages = _PROMPT.format_messages(
            display_name="테스트",
            one_line_summary="온라인 판매를 한다.",
            life_context="상품 사진을 자주 올린다.",
            user_goals="- 상품 등록 시간을 줄이기",
            pain_points="- 등록 과정이 번거로움",
            positive_triggers="- 등록이 쉬움",
            negative_triggers="- 등록이 복잡함",
            speaking_style="차분한 말투",
            guardrails="- 기획안에 없는 기능을 만들지 않는다.",
            title="산지 직거래",
            description="농가와 소비자를 직접 연결한다.",
            target="농촌 생산자, 도시 소비자",
            key_features="- 사진·음성 상품 등록\n- 소비자 주문\n- 산지 배송",
            concerns="배송 책임",
        )
        prompt_text = "\n".join(str(message.content) for message in messages)

        self.assertIn("1차 반응의 주 근거는 서비스 기획안", prompt_text)
        self.assertIn("핵심 기능 또는 우려사항 중 하나", prompt_text)
        self.assertIn("페르소나의 생활 맥락은 보조 근거", prompt_text)
        self.assertIn("근거 없는 숫자", prompt_text)
        self.assertIn("title은 반드시 대괄호", prompt_text)
        self.assertIn("나쁜 예", prompt_text)
        self.assertIn("기획안 원문에 없는 경우 사용 금지", prompt_text)
        self.assertIn("포인트의 근거는 핵심 기능/우려사항 목록만", prompt_text)

    def test_build_opinion_quality_report_classifies_points(self) -> None:
        opinion = Opinion(
            persona_id="persona_a",
            positive_points=[
                ReactionPoint(
                    point_id="a_pos_01",
                    title="사진 등록이 쉬움",
                    detail="나는 상품 사진을 자주 올리기 때문에 사진과 음성으로 등록하는 흐름이 짧으면 좋다.",
                )
            ],
            negative_points=[
                ReactionPoint(
                    point_id="a_neg_01",
                    title="정산 자동화",
                    detail="나는 실시간 정산 자동화 대시보드가 있으면 좋겠다.",
                )
            ],
            would_use=True,
            would_use_description="사진 등록이 쉬우면 써볼 수 있다.",
        )

        report = _build_opinion_quality_report(opinion, _brief(), _persona())

        self.assertIn("a_pos_01", report.pass_point_ids)
        self.assertIn("a_neg_01", report.fail_point_ids)
        self.assertTrue(any(flag.code == "unsupported_solution" for flag in report.flags))


if __name__ == "__main__":
    unittest.main()
