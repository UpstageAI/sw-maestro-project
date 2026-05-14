package com.soma.ai13be.chat.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "메시지 전송 요청")
public record SendChatMessageCommand(
	@Schema(description = "메시지 내용", example = "나 요즘 피곤해")
	String content
) {
}
