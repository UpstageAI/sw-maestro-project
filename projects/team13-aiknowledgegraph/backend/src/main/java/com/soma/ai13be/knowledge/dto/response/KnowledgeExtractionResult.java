package com.soma.ai13be.knowledge.dto.response;

import java.util.List;

import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "개인 지식 추출 및 저장 결과")
public record KnowledgeExtractionResult(
	@ArraySchema(schema = @Schema(implementation = KnowledgeNodeResult.class))
	List<KnowledgeNodeResult> nodes,

	@ArraySchema(schema = @Schema(implementation = KnowledgeEdgeResult.class))
	List<KnowledgeEdgeResult> edges,

	@ArraySchema(schema = @Schema(
		description = "기존 페르소나 도메인에 매칭되지 않아 신규 페르소나 후보로 제안된 도메인 이름",
		example = "업무"
	))
	List<String> suggestedDomains
) {
	public KnowledgeExtractionResult {
		nodes = List.copyOf(nodes == null ? List.of() : nodes);
		edges = List.copyOf(edges == null ? List.of() : edges);
		suggestedDomains = List.copyOf(suggestedDomains == null ? List.of() : suggestedDomains);
	}
}
