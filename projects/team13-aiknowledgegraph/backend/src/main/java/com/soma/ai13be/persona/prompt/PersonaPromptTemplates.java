package com.soma.ai13be.persona.prompt;

/**
 * 도메인 기반 페르소나의 systemPrompt를 생성하기 위한 프롬프트 템플릿 모음입니다.
 *
 * 이 클래스는 페르소나가 실제 토론에서 답변할 때 사용하는 프롬프트를 직접 정의하지 않습니다.
 * 대신, LLM에게 "특정 도메인에 맞는 페르소나 systemPrompt를 생성해달라"고 요청하기 위한
 * system/user prompt를 제공합니다.
 *
 * 생성된 systemPrompt는 Persona 테이블에 저장되며,
 * 이후 해당 페르소나가 멀티 에이전트 토론에 참여할 때 재사용됩니다.
 */
public final class PersonaPromptTemplates {

	/**
	 * 페르소나 systemPrompt 생성을 담당하는 LLM에게 전달할 system prompt입니다.
	 *
	 * 이 프롬프트는 LLM의 역할과 생성 결과물의 품질 기준을 정의합니다.
	 * 특히 생성된 프롬프트가 DB에 저장되어 반복 사용된다는 점을 명시하여,
	 * 일회성 답변이 아닌 안정적인 페르소나 지침을 만들도록 유도합니다.
	 *
	 * 주의:
	 * - 결과물은 한국어 systemPrompt여야 합니다.
	 * - 예시 대화나 코드 블록이 포함되면 DB 저장 후 실제 페르소나 동작에 노이즈가 될 수 있습니다.
	 * - 건강, 재무, 법률 등 민감 도메인을 고려해 안전 규칙을 포함하도록 요구합니다.
	 */
	private static final String PERSONA_PROMPT_GENERATION_SYSTEM_PROMPT = """
		You create system prompts for domain personas used in a multi-agent discussion service.

		The generated persona prompt will be stored in the Persona table and reused when that persona answers during a discussion.
		It must guide the persona on:
		- Which perspective to use in a discussion.
		- Which signals, risks, and patterns to prioritize.
		- How to challenge other personas constructively.
		- How to produce practical recommendations.

		Requirements:
		- Write the persona prompt in Korean.
		- Make the persona analytical, practical, and respectful.
		- Include clear boundaries and safety rules for the domain.
		- Do not include markdown code fences.
		- Do not generate sample conversation.
		- Return only the final system prompt text.
		""";

	private PersonaPromptTemplates() {
	}

	public static String personaPromptGenerationSystemPrompt() {
		return PERSONA_PROMPT_GENERATION_SYSTEM_PROMPT;
	}


	/**
	 * 특정 도메인에 맞는 페르소나 systemPrompt 생성을 요청하는 user prompt를 생성합니다.
	 *
	 * 예를 들어 domainName이 "건강"이면,
	 * LLM은 건강 도메인 토론에 참여할 페르소나의 역할, 관점, 반박 기준,
	 * 추천 원칙, 안전 규칙을 포함한 systemPrompt를 생성하게 됩니다.
	 *
	 * domainName이 null이거나 공백이면 "general" 도메인으로 처리합니다.
	 * 실제 서비스에서는 사용자가 입력한 원문을 그대로 넣기보다는,
	 * 사전에 도메인명을 짧고 명확한 값으로 정규화한 뒤 전달하는 것이 좋습니다.
	 *
	 * @param domainName 페르소나가 담당할 도메인 이름
	 * @return LLM에 전달할 user prompt
	 */
	public static String personaPromptGenerationUserPrompt(String domainName) {
		String resolvedDomainName = isBlank(domainName) ? "general" : domainName.strip();


		return """
			Create a system prompt for an AI persona that participates in discussions for the following domain.

			Domain: %s

			The generated system prompt must include:
			1. The persona's role.
			2. The perspective this persona should prioritize during discussions.
			3. Criteria for challenging other personas' claims.
			4. Principles for creating final action recommendations.
			5. Domain-specific boundaries and safety rules.
			""".formatted(resolvedDomainName);
	}

	private static boolean isBlank(String value) {
		return value == null || value.isBlank();
	}
}
