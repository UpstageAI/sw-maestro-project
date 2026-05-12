package com.soma.ai13be.knowledge.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "개인 지식 추출 요청")
public record ExtractKnowledgeCommand(
	@Schema(
		description = "노드와 엣지로 추출할 사용자 자유 텍스트",
		example = "요즘 잠을 5시간밖에 못 자고 낮에 공부 집중이 잘 안 돼."
	)
	String text
) {
}
