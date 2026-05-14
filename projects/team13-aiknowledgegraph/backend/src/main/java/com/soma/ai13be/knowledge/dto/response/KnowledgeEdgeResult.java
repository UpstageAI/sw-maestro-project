package com.soma.ai13be.knowledge.dto.response;

import java.math.BigDecimal;
import java.time.Instant;

import com.soma.ai13be.knowledge.entity.KnowledgeEdge;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "지식 그래프 엣지 응답")
public record KnowledgeEdgeResult(
	@Schema(description = "엣지 ID", example = "10")
	Long id,

	@Schema(description = "출발 노드 ID", example = "1")
	Long sourceNodeId,

	@Schema(description = "도착 노드 ID", example = "2")
	Long targetNodeId,

	@Schema(description = "관계 유형", example = "AFFECTS")
	String relationType,

	@Schema(description = "관계 신뢰도", example = "0.8200")
	BigDecimal confidence,

	@Schema(description = "관계 판단 근거", example = "수면 부족과 집중도 저하가 같은 입력에서 함께 언급됨")
	String evidenceText,

	@Schema(description = "생성 시각")
	Instant createdAt,

	@Schema(description = "수정 시각")
	Instant updatedAt
) {

	public static KnowledgeEdgeResult from(KnowledgeEdge edge) {
		return new KnowledgeEdgeResult(
			edge.getId(),
			edge.getSourceNode().getId(),
			edge.getTargetNode().getId(),
			edge.getRelationType(),
			edge.getConfidence(),
			edge.getEvidenceText(),
			edge.getCreatedAt(),
			edge.getUpdatedAt()
		);
	}
}
