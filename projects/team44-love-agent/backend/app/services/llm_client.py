from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from typing import Protocol, TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.schemas.consultation import (
    AGENT_NAMES,
    AgentFinalPosition,
    AgentId,
    AgentOpinion,
    AgentRebuttal,
    AgreementType,
    Classify2Payload,
    ClassifiedItem,
    ErrorCode,
    FinalPayload,
    PunchlinePayload,
    PunchlineVibe,
    QuestionAnalysis,
    StanceType,
    Summary1Payload,
    TargetReference,
    ActionItem,
    SupervisorNote,
)
from app.services.prompts import PromptRegistry


T = TypeVar("T")
logger = logging.getLogger(__name__)


class LLMOutputError(ValueError):
    """Raised when an LLM response cannot be parsed or validated for a stage."""

    def __init__(
        self,
        *,
        code: ErrorCode,
        task: str,
        detail: str,
        retry_count: int = 0,
    ) -> None:
        self.code = code
        self.task = task
        self.detail = detail
        self.retry_count = retry_count
        retry_suffix = f" after {retry_count} retries" if retry_count else ""
        super().__init__(f"{code.value} during {task}{retry_suffix}: {detail}")


def _validate_items_max_length(values: list[str], *, max_length: int, field_name: str) -> list[str]:
    too_long = [index for index, value in enumerate(values) if len(value) > max_length]
    if too_long:
        raise ValueError(f"{field_name} items must be at most {max_length} characters")
    return values


class AgentOpinionDraft(BaseModel):
    advice: str = Field(min_length=1, max_length=400)
    rationale: str = Field(min_length=1, max_length=400)
    stance: StanceType
    confidence: float = Field(ge=0.0, le=1.0)
    key_points: list[str] = Field(min_length=1, max_length=3)

    @field_validator("key_points")
    @classmethod
    def validate_key_point_lengths(cls, values: list[str]) -> list[str]:
        return _validate_items_max_length(values, max_length=60, field_name="key_points")


class AgentRebuttalDraft(BaseModel):
    targets: list[TargetReference] = Field(min_length=1, max_length=3)
    statement: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=400)
    updated_position: StanceType | None = None
    new_evidence: list[str] = Field(default_factory=list, max_length=3)


class AgentFinalPositionDraft(BaseModel):
    final_stance: StanceType
    final_advice: str = Field(min_length=1, max_length=400)
    changed_from_round_1: bool
    change_reason: str | None = Field(default=None, max_length=200)
    action_items: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("action_items")
    @classmethod
    def validate_action_item_lengths(cls, values: list[str]) -> list[str]:
        return _validate_items_max_length(values, max_length=80, field_name="action_items")

    @model_validator(mode="after")
    def validate_change_reason_required(self) -> "AgentFinalPositionDraft":
        if self.changed_from_round_1 and not self.change_reason:
            raise ValueError("change_reason is required when changed_from_round_1 is true")
        return self


class LLMClient(Protocol):
    async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
        ...

    async def create_agent_opinion(
        self, agent_id: AgentId, user_question: str, analysis: QuestionAnalysis
    ) -> AgentOpinionDraft:
        ...

    async def summarize_round_1(
        self,
        user_question: str,
        analysis: QuestionAnalysis,
        round_1_opinions: list[AgentOpinion],
    ) -> Summary1Payload:
        ...

    async def create_agent_rebuttal(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        target_opinion: AgentOpinion,
        target: TargetReference,
        prior_rebuttals: list[AgentRebuttal],
    ) -> AgentRebuttalDraft:
        ...

    async def classify_round_2(
        self,
        summary_1: SupervisorNote,
        round_2_rebuttals: list[AgentRebuttal],
    ) -> Classify2Payload:
        ...

    async def create_agent_final_position(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        classify_2: SupervisorNote,
        own_opinion: AgentOpinion | None,
        own_rebuttal: AgentRebuttal | None,
        prior_positions: list[AgentFinalPosition],
    ) -> AgentFinalPositionDraft:
        ...

    async def create_final_summary(
        self,
        user_question: str,
        analysis: QuestionAnalysis | None,
        summary_1: SupervisorNote | None,
        classify_2: SupervisorNote | None,
        round_3_positions: list[AgentFinalPosition],
        round_2_rebuttals: list[AgentRebuttal],
    ) -> FinalPayload:
        ...

    async def create_punchline(
        self,
        user_question: str,
        final: FinalPayload,
    ) -> PunchlinePayload:
        ...


class MockLLMClient:
    """Schema-conformant mock used for local workflow/API/SSE validation."""

    async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
        return QuestionAnalysis(
            consultation_id=consultation_id,
            relationship_state="ambiguous",
            conflict_type="ambiguous",
            key_issues=[_short_issue(user_question), "상대방의 의도 확인 필요"],
            user_emotion="confused",
            debate_goal="상황을 단정하지 않고 다음 행동을 정한다.",
        )

    async def create_agent_opinion(
        self, agent_id: AgentId, user_question: str, analysis: QuestionAnalysis
    ) -> AgentOpinionDraft:
        templates = {
            AgentId.PLAYBOY: (
                "에휴, 내가 이런 거 100번은 봤다. 너무 매달리지 말고 한 발만 빼봐. 상대가 따라오면 게임 시작이고, 안 따라오면 다음 사람 보면 돼.",
                "이런 패턴은 늘 같아. 매달릴수록 가치 떨어지는 거 모르나.",
                StanceType.PAUSE,
                ["밀당의 정석", "거리감 = 가치", "다음 카드 준비"],
            ),
            AgentId.ICE: (
                "감정 변수 제거. 답장 빈도 변화 폭과 시점 데이터를 2주간 수집. 표본 부족 상태에서의 결론은 통계적 의미 없음.",
                "현재 정보 표본 크기가 1~2 이하로 추정됨. 통계적 유의성 부재.",
                StanceType.MIXED,
                ["표본 부족", "변수 통제", "데이터 수집 우선"],
            ),
            AgentId.CONFESSOR: (
                "지금 바로 고백해!!! 답장 늦는 거 신경 쓸 시간에 마음 던져버려! 차여도 데이터 하나 추가야!! 고고고!",
                "고민하는 시간 자체가 손해다. 거절은 데이터, 수락은 보너스.",
                StanceType.PROCEED,
                ["즉시 행동", "거절도 데이터", "오늘 안에"],
            ),
            AgentId.BESTIE: (
                "야 ㅋㅋ 그냥 카톡 한 번 보내봐. '오늘 뭐해?' 이렇게. 답장 늦는 거 가지고 너무 머리 굴리지 마, 그냥 물어보면 끝나는 거야.",
                "친구 시점에서 보면 답 빤한데 본인이 자꾸 어렵게 만들어.",
                StanceType.CLARIFY,
                ["걍 카톡", "복잡하게 X", "쉽게 가자"],
            ),
        }
        advice, rationale, stance, key_points = templates[agent_id]
        return AgentOpinionDraft(
            advice=advice,
            rationale=rationale,
            stance=stance,
            confidence=0.7,
            key_points=key_points,
        )

    async def summarize_round_1(
        self,
        user_question: str,
        analysis: QuestionAnalysis,
        round_1_opinions: list[AgentOpinion],
    ) -> Summary1Payload:
        return Summary1Payload(
            headline="대부분의 의견은 단정보다 확인과 감정 보호에 모입니다.",
            converging_points=["상대 의도 단정 금지", "직접 확인 필요"],
            diverging_points=["바로 행동할지 조금 더 볼지"],
            open_questions=["어떤 방식으로 부담 없이 확인할 수 있을까?"],
        )

    async def create_agent_rebuttal(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        target_opinion: AgentOpinion,
        target: TargetReference,
        prior_rebuttals: list[AgentRebuttal],
    ) -> AgentRebuttalDraft:
        return AgentRebuttalDraft(
            targets=[target],
            statement="그 관점은 타당하지만, 사용자의 불안이 커지지 않도록 확인 방식까지 정해야 합니다.",
            rationale="좋은 조언도 실행 방식이 모호하면 사용자가 다시 망설일 수 있습니다.",
            updated_position=StanceType.CLARIFY,
            new_evidence=["실행 방식의 구체성 필요"],
        )

    async def classify_round_2(
        self,
        summary_1: SupervisorNote,
        round_2_rebuttals: list[AgentRebuttal],
    ) -> Classify2Payload:
        rebuttal_ids = [item.id for item in round_2_rebuttals]
        return Classify2Payload(
            consensus=[
                ClassifiedItem(topic="상대 의도는 직접 확인해야 한다", supporting_message_ids=rebuttal_ids[:3])
            ],
            conflict=[
                ClassifiedItem(topic="바로 행동할지 시간을 둘지", supporting_message_ids=rebuttal_ids[3:5])
            ],
            pending=[
                ClassifiedItem(topic="상대의 실제 상황 정보 부족", supporting_message_ids=rebuttal_ids[5:])
            ],
            consensus_ratio=0.66,
            next_action="proceed_to_round_3",
        )

    async def create_agent_final_position(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        classify_2: SupervisorNote,
        own_opinion: AgentOpinion | None,
        own_rebuttal: AgentRebuttal | None,
        prior_positions: list[AgentFinalPosition],
    ) -> AgentFinalPositionDraft:
        return AgentFinalPositionDraft(
            final_stance=StanceType.CLARIFY,
            final_advice="감정을 몰아붙이지 않는 짧은 질문으로 상대의 의도를 확인하세요.",
            changed_from_round_1=False,
            action_items=["상황을 한 문장으로 정리하기", "부담 없는 확인 메시지 보내기"],
        )

    async def create_punchline(
        self,
        user_question: str,
        final: FinalPayload,
    ) -> PunchlinePayload:
        # 재미 우선 3명(playboy/confessor/bestie) 중 advice 길이 해시로 선택. ice는 mock에서 피함.
        idx = len(final.final_advice) % 3
        templates = [
            (AgentId.PLAYBOY, "거리둬!", PunchlineVibe.HARSH,
             "이런 패턴은 100번 봤다. 매달리지 말고 한 발 빼는 게 답."),
            (AgentId.CONFESSOR, "직진해!", PunchlineVibe.HOPEFUL,
             "고민 길어질수록 손해. 일단 던지면 답이 온다."),
            (AgentId.BESTIE, "그냥 해!", PunchlineVibe.CHAOTIC,
             "친구 시점에서 답 빤한데 본인이 자꾸 어렵게 만듦."),
        ]
        agent_id, one_liner, vibe, rationale = templates[idx]
        return PunchlinePayload(
            chosen_agent_id=agent_id,
            one_liner=one_liner,
            vibe=vibe,
            rationale=rationale,
        )

    async def create_final_summary(
        self,
        user_question: str,
        analysis: QuestionAnalysis | None,
        summary_1: SupervisorNote | None,
        classify_2: SupervisorNote | None,
        round_3_positions: list[AgentFinalPosition],
        round_2_rebuttals: list[AgentRebuttal],
    ) -> FinalPayload:
        return FinalPayload(
            situation="사용자는 상대의 반응을 해석하기 어려워 다음 행동을 고민하고 있습니다.",
            disagreements=["행동 시점을 바로 잡을지 조금 더 지켜볼지 의견 차이가 있습니다."],
            final_advice="상대의 마음을 단정하지 말고, 부담 없는 방식으로 확인하세요. 답을 기다리는 동안에는 내 감정 소모를 줄이는 기준도 함께 세우는 것이 좋습니다.",
            action_items=[
                ActionItem(
                    title="확인 질문 준비",
                    detail="상대가 부담을 느끼지 않도록 짧고 구체적인 질문을 한 문장으로 작성합니다.",
                    timing="immediate",
                ),
                ActionItem(
                    title="기다리는 기준 정하기",
                    detail="답변을 기다릴 기간과 이후 행동 기준을 미리 정해 감정 소모를 줄입니다.",
                    timing="short_term",
                ),
            ],
            caveats=["상대의 의도는 현재 정보만으로 확정할 수 없습니다."],
        )


class UpstageLLMClient:
    """Upstage adapter using the OpenAI-compatible chat completions interface."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.upstage.ai/v1",
        model: str = "solar-pro3",
        prompt_registry: PromptRegistry | None = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for LLM_PROVIDER=upstage") from exc

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._prompts = prompt_registry or PromptRegistry()

    async def _json_completion(
        self,
        task: str,
        output_schema: str,
        user: str,
        *,
        guidance: str = "",
        retry_feedback: str = "",
    ) -> dict:
        system = (
            "You are a backend JSON generator for a Korean relationship-consultation "
            "multi-agent workflow. Return exactly one JSON object and no markdown. "
            "Do not wrap the response in ```json fences. Use Korean text values. "
            "Never invent fields outside the requested schema. "
            "If a field has enum choices, use only one of the enum literals."
        )
        if guidance:
            system = f"{system}\n\nProject prompt guidance:\n{guidance}"
        prompt = (
            f"Task:\n{task}\n\n"
            f"Required JSON schema description:\n{output_schema}\n\n"
            f"Input context:\n{user}\n\n"
            "Return JSON only."
        )
        if retry_feedback:
            prompt = (
                f"{prompt}\n\n"
                "Previous output failed backend validation:\n"
                f"{retry_feedback}\n\n"
                "Retry by returning one corrected JSON object only. "
                "Keep enum literals, item counts, item lengths, and copied IDs exactly valid. "
                "Shorten every Korean text value if needed. Do not include raw newline characters "
                "inside JSON string values. Finish the closing braces."
            )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
        choice = response.choices[0]
        content = choice.message.content or "{}"
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason and finish_reason != "stop":
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task=task,
                detail=(
                    f"LLM finish_reason={finish_reason}. "
                    f"Response excerpt: {content[:320]!r}"
                ),
            )
        return _loads_json_object(content, task=task)

    async def _validated_json_completion(
        self,
        task: str,
        output_schema: str,
        user: str,
        *,
        guidance: str = "",
        validator: Callable[[dict], T],
    ) -> T:
        retry_feedback = ""
        max_attempts = _max_output_attempts()
        for attempt in range(1, max_attempts + 1):
            try:
                data = await self._json_completion(
                    task,
                    output_schema,
                    user,
                    guidance=guidance,
                    retry_feedback=retry_feedback,
                )
                return validator(data)
            except LLMOutputError as exc:
                retry_feedback = exc.detail
                if attempt >= max_attempts:
                    raise LLMOutputError(
                        code=exc.code,
                        task=task,
                        detail=exc.detail,
                        retry_count=attempt - 1,
                    ) from exc
                _log_llm_retry(task, attempt=attempt, max_attempts=max_attempts, reason=exc.detail)
            except ValidationError as exc:
                retry_feedback = _validation_feedback(exc)
                if attempt >= max_attempts:
                    raise LLMOutputError(
                        code=ErrorCode.SCHEMA_VIOLATION,
                        task=task,
                        detail=retry_feedback,
                        retry_count=attempt - 1,
                    ) from exc
                _log_llm_retry(
                    task,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    reason=retry_feedback,
                )
            except ValueError as exc:
                retry_feedback = str(exc)
                if attempt >= max_attempts:
                    raise LLMOutputError(
                        code=ErrorCode.SCHEMA_VIOLATION,
                        task=task,
                        detail=retry_feedback,
                        retry_count=attempt - 1,
                    ) from exc
                _log_llm_retry(task, attempt=attempt, max_attempts=max_attempts, reason=retry_feedback)
        raise LLMOutputError(
            code=ErrorCode.UNKNOWN,
            task=task,
            detail="LLM output retry loop exited unexpectedly",
            retry_count=max_attempts - 1,
        )

    async def analyze_question(self, consultation_id: str, user_question: str) -> QuestionAnalysis:
        return await self._validated_json_completion(
            "Analyze the user's relationship concern for the supervisor analysis stage.",
            "\n".join(
                [
                    "{",
                    '  "relationship_state": "crush|dating|long_term|breakup_aftermath|ambiguous|other",',
                    '  "conflict_type": "communication_frequency|trust|future_alignment|emotional_distance|external_factor|ambiguous|other",',
                    '  "key_issues": ["1 to 5 short Korean strings"],',
                    '  "user_emotion": "anxious|confused|hurt|hopeful|angry|neutral",',
                    '  "debate_goal": "one Korean sentence"',
                    "}",
                ]
            ),
            user_question,
            guidance=self._prompts.supervisor_prompt("analysis"),
            validator=lambda data: _question_analysis_from_llm(data, consultation_id=consultation_id),
        )

    async def create_agent_opinion(
        self, agent_id: AgentId, user_question: str, analysis: QuestionAnalysis
    ) -> AgentOpinionDraft:
        return await self._validated_json_completion(
            f"Generate one round_1 independent opinion for agent_id={agent_id.value}.",
            "\n".join(
                [
                    "{",
                    '  "advice": "1 to 3 Korean sentences, max 400 chars",',
                    '  "rationale": "1 to 3 Korean sentences, max 400 chars",',
                    '  "stance": "proceed|pause|withdraw|clarify|mixed",',
                    '  "confidence": 0.0 to 1.0,',
                    '  "key_points": ["1 to 3 Korean strings, each max 60 chars"]',
                    "}",
                ]
            ),
            f"agent_id={agent_id.value}\nquestion={user_question}\nanalysis={analysis.model_dump_json()}",
            guidance=self._prompts.agent_round_prompt(agent_id, 1),
            validator=_agent_opinion_from_llm,
        )

    async def summarize_round_1(
        self,
        user_question: str,
        analysis: QuestionAnalysis,
        round_1_opinions: list[AgentOpinion],
    ) -> Summary1Payload:
        return await self._validated_json_completion(
            "Summarize round_1 opinions into supervisor summary_1 payload.",
            "\n".join(
                [
                    "{",
                    '  "headline": "one Korean sentence, max 100 chars",',
                    '  "converging_points": ["0 to 5 Korean strings"],',
                    '  "diverging_points": ["0 to 5 Korean strings"],',
                    '  "open_questions": ["1 to 3 Korean strings"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json"),
                    "round_1_opinions": [
                        opinion.model_dump(mode="json") for opinion in round_1_opinions
                    ],
                }
            ),
            guidance=self._prompts.supervisor_prompt("summary_1"),
            validator=_summary1_payload_from_llm,
        )

    async def create_agent_rebuttal(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        target_opinion: AgentOpinion,
        target: TargetReference,
        prior_rebuttals: list[AgentRebuttal],
    ) -> AgentRebuttalDraft:
        return await self._validated_json_completion(
            (
                f"Generate one round_2 rebuttal/complement for agent_id={agent_id.value} "
                f"(이 에이전트의 풀네임: {AGENT_NAMES[agent_id]}). "
                "IMPORTANT: In Korean 'statement' and 'rationale' text, when referring to OTHER agents, "
                "you MUST use their full Korean agent_name (예: '지옥에서 온 바람둥이', '냉혈한 얼음 연애 분석가', "
                "'행동파 연쇄고백마', '리얼 찐친 연애 박사'). "
                "NEVER use English agent_id (playboy/ice/confessor/bestie) or short forms (바람둥이/분석가) in the body text. "
                "The target_agent_id field still uses the English id."
            ),
            "\n".join(
                [
                    "{",
                    '  "targets": [{"target_message_id": "copy from input", "target_agent_id": "copy from input", "agreement": "agree|partial|disagree|extend"}],',
                    '  "statement": "Korean statement, max 500 chars",',
                    '  "rationale": "Korean rationale, max 400 chars",',
                    '  "updated_position": "proceed|pause|withdraw|clarify|mixed or null",',
                    '  "new_evidence": ["0 to 3 Korean strings"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "agent_id": agent_id.value,
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json"),
                    "summary_1": summary_1.model_dump(mode="json"),
                    "target": target.model_dump(mode="json"),
                    "target_opinion": target_opinion.model_dump(mode="json"),
                    "prior_round_2_rebuttals": [
                        rebuttal.model_dump(mode="json") for rebuttal in prior_rebuttals
                    ],
                }
            ),
            guidance=self._prompts.agent_round_prompt(agent_id, 2),
            validator=lambda data: _validate_rebuttal_target_copy(
                _agent_rebuttal_from_llm(data),
                expected=target,
            ),
        )

    async def classify_round_2(
        self,
        summary_1: SupervisorNote,
        round_2_rebuttals: list[AgentRebuttal],
    ) -> Classify2Payload:
        valid_message_ids = {rebuttal.id for rebuttal in round_2_rebuttals}
        return await self._validated_json_completion(
            "Classify round_2 into consensus, conflict, pending, and next action.",
            "\n".join(
                [
                    "{",
                    '  "consensus": [{"topic": "Korean topic", "supporting_message_ids": ["ids from input"]}],',
                    '  "conflict": [{"topic": "Korean topic", "supporting_message_ids": ["ids from input"]}],',
                    '  "pending": [{"topic": "Korean topic", "supporting_message_ids": ["ids from input"]}],',
                    '  "consensus_ratio": 0.0 to 1.0,',
                    '  "next_action": "proceed_to_round_3|skip_to_final"',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "summary_1": summary_1.model_dump(mode="json"),
                    "round_2_rebuttals": [
                        rebuttal.model_dump(mode="json") for rebuttal in round_2_rebuttals
                    ],
                }
            ),
            guidance=self._prompts.supervisor_prompt("classify_2"),
            validator=lambda data: _validate_classify_supporting_ids(
                _classify2_payload_from_llm(data),
                valid_message_ids=valid_message_ids,
            ),
        )

    async def create_agent_final_position(
        self,
        agent_id: AgentId,
        user_question: str,
        analysis: QuestionAnalysis,
        summary_1: SupervisorNote,
        classify_2: SupervisorNote,
        own_opinion: AgentOpinion | None,
        own_rebuttal: AgentRebuttal | None,
        prior_positions: list[AgentFinalPosition],
    ) -> AgentFinalPositionDraft:
        return await self._validated_json_completion(
            (
                f"Generate one round_3 final position for agent_id={agent_id.value} "
                f"(이 에이전트의 풀네임: {AGENT_NAMES[agent_id]}). "
                "IMPORTANT: In Korean 'final_advice' and 'change_reason' text, when referring to OTHER agents, "
                "you MUST use full Korean agent_name (예: '지옥에서 온 바람둥이', '냉혈한 얼음 연애 분석가', "
                "'행동파 연쇄고백마', '리얼 찐친 연애 박사'). "
                "NEVER use English agent_id or short forms in body text."
            ),
            "\n".join(
                [
                    "{",
                    '  "final_stance": "proceed|pause|withdraw|clarify|mixed",',
                    '  "final_advice": "Korean final advice, max 400 chars",',
                    '  "changed_from_round_1": true or false,',
                    '  "change_reason": "Korean reason, max 200 chars, or null",',
                    '  "action_items": ["0 to 3 Korean strings, each max 80 chars"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "agent_id": agent_id.value,
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json"),
                    "summary_1": summary_1.model_dump(mode="json"),
                    "classify_2": classify_2.model_dump(mode="json"),
                    "own_round_1_opinion": own_opinion.model_dump(mode="json")
                    if own_opinion
                    else None,
                    "own_round_2_rebuttal": own_rebuttal.model_dump(mode="json")
                    if own_rebuttal
                    else None,
                    "prior_round_3_positions": [
                        position.model_dump(mode="json") for position in prior_positions
                    ],
                }
            ),
            guidance=self._prompts.agent_round_prompt(agent_id, 3),
            validator=_agent_final_position_from_llm,
        )

    async def create_final_summary(
        self,
        user_question: str,
        analysis: QuestionAnalysis | None,
        summary_1: SupervisorNote | None,
        classify_2: SupervisorNote | None,
        round_3_positions: list[AgentFinalPosition],
        round_2_rebuttals: list[AgentRebuttal],
    ) -> FinalPayload:
        return await self._validated_json_completion(
            (
                "Create the supervisor final integrated consultation answer. "
                "IMPORTANT: In Korean 'situation', 'final_advice', 'disagreements', etc., when referring to agents, "
                "you MUST use their full Korean agent_name "
                "('지옥에서 온 바람둥이', '냉혈한 얼음 연애 분석가', '행동파 연쇄고백마', '리얼 찐친 연애 박사'). "
                "NEVER use English agent_id or short forms."
            ),
            "\n".join(
                [
                    "{",
                    '  "situation": "Korean situation summary, max 600 chars",',
                    '  "disagreements": ["0 to 5 Korean strings"],',
                    '  "final_advice": "Korean final advice, max 800 chars",',
                    '  "action_items": [{"title": "max 50 chars", "detail": "max 200 chars", "timing": "immediate|short_term|long_term"}],',
                    '  "caveats": ["0 to 3 Korean strings"]',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "question": user_question,
                    "analysis": analysis.model_dump(mode="json") if analysis else None,
                    "summary_1": summary_1.model_dump(mode="json") if summary_1 else None,
                    "classify_2": classify_2.model_dump(mode="json") if classify_2 else None,
                    "round_3_positions": [
                        position.model_dump(mode="json") for position in round_3_positions
                    ],
                    "round_2_rebuttals_fallback": [
                        rebuttal.model_dump(mode="json") for rebuttal in round_2_rebuttals
                    ],
                }
            ),
            guidance=self._prompts.final_summary_prompt(),
            validator=_final_payload_from_llm,
        )

    async def create_punchline(
        self,
        user_question: str,
        final: FinalPayload,
    ) -> PunchlinePayload:
        guidance = (
            "당신은 오케스트라(슈퍼바이저)다. 최종 보고서를 읽고 4명의 에이전트 중 사용자에게 가장 어울리는 한 명을 골라 "
            "그 에이전트 톤으로 **극도로 짧고 임팩트 있는** 한 줄 조언을 던진다.\n"
            "최우선 목표: **가장 웃기고 재미있고 인상적인 답변**. 진지함보다 캐릭터 임팩트가 절대 우선이다.\n\n"
            "에이전트 페르소나 (재미·웃김 정도):\n"
            "- playboy (지옥에서 온 바람둥이): ★★★★ 시니컬한 한숨 + 잘난 척. '에휴~ 류'. vibe=harsh\n"
            "- ice (냉혈한 얼음 연애 분석가): ★ 건조한 데이터 톤. 거의 안 웃김. **상황이 정말로 데이터 부족이 핵심일 때만** 선택. vibe=cold\n"
            "- confessor (행동파 연쇄고백마): ★★★★★ 들떠있고 무모. '!!!' 폭격. 매우 웃김. vibe=hopeful\n"
            "- bestie (리얼 찐친 연애 박사): ★★★★★ 반말 + ㅋㅋ. 친구 톤 직설. 매우 웃김. vibe=chaotic\n\n"
            "선택 규칙 (중요):\n"
            "- 기본적으로 playboy / confessor / bestie 중에서 고른다.\n"
            "- ice는 사용자가 '아무 정보도 없고 데이터를 모아야 한다'는 게 핵심 결론일 때만 선택. 90% 이상은 ice를 피한다.\n"
            "- 같은 답을 반복해서 내지 말고, 사용자 상황의 분위기와 가장 잘 맞는 캐릭터를 골라 재미있게 한 방.\n\n"
            "one_liner 포맷 (엄격히 따른다):\n"
            "- **명령형 동사 + 느낌표(!) 형식**이 기본. 사용자에게 즉시 행동을 명령하는 톤.\n"
            "- **3~8자 한국어** 단문. 8자 넘기지 않는다 (예외적으로 12자까지 허용).\n"
            "- 동사 어간 + '해!/지내!/떠!/내!/줘!/봐!/가!/와!' 등 명령형 종결.\n"
            "- 좋은 예 (이 패턴을 따른다):\n"
            "  · '헤어져!'\n"
            "  · '떨어져 지내!'\n"
            "  · '사과해!'\n"
            "  · '사과 받아내!'\n"
            "  · '맞짱떠!'\n"
            "  · '붙잡아!'\n"
            "  · '도망쳐!'\n"
            "  · '확인해!'\n"
            "  · '잊어버려!'\n"
            "  · '정리해!'\n"
            "  · '직진해!'\n"
            "  · '그만해!'\n"
            "  · '거리둬!'\n"
            "  · '대화해!'\n"
            "- 나쁜 예 (절대 금지):\n"
            "  · '상대방과 신중하게 대화를 시도해보세요' (너무 길고 정중)\n"
            "  · '잘 생각해봐' (명령 약함, 모호함)\n"
            "  · '데이터를 모아 결정해' (설명형, 임팩트 부족)\n\n"
            "출력 필드:\n"
            "- chosen_agent_id: playboy|ice|confessor|bestie 중 하나 (supervisor 금지)\n"
            "- vibe: chosen_agent의 기본 vibe 그대로 (playboy=harsh, ice=cold, confessor=hopeful, bestie=chaotic)\n"
            "- rationale: 1~2문장 한국어. 왜 이 에이전트·한마디가 가장 웃기고 어울리는지."
        )
        return await self._validated_json_completion(
            "Create a single punchy one-liner advice in the chosen agent's tone.",
            "\n".join(
                [
                    "{",
                    '  "chosen_agent_id": "playboy|ice|confessor|bestie",',
                    '  "one_liner": "2 to 30 chars Korean single sentence",',
                    '  "vibe": "harsh|hopeful|chaotic|cold",',
                    '  "rationale": "1 to 2 Korean sentences, max 200 chars"',
                    "}",
                ]
            ),
            _json_dumps(
                {
                    "user_question": user_question,
                    "final_report": final.model_dump(mode="json"),
                }
            ),
            guidance=guidance,
            validator=lambda d: PunchlinePayload.model_validate(d),
        )


def build_llm_client_from_env() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockLLMClient()
    if provider == "upstage":
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY is required when LLM_PROVIDER=upstage")
        return UpstageLLMClient(
            api_key=api_key,
            base_url=os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
            model=os.getenv("UPSTAGE_MODEL", "solar-pro3"),
            prompt_registry=PromptRegistry(),
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")


def _short_issue(user_question: str) -> str:
    stripped = " ".join(user_question.split())
    return stripped[:60] if stripped else "질문 핵심 파악 필요"


def _json_dumps(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _max_output_attempts() -> int:
    configured = os.getenv("LLM_OUTPUT_MAX_ATTEMPTS", "3")
    try:
        attempts = int(configured)
    except ValueError:
        attempts = 3
    return min(max(attempts, 1), 4)


def _log_llm_retry(task: str, *, attempt: int, max_attempts: int, reason: str) -> None:
    logger.warning(
        "retrying LLM output generation",
        extra={
            "task": task,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "reason": reason[:500],
        },
    )


def _validation_feedback(exc: ValidationError) -> str:
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ())) or "<root>"
        details.append(f"{location}: {error.get('msg', 'validation failed')}")
    return "; ".join(details)[:1600]


def _question_analysis_from_llm(data: dict, *, consultation_id: str) -> QuestionAnalysis:
    repaired = dict(data)
    repaired["key_issues"] = _string_list(
        repaired.get("key_issues"),
        max_items=5,
        max_length=80,
        fallback=["관계 상황 확인 필요"],
    )
    repaired["debate_goal"] = _trim_text(
        repaired.get("debate_goal"),
        500,
        fallback="상황을 단정하지 않고 다음 행동을 정한다.",
    )
    return QuestionAnalysis(consultation_id=consultation_id, **repaired)


def _agent_opinion_from_llm(data: dict) -> AgentOpinionDraft:
    repaired = dict(data)
    repaired["advice"] = _trim_text(repaired.get("advice"), 400, fallback="상황을 더 확인하세요.")
    repaired["rationale"] = _trim_text(
        repaired.get("rationale"),
        400,
        fallback="현재 정보만으로는 단정하기 어렵습니다.",
    )
    repaired["key_points"] = _string_list(
        repaired.get("key_points"),
        max_items=3,
        max_length=60,
        fallback=["단정 금지"],
    )
    return AgentOpinionDraft(**repaired)


def _summary1_payload_from_llm(data: dict) -> Summary1Payload:
    repaired = dict(data)
    repaired["headline"] = _trim_text(
        repaired.get("headline"),
        100,
        fallback="답장 지연을 단정하지 말고 원인을 확인해야 한다.",
    )
    repaired["converging_points"] = _string_list(
        repaired.get("converging_points"),
        max_items=5,
        fallback=[],
    )
    repaired["diverging_points"] = _string_list(
        repaired.get("diverging_points"),
        max_items=5,
        fallback=[],
    )
    repaired["open_questions"] = _string_list(
        repaired.get("open_questions"),
        max_items=3,
        fallback=["상대방의 실제 상황은 무엇인가?"],
    )
    return Summary1Payload(**repaired)


def _agent_rebuttal_from_llm(data: dict) -> AgentRebuttalDraft:
    repaired = dict(data)
    repaired["statement"] = _trim_text(
        repaired.get("statement"),
        500,
        fallback="대상 의견을 보완해 상황 확인이 필요하다고 봅니다.",
    )
    repaired["rationale"] = _trim_text(
        repaired.get("rationale"),
        400,
        fallback="추측만으로는 관계 상태를 판단하기 어렵습니다.",
    )
    repaired["new_evidence"] = _string_list(
        repaired.get("new_evidence"),
        max_items=3,
        fallback=[],
    )
    return AgentRebuttalDraft(**repaired)


def _classify2_payload_from_llm(data: dict) -> Classify2Payload:
    repaired = dict(data)
    repaired["consensus"] = _classified_items(repaired.get("consensus"))
    repaired["conflict"] = _classified_items(repaired.get("conflict"))
    repaired["pending"] = _classified_items(repaired.get("pending"))
    return Classify2Payload(**repaired)


def _agent_final_position_from_llm(data: dict) -> AgentFinalPositionDraft:
    repaired = dict(data)
    repaired["final_advice"] = _trim_text(
        repaired.get("final_advice"),
        400,
        fallback="상황을 단정하지 말고 부드럽게 확인하세요.",
    )
    if repaired.get("change_reason") is not None:
        repaired["change_reason"] = _trim_text(repaired.get("change_reason"), 200)
    repaired["action_items"] = _string_list(
        repaired.get("action_items"),
        max_items=3,
        max_length=80,
        fallback=[],
    )
    return AgentFinalPositionDraft(**repaired)


def _final_payload_from_llm(data: dict) -> FinalPayload:
    repaired = dict(data)
    repaired["situation"] = _trim_text(
        repaired.get("situation"),
        600,
        fallback="사용자는 상대방의 답장 지연을 관계 변화로 봐야 하는지 고민하고 있습니다.",
    )
    repaired["disagreements"] = _string_list(
        repaired.get("disagreements"),
        max_items=5,
        fallback=[],
    )
    repaired["final_advice"] = _trim_text(
        repaired.get("final_advice"),
        800,
        fallback="답장 속도만으로 단정하지 말고 상대방의 상황과 메시지 패턴을 함께 확인하세요.",
    )
    repaired["caveats"] = _string_list(repaired.get("caveats"), max_items=3, fallback=[])
    action_items = repaired.get("action_items")
    normalized_action_items = []
    if isinstance(action_items, list):
        normalized_action_items = [
            {
                **item,
                "title": _trim_text(item.get("title"), 50, fallback="상황 확인"),
                "detail": _trim_text(
                    item.get("detail"),
                    200,
                    fallback="상대방의 현재 상황을 부드럽게 확인하세요.",
                ),
            }
            for item in action_items[:5]
            if isinstance(item, dict)
        ]
    if not normalized_action_items:
        normalized_action_items = [
            {
                "title": "상황 확인",
                "detail": "상대방의 현재 상황을 부드럽게 확인하세요.",
                "timing": "immediate",
            }
        ]
    repaired["action_items"] = normalized_action_items
    return FinalPayload(**repaired)


def _validate_rebuttal_target_copy(
    draft: AgentRebuttalDraft,
    *,
    expected: TargetReference,
) -> AgentRebuttalDraft:
    for target in draft.targets:
        if (
            target.target_message_id != expected.target_message_id
            or target.target_agent_id != expected.target_agent_id
        ):
            raise ValueError(
                "targets must copy target_message_id and target_agent_id from input target. "
                f"expected=({expected.target_message_id}, {expected.target_agent_id.value}) "
                f"received=({target.target_message_id}, {target.target_agent_id.value})"
            )
    return draft


def _validate_classify_supporting_ids(
    payload: Classify2Payload,
    *,
    valid_message_ids: set[str],
) -> Classify2Payload:
    invalid_ids = sorted(
        {
            message_id
            for item in [*payload.consensus, *payload.conflict, *payload.pending]
            for message_id in item.supporting_message_ids
            if message_id not in valid_message_ids
        }
    )
    if invalid_ids:
        raise ValueError(
            "supporting_message_ids must be copied from input round_2_rebuttals ids. "
            f"invalid={invalid_ids}; valid={sorted(valid_message_ids)}"
        )
    return payload


def _classified_items(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                **item,
                "topic": _trim_text(item.get("topic"), 100, fallback="미도출"),
                "supporting_message_ids": _string_list(
                    item.get("supporting_message_ids"),
                    max_items=20,
                    fallback=[],
                ),
            }
        )
    return items


def _string_list(
    value: object,
    *,
    max_items: int,
    fallback: list[str],
    max_length: int | None = None,
) -> list[str]:
    if not isinstance(value, list):
        value = fallback
    strings = [item for item in value if isinstance(item, str) and item.strip()]
    strings = strings[:max_items]
    if max_length is not None:
        strings = [_trim_text(item, max_length) for item in strings]
    return strings


def _trim_text(value: object, max_length: int, *, fallback: str = "") -> str:
    text = value if isinstance(value, str) else fallback
    text = " ".join(text.split())
    if not text:
        text = fallback
    return text[:max_length]


def _loads_json_object(content: str, *, task: str = "unknown") -> dict:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as first_exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            snippet = stripped[:320]
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task=task,
                detail=(
                    f"{first_exc.msg} at char {first_exc.pos}. "
                    f"Response excerpt: {snippet!r}"
                ),
            ) from first_exc
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            snippet_start = max(0, exc.pos - 160)
            snippet_end = min(len(stripped), exc.pos + 160)
            snippet = stripped[snippet_start:snippet_end]
            raise LLMOutputError(
                code=ErrorCode.JSON_PARSE_FAILED,
                task=task,
                detail=f"{exc.msg} at char {exc.pos}. Response excerpt: {snippet!r}",
            ) from exc

    if not isinstance(parsed, dict):
        raise LLMOutputError(
            code=ErrorCode.JSON_PARSE_FAILED,
            task=task,
            detail="LLM response must be a JSON object",
        )
    return parsed
