package com.soma.ai13be.discussion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

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
import com.soma.ai13be.discussion.repository.AgentDiscussionMessageRepository;
import com.soma.ai13be.discussion.repository.AgentDiscussionRepository;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;
import com.soma.ai13be.knowledge.service.KnowledgeContextBuilder;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

class DiscussionServiceTest {

	private final AgentDiscussionRepository discussionRepository = org.mockito.Mockito.mock(AgentDiscussionRepository.class);
	private final AgentDiscussionMessageRepository messageRepository = org.mockito.Mockito.mock(AgentDiscussionMessageRepository.class);
	private final PersonaRepository personaRepository = org.mockito.Mockito.mock(PersonaRepository.class);
	private final KnowledgeNodeRepository knowledgeNodeRepository = org.mockito.Mockito.mock(KnowledgeNodeRepository.class);
	private final KnowledgeContextBuilder knowledgeContextBuilder = org.mockito.Mockito.mock(KnowledgeContextBuilder.class);
	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);
	private final DiscussionFailureRecorder failureRecorder = org.mockito.Mockito.mock(DiscussionFailureRecorder.class);

	private final DiscussionService service = new DiscussionService(
		discussionRepository,
		messageRepository,
		personaRepository,
		knowledgeNodeRepository,
		knowledgeContextBuilder,
		solarApiClient,
		failureRecorder
	);

	@Test
	void runsThreeRoundDiscussionWithSelectedPersonas() {
		Persona health = persona("health");
		Persona study = persona("study");
		KnowledgeNode node = node("피로 기록", "최근 5시간 수면");

		when(knowledgeNodeRepository.findById(1L)).thenReturn(Optional.of(node));
		when(personaRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> inv.getArgument(0));
		when(messageRepository.save(any(AgentDiscussionMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(knowledgeContextBuilder.buildContextMessage("health")).thenReturn(Optional.of(SolarChatMessage.system("health context")));
		when(knowledgeContextBuilder.buildContextMessage("study")).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("health analysis"))
			.thenReturn(response("study analysis"))
			.thenReturn(response("health rebuttal"))
			.thenReturn(response("study rebuttal"))
			.thenReturn(response("요약:\n수면과 학습 부담이 함께 작용했습니다.\n\n실행 계획:\n1. 수면 시간을 기록합니다."));

		AgentDiscussion discussion = service.createDiscussion(" 피로 원인 분석 ", 1L, List.of(1L, 2L));

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.COMPLETED);
		assertThat(discussion.getTitle()).isEqualTo("피로 원인 분석");
		assertThat(discussion.getTriggerNode()).isEqualTo(node);
		assertThat(discussion.getSummary()).contains("수면과 학습 부담");
		assertThat(discussion.getActionPlan()).contains("수면 시간을 기록");

		ArgumentCaptor<AgentDiscussionMessage> messageCaptor = ArgumentCaptor.forClass(AgentDiscussionMessage.class);
		verify(messageRepository, org.mockito.Mockito.times(5)).save(messageCaptor.capture());
		assertThat(messageCaptor.getAllValues())
			.extracting(AgentDiscussionMessage::getRound)
			.containsExactly(
				DiscussionRound.ANALYSIS,
				DiscussionRound.ANALYSIS,
				DiscussionRound.REBUTTAL,
				DiscussionRound.REBUTTAL,
				DiscussionRound.SYNTHESIS
			);
	}

	@Test
	void usesAllEnabledPersonasWhenPersonaIdsAreMissing() {
		Persona health = persona("health");
		Persona study = persona("study");
		when(personaRepository.findByEnabledTrueOrderByDomainNameAsc()).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> inv.getArgument(0));
		when(messageRepository.save(any(AgentDiscussionMessage.class))).thenAnswer(inv -> inv.getArgument(0));
		when(knowledgeContextBuilder.buildContextMessage(any())).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("health analysis"))
			.thenReturn(response("study analysis"))
			.thenReturn(response("health rebuttal"))
			.thenReturn(response("study rebuttal"))
			.thenReturn(response("요약:\n최종 요약\n\n실행 계획:\n1. 행동"));

		AgentDiscussion discussion = service.createDiscussion("주제", null, null);

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.COMPLETED);
		verify(personaRepository).findByEnabledTrueOrderByDomainNameAsc();
	}

	@Test
	void rejectsBlankTopic() {
		assertThatThrownBy(() -> service.createDiscussion(" ", null, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("topic");
	}

	@Test
	void rejectsWhenLessThanTwoPersonasParticipate() {
		when(personaRepository.findAllById(List.of(1L))).thenReturn(List.of(persona("health")));

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("at least 2");
	}

	@Test
	void rejectsMissingPersonaId() {
		when(personaRepository.findAllById(List.of(1L, 99L))).thenReturn(List.of(persona("health")));

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L, 99L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.PERSONA_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void rejectsMissingKnowledgeNode() {
		when(knowledgeNodeRepository.findById(99L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.createDiscussion("주제", 99L, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.KNOWLEDGE_NODE_NOT_FOUND)
			.hasMessageContaining("99");
	}

	@Test
	void rejectsEmptySolarResponse() {
		Persona health = persona("health");
		Persona study = persona("study");
		when(personaRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> {
			AgentDiscussion discussion = inv.getArgument(0);
			ReflectionTestUtils.setField(discussion, "id", 10L);
			return discussion;
		});
		when(knowledgeContextBuilder.buildContextMessage(any())).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class))).thenReturn(emptyResponse());

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.SOLAR_RESPONSE_EMPTY);
		verify(failureRecorder).recordFailure(10L, "Solar API returned empty response");
	}

	@Test
	void rejectsNullSolarResponseAndRecordsFailure() {
		Persona health = persona("health");
		Persona study = persona("study");
		when(personaRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> {
			AgentDiscussion discussion = inv.getArgument(0);
			ReflectionTestUtils.setField(discussion, "id", 11L);
			return discussion;
		});
		when(knowledgeContextBuilder.buildContextMessage(any())).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class))).thenReturn(null);

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.SOLAR_RESPONSE_EMPTY)
			.hasMessageContaining("Solar API returned empty response");
		verify(failureRecorder).recordFailure(11L, "Solar API returned empty response");
	}

	@Test
	void rejectsSolarTransportFailureAndRecordsFailure() {
		Persona health = persona("health");
		Persona study = persona("study");
		when(personaRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(health, study));
		when(discussionRepository.save(any(AgentDiscussion.class))).thenAnswer(inv -> {
			AgentDiscussion discussion = inv.getArgument(0);
			ReflectionTestUtils.setField(discussion, "id", 12L);
			return discussion;
		});
		when(knowledgeContextBuilder.buildContextMessage(any())).thenReturn(Optional.empty());
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenThrow(new RuntimeException("connection refused"));

		assertThatThrownBy(() -> service.createDiscussion("주제", null, List.of(1L, 2L)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.SOLAR_RESPONSE_EMPTY)
			.hasMessageContaining("Solar API request failed");
		verify(failureRecorder).recordFailure(12L, "Solar API request failed");
	}

	@Test
	void returnsDiscussionMessagesInStoredOrder() {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.title("주제")
			.status(DiscussionStatus.COMPLETED)
			.summary("요약")
			.actionPlan("실행")
			.build();
		AgentDiscussionMessage message = AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona("health"))
			.round(DiscussionRound.ANALYSIS)
			.content("분석")
			.build();
		when(discussionRepository.findById(1L)).thenReturn(Optional.of(discussion));
		when(messageRepository.findByDiscussionOrderByCreatedAtAscIdAsc(discussion)).thenReturn(List.of(message));

		List<AgentDiscussionMessage> messages = service.getMessages(1L);

		assertThat(messages).containsExactly(message);
	}

	private Persona persona(String domainName) {
		Persona persona = Persona.builder()
			.domainName(domainName)
			.name(domainName + " Persona")
			.systemPrompt(domainName + " prompt")
			.builtIn(false)
			.enabled(true)
			.build();
		long id = switch (domainName) {
			case "health" -> 1L;
			case "study" -> 2L;
			default -> 3L;
		};
		ReflectionTestUtils.setField(persona, "id", id);
		return persona;
	}

	private KnowledgeNode node(String title, String content) {
		KnowledgeNode node = KnowledgeNode.builder()
			.title(title)
			.content(content)
			.domainName("health")
			.nodeType("symptom")
			.analyzed(true)
			.build();
		ReflectionTestUtils.setField(node, "id", 1L);
		return node;
	}

	private SolarChatResponse response(String content) {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(0, SolarChatMessage.assistant(content), "stop")),
			new SolarChatResponse.Usage(5, 10, 15)
		);
	}

	private SolarChatResponse emptyResponse() {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(0, null, "stop")),
			new SolarChatResponse.Usage(5, 0, 5)
		);
	}
}
