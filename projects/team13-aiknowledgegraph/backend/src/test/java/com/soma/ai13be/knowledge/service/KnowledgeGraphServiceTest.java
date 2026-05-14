package com.soma.ai13be.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeEdgeCommand;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeNodeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeGraphResult;
import com.soma.ai13be.knowledge.entity.KnowledgeEdge;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.knowledge.repository.KnowledgeEdgeRepository;
import com.soma.ai13be.knowledge.repository.KnowledgeNodeRepository;

class KnowledgeGraphServiceTest {

	private final KnowledgeNodeRepository nodeRepository = org.mockito.Mockito.mock(KnowledgeNodeRepository.class);
	private final KnowledgeEdgeRepository edgeRepository = org.mockito.Mockito.mock(KnowledgeEdgeRepository.class);
	private final KnowledgeGraphService service = new KnowledgeGraphService(nodeRepository, edgeRepository);

	@Test
	void createsNodeAsNotAnalyzed() {
		when(nodeRepository.save(any(KnowledgeNode.class)))
			.thenAnswer(invocation -> invocation.getArgument(0));

		KnowledgeNode node = service.createNode(new CreateKnowledgeNodeCommand(
			"수면 부족",
			"최근 수면 시간이 줄었다.",
			"건강",
			"USER_INPUT"
		));

		assertThat(node.getTitle()).isEqualTo("수면 부족");
		assertThat(node.getContent()).isEqualTo("최근 수면 시간이 줄었다.");
		assertThat(node.getDomainName()).isEqualTo("건강");
		assertThat(node.getNodeType()).isEqualTo("USER_INPUT");
		assertThat(node.isAnalyzed()).isFalse();
	}

	@Test
	void rejectsBlankNodeTitle() {
		assertThatThrownBy(() -> service.createNode(new CreateKnowledgeNodeCommand(
			" ",
			"content",
			"건강",
			"USER_INPUT"
		)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_REQUEST)
			.hasMessageContaining("title");
	}

	@Test
	void createsEdgeBetweenExistingNodes() {
		KnowledgeNode source = node("수면 부족", "건강");
		KnowledgeNode target = node("집중도 저하", "학습");
		when(nodeRepository.findById(1L)).thenReturn(Optional.of(source));
		when(nodeRepository.findById(2L)).thenReturn(Optional.of(target));
		when(edgeRepository.save(any(KnowledgeEdge.class)))
			.thenAnswer(invocation -> invocation.getArgument(0));

		KnowledgeEdge edge = service.createEdge(new CreateKnowledgeEdgeCommand(
			1L,
			2L,
			"AFFECTS",
			new BigDecimal("0.8200"),
			"수면 부족과 집중도 저하가 함께 언급됨"
		));

		assertThat(edge.getSourceNode()).isSameAs(source);
		assertThat(edge.getTargetNode()).isSameAs(target);
		assertThat(edge.getRelationType()).isEqualTo("AFFECTS");
		assertThat(edge.getConfidence()).isEqualByComparingTo("0.8200");
		assertThat(edge.getEvidenceText()).isEqualTo("수면 부족과 집중도 저하가 함께 언급됨");
	}

	@Test
	void rejectsEdgeWhenTargetNodeDoesNotExist() {
		when(nodeRepository.findById(1L)).thenReturn(Optional.of(node("수면 부족", "건강")));
		when(nodeRepository.findById(2L)).thenReturn(Optional.empty());

		assertThatThrownBy(() -> service.createEdge(new CreateKnowledgeEdgeCommand(
			1L,
			2L,
			"AFFECTS",
			BigDecimal.ONE,
			null
		)))
			.isInstanceOf(CustomException.class)
			.hasFieldOrPropertyWithValue("errorCode", ErrorCode.KNOWLEDGE_NODE_NOT_FOUND)
			.hasMessageContaining("2");
	}

	@Test
	void findsOneHopGraphAroundCenterNode() {
		KnowledgeNode center = node("수면 부족", "건강");
		KnowledgeNode related = node("집중도 저하", "학습");
		KnowledgeEdge outgoing = edge(center, related, "AFFECTS");
		KnowledgeEdge incoming = edge(related, center, "RELATED_TO");
		when(nodeRepository.findById(1L)).thenReturn(Optional.of(center));
		when(edgeRepository.findOneHopEdges(1L)).thenReturn(List.of(outgoing, incoming));

		KnowledgeGraphResult graph = service.findOneHopGraph(1L);

		assertThat(graph.centerNode().title()).isEqualTo("수면 부족");
		assertThat(graph.nodes())
			.extracting(node -> node.title())
			.containsExactly("수면 부족", "집중도 저하");
		assertThat(graph.edges())
			.extracting(edge -> edge.relationType())
			.containsExactly("AFFECTS", "RELATED_TO");
		verify(edgeRepository).findOneHopEdges(1L);
	}

	@Test
	void findsNodesByDomainNameWhenProvided() {
		when(nodeRepository.findByDomainNameOrderByCreatedAtDesc("건강"))
			.thenReturn(List.of(node("수면 부족", "건강")));

		List<KnowledgeNode> nodes = service.findNodes("건강");

		assertThat(nodes).hasSize(1);
		ArgumentCaptor<String> captor = ArgumentCaptor.forClass(String.class);
		verify(nodeRepository).findByDomainNameOrderByCreatedAtDesc(captor.capture());
		assertThat(captor.getValue()).isEqualTo("건강");
	}

	private KnowledgeNode node(String title, String domainName) {
		return KnowledgeNode.builder()
			.title(title)
			.content(title + " content")
			.domainName(domainName)
			.nodeType("USER_INPUT")
			.analyzed(false)
			.build();
	}

	private KnowledgeEdge edge(KnowledgeNode source, KnowledgeNode target, String relationType) {
		return KnowledgeEdge.builder()
			.sourceNode(source)
			.targetNode(target)
			.relationType(relationType)
			.confidence(BigDecimal.ONE)
			.evidenceText(relationType + " evidence")
			.build();
	}
}
