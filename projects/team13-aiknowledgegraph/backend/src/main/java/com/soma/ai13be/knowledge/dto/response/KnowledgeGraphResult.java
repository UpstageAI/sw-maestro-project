package com.soma.ai13be.knowledge.dto.response;

import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "특정 노드 주변 1-hop 지식 그래프 응답")
public record KnowledgeGraphResult(
	@Schema(description = "조회 기준이 되는 중심 노드")
	KnowledgeNodeResult centerNode,

	@Schema(description = "중심 노드와 1-hop으로 연결된 노드 목록. 중심 노드도 포함합니다.")
	List<KnowledgeNodeResult> nodes,

	@Schema(description = "중심 노드와 직접 연결된 엣지 목록")
	List<KnowledgeEdgeResult> edges
) {
}
