package com.soma.ai13be.knowledge.service;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeEdgeCommand;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeNodeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeEdgeResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeGraphResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeNodeResult;
import com.soma.ai13be.knowledge.entity.KnowledgeEdge;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.knowledge.repository.KnowledgeEdgeRepository;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class KnowledgeGraphService {

	private final KnowledgeNodeRepository nodeRepository;
	private final KnowledgeEdgeRepository edgeRepository;

	@Transactional
	public KnowledgeNode createNode(CreateKnowledgeNodeCommand command) {
		validateCreateNodeCommand(command);

		KnowledgeNode node = KnowledgeNode.builder()
			.title(command.title().strip())
			.content(command.content().strip())
			.domainName(command.domainName().strip())
			.nodeType(command.nodeType().strip())
			.analyzed(false)
			.build();

		return nodeRepository.save(node);
	}

	@Transactional
	public KnowledgeNodeResult createNodeResult(CreateKnowledgeNodeCommand command) {
		return KnowledgeNodeResult.from(createNode(command));
	}

	@Transactional(readOnly = true)
	public List<KnowledgeNode> findNodes(String domainName) {
		if (StringUtils.hasText(domainName)) {
			return nodeRepository.findByDomainNameOrderByCreatedAtDesc(domainName.strip());
		}
		return nodeRepository.findAllByOrderByCreatedAtDesc();
	}

	@Transactional(readOnly = true)
	public List<KnowledgeNodeResult> findNodeResults(String domainName) {
		return findNodes(domainName).stream()
			.map(KnowledgeNodeResult::from)
			.toList();
	}

	@Transactional(readOnly = true)
	public KnowledgeNode findNode(Long nodeId) {
		return nodeRepository.findById(requiredId(nodeId, "nodeId"))
			.orElseThrow(() -> new CustomException(ErrorCode.KNOWLEDGE_NODE_NOT_FOUND, "Knowledge node not found: " + nodeId));
	}

	@Transactional(readOnly = true)
	public KnowledgeNodeResult findNodeResult(Long nodeId) {
		return KnowledgeNodeResult.from(findNode(nodeId));
	}

	@Transactional
	public KnowledgeEdge createEdge(CreateKnowledgeEdgeCommand command) {
		validateCreateEdgeCommand(command);

		KnowledgeNode sourceNode = findNode(command.sourceNodeId());
		KnowledgeNode targetNode = findNode(command.targetNodeId());
		KnowledgeEdge edge = KnowledgeEdge.builder()
			.sourceNode(sourceNode)
			.targetNode(targetNode)
			.relationType(command.relationType().strip())
			.confidence(command.confidence())
			.evidenceText(stripToNull(command.evidenceText()))
			.build();

		return edgeRepository.save(edge);
	}

	@Transactional
	public KnowledgeEdgeResult createEdgeResult(CreateKnowledgeEdgeCommand command) {
		return KnowledgeEdgeResult.from(createEdge(command));
	}

	@Transactional(readOnly = true)
	public KnowledgeGraphResult findOneHopGraph(Long centerNodeId) {
		KnowledgeNode centerNode = findNode(centerNodeId);
		List<KnowledgeEdge> edges = edgeRepository.findOneHopEdges(centerNodeId);
		Set<KnowledgeNode> nodes = new LinkedHashSet<>();
		nodes.add(centerNode);
		for (KnowledgeEdge edge : edges) {
			nodes.add(edge.getSourceNode());
			nodes.add(edge.getTargetNode());
		}

		return new KnowledgeGraphResult(
			KnowledgeNodeResult.from(centerNode),
			nodes.stream()
				.map(KnowledgeNodeResult::from)
				.toList(),
			edges.stream()
				.map(KnowledgeEdgeResult::from)
				.toList()
		);
	}

	private void validateCreateNodeCommand(CreateKnowledgeNodeCommand command) {
		if (command == null) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "request body is required");
		}
		requireText(command.title(), "title");
		requireText(command.content(), "content");
		requireText(command.domainName(), "domainName");
		requireText(command.nodeType(), "nodeType");
	}

	private void validateCreateEdgeCommand(CreateKnowledgeEdgeCommand command) {
		if (command == null) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "request body is required");
		}
		requiredId(command.sourceNodeId(), "sourceNodeId");
		requiredId(command.targetNodeId(), "targetNodeId");
		requireText(command.relationType(), "relationType");
	}

	private void requireText(String value, String fieldName) {
		if (!StringUtils.hasText(value)) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, fieldName + " must not be blank");
		}
	}

	private Long requiredId(Long value, String fieldName) {
		if (value == null) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, fieldName + " must not be null");
		}
		return value;
	}

	private String stripToNull(String value) {
		if (!StringUtils.hasText(value)) {
			return null;
		}
		return value.strip();
	}
}
