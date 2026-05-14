package com.soma.ai13be.knowledge.dto.request;

import java.math.BigDecimal;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "지식 그래프 엣지 생성 요청")
public record CreateKnowledgeEdgeCommand(
	@Schema(description = "출발 노드 ID", example = "1")
	Long sourceNodeId,

	@Schema(description = "도착 노드 ID", example = "2")
	Long targetNodeId,

	@Schema(description = "관계 유형", example = "AFFECTS")
	String relationType,

	@Schema(description = "관계 신뢰도. 생략하면 1.0으로 저장됩니다.", example = "0.8200")
	BigDecimal confidence,

	@Schema(description = "관계 판단 근거", example = "수면 부족과 집중도 저하가 같은 입력에서 함께 언급됨")
	String evidenceText
) {
}
