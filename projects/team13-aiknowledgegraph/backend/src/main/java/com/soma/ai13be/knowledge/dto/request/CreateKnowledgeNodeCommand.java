package com.soma.ai13be.knowledge.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "지식 그래프 노드 생성 요청")
public record CreateKnowledgeNodeCommand(
	@Schema(description = "노드 제목", example = "수면 부족")
	String title,

	@Schema(description = "노드 본문", example = "최근 3일간 수면 시간이 5시간 이하로 줄었다.")
	String content,

	@Schema(description = "노드의 주 도메인", example = "건강")
	String domainName,

	@Schema(description = "노드 유형", example = "USER_INPUT")
	String nodeType
) {
}
