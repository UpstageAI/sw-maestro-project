package com.soma.ai13be.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.client.dto.SolarChatResponse;
import com.soma.ai13be.knowledge.dto.request.ExtractKnowledgeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeExtractionResult;
import com.soma.ai13be.knowledge.entity.KnowledgeEdge;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

class KnowledgeExtractionServiceTest {

	private final SolarApiClient solarApiClient = org.mockito.Mockito.mock(SolarApiClient.class);
	private final KnowledgeGraphService knowledgeGraphService = org.mockito.Mockito.mock(KnowledgeGraphService.class);
	private final PersonaRepository personaRepository = org.mockito.Mockito.mock(PersonaRepository.class);
	private final KnowledgeExtractionService service = new KnowledgeExtractionService(
		solarApiClient,
		knowledgeGraphService,
		personaRepository,
		new ObjectMapper()
	);

	@Test
	void extractsPersonalKnowledgeFromTextAndStoresNodesAndEdges() {
		when(personaRepository.findByEnabledTrueOrderByDomainNameAsc())
			.thenReturn(List.of(persona("건강"), persona("학습")));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("""
				{
				  "nodes": [
				    {
				      "title": "수면 부족",
				      "content": "최근 수면 시간이 5시간 정도로 줄었다.",
				      "domainName": "건강",
				      "nodeType": "USER_INPUT"
				    },
				    {
				      "title": "집중도 저하",
				      "content": "낮 시간대 공부 집중이 잘 되지 않는다.",
				      "domainName": "학습",
				      "nodeType": "USER_INPUT"
				    }
				  ],
				  "edges": [
				    {
				      "sourceNodeIndex": 0,
				      "targetNodeIndex": 1,
				      "relationType": "AFFECTS",
				      "confidence": 0.7800,
				      "evidenceText": "사용자가 수면 부족과 공부 집중 저하를 같은 맥락에서 언급함"
				    }
				  ]
				}
				"""));
		KnowledgeNode sleepNode = node(1L, "수면 부족", "건강");
		KnowledgeNode focusNode = node(2L, "집중도 저하", "학습");
		when(knowledgeGraphService.createNode(any()))
			.thenReturn(sleepNode)
			.thenReturn(focusNode);
		when(knowledgeGraphService.createEdge(any()))
			.thenReturn(edge(10L, sleepNode, focusNode));

		KnowledgeExtractionResult result = service.extractAndStore(new ExtractKnowledgeCommand(
			"요즘 잠을 5시간밖에 못 자고 낮에 공부 집중이 잘 안 돼."
		));

		assertThat(result.nodes()).extracting(node -> node.title())
			.containsExactly("수면 부족", "집중도 저하");
		assertThat(result.edges()).extracting(edge -> edge.relationType())
			.containsExactly("AFFECTS");
		assertThat(result.suggestedDomains()).isEmpty();

		ArgumentCaptor<SolarChatRequest> requestCaptor = ArgumentCaptor.forClass(SolarChatRequest.class);
		verify(solarApiClient).chatCompletion(requestCaptor.capture());
		assertThat(requestCaptor.getValue().messages().get(0).content())
			.contains("- 건강", "- 학습")
			.doesNotContain("취미|업무|기타");
	}

	@Test
	void returnsSuggestedDomainWithoutStoringNodeWhenNoPersonaDomainMatches() {
		when(personaRepository.findByEnabledTrueOrderByDomainNameAsc())
			.thenReturn(List.of(persona("건강"), persona("학습")));
		when(solarApiClient.chatCompletion(any(SolarChatRequest.class)))
			.thenReturn(response("""
				{
				  "nodes": [
				    {
				      "title": "배포 일정 부담",
				      "content": "프로젝트 배포 일정 때문에 스트레스를 느낌",
				      "domainName": null,
				      "suggestedDomainName": "업무",
				      "nodeType": "USER_INPUT"
				    }
				  ],
				  "edges": []
				}
				"""));

		KnowledgeExtractionResult result = service.extractAndStore(new ExtractKnowledgeCommand(
			"프로젝트 배포 일정 때문에 스트레스가 크다."
		));

		assertThat(result.nodes()).isEmpty();
		assertThat(result.edges()).isEmpty();
		assertThat(result.suggestedDomains()).containsExactly("업무");
		verify(knowledgeGraphService, never()).createNode(any());
	}

	private SolarChatResponse response(String content) {
		return new SolarChatResponse(
			"chatcmpl-test",
			"chat.completion",
			1710000000L,
			"solar-pro3",
			List.of(new SolarChatResponse.Choice(
				0,
				com.soma.ai13be.common.client.dto.SolarChatMessage.assistant(content),
				"stop"
			)),
			null
		);
	}

	private KnowledgeNode node(Long id, String title, String domainName) {
		KnowledgeNode node = KnowledgeNode.builder()
			.title(title)
			.content(title + " content")
			.domainName(domainName)
			.nodeType("USER_INPUT")
			.analyzed(false)
			.build();
		org.springframework.test.util.ReflectionTestUtils.setField(node, "id", id);
		return node;
	}

	private KnowledgeEdge edge(Long id, KnowledgeNode sourceNode, KnowledgeNode targetNode) {
		KnowledgeEdge edge = KnowledgeEdge.builder()
			.sourceNode(sourceNode)
			.targetNode(targetNode)
			.relationType("AFFECTS")
			.confidence(new BigDecimal("0.7800"))
			.evidenceText("사용자가 수면 부족과 공부 집중 저하를 같은 맥락에서 언급함")
			.build();
		org.springframework.test.util.ReflectionTestUtils.setField(edge, "id", id);
		return edge;
	}

	private Persona persona(String domainName) {
		return Persona.builder()
			.domainName(domainName)
			.name(domainName + " Persona")
			.systemPrompt(domainName + " prompt")
			.builtIn(true)
			.enabled(true)
			.build();
	}
}
