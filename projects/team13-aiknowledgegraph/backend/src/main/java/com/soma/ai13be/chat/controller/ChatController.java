package com.soma.ai13be.chat.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.soma.ai13be.chat.dto.request.CreateChatSessionCommand;
import com.soma.ai13be.chat.dto.request.SendChatMessageCommand;
import com.soma.ai13be.chat.dto.response.ChatMessageResult;
import com.soma.ai13be.chat.dto.response.ChatSessionResult;
import com.soma.ai13be.chat.entity.ChatMessage;
import com.soma.ai13be.chat.entity.ChatSession;
import com.soma.ai13be.chat.service.ChatService;
import com.soma.ai13be.common.dto.ErrorResponse;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

@Tag(name = "Chat", description = "페르소나 채팅 API")
@RestController
@RequestMapping("/api/chats")
@RequiredArgsConstructor
public class ChatController {

	private final ChatService chatService;

	@Operation(
		summary = "채팅 세션 생성",
		description = "페르소나와 연결된 채팅 세션을 생성합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "201", description = "세션 생성 성공",
			content = @Content(schema = @Schema(implementation = ChatSessionResult.class))),
		@ApiResponse(responseCode = "400", description = "title이 null 또는 공백",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "404", description = "페르소나를 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping
	public ResponseEntity<ChatSessionResult> createSession(@RequestBody CreateChatSessionCommand command) {
		ChatSession session = chatService.createSession(command.personaId(), command.title());
		return ResponseEntity.status(HttpStatus.CREATED).body(ChatSessionResult.from(session));
	}

	@Operation(
		summary = "메시지 전송",
		description = "사용자 메시지를 전송하고 페르소나 AI 응답을 반환합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "201", description = "메시지 전송 성공",
			content = @Content(schema = @Schema(implementation = ChatMessageResult.class))),
		@ApiResponse(responseCode = "400", description = "content가 null 또는 공백",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "404", description = "채팅 세션을 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "Solar API 응답 오류",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping("/{sessionId}/messages")
	public ResponseEntity<ChatMessageResult> sendMessage(
		@Parameter(description = "채팅 세션 ID", example = "1")
		@PathVariable Long sessionId,
		@RequestBody SendChatMessageCommand command
	) {
		ChatMessage reply = chatService.sendMessage(sessionId, command.content());
		return ResponseEntity.status(HttpStatus.CREATED).body(ChatMessageResult.from(reply));
	}

	@Operation(
		summary = "채팅 히스토리 조회",
		description = "해당 세션의 전체 메시지를 순서대로 반환합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "히스토리 조회 성공",
			content = @Content(array = @ArraySchema(schema = @Schema(implementation = ChatMessageResult.class)))),
		@ApiResponse(responseCode = "404", description = "채팅 세션을 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@GetMapping("/{sessionId}/messages")
	public ResponseEntity<List<ChatMessageResult>> getHistory(
		@Parameter(description = "채팅 세션 ID", example = "1")
		@PathVariable Long sessionId
	) {
		List<ChatMessageResult> history = chatService.getHistory(sessionId).stream()
			.map(ChatMessageResult::from)
			.toList();
		return ResponseEntity.ok(history);
	}
}
