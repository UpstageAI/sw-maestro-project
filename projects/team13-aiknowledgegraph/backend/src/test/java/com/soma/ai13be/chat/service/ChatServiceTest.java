package com.soma.ai13be.chat.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.soma.ai13be.chat.entity.ChatMessage;
import com.soma.ai13be.chat.entity.ChatMessageRole;
import com.soma.ai13be.chat.entity.ChatSession;
import com.soma.ai13be.chat.repository.ChatMessageRepository;
import com.soma.ai13be.chat.repository.ChatSessionRepository;
import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

class ChatServiceTest {

	private final ChatSessionRepository sessionRepository = org.mockito.Mockito.mock(ChatSessionRepository.class);
	private final ChatMessageRepository messageRepository = org.mockito.Mockito.mock(ChatMessageRepository.class);
	private final PersonaRepository personaRepository = org.mockito.Mockito.mock(PersonaRepository.class);
	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);
	private final com.soma.ai13be.knowledge.service.KnowledgeContextBuilder knowledgeContextBuilder =
		org.mockito.Mockito.mock(com.soma.ai13be.knowledge.service.KnowledgeContextBuilder.class);
	private final ChatService service = new ChatService(sessionRepository, messageRepository, personaRepository, solarApiClient, knowledgeContextBuilder);

	// ── createSession ───────────────────────────────────────────────────────────

	@Test
	void createsSessionForExistingPersona() {
		Persona persona = persona("health");
		when(personaRepository.findById(1L)).thenReturn(Optional.of(persona));
		when(sessionRepository.save(any(ChatSession.class)))
			.thenAnswer(inv -> inv.getArgument(0));

		ChatSession session = service.createSession(1L, "나의 건강 일지");

		assertThat(session.getPersona()).isEqualTo(persona);
		assertThat(session.getTitle()).isEqualTo("나의 건강 일지");
	}

	@Test
	void rejectsSessionForNonExistentPersona() {
		when(personaRepository.findById(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.createSession(99L, "제목"))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void rejectsSessionWithBlankTitle() {
		assertThatThrownBy(() -> service.createSession(1L, "  "))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("title");
	}

	// ── sendMessage ─────────────────────────────────────────────────────────────

	@Test
	void sendsFirstMessageAndReturnsAssistantReply() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		when(sessionRepository.findByIdWithLock(1L)).thenReturn(Optional.of(session));
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
		when(messageRepository.countBySession(session)).thenReturn(0L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(solarResponse("건강 관련 답변입니다."));

		ChatMessage reply = service.sendMessage(1L, "나 요즘 피곤해");

		assertThat(reply.getRole()).isEqualTo(ChatMessageRole.ASSISTANT);
		assertThat(reply.getContent()).isEqualTo("건강 관련 답변입니다.");
		assertThat(reply.getSequence()).isEqualTo(1);
	}

	@Test
	void includesConversationHistoryInApiRequest() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		ChatMessage prevUser = chatMessage(session, 0, ChatMessageRole.USER, "이전 질문");
		ChatMessage prevAssist = chatMessage(session, 1, ChatMessageRole.ASSISTANT, "이전 답변");

		when(sessionRepository.findByIdWithLock(1L)).thenReturn(Optional.of(session));
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
		when(messageRepository.countBySession(session)).thenReturn(2L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of(prevUser, prevAssist));
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(solarResponse("새 답변"));

		service.sendMessage(1L, "새 질문");

		ArgumentCaptor<SolarChatRequest> captor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(captor.capture());

		List<SolarChatMessage> messages = captor.getValue().messages();
		// system + prev user + prev assistant + new user
		assertThat(messages).hasSize(4);
		assertThat(messages.get(0).role()).isEqualTo("system");
		assertThat(messages.get(0).content()).isEqualTo("health system prompt");
		assertThat(messages.get(1).role()).isEqualTo("user");
		assertThat(messages.get(1).content()).isEqualTo("이전 질문");
		assertThat(messages.get(2).role()).isEqualTo("assistant");
		assertThat(messages.get(2).content()).isEqualTo("이전 답변");
		assertThat(messages.get(3).role()).isEqualTo("user");
		assertThat(messages.get(3).content()).isEqualTo("새 질문");
	}

	@Test
	void assignsSequentialMessageNumbers() {
		ChatSession session = sessionWithPersona("health", "prompt");
		when(sessionRepository.findByIdWithLock(1L)).thenReturn(Optional.of(session));
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
		when(messageRepository.countBySession(session)).thenReturn(4L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(solarApiClient.chatCompletion(any())).thenReturn(solarResponse("답변"));

		ArgumentCaptor<ChatMessage> captor = ArgumentCaptor.forClass(ChatMessage.class);
		when(messageRepository.save(captor.capture())).thenAnswer(inv -> inv.getArgument(0));

		service.sendMessage(1L, "질문");

		List<ChatMessage> saved = captor.getAllValues();
		assertThat(saved).hasSize(2);
		assertThat(saved.get(0).getSequence()).isEqualTo(4); // USER
		assertThat(saved.get(1).getSequence()).isEqualTo(5); // ASSISTANT
	}

	@Test
	void rejectsSendMessageForNonExistentSession() {
		when(sessionRepository.findByIdWithLock(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.sendMessage(99L, "질문"))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.CHAT_SESSION_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void rejectsBlankUserMessage() {
		assertThatThrownBy(() -> service.sendMessage(1L, "  "))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("content");
	}

	@Test
	void throwsSolarResponseEmptyWhenApiReturnsNullContent() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		when(sessionRepository.findByIdWithLock(1L)).thenReturn(Optional.of(session));
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(java.util.Optional.empty());
		when(messageRepository.countBySession(session)).thenReturn(0L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(new SolarChatResponse("id", "obj", 0L, "model", List.of(), null));

		assertThatThrownBy(() -> service.sendMessage(1L, "질문"))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.SOLAR_RESPONSE_EMPTY);
	}

	// ── getHistory ───────────────────────────────────────────────────────────────

	@Test
	void returnsMessagesOrderedBySequence() {
		ChatSession session = sessionWithPersona("health", "prompt");
		ChatMessage msg0 = chatMessage(session, 0, ChatMessageRole.USER, "질문");
		ChatMessage msg1 = chatMessage(session, 1, ChatMessageRole.ASSISTANT, "답변");

		when(sessionRepository.findById(1L)).thenReturn(Optional.of(session));
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of(msg0, msg1));

		List<ChatMessage> history = service.getHistory(1L);

		assertThat(history).hasSize(2);
		assertThat(history.get(0).getSequence()).isEqualTo(0);
		assertThat(history.get(1).getSequence()).isEqualTo(1);
	}

	@Test
	void returnsEmptyHistoryForNewSession() {
		ChatSession session = sessionWithPersona("health", "prompt");
		when(sessionRepository.findById(1L)).thenReturn(Optional.of(session));
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());

		List<ChatMessage> history = service.getHistory(1L);

		assertThat(history).isEmpty();
	}

	@Test
	void rejectsGetHistoryForNonExistentSession() {
		when(sessionRepository.findById(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.getHistory(99L))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.CHAT_SESSION_NOT_FOUND)
			.hasMessageContaining("99");
	}

	// ── knowledge context injection ─────────────────────────────────────────────

	@Test
	void injectsKnowledgeContextBetweenSystemPromptAndHistory() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		when(sessionRepository.findByIdWithLock(1L)).thenReturn(Optional.of(session));
		when(knowledgeContextBuilder.buildContextMessage("health"))
			.thenReturn(Optional.of(SolarChatMessage.system("[사용자 지식 그래프 - health 도메인]\n1. 제목: 수면\n   내용: 5시간")));
		when(messageRepository.countBySession(session)).thenReturn(0L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(solarResponse("답변"));

		service.sendMessage(1L, "질문");

		ArgumentCaptor<SolarChatRequest> captor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(captor.capture());

		List<SolarChatMessage> messages = captor.getValue().messages();
		// system(role) + system(knowledge) + user
		assertThat(messages).hasSize(3);
		assertThat(messages.get(0).role()).isEqualTo("system");
		assertThat(messages.get(0).content()).isEqualTo("health system prompt");
		assertThat(messages.get(1).role()).isEqualTo("system");
		assertThat(messages.get(1).content()).contains("[사용자 지식 그래프 - health 도메인]");
		assertThat(messages.get(2).role()).isEqualTo("user");
		assertThat(messages.get(2).content()).isEqualTo("질문");
	}

	@Test
	void skipsKnowledgeContextWhenNoNodes() {
		ChatSession session = sessionWithPersona("health", "health system prompt");
		when(sessionRepository.findByIdWithLock(1L)).thenReturn(Optional.of(session));
		when(knowledgeContextBuilder.buildContextMessage("health"))
			.thenReturn(Optional.empty());
		when(messageRepository.countBySession(session)).thenReturn(0L);
		when(messageRepository.findBySessionOrderBySequenceAsc(session)).thenReturn(List.of());
		when(messageRepository.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(solarResponse("답변"));

		service.sendMessage(1L, "질문");

		ArgumentCaptor<SolarChatRequest> captor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(captor.capture());

		List<SolarChatMessage> messages = captor.getValue().messages();
		// system(role) + user only
		assertThat(messages).hasSize(2);
		assertThat(messages.get(0).content()).isEqualTo("health system prompt");
		assertThat(messages.get(1).role()).isEqualTo("user");
	}

	// ── helpers ──────────────────────────────────────────────────────────────────

	private Persona persona(String domain) {
		return Persona.builder()
			.domainName(domain)
			.name(domain + " Persona")
			.systemPrompt(domain + " system prompt")
			.builtIn(false)
			.enabled(true)
			.build();
	}

	private ChatSession sessionWithPersona(String domain, String systemPrompt) {
		Persona p = Persona.builder()
			.domainName(domain)
			.name(domain + " Persona")
			.systemPrompt(systemPrompt)
			.builtIn(false)
			.enabled(true)
			.build();
		return ChatSession.builder()
			.persona(p)
			.title(domain + " chat")
			.build();
	}

	private ChatMessage chatMessage(ChatSession session, int seq, ChatMessageRole role, String content) {
		return ChatMessage.builder()
			.session(session)
			.sequence(seq)
			.role(role)
			.content(content)
			.build();
	}

	private SolarChatResponse solarResponse(String content) {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(
				0,
				SolarChatMessage.assistant(content),
				"stop"
			)),
			new SolarChatResponse.Usage(5, 10, 15)
		);
	}
}
