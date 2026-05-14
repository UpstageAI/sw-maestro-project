package com.soma.ai13be.discussion.entity;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class AgentDiscussionTest {

	@Test
	void markRunningUpdatesStatusToRunning() {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.title("title")
			.build();

		discussion.markRunning();

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.RUNNING);
	}

	@Test
	void markCompletedUpdatesStatusSummaryAndActionPlan() {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.title("title")
			.build();

		discussion.markCompleted("summary", "action plan");

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.COMPLETED);
		assertThat(discussion.getSummary()).isEqualTo("summary");
		assertThat(discussion.getActionPlan()).isEqualTo("action plan");
	}

	@Test
	void markFailedUpdatesStatusAndSummary() {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.title("title")
			.actionPlan("previous action plan")
			.build();

		discussion.markFailed("failure summary");

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.FAILED);
		assertThat(discussion.getSummary()).isEqualTo("failure summary");
		assertThat(discussion.getActionPlan()).isEqualTo("previous action plan");
	}
}
