package com.soma.ai13be.discussion.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.discussion.entity.AgentDiscussion;

public interface AgentDiscussionRepository extends JpaRepository<AgentDiscussion, Long> {

	@Override
	@EntityGraph(attributePaths = "triggerNode")
	Optional<AgentDiscussion> findById(Long id);
}
