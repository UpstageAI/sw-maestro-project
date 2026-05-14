package com.soma.ai13be.persona.dto.response;

import java.time.Instant;

import com.soma.ai13be.persona.entity.Persona;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "페르소나 응답")
public record PersonaResult(
	@Schema(description = "페르소나 ID", example = "1")
	Long id,

	@Schema(description = "페르소나가 담당하는 도메인 이름", example = "건강")
	String domainName,

	@Schema(description = "Solar가 생성한 페르소나 이름", example = "건강 코치 아리아")
	String name,

	@Schema(description = "페르소나 시스템 프롬프트 전문", example = "당신은 수면·피로 전문 건강 코치입니다.")
	String systemPrompt,

	@Schema(description = "기본 내장 페르소나 여부. true이면 삭제 불가.", example = "false")
	boolean builtIn,

	@Schema(description = "페르소나 활성화 여부", example = "true")
	boolean enabled,

	@Schema(description = "생성 시각")
	Instant createdAt,

	@Schema(description = "수정 시각")
	Instant updatedAt
) {

	public static PersonaResult from(Persona persona) {
		return new PersonaResult(
			persona.getId(),
			persona.getDomainName(),
			persona.getName(),
			persona.getSystemPrompt(),
			persona.isBuiltIn(),
			persona.isEnabled(),
			persona.getCreatedAt(),
			persona.getUpdatedAt()
		);
	}
}
