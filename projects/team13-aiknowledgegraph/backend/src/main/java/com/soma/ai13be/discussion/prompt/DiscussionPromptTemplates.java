package com.soma.ai13be.discussion.prompt;

import org.springframework.util.StringUtils;

public final class DiscussionPromptTemplates {

	private DiscussionPromptTemplates() {
	}

	public static String analysisUserPrompt(String topic, String triggerNodeContext) {
		return """
			Round 1 - 도메인 관점 독립 분석

			토론 주제:
			%s

			선택된 지식 노드:
			%s

			위 주제를 자신의 도메인 관점에서 분석하십시오.
			다음 항목을 포함하십시오.
			1. 가능한 원인
			2. 근거로 볼 수 있는 사용자 데이터
			3. 아직 확인이 필요한 점
			4. 사용자가 바로 시도할 수 있는 제안
			""".formatted(topic, contextOrNone(triggerNodeContext));
	}

	public static String rebuttalUserPrompt(String topic, String analysisTranscript) {
		return """
			Round 2 - 교차 도메인 반론

			토론 주제:
			%s

			Round 1 분석 내용:
			%s

			다른 페르소나의 분석을 검토하고 반론하십시오.
			다음 항목을 포함하십시오.
			1. 과도한 추론 또는 근거가 약한 주장
			2. 빠진 변수나 대안적 설명
			3. 자신의 도메인 관점에서 보완해야 할 해석
			""".formatted(topic, analysisTranscript);
	}

	public static String synthesisSystemPrompt() {
		return """
			당신은 멀티 에이전트 토론 결과를 종합하는 오케스트레이터입니다.
			각 페르소나의 분석과 반론을 비교해 사용자에게 실행 가능한 결론을 제공합니다.
			근거가 약한 내용은 단정하지 말고 확인이 필요한 항목으로 분리하십시오.
			""";
	}

	public static String synthesisUserPrompt(String topic, String analysisTranscript, String rebuttalTranscript) {
		return """
			Round 3 - 종합

			토론 주제:
			%s

			Round 1 분석:
			%s

			Round 2 반론:
			%s

			아래 형식을 반드시 지켜 최종 답변을 작성하십시오.

			요약:
			핵심 결론을 3-5문장으로 작성하십시오.

			실행 계획:
			사용자가 바로 실행할 수 있는 행동 항목을 번호 목록으로 작성하십시오.
			""".formatted(topic, analysisTranscript, rebuttalTranscript);
	}

	private static String contextOrNone(String context) {
		if (!StringUtils.hasText(context)) {
			return "선택된 지식 노드 없음";
		}
		return context;
	}
}
