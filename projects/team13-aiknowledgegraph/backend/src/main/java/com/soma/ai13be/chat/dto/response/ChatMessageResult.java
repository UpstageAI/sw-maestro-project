package com.soma.ai13be.chat.dto.response;

import java.time.Instant;

import com.soma.ai13be.chat.entity.ChatMessage;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "채팅 메시지 응답")
public record ChatMessageResult(
	@Schema(description = "메시지 ID", example = "10")
	Long id,

	@Schema(description = "세션 안에서의 메시지 순서", example = "0")
	int sequence,

	@Schema(description = "메시지 역할 (USER, ASSISTANT, SYSTEM)", example = "USER")
	String role,

	@Schema(description = "메시지 내용", example = "나 요즘 피곤해")
	String content,

	@Schema(description = "생성 시각")
	Instant createdAt
) {

	public static ChatMessageResult from(ChatMessage message) {
		return new ChatMessageResult(
			message.getId(),
			message.getSequence(),
			message.getRole().name(),
			message.getContent(),
			message.getCreatedAt()
		);
	}
}
