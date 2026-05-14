package com.soma.ai13be.knowledge.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.soma.ai13be.common.exception.GlobalExceptionHandler;
import com.soma.ai13be.knowledge.dto.request.ExtractKnowledgeCommand;
import com.soma.ai13be.knowledge.dto.response.KnowledgeEdgeResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeExtractionResult;
import com.soma.ai13be.knowledge.dto.response.KnowledgeNodeResult;
import com.soma.ai13be.knowledge.service.KnowledgeExtractionService;

class KnowledgeExtractionControllerTest {

	private final KnowledgeExtractionService knowledgeExtractionService =
		org.mockito.Mockito.mock(KnowledgeExtractionService.class);
	private final MockMvc mockMvc = MockMvcBuilders
		.standaloneSetup(new KnowledgeExtractionController(knowledgeExtractionService))
		.setControllerAdvice(new GlobalExceptionHandler())
		.build();

	@Test
	void extractsKnowledgeFromFreeText() throws Exception {
		when(knowledgeExtractionService.extractAndStore(any(ExtractKnowledgeCommand.class)))
			.thenReturn(new KnowledgeExtractionResult(
				List.of(nodeResult(1L, "수면 부족", "건강")),
				List.of(edgeResult(10L, 1L, 2L, "AFFECTS")),
				List.of()
			));

		mockMvc.perform(post("/api/knowledge/extractions")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "text": "요즘 잠을 5시간밖에 못 자고 낮에 공부 집중이 잘 안 돼."
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.nodes[0].title").value("수면 부족"))
			.andExpect(jsonPath("$.edges[0].relationType").value("AFFECTS"));
	}

	@Test
	void rejectsBlankText() throws Exception {
		mockMvc.perform(post("/api/knowledge/extractions")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "text": " "
					}
					"""))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
			.andExpect(jsonPath("$.message").value("text must not be blank"));
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
			null,
			relationType + " evidence",
			null,
			null
		);
	}
}
