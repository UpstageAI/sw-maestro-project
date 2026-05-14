package com.soma.ai13be.chat.dto.response;

import java.time.Instant;

import com.soma.ai13be.chat.entity.ChatSession;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "채팅 세션 응답")
public record ChatSessionResult(
	@Schema(description = "채팅 세션 ID", example = "1")
	Long id,

	@Schema(description = "연결된 페르소나 ID", example = "2")
	Long personaId,

	@Schema(description = "페르소나 도메인명", example = "health")
	String personaDomain,

	@Schema(description = "채팅방 제목", example = "나의 건강 일지")
	String title,

	@Schema(description = "생성 시각")
	Instant createdAt
) {

	public static ChatSessionResult from(ChatSession session) {
		return new ChatSessionResult(
			session.getId(),
			session.getPersona() != null ? session.getPersona().getId() : null,
			session.getPersona() != null ? session.getPersona().getDomainName() : null,
			session.getTitle(),
			session.getCreatedAt()
		);
	}
}
