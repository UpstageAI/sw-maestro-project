package com.soma.ai13be.knowledge.dto.response;

import java.time.Instant;

import com.soma.ai13be.knowledge.entity.KnowledgeNode;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "지식 그래프 노드 응답")
public record KnowledgeNodeResult(
	@Schema(description = "노드 ID", example = "1")
	Long id,

	@Schema(description = "노드 제목", example = "수면 부족")
	String title,

	@Schema(description = "노드 본문", example = "최근 3일간 수면 시간이 5시간 이하로 줄었다.")
	String content,

	@Schema(description = "노드의 주 도메인", example = "건강")
	String domainName,

	@Schema(description = "노드 유형", example = "USER_INPUT")
	String nodeType,

	@Schema(description = "노드 관리 에이전트 처리 완료 여부", example = "false")
	boolean analyzed,

	@Schema(description = "생성 시각")
	Instant createdAt,

	@Schema(description = "수정 시각")
	Instant updatedAt
) {

	public static KnowledgeNodeResult from(KnowledgeNode node) {
		return new KnowledgeNodeResult(
			node.getId(),
			node.getTitle(),
			node.getContent(),
			node.getDomainName(),
			node.getNodeType(),
			node.isAnalyzed(),
			node.getCreatedAt(),
			node.getUpdatedAt()
		);
	}
}
