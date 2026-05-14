package com.soma.ai13be.chat.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.soma.ai13be.chat.entity.ChatMessage;
import com.soma.ai13be.chat.entity.ChatMessageRole;
import com.soma.ai13be.chat.entity.ChatSession;
import com.soma.ai13be.chat.service.ChatService;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.common.exception.GlobalExceptionHandler;
import com.soma.ai13be.persona.entity.Persona;

class ChatControllerTest {

	private final ChatService chatService = org.mockito.Mockito.mock(ChatService.class);
	private final MockMvc mockMvc = MockMvcBuilders.standaloneSetup(new ChatController(chatService))
		.setControllerAdvice(new GlobalExceptionHandler())
		.build();

	// ── POST /api/chats ──────────────────────────────────────────────────────────

	@Test
	void createsSession() throws Exception {
		when(chatService.createSession(1L, "나의 건강 일지")).thenReturn(session("health", "나의 건강 일지"));

		mockMvc.perform(post("/api/chats")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "personaId": 1,
					  "title": "나의 건강 일지"
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.title").value("나의 건강 일지"))
			.andExpect(jsonPath("$.personaDomain").value("health"));
	}

	@Test
	void returnsNotFoundWhenPersonaDoesNotExist() throws Exception {
		when(chatService.createSession(eq(99L), any()))
			.thenThrow(new CustomException(ErrorCode.PERSONA_NOT_FOUND, "Persona not found: 99"));

		mockMvc.perform(post("/api/chats")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "personaId": 99,
					  "title": "제목"
					}
					"""))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("PERSONA_NOT_FOUND"))
			.andExpect(jsonPath("$.message").value("Persona not found: 99"));
	}

	@Test
	void returnsBadRequestWhenTitleIsBlank() throws Exception {
		when(chatService.createSession(any(), any()))
			.thenThrow(new CustomException(ErrorCode.INVALID_REQUEST, "title must not be blank"));

		mockMvc.perform(post("/api/chats")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "personaId": 1,
					  "title": " "
					}
					"""))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
	}

	// ── POST /api/chats/{sessionId}/messages ────────────────────────────────────

	@Test
	void sendsMessageAndReturnsAssistantReply() throws Exception {
		ChatSession session = session("health", "건강 채팅");
		ChatMessage reply = chatMessage(session, 1, ChatMessageRole.ASSISTANT, "건강 관련 답변입니다.");
		when(chatService.sendMessage(1L, "나 요즘 피곤해")).thenReturn(reply);

		mockMvc.perform(post("/api/chats/{sessionId}/messages", 1L)
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "content": "나 요즘 피곤해"
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.role").value("ASSISTANT"))
			.andExpect(jsonPath("$.content").value("건강 관련 답변입니다."))
			.andExpect(jsonPath("$.sequence").value(1));
	}

	@Test
	void returnsNotFoundWhenSessionDoesNotExist() throws Exception {
		when(chatService.sendMessage(eq(99L), any()))
			.thenThrow(new CustomException(ErrorCode.CHAT_SESSION_NOT_FOUND, "Chat session not found: 99"));

		mockMvc.perform(post("/api/chats/{sessionId}/messages", 99L)
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "content": "질문"
					}
					"""))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("CHAT_SESSION_NOT_FOUND"))
			.andExpect(jsonPath("$.message").value("Chat session not found: 99"));
	}

	// ── GET /api/chats/{sessionId}/messages ──────────────────────────────────────

	@Test
	void returnsMessageHistory() throws Exception {
		ChatSession session = session("health", "건강 채팅");
		ChatMessage userMsg = chatMessage(session, 0, ChatMessageRole.USER, "나 요즘 피곤해");
		ChatMessage assistantMsg = chatMessage(session, 1, ChatMessageRole.ASSISTANT, "충분한 수면을 취하세요.");

		when(chatService.getHistory(1L)).thenReturn(List.of(userMsg, assistantMsg));

		mockMvc.perform(get("/api/chats/{sessionId}/messages", 1L))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[0].role").value("USER"))
			.andExpect(jsonPath("$[0].content").value("나 요즘 피곤해"))
			.andExpect(jsonPath("$[0].sequence").value(0))
			.andExpect(jsonPath("$[1].role").value("ASSISTANT"))
			.andExpect(jsonPath("$[1].content").value("충분한 수면을 취하세요."))
			.andExpect(jsonPath("$[1].sequence").value(1));
	}

	@Test
	void returnsEmptyArrayForNewSession() throws Exception {
		when(chatService.getHistory(1L)).thenReturn(List.of());

		mockMvc.perform(get("/api/chats/{sessionId}/messages", 1L))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$").isArray())
			.andExpect(jsonPath("$").isEmpty());
	}

	// ── helpers ──────────────────────────────────────────────────────────────────

	private Persona persona(String domain) {
		return Persona.builder()
			.domainName(domain)
			.name(domain + " Persona")
			.systemPrompt(domain + " prompt")
			.builtIn(false)
			.enabled(true)
			.build();
	}

	private ChatSession session(String domain, String title) {
		return ChatSession.builder()
			.persona(persona(domain))
			.title(title)
			.build();
	}

	private ChatMessage chatMessage(ChatSession session, int sequence, ChatMessageRole role, String content) {
		return ChatMessage.builder()
			.session(session)
			.sequence(sequence)
			.role(role)
			.content(content)
			.build();
	}
}
