package com.soma.ai13be.chat.service;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.soma.ai13be.chat.entity.ChatMessage;
import com.soma.ai13be.chat.entity.ChatMessageRole;
import com.soma.ai13be.chat.entity.ChatSession;
import com.soma.ai13be.chat.repository.ChatMessageRepository;
import com.soma.ai13be.chat.repository.ChatSessionRepository;
import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.knowledge.service.KnowledgeContextBuilder;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class ChatService {

	private static final double CHAT_TEMPERATURE = 0.7;
	private static final int CHAT_MAX_TOKENS = 1000;

	private final ChatSessionRepository sessionRepository;
	private final ChatMessageRepository messageRepository;
	private final PersonaRepository personaRepository;
	private final SolarApiClient solarApiClient;
	private final KnowledgeContextBuilder knowledgeContextBuilder;

	@Transactional
	public ChatSession createSession(Long personaId, String title) {
		if (!StringUtils.hasText(title)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "title must not be blank");
		}
		Persona persona = personaRepository.findById(personaId)
			.orElseThrow(() -> new CustomException(ErrorCode.PERSONA_NOT_FOUND, "Persona not found: " + personaId));

		ChatSession session = ChatSession.builder()
			.persona(persona)
			.title(title.strip())
			.build();

		return sessionRepository.save(session);
	}

	@Transactional
	public ChatMessage sendMessage(Long sessionId, String content) {
		if (!StringUtils.hasText(content)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "content must not be blank");
		}
		ChatSession session = sessionRepository.findByIdWithLock(sessionId)
			.orElseThrow(() -> new CustomException(ErrorCode.CHAT_SESSION_NOT_FOUND, "Chat session not found: " + sessionId));

		int nextSequence = Math.toIntExact(messageRepository.countBySession(session));
		List<ChatMessage> history = messageRepository.findBySessionOrderBySequenceAsc(session);

		ChatMessage userMessage = messageRepository.save(ChatMessage.builder()
			.session(session)
			.sequence(nextSequence)
			.role(ChatMessageRole.USER)
			.content(content.strip())
			.build());

		String assistantContent = callSolarApi(session, history, userMessage);

		return messageRepository.save(ChatMessage.builder()
			.session(session)
			.sequence(nextSequence + 1)
			.role(ChatMessageRole.ASSISTANT)
			.content(assistantContent)
			.build());
	}

	@Transactional(readOnly = true)
	public List<ChatMessage> getHistory(Long sessionId) {
		ChatSession session = sessionRepository.findById(sessionId)
			.orElseThrow(() -> new CustomException(ErrorCode.CHAT_SESSION_NOT_FOUND, "Chat session not found: " + sessionId));
		return messageRepository.findBySessionOrderBySequenceAsc(session);
	}

	private String callSolarApi(ChatSession session, List<ChatMessage> history, ChatMessage userMessage) {
		List<SolarChatMessage> messages = new ArrayList<>();

		Persona persona = session.getPersona();
		if (persona != null && StringUtils.hasText(persona.getSystemPrompt())) {
			messages.add(SolarChatMessage.system(persona.getSystemPrompt()));
		}

		if (persona != null && StringUtils.hasText(persona.getDomainName())) {
			knowledgeContextBuilder.buildContextMessage(persona.getDomainName())
				.ifPresent(messages::add);
		}

		for (ChatMessage msg : history) {
			messages.add(toSolarMessage(msg));
		}
		messages.add(SolarChatMessage.user(userMessage.getContent()));

		SolarChatRequest request = new SolarChatRequest(messages, CHAT_TEMPERATURE, CHAT_MAX_TOKENS);
		String content = solarApiClient.chatCompletion(request).firstContent();
		if (!StringUtils.hasText(content)) {
			throw new CustomException(ErrorCode.SOLAR_RESPONSE_EMPTY, "Solar API returned empty response");
		}
		return content;
	}

	private SolarChatMessage toSolarMessage(ChatMessage msg) {
		return switch (msg.getRole()) {
			case USER -> SolarChatMessage.user(msg.getContent());
			case ASSISTANT -> SolarChatMessage.assistant(msg.getContent());
			case SYSTEM -> SolarChatMessage.system(msg.getContent());
		};
	}

}
