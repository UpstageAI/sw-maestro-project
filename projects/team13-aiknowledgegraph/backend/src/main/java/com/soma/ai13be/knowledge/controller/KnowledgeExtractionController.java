package com.soma.ai13be.knowledge.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.soma.ai13be.common.dto.ErrorResponse;
import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.knowledge.dto.request.ExtractKnowledgeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeExtractionResult;
import com.soma.ai13be.knowledge.service.KnowledgeExtractionService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

@Tag(name = "Knowledge Extraction", description = "LLM 기반 개인 지식 추출 API")
@RestController
@RequestMapping("/api/knowledge")
@RequiredArgsConstructor
public class KnowledgeExtractionController {

	private final KnowledgeExtractionService knowledgeExtractionService;

	@Operation(
		summary = "개인 지식 추출 및 저장",
		description = "사용자의 자유 텍스트를 Solar LLM으로 분석해 지식 그래프 노드와 엣지를 추출하고 저장합니다. "
			+ "노드 도메인은 현재 활성 페르소나 도메인 중에서 매칭하며, 매칭되지 않는 도메인은 suggestedDomains로 신규 페르소나 후보를 반환합니다."
	)
	@ApiResponses({
		@ApiResponse(responseCode = "201", description = "지식 추출 및 저장 성공",
			content = @Content(schema = @Schema(implementation = KnowledgeExtractionResult.class))),
		@ApiResponse(responseCode = "400", description = "필수 요청값 누락 또는 공백",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "LLM 호출 또는 추출 결과 파싱 실패",
			content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	@PostMapping("/extractions")
	public ResponseEntity<KnowledgeExtractionResult> extractKnowledge(@RequestBody ExtractKnowledgeCommand command) {
		if (command == null || !StringUtils.hasText(command.text())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "text must not be blank");
		}
		return ResponseEntity.status(HttpStatus.CREATED)
			.body(knowledgeExtractionService.extractAndStore(command));
	}
}
