package com.soma.ai13be.discussion.repository;

import java.util.List;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.discussion.entity.AgentDiscussion;
import com.soma.ai13be.discussion.entity.AgentDiscussionMessage;

public interface AgentDiscussionMessageRepository extends JpaRepository<AgentDiscussionMessage, Long> {

	@EntityGraph(attributePaths = "persona")
	List<AgentDiscussionMessage> findByDiscussionOrderByCreatedAtAscIdAsc(AgentDiscussion discussion);
}
