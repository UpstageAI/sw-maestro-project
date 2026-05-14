package com.soma.ai13be.discussion.dto.response;

import java.time.Instant;
import java.util.List;

import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토론 상세 응답")
public record DiscussionResult(
	@Schema(description = "토론 ID", example = "1")
	Long id,

	@Schema(description = "토론을 트리거한 지식 노드 ID. 주제만으로 시작한 토론은 null입니다.", example = "1", nullable = true)
	Long triggerNodeId,

	@Schema(description = "토론 상태", example = "COMPLETED")
	String status,

	@Schema(description = "토론 제목", example = "요즘 피곤한 이유 분석")
	String title,

	@Schema(description = "최종 요약", example = "수면 부족과 학업 부담이 함께 작용했습니다.")
	String summary,

	@Schema(description = "실행 계획", example = "1. 수면 시간을 기록합니다.")
	String actionPlan,

	@Schema(description = "생성 시각", example = "2026-05-08T09:00:00Z")
	Instant createdAt,

	@Schema(description = "라운드별 메시지",
		example = "[{\"id\":10,\"personaId\":1,\"personaName\":\"health Persona\",\"round\":\"ANALYSIS\",\"content\":\"건강 관점 분석입니다.\",\"createdAt\":\"2026-05-08T09:00:00Z\"}]")
	List<DiscussionMessageResult> messages
) {

	public static DiscussionResult from(AgentDiscussion discussion, List<AgentDiscussionMessage> messages) {
		return new DiscussionResult(
			discussion.getId(),
			discussion.getTriggerNode() != null ? discussion.getTriggerNode().getId() : null,
			discussion.getStatus().name(),
			discussion.getTitle(),
			discussion.getSummary(),
			discussion.getActionPlan(),
			discussion.getCreatedAt(),
			messages.stream().map(DiscussionMessageResult::from).toList()
		);
	}
}
