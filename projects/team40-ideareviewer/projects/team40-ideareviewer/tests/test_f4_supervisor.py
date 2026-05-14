import unittest
from unittest.mock import patch

from nodes.f4_supervisor import (
    _PROMPT,
    _build_supervisor_prompt_vars,
    _decision_from_quality,
    _relocate_unsupported_hypothesis_lines,
    _strip_decision_tokens,
    supervisor_finalize,
)
from schemas import (
    Opinion,
    OpinionQualityReport,
    PointFeedback,
    QualityFlag,
    ReactionPoint,
    Review,
    ReviewQualityReport,
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


class _FakeSupervisorPrompt:
    def __init__(self) -> None:
        self.invoked = False

    def __or__(self, _other: object) -> "_FakeSupervisorPrompt":
        return self

    def invoke(self, _params: dict[str, str]) -> str:
        self.invoked = True
        return "LLM HALLUCINATED BODY"


class SupervisorFormattingTests(unittest.TestCase):
    def test_prompt_separates_grounded_judgment_from_additional_hypotheses(self) -> None:
        messages = _PROMPT.format_messages(
            brief="핵심 기능:\n- 산지 직배송",
            persona_a="농번기 시간이 부족한 생산자",
            persona_b="신선한 농산물을 찾는 소비자",
            opinion_a="품질 기준을 통과한 포인트만 포함했습니다.",
            opinion_b="품질 기준을 통과한 포인트만 포함했습니다.",
            review_a="품질 기준을 통과한 리뷰 피드백만 포함했습니다.",
            review_b="품질 기준을 통과한 리뷰 피드백만 포함했습니다.",
        )
        prompt_text = "\n".join(str(message.content) for message in messages)

        self.assertIn("추가 검증 가설", prompt_text)
        self.assertIn("기획안에 명시되지 않은 추론", prompt_text)
        self.assertIn("본문 판단 근거로 사용하지 마세요", prompt_text)
        self.assertIn("[가설 | 기획안 미명시]", prompt_text)
        self.assertIn("입력 근거에서 자연스럽게 이어지는 경우", prompt_text)
        self.assertIn("최대 3개", prompt_text)

    def test_relocate_unsupported_hypothesis_lines_keeps_grounded_sections_clean(self) -> None:
        brief = ServicePlanInput(
            raw_text="농가와 소비자를 연결하고 산지에서 직접 배송한다.",
            title="산지 직거래",
            description="농가와 소비자를 직접 연결한다.",
            target="농가, 소비자",
            key_features=["농가와 소비자 직접 연결", "산지 직접 배송"],
            concerns="배송 책임",
        )
        body = "\n".join([
            "1. 종합 판단",
            "산지 직배송 반응은 긍정적입니다.",
            "2. 긍정 신호",
            "- 산지 직접 배송은 소비자에게 신뢰를 줍니다.",
            "3. 주요 우려",
            "- 정산 및 물류 관리가 생산자 부담으로 작용할 수 있습니다.",
            "4. 페르소나 간 차이",
            "- 생산자는 배송 책임에 민감합니다.",
            "5. 추가 검증 가설",
            "- 없음",
            "6. 다음 검증 질문",
            "- 배송 책임 범위를 확인합니다.",
        ])

        cleaned = _relocate_unsupported_hypothesis_lines(body, brief)
        concern_section = cleaned.split("5. 추가 검증 가설", maxsplit=1)[0]
        hypothesis_section = cleaned.split("5. 추가 검증 가설", maxsplit=1)[1]

        self.assertNotIn("정산", concern_section)
        self.assertIn("[가설 | 기획안 미명시]", hypothesis_section)
        self.assertIn("정산 및 물류 관리", hypothesis_section)
        self.assertNotIn("- 없음", hypothesis_section)

    def test_relocate_unsupported_hypothesis_lines_limits_hypotheses_to_three(self) -> None:
        brief = ServicePlanInput(
            raw_text="농가와 소비자를 연결하고 산지에서 직접 배송한다.",
            title="산지 직거래",
            description="농가와 소비자를 직접 연결한다.",
            target="농가, 소비자",
            key_features=["농가와 소비자 직접 연결", "산지 직접 배송"],
            concerns="배송 책임",
        )
        body = "\n".join([
            "1. 종합 판단",
            "산지 직배송 반응은 긍정적입니다.",
            "5. 추가 검증 가설",
            "[가설 | 기획안 미명시] 정산 방식 확인",
            "- [가설 | 기획안 미명시] 고객 문의 대응 확인",
            "[가설 | 기획안 미명시] 배송 지연 보상 확인",
            "- [가설 | 기획안 미명시] 추천 알고리즘 확인",
            "6. 다음 검증 질문",
            "- 배송 책임 범위를 확인합니다.",
        ])

        cleaned = _relocate_unsupported_hypothesis_lines(body, brief)
        hypothesis_section = cleaned.split("5. 추가 검증 가설", maxsplit=1)[1].split(
            "6. 다음 검증 질문",
            maxsplit=1,
        )[0]
        hypothesis_lines = [
            line.strip()
            for line in hypothesis_section.splitlines()
            if "[가설 | 기획안 미명시]" in line
        ]

        self.assertEqual(len(hypothesis_lines), 3)
        self.assertTrue(all(line.startswith("- [가설 | 기획안 미명시]") for line in hypothesis_lines))
        self.assertNotIn("추천 알고리즘 확인", hypothesis_section)

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

    def test_build_supervisor_prompt_vars_excludes_failed_opinion_points(self) -> None:
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
            "opinion_a": Opinion(
                persona_id="persona_a",
                positive_points=[
                    ReactionPoint(point_id="a_pos_01", title="검증된 포인트", detail="핵심 기능에 대한 반응"),
                    ReactionPoint(point_id="a_pos_02", title="정산 자동화", detail="서비스에 없는 기능"),
                ],
                negative_points=[],
                would_use=True,
                would_use_description="사용 의향 설명",
            ),
            "opinion_b": _opinion("persona_b", "b"),
            "review_a": _review("persona_a", "persona_b", "b_pos_01"),
            "review_b": _review("persona_b", "persona_a", "a_pos_01"),
            "opinion_quality_a": OpinionQualityReport(
                persona_id="persona_a",
                pass_point_ids=["a_pos_01"],
                fail_point_ids=["a_pos_02"],
            ),
            "opinion_quality_b": OpinionQualityReport(persona_id="persona_b"),
        }

        prompt_vars = _build_supervisor_prompt_vars(state)

        self.assertIn("검증된 포인트", prompt_vars["opinion_a"])
        self.assertNotIn("정산 자동화", prompt_vars["opinion_a"])
        self.assertIn("품질 기준을 통과한 포인트만 포함", prompt_vars["opinion_a"])

    def test_build_supervisor_prompt_vars_excludes_failed_review_feedback(self) -> None:
        state = {
            "brief": ServicePlanInput(
                raw_text="raw",
                title="service",
                description="description",
                target="target",
                key_features=["feature"],
                concerns="concerns",
            ),
            "persona_a": _persona("persona_a", "persona A"),
            "persona_b": _persona("persona_b", "persona B"),
            "opinion_a": _opinion("persona_a", "a"),
            "opinion_b": _opinion("persona_b", "b"),
            "review_a": Review(
                reviewer_id="persona_a",
                target_id="persona_b",
                point_feedbacks=[
                    PointFeedback(
                        target_point_id="b_pos_01",
                        agreement="agree",
                        comment="grounded review feedback",
                    ),
                    PointFeedback(
                        target_point_id="b_pos_02",
                        agreement="agree",
                        comment="unsupported biometric login recommendation",
                    ),
                ],
                overall_comment="overall",
                revised_would_use=True,
            ),
            "review_b": _review("persona_b", "persona_a", "a_pos_01"),
            "review_quality_a": ReviewQualityReport(
                reviewer_id="persona_a",
                target_id="persona_b",
                pass_feedback_ids=["b_pos_01"],
                fail_feedback_ids=["b_pos_02"],
            ),
            "review_quality_b": ReviewQualityReport(
                reviewer_id="persona_b",
                target_id="persona_a",
            ),
        }

        prompt_vars = _build_supervisor_prompt_vars(state)

        self.assertIn("grounded review feedback", prompt_vars["review_a"])
        self.assertNotIn("unsupported biometric login", prompt_vars["review_a"])

    def test_decision_from_quality_rechecks_review_failures(self) -> None:
        state = {
            "opinion_quality_a": OpinionQualityReport(persona_id="persona_a"),
            "opinion_quality_b": OpinionQualityReport(persona_id="persona_b"),
            "review_quality_a": ReviewQualityReport(
                reviewer_id="persona_a",
                target_id="persona_b",
                flags=[
                    QualityFlag(
                        code="unsupported_solution",
                        severity="fail",
                        message="없는 기능 제안",
                        point_id="b_pos_01",
                    )
                ],
            ),
            "review_quality_b": ReviewQualityReport(reviewer_id="persona_b", target_id="persona_a"),
        }

        self.assertEqual(_decision_from_quality(state), "[재검토]")

    def test_decision_from_quality_passes_positive_reviews_with_small_f2_failures(self) -> None:
        state = {
            "review_a": _review("persona_a", "persona_b", "b_pos_01"),
            "review_b": _review("persona_b", "persona_a", "a_pos_01"),
            "opinion_quality_a": OpinionQualityReport(
                persona_id="persona_a",
                pass_point_ids=["a_pos_01", "a_pos_02", "a_neg_01", "a_neg_02", "a_neg_03"],
                fail_point_ids=["a_pos_03"],
                flags=[
                    QualityFlag(
                        code="unsupported_solution",
                        severity="fail",
                        message="없는 기능 언급",
                        point_id="a_pos_03",
                    )
                ],
            ),
            "opinion_quality_b": OpinionQualityReport(
                persona_id="persona_b",
                pass_point_ids=["b_pos_01", "b_pos_02", "b_pos_03", "b_neg_01", "b_neg_02", "b_neg_03"],
            ),
            "review_quality_a": ReviewQualityReport(
                reviewer_id="persona_a",
                target_id="persona_b",
                pass_feedback_ids=["b_pos_01", "b_pos_02", "b_neg_01"],
            ),
            "review_quality_b": ReviewQualityReport(
                reviewer_id="persona_b",
                target_id="persona_a",
                pass_feedback_ids=["a_pos_01", "a_pos_02", "a_neg_01"],
                flags=[
                    QualityFlag(
                        code="skipped_failed_opinion_point",
                        severity="weak",
                        message="실패 포인트 제외",
                        point_id="a_pos_03",
                    )
                ],
            ),
        }

        self.assertEqual(_decision_from_quality(state), "[통과]")

    def test_decision_from_quality_passes_when_weakness_is_small_share(self) -> None:
        state = {
            "opinion_quality_a": OpinionQualityReport(
                persona_id="persona_a",
                pass_point_ids=["a_pos_01", "a_pos_02", "a_neg_01"],
                weak_point_ids=["a_neg_02"],
                flags=[
                    QualityFlag(
                        code="weak_persona_context",
                        severity="weak",
                        message="맥락 약함",
                        point_id="a_neg_02",
                    )
                ],
            ),
            "opinion_quality_b": OpinionQualityReport(
                persona_id="persona_b",
                pass_point_ids=["b_pos_01", "b_pos_02", "b_neg_01", "b_neg_02"],
            ),
            "review_quality_a": ReviewQualityReport(
                reviewer_id="persona_a",
                target_id="persona_b",
                pass_feedback_ids=["b_pos_01"],
            ),
            "review_quality_b": ReviewQualityReport(
                reviewer_id="persona_b",
                target_id="persona_a",
                pass_feedback_ids=["a_pos_01"],
            ),
        }

        self.assertEqual(_decision_from_quality(state), "[통과]")

    def test_decision_from_quality_holds_when_weakness_is_large_share(self) -> None:
        state = {
            "opinion_quality_a": OpinionQualityReport(
                persona_id="persona_a",
                weak_point_ids=["a_pos_01"],
                flags=[
                    QualityFlag(
                        code="weak_persona_context",
                        severity="weak",
                        message="맥락 약함",
                        point_id="a_pos_01",
                    )
                ],
            ),
            "opinion_quality_b": OpinionQualityReport(persona_id="persona_b"),
            "review_quality_a": ReviewQualityReport(reviewer_id="persona_a", target_id="persona_b"),
            "review_quality_b": ReviewQualityReport(reviewer_id="persona_b", target_id="persona_a"),
        }

        self.assertEqual(_decision_from_quality(state), "[보류]")

    def test_strip_decision_tokens_removes_conflicting_llm_tokens(self) -> None:
        text = "[통과]\n1. 종합 판단\n좋습니다.\n[재검토] 다시 봐야 합니다."

        cleaned = _strip_decision_tokens(text)

        self.assertNotIn("[통과]", cleaned)
        self.assertNotIn("[재검토]", cleaned)
        self.assertIn("종합 판단", cleaned)


    def test_supervisor_finalize_uses_fallback_when_no_valid_artifacts(self) -> None:
        state = {
            "brief": ServicePlanInput(
                raw_text="raw",
                title="service",
                description="description",
                target="target",
                key_features=["feature"],
                concerns="concerns",
            ),
            "persona_a": _persona("persona_a", "persona A"),
            "persona_b": _persona("persona_b", "persona B"),
            "opinion_a": _opinion("persona_a", "a"),
            "opinion_b": _opinion("persona_b", "b"),
            "review_a": Review(
                reviewer_id="persona_a",
                target_id="persona_b",
                point_feedbacks=[],
                overall_comment="no reviewable points",
                revised_would_use=False,
            ),
            "review_b": Review(
                reviewer_id="persona_b",
                target_id="persona_a",
                point_feedbacks=[],
                overall_comment="no reviewable points",
                revised_would_use=False,
            ),
            "opinion_quality_a": OpinionQualityReport(
                persona_id="persona_a",
                fail_point_ids=["a_pos_01", "a_neg_01"],
                flags=[
                    QualityFlag(
                        code="no_brief_feature_overlap",
                        severity="fail",
                        message="not grounded",
                        point_id="a_pos_01",
                    )
                ],
            ),
            "opinion_quality_b": OpinionQualityReport(
                persona_id="persona_b",
                fail_point_ids=["b_pos_01", "b_neg_01"],
            ),
            "review_quality_a": ReviewQualityReport(
                reviewer_id="persona_a",
                target_id="persona_b",
            ),
            "review_quality_b": ReviewQualityReport(
                reviewer_id="persona_b",
                target_id="persona_a",
            ),
        }
        fake_prompt = _FakeSupervisorPrompt()

        with patch("nodes.f4_supervisor._PROMPT", fake_prompt):
            result = supervisor_finalize(state)

        self.assertFalse(fake_prompt.invoked)
        self.assertNotIn("LLM HALLUCINATED BODY", result["final_review_text"])
        self.assertIn("품질 기준", result["final_review_text"])


if __name__ == "__main__":
    unittest.main()
