package com.soma.ai13be.knowledge.service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.soma.ai13be.common.client.SolarApiClient;
import com.soma.ai13be.common.client.dto.SolarChatMessage;
import com.soma.ai13be.common.client.dto.SolarChatRequest;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeEdgeCommand;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeNodeCommand;
import com.soma.ai13be.knowledge.dto.request.ExtractKnowledgeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeEdgeResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeExtractionResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeNodeResult;
import com.soma.ai13be.knowledge.entity.KnowledgeEdge;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.persona.entity.Persona;
import com.soma.ai13be.persona.repository.PersonaRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class KnowledgeExtractionService {

	private static final String SYSTEM_PROMPT = """
		너는 개인 지식 그래프 추출기다.
		사용자의 자유 텍스트에서 개인 지식 노드와 노드 사이의 방향성 관계만 추출한다.
		%s
		각 노드는 먼저 현재 사용 가능한 도메인 페르소나 중 가장 적절한 domainName을 선택한다.
		어떤 도메인 페르소나에도 자연스럽게 속하지 않으면 domainName은 null로 두고 suggestedDomainName에 새 도메인 이름을 제안한다.
		반드시 아래 JSON 형식만 반환하고, 설명 문장이나 마크다운 코드 블록은 포함하지 않는다.
		{
		  "nodes": [
		    {
		      "title": "짧은 노드 제목",
		      "content": "원문에 근거한 구체적 설명",
		      "domainName": "현재 사용 가능한 도메인 페르소나 이름 또는 null",
		      "suggestedDomainName": "신규 도메인 후보 또는 null",
		      "nodeType": "USER_INPUT"
		    }
		  ],
		  "edges": [
		    {
		      "sourceNodeIndex": 0,
		      "targetNodeIndex": 1,
		      "relationType": "AFFECTS|CAUSES|RELATED_TO|IMPROVES|WORSENS|TRIGGERS 중 하나",
		      "confidence": 0.0,
		      "evidenceText": "관계를 판단한 원문 근거"
		    }
		  ]
		}
		노드는 최대 5개, 엣지는 최대 6개로 제한한다.
		근거가 약한 관계는 만들지 않는다.
		""";

	private final SolarApiClient solarApiClient;
	private final KnowledgeGraphService knowledgeGraphService;
	private final PersonaRepository personaRepository;
	private final ObjectMapper objectMapper;

	@Transactional
	public KnowledgeExtractionResult extractAndStore(ExtractKnowledgeCommand command) {
		validateCommand(command);
		List<String> personaDomains = findEnabledPersonaDomains();
		Set<String> personaDomainSet = Set.copyOf(personaDomains);

		String content = solarApiClient.chatCompletion(new SolarChatRequest(
			List.of(
				SolarChatMessage.system(systemPrompt(personaDomains)),
				SolarChatMessage.user(command.text().strip())
			),
			0.0,
			1400
		)).firstContent();

		ExtractedKnowledge extractedKnowledge = parseExtraction(content);
		List<String> suggestedDomains = suggestedDomains(extractedKnowledge.nodes(), personaDomainSet);
		SavedNodes savedNodes = saveNodes(extractedKnowledge.nodes(), personaDomainSet, !suggestedDomains.isEmpty());
		List<KnowledgeEdge> savedEdges = saveEdges(savedNodes.nodesByOriginalIndex(), extractedKnowledge.edges());

		return new KnowledgeExtractionResult(
			savedNodes.nodes().stream()
				.map(KnowledgeNodeResult::from)
				.toList(),
			savedEdges.stream()
				.map(KnowledgeEdgeResult::from)
				.toList(),
			suggestedDomains
		);
	}

	private List<String> findEnabledPersonaDomains() {
		return personaRepository.findByEnabledTrueOrderByDomainNameAsc().stream()
			.map(Persona::getDomainName)
			.filter(StringUtils::hasText)
			.map(String::strip)
			.distinct()
			.toList();
	}

	private String systemPrompt(List<String> personaDomains) {
		String domainGuide = personaDomains.isEmpty()
			? "현재 사용 가능한 도메인 페르소나가 없다."
			: personaDomains.stream()
				.map(domain -> "- " + domain)
				.reduce("현재 사용 가능한 도메인 페르소나:", (left, right) -> left + "\n" + right);

		return SYSTEM_PROMPT.formatted(domainGuide);
	}

	private SavedNodes saveNodes(List<ExtractedNode> nodes, Set<String> personaDomains, boolean hasSuggestedDomains) {
		if (nodes == null || nodes.isEmpty()) {
			throw new CustomException(ErrorCode.KNOWLEDGE_EXTRACTION_FAILED, "No knowledge nodes were extracted.");
		}

		List<KnowledgeNode> savedNodes = new ArrayList<>();
		Map<Integer, KnowledgeNode> nodesByOriginalIndex = new HashMap<>();
		for (int index = 0; index < nodes.size(); index++) {
			ExtractedNode node = nodes.get(index);
			if (node == null
				|| !StringUtils.hasText(node.title())
				|| !StringUtils.hasText(node.content())
				|| !StringUtils.hasText(node.domainName())
				|| !personaDomains.contains(node.domainName().strip())) {
				continue;
			}
			KnowledgeNode savedNode = knowledgeGraphService.createNode(new CreateKnowledgeNodeCommand(
				node.title(),
				node.content(),
				node.domainName().strip(),
				StringUtils.hasText(node.nodeType()) ? node.nodeType() : "USER_INPUT"
			));
			savedNodes.add(savedNode);
			nodesByOriginalIndex.put(index, savedNode);
		}

		if (savedNodes.isEmpty() && !hasSuggestedDomains) {
			throw new CustomException(ErrorCode.KNOWLEDGE_EXTRACTION_FAILED, "No valid knowledge nodes were extracted.");
		}
		return new SavedNodes(savedNodes, nodesByOriginalIndex);
	}

	private List<KnowledgeEdge> saveEdges(Map<Integer, KnowledgeNode> savedNodes, List<ExtractedEdge> edges) {
		if (edges == null || edges.isEmpty()) {
			return List.of();
		}

		List<KnowledgeEdge> savedEdges = new ArrayList<>();
		for (ExtractedEdge edge : edges) {
			if (!isValidEdge(edge, savedNodes)) {
				continue;
			}
			KnowledgeNode sourceNode = savedNodes.get(edge.sourceNodeIndex());
			KnowledgeNode targetNode = savedNodes.get(edge.targetNodeIndex());
			savedEdges.add(knowledgeGraphService.createEdge(new CreateKnowledgeEdgeCommand(
				sourceNode.getId(),
				targetNode.getId(),
				edge.relationType(),
				edge.confidence(),
				edge.evidenceText()
			)));
		}
		return savedEdges;
	}

	private boolean isValidEdge(ExtractedEdge edge, Map<Integer, KnowledgeNode> savedNodes) {
		return edge != null
			&& edge.sourceNodeIndex() != null
			&& edge.targetNodeIndex() != null
			&& savedNodes.containsKey(edge.sourceNodeIndex())
			&& savedNodes.containsKey(edge.targetNodeIndex())
			&& !edge.sourceNodeIndex().equals(edge.targetNodeIndex())
			&& StringUtils.hasText(edge.relationType());
	}

	private List<String> suggestedDomains(List<ExtractedNode> nodes, Set<String> personaDomains) {
		if (nodes == null || nodes.isEmpty()) {
			return List.of();
		}

		Set<String> suggestedDomains = new LinkedHashSet<>();
		for (ExtractedNode node : nodes) {
			if (node == null) {
				continue;
			}
			if (StringUtils.hasText(node.suggestedDomainName())) {
				suggestedDomains.add(node.suggestedDomainName().strip());
				continue;
			}
			if (StringUtils.hasText(node.domainName()) && !personaDomains.contains(node.domainName().strip())) {
				suggestedDomains.add(node.domainName().strip());
			}
		}
		return List.copyOf(suggestedDomains);
	}

	private ExtractedKnowledge parseExtraction(String content) {
		if (!StringUtils.hasText(content)) {
			throw new CustomException(
				ErrorCode.KNOWLEDGE_EXTRACTION_FAILED,
				"Solar API returned an empty extraction result."
			);
		}
		try {
			return objectMapper.readValue(stripJsonFence(content), ExtractedKnowledge.class);
		} catch (Exception exception) {
			throw new CustomException(
				ErrorCode.KNOWLEDGE_EXTRACTION_FAILED,
				"Failed to parse knowledge extraction result.",
				exception
			);
		}
	}

	private String stripJsonFence(String content) {
		String stripped = content.strip();
		if (!stripped.startsWith("```")) {
			return stripped;
		}
		int firstNewline = stripped.indexOf('\n');
		if (firstNewline == -1) {
			return stripped;
		}
		stripped = stripped.substring(firstNewline + 1);
		int lastFence = stripped.lastIndexOf("```");
		if (lastFence != -1) {
			stripped = stripped.substring(0, lastFence);
		}
		return stripped.strip();
	}

	private void validateCommand(ExtractKnowledgeCommand command) {
		if (command == null || !StringUtils.hasText(command.text())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "text must not be blank");
		}
	}

	private record SavedNodes(
		List<KnowledgeNode> nodes,
		Map<Integer, KnowledgeNode> nodesByOriginalIndex
	) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	private record ExtractedKnowledge(
		List<ExtractedNode> nodes,
		List<ExtractedEdge> edges
	) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	private record ExtractedNode(
		String title,
		String content,
		String domainName,
		String suggestedDomainName,
		String nodeType
	) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	private record ExtractedEdge(
		Integer sourceNodeIndex,
		Integer targetNodeIndex,
		String relationType,
		BigDecimal confidence,
		String evidenceText
	) {
	}
}
