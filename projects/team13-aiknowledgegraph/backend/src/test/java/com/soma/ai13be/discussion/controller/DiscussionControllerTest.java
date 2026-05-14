package com.soma.ai13be.discussion.controller;

import static org.hamcrest.Matchers.nullValue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.common.exception.GlobalExceptionHandler;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;
import com.soma.ai13be.discussion.entity.DiscussionRound;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.discussion.service.DiscussionService;
import com.soma.ai13be.knowledge.entity.KnowledgeNode;
import com.soma.ai13be.persona.entity.Persona;

class DiscussionControllerTest {

	private final DiscussionService discussionService = org.mockito.Mockito.mock(DiscussionService.class);
	private final MockMvc mockMvc = MockMvcBuilders.standaloneSetup(new DiscussionController(discussionService))
		.setControllerAdvice(new GlobalExceptionHandler())
		.build();

	@Test
	void createsDiscussion() throws Exception {
		AgentDiscussion discussion = completedDiscussion(node());
		when(discussionService.createDiscussion("피로 원인 분석", 1L, List.of(1L, 2L))).thenReturn(discussion);
		when(discussionService.getMessages(1L)).thenReturn(List.of(
			message(discussion, persona("health"), DiscussionRound.ANALYSIS, "건강 분석")
		));

		mockMvc.perform(post("/api/discussions")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "topic": "피로 원인 분석",
					  "knowledgeNodeId": 1,
					  "personaIds": [1, 2]
					}
					"""))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(1))
			.andExpect(jsonPath("$.triggerNodeId").value(1))
			.andExpect(jsonPath("$.status").value("COMPLETED"))
			.andExpect(jsonPath("$.title").value("피로 원인 분석"))
			.andExpect(jsonPath("$.summary").value("최종 요약"))
			.andExpect(jsonPath("$.actionPlan").value("1. 실행"))
			.andExpect(jsonPath("$.messages[0].personaId").value(1))
			.andExpect(jsonPath("$.messages[0].personaName").value("health Persona"))
			.andExpect(jsonPath("$.messages[0].round").value("ANALYSIS"))
			.andExpect(jsonPath("$.messages[0].content").value("건강 분석"));
	}

	@Test
	void returnsBadRequestWhenTopicIsBlank() throws Exception {
		when(discussionService.createDiscussion(any(), any(), any()))
			.thenThrow(new CustomException(ErrorCode.INVALID_REQUEST, "topic must not be blank"));

		mockMvc.perform(post("/api/discussions")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "topic": " "
					}
					"""))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
			.andExpect(jsonPath("$.message").value("topic must not be blank"));
	}

	@Test
	void returnsNotFoundWhenDiscussionDoesNotExist() throws Exception {
		when(discussionService.getDiscussion(99L))
			.thenThrow(new CustomException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not found: 99"));

		mockMvc.perform(get("/api/discussions/{discussionId}", 99L))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("DISCUSSION_NOT_FOUND"))
			.andExpect(jsonPath("$.message").value("Discussion not found: 99"));
	}

	@Test
	void returnsDiscussionDetail() throws Exception {
		AgentDiscussion discussion = completedDiscussion(node());
		when(discussionService.getDiscussion(1L)).thenReturn(discussion);
		when(discussionService.getMessages(discussion)).thenReturn(List.of(
			message(discussion, persona("study"), DiscussionRound.REBUTTAL, "학업 반론")
		));

		mockMvc.perform(get("/api/discussions/{discussionId}", 1L))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.id").value(1))
			.andExpect(jsonPath("$.triggerNodeId").value(1))
			.andExpect(jsonPath("$.status").value("COMPLETED"))
			.andExpect(jsonPath("$.messages[0].personaName").value("study Persona"))
			.andExpect(jsonPath("$.messages[0].round").value("REBUTTAL"))
			.andExpect(jsonPath("$.messages[0].content").value("학업 반론"));
	}

	@Test
	void returnsDiscussionMessages() throws Exception {
		AgentDiscussion discussion = completedDiscussion(null);
		when(discussionService.getMessages(1L)).thenReturn(List.of(
			message(discussion, persona("health"), DiscussionRound.ANALYSIS, "건강 분석"),
			message(discussion, null, DiscussionRound.SYNTHESIS, "종합")
		));

		mockMvc.perform(get("/api/discussions/{discussionId}/messages", 1L))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[0].personaId").value(1))
			.andExpect(jsonPath("$[0].personaName").value("health Persona"))
			.andExpect(jsonPath("$[0].round").value("ANALYSIS"))
			.andExpect(jsonPath("$[1].personaId").value(nullValue()))
			.andExpect(jsonPath("$[1].personaName").value(nullValue()))
			.andExpect(jsonPath("$[1].round").value("SYNTHESIS"))
			.andExpect(jsonPath("$[1].content").value("종합"));
	}

	private AgentDiscussion completedDiscussion(KnowledgeNode node) {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.triggerNode(node)
			.status(DiscussionStatus.COMPLETED)
			.title("피로 원인 분석")
			.summary("최종 요약")
			.actionPlan("1. 실행")
			.build();
		ReflectionTestUtils.setField(discussion, "id", 1L);
		return discussion;
	}

	private AgentDiscussionMessage message(AgentDiscussion discussion, Persona persona, DiscussionRound round, String content) {
		AgentDiscussionMessage message = AgentDiscussionMessage.builder()
			.discussion(discussion)
			.persona(persona)
			.round(round)
			.content(content)
			.build();
		ReflectionTestUtils.setField(message, "id", 1L);
		return message;
	}

	private Persona persona(String domain) {
		Persona persona = Persona.builder()
			.domainName(domain)
			.name(domain + " Persona")
			.systemPrompt(domain + " prompt")
			.builtIn(false)
			.enabled(true)
			.build();
		long id = switch (domain) {
			case "health" -> 1L;
			case "study" -> 2L;
			default -> 3L;
		};
		ReflectionTestUtils.setField(persona, "id", id);
		return persona;
	}

	private KnowledgeNode node() {
		KnowledgeNode node = KnowledgeNode.builder()
			.title("피로 기록")
			.content("최근 피곤함")
			.domainName("health")
			.nodeType("symptom")
			.analyzed(true)
			.build();
		ReflectionTestUtils.setField(node, "id", 1L);
		return node;
	}
}
