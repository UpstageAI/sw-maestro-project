package com.soma.ai13be.knowledge.repository;

import java.util.List;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import com.soma.ai13be.knowledge.entity.KnowledgeNode;

public interface KnowledgeNodeRepository extends JpaRepository<KnowledgeNode, Long> {

	List<KnowledgeNode> findAllByOrderByCreatedAtDesc();

	List<KnowledgeNode> findByDomainNameOrderByCreatedAtDesc(String domainName);

	List<KnowledgeNode> findByDomainNameOrderByCreatedAtDesc(String domainName, Pageable pageable);
}
