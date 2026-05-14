package com.soma.ai13be.persona.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "페르소나 생성 요청. systemPrompt는 서버가 Solar를 호출해 자동 생성합니다.")
public record CreatePersonaCommand(
	@Schema(description = "페르소나가 담당할 도메인 이름", example = "건강", requiredMode = Schema.RequiredMode.REQUIRED)
	String domainName
) {
}
