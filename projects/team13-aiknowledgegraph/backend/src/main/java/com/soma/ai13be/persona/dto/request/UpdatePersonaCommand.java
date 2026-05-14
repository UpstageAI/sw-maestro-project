package com.soma.ai13be.persona.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "페르소나 시스템 프롬프트 수정 요청")
public record UpdatePersonaCommand(
	@Schema(description = "교체할 시스템 프롬프트 전문", example = "당신은 수면·피로 전문 건강 코치입니다.", requiredMode = Schema.RequiredMode.REQUIRED)
	String systemPrompt
) {
}
