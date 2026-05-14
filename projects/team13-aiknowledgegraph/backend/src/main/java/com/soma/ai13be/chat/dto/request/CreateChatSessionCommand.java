package com.soma.ai13be.chat.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "채팅 세션 생성 요청")
public record CreateChatSessionCommand(
	@Schema(description = "페르소나 ID", example = "1")
	Long personaId,

	@Schema(description = "채팅방 제목", example = "나의 건강 일지")
	String title
) {
}
