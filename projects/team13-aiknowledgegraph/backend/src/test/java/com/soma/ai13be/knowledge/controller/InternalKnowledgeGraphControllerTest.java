package com.soma.ai13be.knowledge.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.common.exception.GlobalExceptionHandler;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeEdgeCommand;
import com.soma.ai13be.knowledge.dto.request.CreateKnowledgeNodeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeEdgeResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeNodeResult;
import com.soma.ai13be.knowledge.service.KnowledgeGraphService;

class InternalKnowledgeGraphControllerTest {

	private final KnowledgeGraphService knowledgeGraphService = org.mockito.Mockito.mock(KnowledgeGraphService.class);
	private final MockMvc mockMvc = MockMvcBuilders
		.standaloneSetup(new InternalKnowledgeGraphController(knowledgeGraphService))
		.setControllerAdvice(new GlobalExceptionHandler())
		.build();

	@Test
	void createsNodeThroughInternalEndpoint() throws Exception {
		when(knowledgeGraphService.createNodeResult(any(CreateKnowledgeNodeCommand.class)))
			.thenReturn(nodeResult(1L, "수면 부족", "건강"));

		mockMvc.perform(post("/internal/knowledge/nodes")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "title": "수면 부족",
					  "content": "최근 수면 시간이 줄었다.",
					  "domainName": "건강",
					  "nodeType": "USER_INPUT"
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(1))
			.andExpect(jsonPath("$.title").value("수면 부족"))
			.andExpect(jsonPath("$.analyzed").value(false));
	}

	@Test
	void createsEdgeThroughInternalEndpoint() throws Exception {
		when(knowledgeGraphService.createEdgeResult(any(CreateKnowledgeEdgeCommand.class)))
			.thenReturn(edgeResult(10L, 1L, 2L, "AFFECTS"));

		mockMvc.perform(post("/internal/knowledge/edges")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "sourceNodeId": 1,
					  "targetNodeId": 2,
					  "relationType": "AFFECTS",
					  "confidence": 0.8200,
					  "evidenceText": "수면 부족과 집중도 저하가 함께 언급됨"
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(10))
			.andExpect(jsonPath("$.relationType").value("AFFECTS"));
	}

	@Test
	void returnsNotFoundWhenCreatingInternalEdgeForUnknownNode() throws Exception {
		when(knowledgeGraphService.createEdgeResult(any(CreateKnowledgeEdgeCommand.class)))
			.thenThrow(new CustomException(ErrorCode.KNOWLEDGE_NODE_NOT_FOUND, "Knowledge node not found: 2"));

		mockMvc.perform(post("/internal/knowledge/edges")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "sourceNodeId": 1,
					  "targetNodeId": 2,
					  "relationType": "AFFECTS"
					}
					"""))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("KNOWLEDGE_NODE_NOT_FOUND"))
			.andExpect(jsonPath("$.message").value("Knowledge node not found: 2"));
	}

	private KnowledgeNodeResult nodeResult(Long id, String title, String domainName) {
		return new KnowledgeNodeResult(
			id,
			title,
			title + " content",
			domainName,
			"USER_INPUT",
			false,
			null,
			null
		);
	}

	private KnowledgeEdgeResult edgeResult(Long id, Long sourceNodeId, Long targetNodeId, String relationType) {
		return new KnowledgeEdgeResult(
			id,
			sourceNodeId,
			targetNodeId,
			relationType,
			new BigDecimal("0.8200"),
			relationType + " evidence",
			null,
			null
		);
	}
}
