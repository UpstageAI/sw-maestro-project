package com.soma.ai13be.discussion.service;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.entity.DiscussionRound;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.discussion.prompt.DiscussionPromptTemplates;
import com.soma.ai13be.discussion.repository.AgentDiscussionMessageRepository;
import com.soma.ai13be.discussion.repository.AgentDiscussionRepository;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;
import com.soma.ai13be.knowledge.service.KnowledgeContextBuilder;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class DiscussionService {

	private static final double DISCUSSION_TEMPERATURE = 0.4;
	private static final int DISCUSSION_MAX_TOKENS = 1200;

	private final AgentDiscussionRepository discussionRepository;
	private final AgentDiscussionMessageRepository messageRepository;
	private final PersonaRepository personaRepository;
	private final KnowledgeNodeRepository knowledgeNodeRepository;
	private final KnowledgeContextBuilder knowledgeContextBuilder;
	private final SolarApiClient solarApiClient;
	private final DiscussionFailureRecorder failureRecorder;

	public AgentDiscussion createDiscussion(String topic, Long knowledgeNodeId, List<Long> personaIds) {
		String normalizedTopic = normalizeTopic(topic);
		KnowledgeNode triggerNode = resolveTriggerNode(knowledgeNodeId);
		List<Persona> personas = resolvePersonas(personaIds);

		AgentDiscussion discussion = discussionRepository.save(AgentDiscussion.builder()
			.triggerNode(triggerNode)
			.status(DiscussionStatus.REQUESTED)
			.title(normalizedTopic)
			.build());

		try {
			discussion.markRunning();
			discussionRepository.save(discussion);
			List<AgentDiscussionMessage> analyses = runAnalysisRound(discussion, normalizedTopic, triggerNode, personas);
			List<AgentDiscussionMessage> rebuttals = runRebuttalRound(discussion, normalizedTopic, personas, analyses);
			AgentDiscussionMessage synthesis = runSynthesisRound(discussion, normalizedTopic, analyses, rebuttals);
			DiscussionSummary summary = parseSynthesis(synthesis.getContent());
			discussion.markCompleted(summary.summary(), summary.actionPlan());
			return discussionRepository.save(discussion);
		} catch (RuntimeException ex) {
			discussion.markFailed(ex.getMessage());
			failureRecorder.recordFailure(discussion.getId(), ex.getMessage());
			throw ex;
		}
	}

	@Transactional(readOnly = true)
	public AgentDiscussion getDiscussion(Long discussionId) {
		return discussionRepository.findById(discussionId)
			.orElseThrow(() -> new CustomException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not found: " + discussionId));
	}

	@Transactional(readOnly = true)
	public List<AgentDiscussionMessage> getMessages(Long discussionId) {
		AgentDiscussion discussion = getDiscussion(discussionId);
		return getMessages(discussion);
	}

	@Transactional(readOnly = true)
	public List<AgentDiscussionMessage> getMessages(AgentDiscussion discussion) {
		return messageRepository.findByDiscussionOrderByCreatedAtAscIdAsc(discussion);
	}

	private List<AgentDiscussionMessage> runAnalysisRound(
		AgentDiscussion discussion,
		String topic,
		KnowledgeNode triggerNode,
		List<Persona> personas
	) {
		List<AgentDiscussionMessage> messages = new ArrayList<>();
		String triggerNodeContext = formatTriggerNode(triggerNode);
		for (Persona persona : personas) {
			List<SolarChatMessage> requestMessages = personaMessages(persona);
			knowledgeContextBuilder.buildContextMessage(persona.getDomainName()).ifPresent(requestMessages::add);
			requestMessages.add(SolarChatMessage.user(DiscussionPromptTemplates.analysisUserPrompt(topic, triggerNodeContext)));
			String content = callSolar(requestMessages);
			messages.add(saveMessage(discussion, persona, DiscussionRound.ANALYSIS, content));
		}
		return messages;
	}

	private List<AgentDiscussionMessage> runRebuttalRound(
		AgentDiscussion discussion,
		String topic,
		List<Persona> personas,
		List<AgentDiscussionMessage> analyses
	) {
		List<AgentDiscussionMessage> messages = new ArrayList<>();
		String analysisTranscript = formatTranscript(analyses);
		for (Persona persona : personas) {
			List<SolarChatMessage> requestMessages = personaMessages(persona);
			requestMessages.add(SolarChatMessage.user(DiscussionPromptTemplates.rebuttalUserPrompt(topic, analysisTranscript)));
			String content = callSolar(requestMessages);
			messages.add(saveMessage(discussion, persona, DiscussionRound.REBUTTAL, content));
		}
		return messages;
	}

	private AgentDiscussionMessage runSynthesisRound(
		AgentDiscussion discussion,
		String topic,
		List<AgentDiscussionMessage> analyses,
		List<AgentDiscussionMessage> rebuttals
	) {
		List<SolarChatMessage> requestMessages = List.of(
			SolarChatMessage.system(DiscussionPromptTemplates.synthesisSystemPrompt()),
			SolarChatMessage.user(DiscussionPromptTemplates.synthesisUserPrompt(
				topic,
				formatTranscript(analyses),
				formatTranscript(rebuttals)
			))
		);
		String content = callSolar(requestMessages);
		return saveMessage(discussion, null, DiscussionRound.SYNTHESIS, content);
	}

	private AgentDiscussionMessage saveMessage(
		AgentDiscussion discussion,
		Persona persona,
		DiscussionRound round,
		String content
	) {
		return messageRepository.save(AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona)
			.round(round)
			.content(content)
			.build());
	}

	private String callSolar(List<SolarChatMessage> messages) {
		SolarChatRequest request = new SolarChatRequest(messages, DISCUSSION_TEMPERATURE, DISCUSSION_MAX_TOKENS);
		SolarChatResponse response;
		try {
			response = solarApiClient.chatCompletion(request);
		} catch (RuntimeException ex) {
			throw new CustomException(ErrorCode.SOLAR_RESPONSE_EMPTY, "Solar API request failed", ex);
		}
		if (response == null) {
			throw new CustomException(ErrorCode.SOLAR_RESPONSE_EMPTY, "Solar API returned empty response");
		}
		String content = response.firstContent();
		if (!StringUtils.hasText(content)) {
			throw new CustomException(ErrorCode.SOLAR_RESPONSE_EMPTY, "Solar API returned empty response");
		}
		return content.strip();
	}

	private List<SolarChatMessage> personaMessages(Persona persona) {
		List<SolarChatMessage> messages = new ArrayList<>();
		if (StringUtils.hasText(persona.getSystemPrompt())) {
			messages.add(SolarChatMessage.system(persona.getSystemPrompt()));
		}
		return messages;
	}

	private String normalizeTopic(String topic) {
		if (!StringUtils.hasText(topic)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "topic must not be blank");
		}
		return topic.strip();
	}

	private KnowledgeNode resolveTriggerNode(Long knowledgeNodeId) {
		if (knowledgeNodeId == null) {
			return null;
		}
		return knowledgeNodeRepository.findById(knowledgeNodeId)
			.orElseThrow(() -> new CustomException(ErrorCode.KNOWLEDGE_NODE_NOT_FOUND, "Knowledge node not found: " + knowledgeNodeId));
	}

	private List<Persona> resolvePersonas(List<Long> personaIds) {
		List<Persona> personas;
		if (personaIds == null || personaIds.isEmpty()) {
			personas = personaRepository.findByEnabledTrueOrderByDomainNameAsc();
		} else {
			List<Persona> foundPersonas = personaRepository.findAllById(personaIds);
			validateAllPersonaIdsExist(personaIds, foundPersonas);
			personas = foundPersonas.stream()
				.sorted(java.util.Comparator.comparing(p -> personaIds.indexOf(p.getId())))
				.toList();
		}

		if (personas.size() < 2) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "discussion requires at least 2 personas");
		}
		return personas;
	}

	private void validateAllPersonaIdsExist(List<Long> requestedIds, List<Persona> personas) {
		Set<Long> foundIds = new HashSet<>();
		for (Persona persona : personas) {
			if (persona.getId() != null) {
				foundIds.add(persona.getId());
			}
		}

		List<Long> missingIds = requestedIds.stream()
			.distinct()
			.filter(id -> !foundIds.contains(id))
			.toList();

		if (!missingIds.isEmpty()) {
			throw new CustomException(ErrorCode.PERSONA_NOT_FOUND, "Persona not found: " + missingIds.getFirst());
		}
	}

	private String formatTriggerNode(KnowledgeNode node) {
		if (node == null) {
			return null;
		}
		return "제목: %s%n도메인: %s%n유형: %s%n내용: %s".formatted(
			node.getTitle(),
			node.getDomainName(),
			node.getNodeType(),
			node.getContent()
		);
	}

	private String formatTranscript(List<AgentDiscussionMessage> messages) {
		StringBuilder sb = new StringBuilder();
		for (AgentDiscussionMessage message : messages) {
			String speaker = Optional.ofNullable(message.getPersona())
				.map(Persona::getName)
				.orElse("Synthesis");
			sb.append("[").append(speaker).append("]\n");
			sb.append(message.getContent()).append("\n\n");
		}
		return sb.toString().strip();
	}

	private DiscussionSummary parseSynthesis(String content) {
		String marker = "실행 계획:";
		int actionIndex = content.indexOf(marker);
		if (actionIndex < 0) {
			return new DiscussionSummary(content, "");
		}

		String summary = content.substring(0, actionIndex)
			.replaceFirst("^요약:\\s*", "")
			.strip();
		String actionPlan = content.substring(actionIndex + marker.length()).strip();
		return new DiscussionSummary(summary, actionPlan);
	}

	private record DiscussionSummary(String summary, String actionPlan) {
	}
}
