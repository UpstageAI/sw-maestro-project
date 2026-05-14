package com.soma.ai13be.discussion.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.soma.ai13be.common.dto.ErrorResponse;
import com.soma.ai13be.discussion.dto.request.CreateDiscussionCommand;
import com.soma.ai13be.discussion.dto.response.DiscussionMessageResult;
import com.soma.ai13be.discussion.dto.response.DiscussionResult;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.service.DiscussionService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

@Tag(name = "Discussion", description = "멀티 페르소나 토론 API")
@RestController
@RequestMapping("/api/discussions")
@RequiredArgsConstructor
public class DiscussionController {

	private final DiscussionService discussionService;

	@Operation(
		summary = "토론 생성 및 실행",
		description = "토론 주제, 선택 지식 노드, 선택 페르소나 목록을 받아 3라운드 토론을 동기식으로 실행합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "201", description = "토론 실행 성공",
			content = @Content(schema = @Schema(implementation = DiscussionResult.class))),
		@ApiResponse(responseCode = "400", description = "topic이 공백이거나 참여 페르소나가 2명 미만",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "404", description = "지식 노드 또는 페르소나를 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "Solar API 응답 오류",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping
	public ResponseEntity<DiscussionResult> createDiscussion(@RequestBody CreateDiscussionCommand command) {
		AgentDiscussion discussion = discussionService.createDiscussion(
			command.topic(),
			command.knowledgeNodeId(),
			command.personaIds()
		);
		List<AgentDiscussionMessage> messages = discussionService.getMessages(discussion.getId());
		return ResponseEntity.status(HttpStatus.CREATED).body(DiscussionResult.from(discussion, messages));
	}

	@Operation(
		summary = "토론 상세 조회",
		description = "토론의 최종 요약, 실행 계획, 라운드별 메시지를 조회합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "토론 조회 성공",
			content = @Content(schema = @Schema(implementation = DiscussionResult.class))),
		@ApiResponse(responseCode = "404", description = "토론을 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@GetMapping("/{discussionId}")
	public ResponseEntity<DiscussionResult> getDiscussion(
		@Parameter(description = "토론 ID", example = "1")
		@PathVariable Long discussionId
	) {
		AgentDiscussion discussion = discussionService.getDiscussion(discussionId);
		List<AgentDiscussionMessage> messages = discussionService.getMessages(discussion);
		return ResponseEntity.ok(DiscussionResult.from(discussion, messages));
	}

	@Operation(
		summary = "토론 메시지 조회",
		description = "해당 토론의 라운드별 메시지를 생성 순서대로 조회합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "200", description = "토론 메시지 조회 성공",
			content = @Content(array = @ArraySchema(schema = @Schema(implementation = DiscussionMessageResult.class)))),
		@ApiResponse(responseCode = "404", description = "토론을 찾을 수 없음",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@GetMapping("/{discussionId}/messages")
	public ResponseEntity<List<DiscussionMessageResult>> getMessages(
		@Parameter(description = "토론 ID", example = "1")
		@PathVariable Long discussionId
	) {
		List<DiscussionMessageResult> messages = discussionService.getMessages(discussionId).stream()
			.map(DiscussionMessageResult::from)
			.toList();
		return ResponseEntity.ok(messages);
	}
}
