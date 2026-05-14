package com.soma.ai13be.discussion.dto.request;

import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토론 생성 요청")
public record CreateDiscussionCommand(
	@Schema(description = "토론 주제", example = "요즘 피곤한 이유를 건강과 학업 관점에서 분석해줘")
	String topic,

	@Schema(description = "토론의 근거로 사용할 지식 노드 ID. 없으면 주제만으로 토론합니다.", example = "1", nullable = true)
	Long knowledgeNodeId,

	@Schema(description = "참여 페르소나 ID 목록. 비어 있으면 활성화된 모든 페르소나가 참여합니다.", example = "[1, 2]", nullable = true)
	List<Long> personaIds
) {
}
