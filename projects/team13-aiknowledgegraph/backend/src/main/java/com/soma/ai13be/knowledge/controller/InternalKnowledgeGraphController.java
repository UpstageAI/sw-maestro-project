package com.soma.ai13be.knowledge.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeEdgeCommand;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeNodeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeEdgeResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeNodeResult;
import com.soma.ai13be.knowledge.service.KnowledgeGraphService;

import io.swagger.v3.oas.annotations.Hidden;
import lombok.RequiredArgsConstructor;

@Hidden
@RestController
@RequestMapping("/internal/knowledge")
@RequiredArgsConstructor
public class InternalKnowledgeGraphController {

	private final KnowledgeGraphService knowledgeGraphService;

	@PostMapping("/nodes")
	public ResponseEntity<KnowledgeNodeResult> createNode(@RequestBody CreateKnowledgeNodeCommand command) {
		validateCreateNodeCommand(command);
		return ResponseEntity.status(HttpStatus.CREATED)
			.body(knowledgeGraphService.createNodeResult(command));
	}

	@PostMapping("/edges")
	public ResponseEntity<KnowledgeEdgeResult> createEdge(@RequestBody CreateKnowledgeEdgeCommand command) {
		validateCreateEdgeCommand(command);
		return ResponseEntity.status(HttpStatus.CREATED)
			.body(knowledgeGraphService.createEdgeResult(command));
	}

	private void validateCreateNodeCommand(CreateKnowledgeNodeCommand command) {
		if (command == null || !StringUtils.hasText(command.title())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "title must not be blank");
		}
		if (!StringUtils.hasText(command.content())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "content must not be blank");
		}
		if (!StringUtils.hasText(command.domainName())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "domainName must not be blank");
		}
		if (!StringUtils.hasText(command.nodeType())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "nodeType must not be blank");
		}
	}

	private void validateCreateEdgeCommand(CreateKnowledgeEdgeCommand command) {
		if (command == null || command.sourceNodeId() == null) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "sourceNodeId must not be null");
		}
		if (command.targetNodeId() == null) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "targetNodeId must not be null");
		}
		if (!StringUtils.hasText(command.relationType())) {
			throw new CustomException(ErrorCode.INVALID_REQUEST, "relationType must not be blank");
		}
	}
}
