package com.soma.ai13be.discussion.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.soma.ai13be.common.exception.CustomException;
import com.soma.ai13be.common.exception.ErrorCode;
import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.repository.AgentDiscussionRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class DiscussionFailureRecorder {

	private final AgentDiscussionRepository discussionRepository;

	@Transactional(propagation = Propagation.REQUIRES_NEW)
	public void recordFailure(Long discussionId, String summary) {
		AgentDiscussion discussion = discussionRepository.findById(discussionId)
			.orElseThrow(() -> new CustomException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not found: " + discussionId));
		discussion.markFailed(summary);
	}
}
