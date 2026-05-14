package com.soma.ai13be.discussion.dto.response;

import java.time.Instant;

import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토론 라운드 메시지 응답")
public record DiscussionMessageResult(
	@Schema(description = "메시지 ID", example = "10")
	Long id,

	@Schema(description = "페르소나 ID. 서버 합성 메시지는 null입니다.", example = "1", nullable = true)
	Long personaId,

	@Schema(description = "페르소나 이름. 서버 합성 메시지는 null입니다.", example = "health Persona", nullable = true)
	String personaName,

	@Schema(description = "토론 라운드 (ANALYSIS, REBUTTAL, SYNTHESIS)", example = "ANALYSIS")
	String round,

	@Schema(description = "라운드 메시지 내용", example = "건강 관점 분석입니다.")
	String content,

	@Schema(description = "생성 시각", example = "2026-05-08T09:00:00Z")
	Instant createdAt
) {

	public static DiscussionMessageResult from(AgentDiscussionMessage message) {
		return new DiscussionMessageResult(
			message.getId(),
			message.getPersona() != null ? message.getPersona().getId() : null,
			message.getPersona() != null ? message.getPersona().getName() : null,
			message.getRound().name(),
			message.getContent(),
			message.getCreatedAt()
		);
	}
}
