package com.soma.ai13be.discussion.prompt;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class DiscussionPromptTemplatesTest {

	@Test
	void analysisPromptContainsTopicAndNodeContext() {
		String prompt = DiscussionPromptTemplates.analysisUserPrompt(
			"요즘 피곤해",
			"제목: 수면\n내용: 5시간 수면"
		);

		assertThat(prompt).contains("요즘 피곤해");
		assertThat(prompt).contains("제목: 수면");
		assertThat(prompt).contains("Round 1");
		assertThat(prompt).contains("도메인 관점");
	}

	@Test
	void rebuttalPromptContainsPreviousAnalyses() {
		String prompt = DiscussionPromptTemplates.rebuttalUserPrompt(
			"피로 분석",
			"[health Persona]\n수면 부족"
		);

		assertThat(prompt).contains("피로 분석");
		assertThat(prompt).contains("수면 부족");
		assertThat(prompt).contains("Round 2");
		assertThat(prompt).contains("반론");
	}

	@Test
	void synthesisPromptRequestsSummaryAndActionPlanSections() {
		String systemPrompt = DiscussionPromptTemplates.synthesisSystemPrompt();
		String userPrompt = DiscussionPromptTemplates.synthesisUserPrompt(
			"피로 분석",
			"[Round 1]\n분석",
			"[Round 2]\n반론"
		);

		assertThat(systemPrompt).contains("종합");
		assertThat(userPrompt).contains("요약:");
		assertThat(userPrompt).contains("실행 계획:");
		assertThat(userPrompt).contains("분석");
		assertThat(userPrompt).contains("반론");
	}
}
