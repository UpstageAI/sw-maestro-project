package com.soma.ai13be.knowledge.entity;

import java.math.BigDecimal;

import com.soma.ai13be.common.entity.BaseTimeEntity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 지식 노드 사이의 방향성 있는 관계를 저장한다.
 * 양 끝 노드만으로도 사용자를 추론할 수 있지만, 사용자 범위 그래프 조회를 단순하게 만들기 위해 owner를 별도로 둔다.
 */
@Getter
@Entity
@Table(name = "knowledge_edges")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class KnowledgeEdge extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "source_node_id", nullable = false)
	private KnowledgeNode sourceNode;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "target_node_id", nullable = false)
	private KnowledgeNode targetNode;

	// LLM 구조화 출력 스키마와 맞춘 값만 저장한다. 예: CAUSES, RELATED_TO, IMPROVES.
	@Column(nullable = false, length = 120)
	private String relationType;

	// 관계 추출 결과를 바로 확정하지 않고, 낮은 신뢰도 결과를 필터링할 수 있게 둔다.
	@Column(nullable = false, precision = 5, scale = 4)
	private BigDecimal confidence;

	// 사용자가 그래프 연결의 근거를 확인할 수 있도록 LLM 판단 근거를 보관한다.
	@Column(columnDefinition = "TEXT")
	private String evidenceText;

	@Builder
	private KnowledgeEdge(
		KnowledgeNode sourceNode,
		KnowledgeNode targetNode,
		String relationType,
		BigDecimal confidence,
		String evidenceText
	) {
		this.sourceNode = sourceNode;
		this.targetNode = targetNode;
		this.relationType = relationType;
		this.confidence = confidence == null ? BigDecimal.ONE : confidence;
		this.evidenceText = evidenceText;
	}
}
