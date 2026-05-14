package com.soma.ai13be.discussion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.lang.reflect.Method;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.DiscussionStatus;
import com.soma.ai13be.discussion.repository.AgentDiscussionRepository;

class DiscussionFailureRecorderTest {

	private final AgentDiscussionRepository discussionRepository = org.mockito.Mockito.mock(AgentDiscussionRepository.class);
	private final DiscussionFailureRecorder recorder = new DiscussionFailureRecorder(discussionRepository);

	@Test
	void recordsFailureInRequiresNewTransaction() throws NoSuchMethodException {
		Method method = DiscussionFailureRecorder.class.getDeclaredMethod("recordFailure", Long.class, String.class);
		Transactional transactional = method.getAnnotation(Transactional.class);

		assertThat(transactional).isNotNull();
		assertThat(transactional.propagation()).isEqualTo(Propagation.REQUIRES_NEW);
	}

	@Test
	void marksDiscussionAsFailed() {
		AgentDiscussion discussion = AgentDiscussion.builder()
			.title("주제")
			.status(DiscussionStatus.RUNNING)
			.build();
		when(discussionRepository.findById(1L)).thenReturn(Optional.of(discussion));

		recorder.recordFailure(1L, "Solar API returned empty response");

		assertThat(discussion.getStatus()).isEqualTo(DiscussionStatus.FAILED);
		assertThat(discussion.getSummary()).isEqualTo("Solar API returned empty response");
	}
}
